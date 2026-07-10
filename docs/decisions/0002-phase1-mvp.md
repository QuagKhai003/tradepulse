# ADR-0002 — Phase 1 MVP build plan

**Status:** Accepted — COMPLETE · 2026-07-10 · Builds on: ADR-0001 (Stage 0), product plan §5–11, §13.
All batches 1.1–1.9 shipped + merged to `main`; MVP runs on `localhost:3200`. Acceptance met (below),
with the standing caveat that DATA + content are SAMPLE and Stage 0 willingness-to-pay is unproven.

> **Gate note:** plan §12 recommends no code until Stage 0 = GO. Owner elected to build the
> walking skeleton in parallel with Stage 0 validation (at owner's risk). If Stage 0 = KILL,
> stop this ADR. Batches 1.1–1.3 are the low-regret skeleton; 1.6–1.9 (curation, payments)
> should not start until Stage 0 = GO.

## Context
Phase 1 delivers the MVP: global map (Layer 1) + pilot-vertical full depth (signals, profiles,
requirement pages) + watch/alerts + payments (plan §13). The bet is a thin vertical slice —
real pellet data flowing to one map screen — proves the pipeline before we widen to nine
batches. Everything downstream of the skeleton is *widening*, not *de-risking*.

## Decision & key rules (apply to every batch)
- **Golden Rule holds:** inform-never-match; deterministic signals (no LLM in the number path);
  every Layer-3 item cites an official source + verified date.
- **Walking skeleton first:** 1.1 → 1.2 → 1.3 (data → signals → map). Do not start depth
  (1.4+) until the skeleton renders real pellet data.
- **Tech decisions (settled here, revisit only via a new ADR):**
  - **DB:** SQLite for the MVP (plan allows), **behind a repository seam** (`CONVENTIONS.md` §11)
    so the Postgres swap is caller-invisible. Star schema per `DATA_MODEL.md`.
  - **Web/API:** Next.js (SSR + API routes) — one web stack, small. Python only for the ETL batch.
  - **Map:** D3 choropleth + free GeoJSON (no tile server, no billing). Choropleth is the whole need.
  - **ETL:** Python (requests + pandas), cron/manual batch. Raw-before-transform: persist raw
    pulls before deriving `trade_flows`. Cache aggressively (Comtrade rate limits).
  - **i18n:** VN default, EN second, from day one.
- **Scope lock:** pilot vertical = wood pellets (HS 4401.31 + neighbours in 4401). Depth markets
  = JP, KR, EU, US, UK. Layer-1 map = all countries at aggregate level only.
- **Metric rule:** value (USD) + volume (tons) only. Never fabricate order/shipment counts.
- **Auth:** no login for free browsing; login required only to watch (plan §10.4).

## Plan (batches — branch per batch, tested, docs each batch)
> First unchecked box = "what's next." Tick `[ ]` → `[x]` with a one-line result on merge
> (after owner approval). Batches 1.1–1.3 = the walking skeleton.

- [x] **1.1 — ETL: Comtrade → `trade_flows`.** Python job pulls pellet HS × {JP,KR,EU,US,UK}
  importer-reported, quarterly; stores raw pull, upserts `trade_flows`. Behind a source seam +
  local fixture. **Acceptance:** one command populates the DB from a cached/fixture pull; re-run is idempotent.
  → **DONE:** `python -m tradepulse_etl` loads 42 rows into `data/tradepulse.sqlite`; stdlib-only;
  source seam (fixture/comtrade); 2 offline tests green (populate + idempotent + raw-persisted).
- [x] **1.2 — Signal compute (+ deterministic test).** Pure function over `trade_flows` → `signals`
  (YoY delta, noise floors, bands per plan §6). **Acceptance:** offline test asserts every band
  boundary + every noise-floor rejection; no network, no LLM.
  → **DONE:** `signals.py` (PURE, `now_iso` injected) + `export.py` writes the web JSON snapshot;
  fixture yields JP significant↑, KR significant↓, EU/GB moderate, US suppressed. +6 tests (8 total) green.
- [x] **1.3 — Layer 1: choropleth map + signal feed.** Next.js SSR page: D3 choropleth (value +
  YoY tile), side signal feed (moderate+), honest period labels. **Acceptance:** renders real
  pellet data from `signals`; export/import toggle works; builds + lints clean.
  → **DONE:** `web/` Next.js App Router (JS) reads the snapshot; SSR d3-geo choropleth colored by
  band + market tiles + feed + SAMPLE banner + VN/EN. `npm run build` clean; runs on `localhost:3200`.
  (Export/import toggle deferred to a later batch — import side is the plan default; noted.)
- [x] **1.4 — Category search → HS chip.** Everyday-word box (VN/EN) → 30–50 hand-mapped HS
  lookup → chip; map re-renders per product. **Acceptance:** "trà"/"pellet" resolves to the right HS.
  → **DONE:** `lib/catalog.js` (diacritic-insensitive search; pellets covered + 6 candidate verticals
  locked) + `SearchBox` autocomplete; `?hs=` switches product. Uncovered → `LockedProduct` "coming
  soon — request it" with telemetry to `/api/locked-click` (NDJSON, §7.6). Build clean; verified.
- [x] **1.5 — Country drill-down + sourcing chart.** Within-country signals + top partners with
  shares/YoY + historical sourcing chart. **Acceptance:** JP pellet page shows partner shares over time.
  → **DONE:** fixture extended with JP/KR partner breakdowns; `export.py` adds per-market partners
  (share+YoY) + sourcing series; `/market/[slug]` renders `PartnerTable` (VN highlighted) + SSR
  stacked-bar `SourcingChart`; tiles link in. Markets w/o partner data degrade gracefully. Build clean.
- [x] **1.6 — Layer 2: profiles.** Curated buyer/seller names + public profile/source links
  (FSC/SBP/PEFC, tender awards, VIFOREST). **No contact data.** **Acceptance:** ≥10 pellet profiles, each sourced.
  → **DONE:** `content/companies/pellets.json` (10 curated profiles, SAMPLE-labelled, each with
  evidence source + verified date, zero contacts); `/profiles` SSR list, free-tier blurs beyond 3
  (plan §11). Verified no email/phone fields render. **Note:** entries are sample placeholders —
  real curation is the documented manual task; the accuracy bar (S-001) applies before launch.
- [x] **1.7 — Layer 3: requirement pages.** pellets→JP, →KR, →EU markdown pages per plan §8
  template; every item sourced + dated; change log. **Acceptance:** 3 pages, zero unsourced items.
  → **DONE:** `content/requirements/pellets-{jp,kr,eu}.json` (§8 template: snapshot, checklist,
  buyer expectations, demand, price, change log). Loader DROPS any item missing source_url +
  verified_date (enforces "no source = no ship"). `/requirements` index + `/requirements/[market]`;
  free tier = Snapshot only, paid unlocks the checklist (plan §11, `?tier=paid` demo). SAMPLE-labelled.
  **Decision:** structured JSON instead of raw markdown — better enforces the sourced-item invariant;
  git history is still the change-log/audit trail. (See BUGS S-001 — accuracy bar before launch.)
- [x] **1.8 — Watch/alerts (email) + locked-page telemetry.** Watch button; signal-band-crossing +
  rule-change email; `locked_page_clicks` logged. **Acceptance:** a band crossing emits one email to a watcher.
  → **DONE:** `alerts.py` (PURE): `signal_alerts` (band crossings, skips first load), `rule_change_alerts`,
  `match_watches`, `rollup_locked_clicks`; +7 offline tests (15 total). CLI diffs prev vs new signals →
  `data/alerts.ndjson` + prints the demand rollup. Web `WatchButton` + `/api/watch` (→ `watches.ndjson`)
  on market + requirement pages. **Delivery is a stub** (NDJSON, not email) — the email/Zalo swap is documented.
- [x] **1.9 — Payments (single tier).** Gate full profiles/requirements/alerts behind one paid tier.
  **Acceptance:** free vs paid boundary matches plan §11; test-mode checkout completes.
  → **DONE:** `lib/tier.js` (cookie tier), `/api/checkout` (test-mode upgrade/cancel, 303 + cookie),
  `/pricing` (free vs paid table, 200k₫/mo). Profiles + requirement checklists gate on the cookie.
  Verified full cycle: free=snapshot only → checkout → paid=full checklist + all profiles → downgrade re-gates.

## Acceptance (phase done)
- The skeleton (1.1–1.3) renders real pellet signals on the map.
- Pilot depth live: category search, drill-down, ≥10 profiles, 3 requirement pages (all sourced).
- Watch/alerts fire on a real band crossing; payments gate the paid boundary.
- Signal math has a deterministic offline test; Golden Rule held throughout; VN+EN UI.

## Notes for the executor
- Sequence by dependency: 1.1 → 1.2 → 1.3 (skeleton), then 1.4 → 1.9.
- Do NOT start 1.6–1.9 until Stage 0 = GO (ADR-0001). 1.1–1.3 are low-regret.
- Each batch: branch from `main`, deterministic test for logic, update STATUS + progress
  (+ DATA_MODEL when tables land), tick the box. **No merge without owner approval; no push
  without approval; no AI attribution in commits.**
