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
from .sources import ComtradeSource, FixtureSource, TradeSource
from .transform import transform_all

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


def get_source(kind: str, period: str | None = None) -> TradeSource:
    if kind == "fixture":
        return FixtureSource()
    if kind == "comtrade":
        return ComtradeSource()   # pulls recent months, aggregates to quarters
    raise ValueError(f"unknown source: {kind!r} (use 'fixture' or 'comtrade')")


def _store_raw(records: list[dict], source_name: str, raw_dir: Path) -> Path:
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f"{source_name}.json"
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def run(source: TradeSource, conn, *, raw_dir: Path = RAW_DIR) -> int:
    reporters = [m["reporter"] for m in config.MARKETS.values()]
    # partners=None -> pull ALL partners (World + every exporter) so the drill-down has sourcing data.
    raw = source.pull(config.HS_PELLETS, reporters, None)
    _store_raw(raw, source.name, raw_dir)
    rows = transform_all(raw, source.name)
    return upsert_trade_flows(conn, rows)
