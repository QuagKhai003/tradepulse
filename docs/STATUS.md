# STATUS — what's happening right now

> Single source of truth for the CURRENT moment. Update at the start and end of every
> session. History goes in `docs/progress/`, not here.

**Last updated:** 2026-07-12 (globe-3d branch: AI-slop pass — humanist font, contrast, portal sort, align)

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
**IN FLIGHT (branch `feature/globe-3d`, NOT merged — awaiting owner approval):** stunning 3D WebGL
globe hero (react-globe.gl) + all-products default + client-state pills (no reload) + AI-slop pass
(Plus Jakarta Sans, dark-panel contrast, portal sort menu, top-20 alignment, "Tìm kiếm quốc gia" +
globe icon, "Khối lượng giao dịch"). Compile: cold `/` 6.6s (three.js floor), warm/HMR <0.6s.
**NEXT: nothing queued.** Options: real email/Zalo alert delivery + login (Phase 2), mirror-based VN
sourcing, more requirement pages (per demand telemetry), or Stage 0 validation with the live demo.
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
