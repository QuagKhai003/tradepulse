# STATUS — what's happening right now

> Single source of truth for the CURRENT moment. Update at the start and end of every
> session. History goes in `docs/progress/`, not here.

**Last updated:** 2026-07-14 (tender feed + view fixes + EN-only; full Comtrade refresh RUNNING)

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
**MERGED to `main` (2026-07-13, `20c396b`, not pushed):** multi-source data spine.
Sources merged + deduped (one number per cell, national authority > freshness > priority, never sums):
**BACI bulk** (global history, all ~5,600 HS6, NO API throttle) + **Comtrade API** (recent) + **US
Census / EU Eurostat / UK HMRC** (fresh national primaries; EUR/GBP -> USD via ECB FX). Japan/Korea
national sources dropped on purpose (Comtrade covers them in HS). Incremental refresh (frozen periods
never re-fetched) + per-product persistence. `freq` (A/Q/M) + Nam/Quy toggle across map/ranking/feed.
**Catalog: 1,240 products** (every official HS4 heading + 32 curated w/ Vietnamese names). Slim snapshot
(310KB -> 64KB) so all ship (79MB incl. history); indexed export = 1,239 snapshots in 96s. **61 offline tests green.**

**IN FLIGHT — branch `feat/tender-feed` (NOT merged, needs owner approval):**
- **Tenders (Phase 2.2)** — EU TED, keyless, CPV-mapped: 670 open notices across 18 products. Right-panel
  tab on the globe + each country page lists **its own** public buyers' open tenders. English subject only.
- **View fixes (2026-07-14 owner review):** panel-header overflow (flow/grain moved to a globe control
  bar); country page has its own product search (switching product stays on the country); exports/imports
  panels aligned; **history restored** to the slim snapshot (shared period index; 59MB -> 79MB); the
  freshness chip now shows *that country's* latest period ("Data as of"), not the snapshot-wide max.
- **English-only (ADR-0004):** `i18n.VI_ENABLED = false` — 1,208 of 1,240 products still have
  English-only names, so the VN UI was showing English content anyway. Strings stay; one flag to revert.

**DATA CURRENCY — being fixed right now.** Owner spotted "newest data is 2024" in 2026. Cause: BACI
(bulk history) **ends at 2023**, and the Comtrade API had only ever covered **13 products** before its
quota throttled — so 1,227 products were frozen at 2023. Fix: Comtrade `cmdCode` takes a comma-separated
list, so annual pulls now **batch 10 products/call** (full refresh of the two non-final years: ~2,480
calls -> **~248**), with a halving retry when the API's 100k-row cap truncates a batch.
**A 1,240-product refresh of 2024 + 2025 is RUNNING (started 2026-07-14 05:43, ~2-5h).** When it lands:
`cd etl && python -m tradepulse_etl --export-only` to rebuild the snapshots.

**NEXT:** merge `feat/tender-feed` (owner approval); then new signal types (prices / border-rejections /
rule-changes). Phase-2 alerts + login. Zalo deferred by owner.
Note: `prepare-data` staleness threshold = 7 days; 2023 and older are `is_final` and never re-fetched.

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
