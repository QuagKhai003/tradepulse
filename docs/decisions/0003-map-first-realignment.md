# ADR-0003 — Map-first realignment (global, both flows, product filter)

**Status:** Accepted — COMPLETE · 2026-07-11 · Builds on: ADR-0002, product plan §5, §7.1.
All batches (3.1–3.7) shipped + merged to `main`.

## Context
Owner feedback: the built UI was *pellet-first / import-only / 5-market*, not the plan's Layer-1
vision (§5, §7.1): a **world map of all countries** showing **export AND import** per country,
quarterly, with an **export/import/all toggle**, a **global signal feed** (both flows), and a
**product filter** (pick tea → map reshapes). Click a country → its signals → deeper → profiles.
A qualifications tab informs per export/import choice.

## Decision & key rules (apply to every batch)
- The **map is the hero**; product is a filter, not the frame. Default = pilot product across all countries.
- Data is **all-reporters, both flows** (World partner) via the authenticated Comtrade `/data` (annual —
  monthly-all-countries times out; annual is light + reliable). Signals stay deterministic + flow-aware.
- Snapshot is **country-centric**: `countries[{code,name,exp{},imp{}}]` + a global `feed[]` (both flows).
- Inform-never-match; value/volume only; honest labels; keyless fallback = annual World-only import.

## Plan (batches)
- [x] **3.1 — ETL global both-flows.** All-reporters annual X+M → per-country export+import + signals;
  bundled country-name reference; country-centric snapshot. → **DONE:** 162 countries, feed=34, real.
- [x] **3.2 — Map hero + toggle.** All-country choropleth colored by the selected flow's band;
  export/import/all toggle; country tiles show both flows. → **DONE.**
- [x] **3.3 — Global feed (both flows).** Moderate+ worldwide, flow-tagged, toggle-filtered. → **DONE.**
- [x] **3.4 — Country drill.** `/country/[code]`: export + import signal + history sparkline + links
  to profiles and (if covered) the qualification page. → **DONE.**
- [x] **3.5 — Qualifications tab per flow.** Re-anchor requirement pages to the export/import choice
  (VN-exporter framing) + a country-level qualifications entry point.
  → **DONE:** `QualPanel` on the country drill = market-entry qualifications for (product × country),
  exporter-framed. Covered pairs (pellets→JP/KR/EU) show snapshot + sourced teaser + full-checklist link;
  uncovered pairs show "coming soon — request it" (`RequestQual` → `/api/locked-click`, demand telemetry §7.6).
- [x] **3.6 — Quarterly + partner sourcing.** Per-country quarterly + partner breakdown for the
  drill-down sourcing chart. → **DONE:** two-tier data — global map stays annual (all countries too
  heavy monthly); a **focus set** (Vietnam + JP/KR/US/UK) gets a quarterly, all-partner pull
  (`ComtradeSource.pull_sourcing` → `sourcing.py` → `sourcing-<hs>.json`). Country page renders
  `PartnerTable` (top partners, share, YoY) + SSR stacked-bar `SourcingChart` (quarters) per flow;
  non-focus countries show annual history. Others addable via `config.FOCUS_REPORTERS`.
- [x] **3.7 — Multiple product categories.** Pull each covered HS (pellets, sawn wood, tea, coffee,
  shrimp, cashew, rice) → one snapshot per product; the category switch loads real per-product maps.
  → **DONE:** `config.COVERED_HS`; ETL loops HS×year; `snapshot-<hs>.json` per product; web loader +
  catalog + page/country switch by `?hs`. Pellet-only Layer-2/3 links gated to the pellet product.

## Acceptance
- Map shows all countries with export+import, toggled; feed lists global both-flow signals; a category
  reshapes the map; clicking a country drills into its signals → profiles/qualifications. (3.1–3.4 met.)

## Notes for the executor
- Removed the old market-centric route + partner components (snapshot changed shape). Sourcing chart
  returns in 3.6. Git: branch per batch; no merge without owner approval; no AI attribution.
