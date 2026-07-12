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

    source = get_source(args.source, period=args.period)
    n = run(source, conn)

    prev = fetch_signals(conn)                       # state before this run (for band crossings)
    sigs = compute_signals(fetch_flows(conn), now_iso)
    upsert_signals(conn, sigs)

    alerts = signal_alerts(prev, sigs)               # skips first load (prev empty)
    if alerts:
        _append_alerts(alerts, now_iso)

    # One snapshot per covered product; the map switches between them. Default = first covered.
    from .config import COVERED_HS
    default_path = Path(args.snapshot)
    covered = []
    for hs in COVERED_HS:
        snap = build_snapshot(conn, generated_at=now_iso, hs6=hs)
        if not snap["countries"]:
            continue
        write_snapshot(snap, default_path.parent / f"snapshot-{hs}.json")
        covered.append(f"{hs}:{len(snap['countries'])}c")
        if hs == COVERED_HS[0]:
            write_snapshot(snap, default_path)       # landing default

    print(f"[tradepulse] flows={count_trade_flows(conn)} (upserted {n}) signals={len(sigs)} "
          f"alerts={len(alerts)} products={len(covered)} [{' '.join(covered)}]")

    # Tier 2: quarterly partner sourcing for the focus reporters (needs the Comtrade key).
    if getattr(source, "key", None):
        from .config import FOCUS_REPORTERS, SOURCING_HS
        from .sourcing import build_sourcing, write_sourcing
        srcs = []
        for hs in SOURCING_HS:
            rows = source.pull_sourcing([hs], FOCUS_REPORTERS)
            sm = build_sourcing(rows, hs)
            if sm:
                write_sourcing(sm, default_path.parent / f"sourcing-{hs}.json")
                srcs.append(f"{hs}:{len(sm)}r")
        print(f"[tradepulse] sourcing (quarterly, {len(FOCUS_REPORTERS)} focus reporters) [{' '.join(srcs)}]")

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
