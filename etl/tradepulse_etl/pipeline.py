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
from pathlib import Path

from . import config
from .db import upsert_trade_flows
from .merge import merge_flows
from .sources import ComtradeSource, FixtureSource, TradeSource, USCensusSource
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
    raise ValueError(f"unknown source: {kind!r} (use 'fixture', 'comtrade' or 'census')")


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


def run_multi(sources: list[TradeSource], conn, *, raw_dir: Path = RAW_DIR) -> int:
    """Pull every source, transform each (tagged with its own name), then MERGE to one row per cell
    (national authority > freshness > priority — see merge.py) before the upsert. Never sums sources."""
    reporters = [m["reporter"] for m in config.MARKETS.values()]
    all_rows: list[dict] = []
    for source in sources:
        # All covered products; partners=None so the source decides (authenticated = all countries).
        raw = source.pull(config.COVERED_HS, reporters, None)
        _store_raw(raw, source.name, raw_dir)
        all_rows += transform_all(raw, source.name)
    merged = merge_flows(all_rows)
    return upsert_trade_flows(conn, merged)
