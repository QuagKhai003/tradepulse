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
from .export import (DEFAULT_SNAPSHOT, build_all, build_awards, build_cpv_match, build_events,
                     build_forward, build_sellers_web, build_snapshot, build_tenders, write_countries,
                     write_json, write_snapshot, write_tenders)
from .pipeline import get_sources, run_multi
from .signals import compute_signals

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def main() -> None:
    ap = argparse.ArgumentParser(prog="tradepulse_etl", description="Build TradePulse Layer-1 data.")
    ap.add_argument("--source", default="fixture",
                    help="data source(s), comma-separated: fixture | comtrade | census "
                         "(e.g. 'comtrade,census' — merged, one number per cell)")
    ap.add_argument("--period", default="2025", help="period for the comtrade source")
    ap.add_argument("--freq", default="A", choices=["A", "AQ"],
                    help="grain(s) for comtrade: A=annual (default), AQ=annual + monthly->quarterly")
    ap.add_argument("--db", default=str(DEFAULT_DB), help="SQLite path")
    ap.add_argument("--snapshot", default=str(DEFAULT_SNAPSHOT), help="web snapshot output path")
    ap.add_argument("--tenders", action="store_true",
                    help="also pull EU TED tenders (forward demand: who is buying now)")
    ap.add_argument("--export-only", action="store_true",
                    help="skip every network pull; rebuild snapshots/signals from the stored DB")
    ap.add_argument("--no-flows", action="store_true",
                    help="skip the trade-flow pull (use with --tenders to refresh tenders/awards only)")
    ap.add_argument("--only", metavar="HS",
                    help="build ONLY this product (lazy per-product build for the web, on first open)")
    args = ap.parse_args()

    now_iso = datetime.now(timezone.utc).isoformat()
    conn = connect(args.db)
    only = args.only                                 # None = whole catalogue; else one HS

    skip_flows = args.export_only or args.no_flows
    sources = [] if skip_flows else get_sources(args.source.split(","), freqs=tuple(args.freq))
    n = 0 if skip_flows else run_multi(sources, conn, hs_codes=([only] if only else None))

    prev = fetch_signals(conn)                       # state before this run (for band crossings)
    sigs = compute_signals(fetch_flows(conn, hs6=only) if only else fetch_flows(conn), now_iso)
    upsert_signals(conn, sigs)

    alerts = signal_alerts(prev, sigs)               # skips first load (prev empty)
    if alerts:
        _append_alerts(alerts, now_iso)

    # One snapshot per covered product; the map switches between them. Default = first covered.
    from .config import COVERED_HS
    hs_list = [only] if only else COVERED_HS         # lazy build writes just the one product
    default_path = Path(args.snapshot)
    if not only:   # countries.json is a shared batch artifact — a lazy build reuses it, no full scan
        write_countries(conn, default_path.parent / "countries.json")
    covered = []
    for hs in hs_list:
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
    sourcing_src = next((s for s in sources if getattr(s, "key", None) and hasattr(s, "pull_sourcing")), None)
    if sourcing_src is not None:
        from .config import FOCUS_REPORTERS, SOURCING_HS
        from .sourcing import build_sourcing, write_sourcing
        srcs = []
        for hs in SOURCING_HS:
            rows = sourcing_src.pull_sourcing([hs], FOCUS_REPORTERS)
            sm = build_sourcing(rows, hs)
            if sm:
                write_sourcing(sm, default_path.parent / f"sourcing-{hs}.json")
                srcs.append(f"{hs}:{len(sm)}r")
        print(f"[tradepulse] sourcing (quarterly, {len(FOCUS_REPORTERS)} focus reporters) [{' '.join(srcs)}]")

    # --- Forward demand: EU TED tenders (who is buying RIGHT NOW) — plan §9.2 / Phase 2.2 ---
    if args.tenders or args.export_only or only:
        from datetime import date, timedelta
        from .config import TENDER_CPV, TENDER_LOOKBACK_DAYS, AWARD_LOOKBACK_DAYS
        from .db import upsert_awards, upsert_tenders
        today = date.today()
        # A lazy per-product build (--only) rebuilds that product's files from STORED tender/award/seller
        # data (fast, no network) — the TED + DG SANTE pulls are a periodic batch, not per-open.
        do_pull = args.tenders and not args.export_only and not only
        rows, awards = [], []
        if do_pull:
            from .sources.ted import TedSource
            ted = TedSource()
            since = (today - timedelta(days=TENDER_LOOKBACK_DAYS)).strftime("%Y%m%d")
            rows = ted.pull(TENDER_CPV, since, now_iso)
            upsert_tenders(conn, rows)
            # PAST ORDERS: awarded contracts -> also the only public evidence of who SELLS this product.
            asince = (today - timedelta(days=AWARD_LOOKBACK_DAYS)).strftime("%Y%m%d")
            awards = ted.pull_awards(TENDER_CPV, asince, now_iso)
            upsert_awards(conn, awards)
        # SELLERS = real exporters from approval registries (ADR-0006), NOT award winners. Pulled from
        # DG SANTE (keyless; animal-origin -> seafood + honey among our products). A won contract is a
        # PAST ORDER, so sellers must come from a different source or the two tabs are the same data.
        from .config import SELLER_COUNTRIES, SELLER_SECTIONS
        from .db import fetch_registry_sellers, upsert_registry_sellers
        sellers_raw = []
        if do_pull:
            from .sources.registry import DgSanteSource
            sellers_raw = DgSanteSource().pull(SELLER_COUNTRIES, list(SELLER_SECTIONS), today.isoformat())
            upsert_registry_sellers(conn, sellers_raw)

        write_json(build_cpv_match(), default_path.parent / "cpv-match.json")   # cheap; no network
        open_n = award_n = 0
        for hs in ([only] if only else list(TENDER_CPV)):
            if hs not in TENDER_CPV:                 # a lazily-built product with no tender coverage
                continue
            ten = build_tenders(conn, hs, today.isoformat())
            write_tenders(ten, default_path.parent / f"tenders-{hs}.json")
            open_n += len(ten)
            aw = build_awards(conn, hs)                  # PAST ORDERS (won contracts)
            write_json(aw, default_path.parent / f"awards-{hs}.json")
            award_n += len(aw)

        # sellers-<hs>.json for every product a registry covers, plus the tender products (they get []
        # until a registry covers them — an honest "coming soon", not a fake list).
        seller_hs = sorted({h for codes in SELLER_SECTIONS.values() for h in codes} | set(TENDER_CPV))
        seller_n = 0
        for hs in ([only] if only else seller_hs):
            se = build_sellers_web(conn, hs)
            write_json(se, default_path.parent / f"sellers-{hs}.json")
            seller_n += len(se)

        # REGULATORY CHANGES (ADR-0007): WTO ePing SPS/TBT -> the qualification tab (a SEPARATE lane,
        # never merged into a signal). Pulled in the batch; a lazy --only build reads the stored DB.
        from .config import MARKET_SLUG_BY_M49, RASFF_CAT, RASFF_LOOKBACK_DAYS, REGULATORY_HS
        from .db import fetch_regulatory_event_keys, upsert_regulatory_events
        events_pulled = 0
        if do_pull:
            from .sources.eping import EpingSource
            from .sources.rasff import RasffSource
            prev_ev_keys = fetch_regulatory_event_keys(conn)     # what was 'seen' BEFORE this pull
            pulled_events = (EpingSource().pull(REGULATORY_HS, today.isoformat())
                             + RasffSource().pull(RASFF_CAT, REGULATORY_HS, today.isoformat(), RASFF_LOOKBACK_DAYS))
            events_pulled = upsert_regulatory_events(conn, pulled_events)
            # CHANGE-ALERTS (owner: fire on the SIGNAL watch = country + product). New events only; the
            # first-ever load is skipped (an initial import is a baseline, not a change).
            from .alerts import match_event_watches, regulatory_event_alerts
            new_ev = regulatory_event_alerts(prev_ev_keys, pulled_events)
            if new_ev:
                _append_alerts(new_ev, now_iso)
                matched = match_event_watches(new_ev, _load_active_watches(), MARKET_SLUG_BY_M49)
                print(f"[tradepulse] change-alerts: {len(new_ev)} new events -> "
                      f"{len(matched)} watched signal(s) notified")
        event_n = 0
        for hs in ([only] if only else sorted(REGULATORY_HS)):
            ev = build_events(conn, hs)                  # [] for products with no coverage (honest)
            write_json(ev, default_path.parent / f"events-{hs}.json")
            event_n += len(ev)
        print(f"[tradepulse] regulatory events (ePing): {events_pulled} pulled, {event_n} product-rows")

        # FORWARD lane (ADR-0007): IMF world PRICE trend. Pulled in the batch; a lazy --only build reads
        # the stored DB. Only products with an honest direct IMF series get a line (null otherwise).
        from .config import PRICE_HS
        from .db import upsert_commodity_prices
        if do_pull:
            from .sources.imf_pcps import ImfPcpsSource
            upsert_commodity_prices(conn, ImfPcpsSource().pull(PRICE_HS, today.isoformat()))
        fwd_n = 0
        for hs in ([only] if only else sorted(PRICE_HS)):
            fwd = build_forward(conn, hs)                # None -> null file -> the UI shows no price line
            write_json(fwd, default_path.parent / f"forward-{hs}.json")
            fwd_n += 1 if fwd else 0
        print(f"[tradepulse] forward price (IMF PCPS): {fwd_n} products with a trend line")

        # TOTAL sellers = every registry seller, deduped by (org, country). Skipped on a lazy build.
        allrows = [] if only else fetch_registry_sellers(conn, list(SELLER_SECTIONS))
        seen, s_all = set(), []
        for r in allrows:
            k = (r["seller"], r["seller_code"])
            if k in seen:
                continue
            seen.add(k)
            s_all.append({"seller": r["seller"], "seller_country": r["seller_iso"],
                          "seller_code": r["seller_code"], "approval_no": r["approval_no"],
                          "activity": r["activity"], "city": r["city"], "source": r["source"],
                          "url": r["source_url"], "verified": r["verified_date"]})
        if not only:                                 # the "All products" rollup is a full-build artifact
            write_json(s_all, default_path.parent / "sellers-TOTAL.json")
            # PAST ORDERS + BUYERS rollup for "All products" (deduped; sellers handled above, registry).
            t_all, a_all, _ = build_all(conn, today.isoformat())
            write_tenders(t_all, default_path.parent / "tenders-TOTAL.json")
            write_json(a_all, default_path.parent / "awards-TOTAL.json")
        print(f"[tradepulse] tenders: {len(rows)} scraped, {open_n} still open | "
              f"awards: {len(awards)} scraped, {award_n} on-product | "
              f"sellers (registry): {len(sellers_raw)} pulled, {seller_n} product-rows | "
              f"{'ONLY ' + only if only else 'full'}")

    _print_rollup()


def _load_active_watches() -> list[dict]:
    """Active watches = the keys whose LAST action was 'watch' (data/watches.ndjson is append-only:
    each toggle logs watch/unwatch). Used to route change-alerts to who asked for them."""
    log = DATA_DIR / "watches.ndjson"
    if not log.exists():
        return []
    state: dict[str, dict] = {}
    for line in log.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("action") == "unwatch":
            state.pop(r.get("key"), None)
        else:
            state[r.get("key")] = r
    return list(state.values())


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
