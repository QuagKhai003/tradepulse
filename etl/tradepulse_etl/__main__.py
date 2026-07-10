"""
__main__.py — CLI entry: `python -m tradepulse_etl [--source fixture|comtrade]`.
@context  One command runs the whole batch (plan §10.3): pull -> trade_flows -> signals ->
          web snapshot. That single command is what makes the localhost app show data.
@done     Parses args; runs pipeline; computes + upserts signals; writes the web snapshot.
@limits   Thin CLI wrapper; logic lives in pipeline/signals/export. Supplies the clock (computed_at).
@affects  Calls pipeline.run + signals.compute_signals + export.write_snapshot.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .alerts import rollup_locked_clicks, signal_alerts
from .db import DEFAULT_DB, connect, count_trade_flows, fetch_flows, fetch_signals, upsert_signals
from .export import DEFAULT_SNAPSHOT, build_snapshot, write_snapshot
from .pipeline import get_source, run
from .signals import compute_signals

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def main() -> None:
    ap = argparse.ArgumentParser(prog="tradepulse_etl", description="Build TradePulse Layer-1 data.")
    ap.add_argument("--source", default="fixture", choices=["fixture", "comtrade"],
                    help="data source (default: fixture — offline sample data)")
    ap.add_argument("--period", default="2025", help="period for the comtrade source")
    ap.add_argument("--db", default=str(DEFAULT_DB), help="SQLite path")
    ap.add_argument("--snapshot", default=str(DEFAULT_SNAPSHOT), help="web snapshot output path")
    args = ap.parse_args()

    now_iso = datetime.now(timezone.utc).isoformat()
    conn = connect(args.db)

    n = run(get_source(args.source, period=args.period), conn)

    prev = fetch_signals(conn)                       # state before this run (for band crossings)
    sigs = compute_signals(fetch_flows(conn), now_iso)
    upsert_signals(conn, sigs)

    alerts = signal_alerts(prev, sigs)               # skips first load (prev empty)
    if alerts:
        _append_alerts(alerts, now_iso)

    snap = build_snapshot(conn, generated_at=now_iso)
    out = write_snapshot(snap, args.snapshot)

    print(f"[tradepulse] flows={count_trade_flows(conn)} (upserted {n}) signals={len(sigs)} "
          f"feed={len(snap['feed'])} alerts={len(alerts)} snapshot={out}")
    _print_rollup()


def _append_alerts(alerts: list[dict], now_iso: str) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with (DATA_DIR / "alerts.ndjson").open("a", encoding="utf-8") as f:
        for a in alerts:
            f.write(json.dumps({"ts": now_iso, **a}, ensure_ascii=False) + "\n")


def _print_rollup() -> None:
    log = DATA_DIR / "locked_clicks.ndjson"
    if not log.exists():
        return
    entries = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines() if x.strip()]
    top = rollup_locked_clicks(entries)[:5]
    if top:
        print("[tradepulse] locked-page demand (roadmap oracle):",
              ", ".join(f"{r['hs6']}={r['requests']}req/{r['views']}v" for r in top))


if __name__ == "__main__":
    main()
