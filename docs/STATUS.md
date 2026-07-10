# STATUS — what's happening right now

> Single source of truth for the CURRENT moment. Update at the start and end of every
> session. History goes in `docs/progress/`, not here.

**Last updated:** 2026-07-11 (MVP complete + running on REAL Comtrade data; annual World-only)

## Phase
**Phase 1 MVP — COMPLETE, now on real trade data.** Runs on `localhost:3200`. Layer-1 map/signals
use REAL UN Comtrade figures (`--source comtrade`, annual World-only — L-003). Profiles + Layer-3
requirements remain SAMPLE (curation pending). Stage 0 validation still deferred (ADR-0001).

## Active task
**Phase 1 — ADR-0002 — DONE (1.1–1.9 merged to `main`).** Shipped: Layer-1 map + deterministic
signals, product search + locked pages, country drill-down (partners + sourcing chart), Layer-2
profiles, Layer-3 requirement pages, watch/alerts engine + telemetry, and the free↔paid gate
(cookie + test-mode checkout). 15 offline Python tests green; web build clean.
**NEXT: nothing queued.** Options below — owner picks.

## How to run (localhost MVP)
```
# optional: put a FREE Comtrade key in etl/.env (see etl/.env.example) -> quarterly + partners
cd etl && python -m tradepulse_etl --source comtrade   # REAL data (keyed=quarterly, keyless=annual)
#   or: python -m tradepulse_etl                        # offline SAMPLE fixture (instant)
cd ../web && npm install && npm run dev                 # http://localhost:3200  (?lang=en)
```

## Next action (owner picks)
1. **Make it real (highest value):** run the actual Comtrade pull (`--source comtrade` + monthly→
   quarter aggregation) and replace SAMPLE profiles/requirements with verified content (S-001 bar).
2. **Validate:** do Stage 0 (ADR-0001) now that there's a live demo to show exporters.
3. **Phase 2 (ADR-0003, write when starting):** 2nd vertical, real tender feed, Zalo alerts, real email delivery + login.
- Confirm Golden Rule wording ("Inform, never match" — CLAUDE.md).

## Path to MVP (localhost) — see docs/ROADMAP.md
Skeleton: **1.1 ETL ✅ → 1.2 signals(+test) → 1.3 map+feed** = runnable localhost demo.
Then 1.4 search → 1.5 drill-down → 1.6 profiles → 1.7 requirement pages → 1.8 alerts → 1.9 payments.

## Watch / before launch
- **Data is SAMPLE (fixture), clearly labelled.** Swap to real Comtrade (`--source comtrade`) +
  monthly→quarter aggregation before any external launch. Never imply the sample is published stats.
- Stage 0 willingness-to-pay still unproven — plan §12 gate deferred, not cleared.
- Price point (200k vs 500k VND) — plan §15 Q2. Comtrade rate limits: cache raw pulls.
