# CLAUDE.md — TradePulse (Export Intelligence Terminal)

> Auto-loaded every session. Project working memory. Read first.
> Keep short + current. Detail lives in `docs/`. Full vision: `trade-signal-terminal-plan.md`.

## What this is
A map-first web app showing Vietnamese SME exporters where global demand for their product
is moving, who the public buyers/sellers are, and exactly what it takes to qualify for each
destination market. **Information terminal, not a marketplace** — the app informs, the user
acts. Wedge: incumbents (ITC/Trade Map free, Volza, Panjiva, Tridge) sell *databases to
analysts*; we sell *answers to factory owners* — plain-language signal cards + per-market
qualification requirements + change alerts, in Vietnamese first. Pilot vertical: wood pellets
& wood products; pilot markets: Japan, Korea, EU, US, UK.

## The Golden Rule (never violate)
**Inform, never match.** The app never matches a buyer to a seller, never introduces parties,
never brokers a contact, never touches a transaction. Layer 2 shows public *names + source
links only* — never private/verified contact data. Breaking this re-imports the
trust/verification/liability problem the whole positioning exists to avoid. If a feature
introduces two parties to each other, **stop.**

Two engineering non-negotiables ride under it:
- **Deterministic signals only.** Every signal is a reproducible formula over published data
  (see plan §6). An LLM never produces a number the app displays. No AI-guessed trends.
- **Every requirement cites its source.** Each Layer-3 item shows an official source link +
  "last verified" date. No source = it does not ship. A wrong requirement rejects a container.

## Tech stack (deliberately boring & cheap — plan §10)
- **ETL/pipeline:** Python (requests, pandas), cron-scheduled batch. Monthly/quarterly data — no streaming.
- **Database:** PostgreSQL (SQLite acceptable for MVP). Star schema over trade flows.
- **Backend/API:** FastAPI *or* Next.js API routes — pick one, stay small.
- **Frontend:** Next.js (SSR for SEO on public map/category pages).
- **Map:** MapLibre GL or D3 choropleth + free GeoJSON. No Google Maps billing.
- **Layer-3 CMS:** Markdown in-repo (git history = free change log & audit trail).
- **Alerts:** cheap transactional email first; Zalo OA phase 2.
- **Secrets:** live in `.env` (gitignored). Never commit them.
- **Nothing is built yet** — stack is the committed target, not current state.

## Where things live
```
docs/          # the living documentation (read these, keep them updated)
trade-signal-terminal-plan.md   # full product vision (source of truth for scope)
# code dirs appear when Phase 1 starts (see docs/ROADMAP.md):
# etl/         # Python data pipeline (Layer 1 flows)
# web/         # Next.js frontend + API
# content/     # Layer-3 requirement pages (markdown, one per product × market)
```

## How to run (ONE command)
```bash
cd web && npm install && npm run dev     # -> http://localhost:3200  (?lang=en)
```
`npm run dev` auto-runs the ETL first (`predev` → `scripts/prepare-data.mjs`): fetches REAL Comtrade
data if the snapshot is missing (waits) or stale >24h (background), else skips. Force refresh: `npm run data`.
Comtrade key lives in `etl/.env` (gitignored) → authenticated = quarterly + partners; no key = annual.
Offline Python tests: `cd etl && python -m unittest discover -s tests` (22).

## Current state (read docs/STATUS.md for live detail)
- **Phase 1 MVP COMPLETE — runs on `localhost:3200`** (owner chose sequential build over the Stage 0
  gate). Map + signals + search + drill-down (sourcing chart) + Layer-2 profiles + Layer-3 requirement
  pages + watch/alerts + free↔paid paywall. All batches 1.1–1.9 merged to `main`.
- **Map-first (ADR-0003):** world map (up to ~177 countries), export + import, colored by signal, with
  an export/import/all toggle + global feed (both flows) + country drill (`/country/[code]`).
  **7 product categories** (pellets, sawn wood, tea, coffee, shrimp, cashew, rice) — search/`?hs`
  swaps to a real per-product map (`snapshot-<hs>.json`).
- **Data is REAL:** Layer-1 trade (Comtrade authenticated, annual all-countries both flows) + Layer-2
  profiles + Layer-3 requirement pages (curated, official sources + verified dates). Stage 0 WTP unproven.
  Quarterly + partner sourcing = deferred refinement (3.6); requirement rules age — quarterly review (S-001).
- **Tests:** 20 offline (ETL + deterministic signal/alert math + Comtrade helpers). `cd etl && python -m unittest discover -s tests`.

## New here?
Start at `docs/ONBOARDING.md`. `docs/CONVENTIONS.md` is the mandatory hygiene contract.

## Working agreement (how to develop here)
Production intent, many readers, high accuracy bar (wrong data has real cost). Optimise for the next reader.
1. Follow `docs/CONVENTIONS.md` — small files, one concept per file, header brief on every source file.
2. Before coding, check `docs/ROADMAP.md` (phase scope) + `docs/STATUS.md` (in flight).
3. Core/logic changes need a deterministic, offline test. No exceptions (signal math especially).
4. Changed a class/table? Update `docs/DATA_MODEL.md` in the same change.
5. Hit a bug/limitation → log in `docs/BUGS.md`. Non-obvious choice → add an ADR under `docs/decisions/`.
6. "Done" = code + header updated, tests green, `docs/STATUS.md` + `docs/progress/` updated, ADR batch ticked.
7. **Git (overrides kit default):** every feature/fix/change on its own branch off `main`.
   **NEVER merge without the owner's explicit approval.** Never push without approval. No AI attribution in commits.
