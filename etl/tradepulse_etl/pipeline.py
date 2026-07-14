"""
pipeline.py — orchestrate one ETL run: pull -> store raw -> transform -> upsert trade_flows.
@context  The batch entry the cron/CLI calls (plan §10.3). Raw is persisted BEFORE transform so
          every derived row is reproducible from disk (plan §10.4).
@done     get_source(); run() writes raw JSON then upserts trade_flows; returns row count.
@todo     Add trailing-4-quarter re-pull for revisions when the live source lands (plan §6.4).
@limits   Orchestration only — logic lives in transform/signals. Deterministic given a source.
@affects  Uses sources + transform + db. Invoked by __main__.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from . import config
from .db import upsert_trade_flows
from .merge import merge_flows
from .sources import (BaciSource, ComtradeSource, EurostatSource, FixtureSource,
                      TradeSource, UKHmrcSource, USCensusSource)
from .transform import transform_all

PRODUCTS_PER_UPSERT = 80      # how much work a killed run can lose
RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


def get_source(kind: str, period: str | None = None, freqs: tuple[str, ...] = ("A",)) -> TradeSource:
    if kind == "fixture":
        return FixtureSource()
    if kind == "comtrade":
        from .settings import comtrade_key
        key = comtrade_key()
        qhs = config.QUARTERLY_HS if "Q" in freqs else None
        print(f"[comtrade] mode={'authenticated' if key else 'keyless annual World-only'} freqs={freqs}")
        return ComtradeSource(key=key, freqs=freqs, quarterly_hs=qhs)
    if kind == "census":
        from .settings import census_key
        return USCensusSource(key=census_key(), freqs=freqs)
    if kind == "eurostat":
        return EurostatSource(freqs=freqs)   # keyless EU (DS-059341); EUR->USD via ECB FX
    if kind == "hmrc":
        return UKHmrcSource()            # keyless (UK); GBP->USD via ECB FX
    if kind == "kcs":
        from .settings import kcs_service_key
        return KcsSource(key=kcs_service_key(), freqs=freqs)   # Korea national primary (reporter 410)
    if kind == "baci":
        return BaciSource()             # local bulk file (no API throttle); global history
    if kind in ("mirror", "comtrade-mirror"):
        from .settings import comtrade_key
        from .sources.comtrade import ComtradeMirrorSource
        return ComtradeMirrorSource(key=comtrade_key())   # recent exports rebuilt from partner reports
    raise ValueError(f"unknown source: {kind!r} (use fixture|comtrade|mirror|census|eurostat|hmrc|baci)")


def get_sources(kinds: list[str], freqs: tuple[str, ...] = ("A",)) -> list[TradeSource]:
    return [get_source(k.strip(), freqs=freqs) for k in kinds if k.strip()]


def _store_raw(records: list[dict], source_name: str, raw_dir: Path) -> Path:
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f"{source_name}.json"
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def run(source: TradeSource, conn, *, raw_dir: Path = RAW_DIR) -> int:
    """Single source: pull -> store raw -> transform -> merge -> upsert."""
    return run_multi([source], conn, raw_dir=raw_dir)


def run_multi(sources: list[TradeSource], conn, *, raw_dir: Path = RAW_DIR, today=None,
              hs_codes: list[str] | None = None) -> int:
    """Pull every source, transform each (tagged with its own name), then MERGE to one row per cell
    (national authority > freshness > priority — see merge.py) before the upsert. Never sums sources.
    INCREMENTAL: (hs6, period) pairs already stored + final are skipped, so a re-run only fetches the
    revisable recent window (not the whole history again). `hs_codes` restricts the pull to a subset
    (lazy per-product build); defaults to the whole catalogue."""
    codes = hs_codes or config.COVERED_HS
    reporters = [m["reporter"] for m in config.MARKETS.values()]
    skip = frozenset(_final_stored(conn, today or date.today(), codes))
    raw_by: dict[str, list] = {s.name: [] for s in sources}

    # BULK sources (a local file covering every product) are pulled ONCE for all products — re-parsing
    # a 22M-row file per product would take hours. API sources stay per-product (that's how they fetch).
    bulk_by_hs: dict[str, list] = {}
    api_sources = []
    for source in sources:
        if getattr(source, "bulk", False):
            raw = source.pull(codes, reporters, None, skip=skip)
            raw_by[source.name] += raw
            for row in transform_all(raw, source.name):
                bulk_by_hs.setdefault(row["hs6"], []).append(row)
        else:
            api_sources.append(source)

    # A BATCHED source takes many products in ONE request (Comtrade's cmdCode is a comma-separated
    # list). Asking it product-by-product wastes that entirely: 1,240 products x 2 revisable years is
    # 2,480 calls one-at-a-time versus ~250 batched — the difference between ~17 hours and under an
    # hour. Non-batched API sources (census/eurostat/hmrc) still go one product per call.
    batched = [s for s in api_sources if getattr(s, "batched", False)]
    per_product = [s for s in api_sources if not getattr(s, "batched", False)]

    total = 0
    # Work in CHUNKS of products and upsert each chunk: a slow/throttled/killed run keeps every chunk
    # it finished. Merging stays correct because a cell lives within one product, so merging
    # per product == merging globally.
    for chunk in _chunks(codes, PRODUCTS_PER_UPSERT):
        rows_by_hs: dict[str, list] = {hs: list(bulk_by_hs.get(hs, ())) for hs in chunk}
        for source in batched:
            raw = source.pull(chunk, reporters, None, skip=skip)
            raw_by[source.name] += raw
            for row in transform_all(raw, source.name):
                rows_by_hs.setdefault(row["hs6"], []).append(row)
        for hs in chunk:
            for source in per_product:
                raw = source.pull([hs], reporters, None, skip=skip)
                raw_by[source.name] += raw
                rows_by_hs[hs] += transform_all(raw, source.name)
            if rows_by_hs.get(hs):
                total += upsert_trade_flows(conn, merge_flows(rows_by_hs[hs]))
    for name, raw in raw_by.items():
        _store_raw(raw, name, raw_dir)
    return total


def _chunks(items: list, n: int) -> list[list]:
    return [items[i:i + n] for i in range(0, len(items), n)]


def _final_stored(conn, today, hs_codes: list[str] | None = None) -> set:
    """(hs6, period) pairs already in trade_flows AND final (outside the revision window). Scoped to
    hs_codes when given (a lazy per-product build must not scan the whole ~2M-row table)."""
    if hs_codes and len(hs_codes) <= 50:
        q = ",".join("?" * len(hs_codes))
        rows = conn.execute(f"SELECT DISTINCT hs6, period FROM trade_flows WHERE hs6 IN ({q})", hs_codes)
    else:
        rows = conn.execute("SELECT DISTINCT hs6, period FROM trade_flows")
    return {(hs6, period) for hs6, period in rows if config.is_final(period, today)}
