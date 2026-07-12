# STATUS — what's happening right now

> Single source of truth for the CURRENT moment. Update at the start and end of every
> session. History goes in `docs/progress/`, not here.

**Last updated:** 2026-07-12 (feature/globe-3d MERGED to main — 3D globe hero + redesign + perf)

## Phase
**Phase 1 MVP complete + map-first realignment (ADR-0003, 3.1–3.4 done).** `npm run dev` auto-fetches.
The map is now the hero: **162 countries, export + import**, colored by signal, with an
export/import/all toggle + global feed (both flows) + country drill (`/country/[code]`). Layer-2
profiles + Layer-3 requirement pages REAL curated. Stage 0 deferred (ADR-0001).
Data = REAL Comtrade, authenticated, **annual all-countries both flows** (quarterly + partner sourcing
= refinement 3.6). Key in `etl/.env`.

## Active task
**ADR-0003 COMPLETE (3.1–3.7 merged to `main`).** Map-first + multi-product + quarterly sourcing +
qualifications: global both-flows map per product (7 covered); export/import/all toggle; global feed;
`/country/[code]` drill with quarterly partner-sourcing charts (focus markets) + a **market-entry
qualifications panel** (covered pairs show sourced checklist, uncovered log demand). 22 tests green.
**MERGED to `main` (2026-07-12, merge `77b31e3`, not pushed):** stunning 3D WebGL globe hero
(react-globe.gl) + all-products default + client-state CSS pills (no reload) + AI-slop pass (Plus
Jakarta Sans body + Be Vietnam Pro display, dark-panel contrast, portal sort menu w/ 6 options,
full country ranking list, "Tìm kiếm quốc gia" + globe icon). Country borders on zoom-in only (one
GL LineSegments buffer, 50m lazy-loaded). Next 15.5.20; framer-motion dropped for CSS. Compile:
warm `/` ~8-10s, cold ~48s (three.js floor — one-time; keep `.next`), HMR <1s.
**IN FLIGHT (branch `feat/multi-source-data`, NOT merged):** multi-source data spine —
`merge.merge_flows` = one number per cell (national authority > freshness > priority, never sums);
`freq` (A/Q/M) dimension + M/Q/A UI toggle (`by_freq` in snapshot); **US Census** source (fresh
authoritative US totals — verified live, caught+fixed a region double-count); **Comtrade
monthly→quarterly** (core products, 1 month/call); "in 2024" freshness stamp. `npm run data` now runs
`--source comtrade,census --freq AQ`. **34 offline tests.** Full multi-source refresh NOT yet run
(heavy: ~320 Comtrade + ~370 Census calls). Catalog: `docs/DATA_SOURCES.md`.
**NEXT (same frame):** feed-by-freq; more national sources (HMRC/Eurostat keyless, JP/KR need keys);
then new signal types (prices/tenders/border-rejections/rule-changes). Then Phase-2 alerts + login.
Note: full data refresh = 112 Comtrade calls (~6 min); `prepare-data` threshold = 7 days.

## How to run (ONE command)
```
cd web && npm install && npm run dev     # http://localhost:3200  — auto-fetches real data first
#   npm run data                          # force a data refresh
#   offline sample instead: cd etl && python -m tradepulse_etl   (fixture)
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
