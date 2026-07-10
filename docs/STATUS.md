# STATUS — what's happening right now

> Single source of truth for the CURRENT moment. Update at the start and end of every
> session. History goes in `docs/progress/`, not here.

**Last updated:** 2026-07-10 (batch 1.8 watch/alerts + telemetry done + merged; next = 1.9 payments = last)

## Phase
**Phase 1 MVP — sequential build (owner direction).** Stage 0 validation deferred (ADR-0001 on
record). Goal this stretch: a Next.js app runnable on `localhost` showing pellet demand signals.

## Active task
**Phase 1 — ADR-0002 — batches 1.1–1.8 DONE (merged to `main`).** Full stack + alert engine live:
map, search, drill-down, profiles, requirement pages, Watch button + `/api/watch`, PURE alert logic
(band-crossing + rule-change + telemetry rollup). Runs on `localhost:3200`.
**NEXT: batch 1.9 (LAST)** — payments / paid-tier gate (branch `phase/1-payments`): make the
free↔paid boundary real (plan §11) — a tier cookie/session + test-mode checkout stub gating full
profiles, requirement checklists, and unlimited watches.

## How to run right now (localhost MVP)
```
cd etl && python -m tradepulse_etl        # build data + snapshot (stdlib, no pip)
cd ../web && npm install && npm run dev    # http://localhost:3200  (?lang=en)
```

## Next action (whoever picks this up)
- Batch 1.4 search, then 1.5 country drill-down. (Depth 1.6–1.9 still advised behind Stage 0 GO.)
- Confirm Golden Rule wording ("Inform, never match" — CLAUDE.md).
- Decide pilot-vertical fallback if pellets stall (tea/seafood/cashew — plan §15 Q1).

## Path to MVP (localhost) — see docs/ROADMAP.md
Skeleton: **1.1 ETL ✅ → 1.2 signals(+test) → 1.3 map+feed** = runnable localhost demo.
Then 1.4 search → 1.5 drill-down → 1.6 profiles → 1.7 requirement pages → 1.8 alerts → 1.9 payments.

## Watch / before launch
- **Data is SAMPLE (fixture), clearly labelled.** Swap to real Comtrade (`--source comtrade`) +
  monthly→quarter aggregation before any external launch. Never imply the sample is published stats.
- Stage 0 willingness-to-pay still unproven — plan §12 gate deferred, not cleared.
- Price point (200k vs 500k VND) — plan §15 Q2. Comtrade rate limits: cache raw pulls.
