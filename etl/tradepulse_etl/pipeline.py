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
        return USCensusSource(key=census_key())
    if kind == "eurostat":
        return EurostatSource()          # keyless (EU); EUR->USD via ECB FX
    if kind == "hmrc":
        return UKHmrcSource()            # keyless (UK); GBP->USD via ECB FX
    if kind == "baci":
        return BaciSource()             # local bulk file (no API throttle); global history
    raise ValueError(f"unknown source: {kind!r} (use fixture|comtrade|census|eurostat|hmrc|baci)")


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


def run_multi(sources: list[TradeSource], conn, *, raw_dir: Path = RAW_DIR, today=None) -> int:
    """Pull every source, transform each (tagged with its own name), then MERGE to one row per cell
    (national authority > freshness > priority — see merge.py) before the upsert. Never sums sources.
    INCREMENTAL: (hs6, period) pairs already stored + final are skipped, so a re-run only fetches the
    revisable recent window (not the whole history again)."""
    reporters = [m["reporter"] for m in config.MARKETS.values()]
    skip = frozenset(_final_stored(conn, today or date.today()))
    raw_by: dict[str, list] = {s.name: [] for s in sources}

    # BULK sources (a local file covering every product) are pulled ONCE for all products — re-parsing
    # a 22M-row file per product would take hours. API sources stay per-product (that's how they fetch).
    bulk_by_hs: dict[str, list] = {}
    api_sources = []
    for source in sources:
        if getattr(source, "bulk", False):
            raw = source.pull(config.COVERED_HS, reporters, None, skip=skip)
            raw_by[source.name] += raw
            for row in transform_all(raw, source.name):
                bulk_by_hs.setdefault(row["hs6"], []).append(row)
        else:
            api_sources.append(source)

    total = 0
    # Per PRODUCT: combine the bulk rows with each API source, merge, upsert — so a slow/throttled/
    # killed run keeps the products already finished, and cells still merge correctly (a cell lives
    # within one product, so merging per product == merging globally).
    for hs in config.COVERED_HS:
        rows: list[dict] = list(bulk_by_hs.get(hs, ()))
        for source in api_sources:
            raw = source.pull([hs], reporters, None, skip=skip)
            raw_by[source.name] += raw
            rows += transform_all(raw, source.name)
        if rows:
            total += upsert_trade_flows(conn, merge_flows(rows))
    for name, raw in raw_by.items():
        _store_raw(raw, name, raw_dir)
    return total


def _final_stored(conn, today) -> set:
    """(hs6, period) pairs already in trade_flows AND final (outside the revision window)."""
    rows = conn.execute("SELECT DISTINCT hs6, period FROM trade_flows").fetchall()
    return {(hs6, period) for hs6, period in rows if config.is_final(period, today)}
