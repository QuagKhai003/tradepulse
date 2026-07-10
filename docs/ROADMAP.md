# ROADMAP

> Phases and their batches. Status per batch. Detail + acceptance live in the ADRs.
> Mirrors plan §13. Legend: ⬜ planned · 🔄 in progress · ✅ done.

## Stage 0 — Manual report validation — IN PROGRESS (ADR-0001)
**Goal:** prove willingness-to-pay with one hand-made report before writing any code (plan §12).

| # | Task | Status |
|---|------|--------|
| 0.1 | Build "Wood Pellet Export Opportunities" report — Vietnamese PDF | ⬜ |
| 0.2 | Distribute to 20–30 exporters (VIFOREST, wood FB/Zalo groups, direct email) | ⬜ |
| 0.3 | Measure replies + willingness-to-pay; record GO/PIVOT/KILL decision | ⬜ |

**Sequence:** 0.1 → 0.2 → 0.3. **Gate:** GO = ≥5 substantive replies AND ≥3 say yes to paying.
**Acceptance:** in ADR-0001.

## Phase 1 — MVP — IN PROGRESS (ADR-0002) — 6–8 weeks
**Goal:** global map + pilot vertical full depth + watch/alerts + payments (plan §13).
Building sequentially toward a localhost-runnable MVP (owner direction). Walking skeleton =
1.1→1.2→1.3. Depth 1.6–1.9 still advised to wait for Stage 0 GO (plan §12). Batches (ADR-0002):

| # | Task | Status |
|---|------|--------|
| 1.1 | ETL: Comtrade quarterly pull → `trade_flows` (raw-before-transform, cached) | ✅ |
| 1.2 | Signal compute: deterministic YoY bands over `trade_flows` (+ offline test) | ✅ |
| 1.3 | Layer 1: global choropleth map + signal feed (Next.js SSR) | ✅ |
| 1.4 | Category search: everyday words → HS chip (30–50 hand-mapped codes) | ✅ |
| 1.5 | Country drill-down + historical sourcing chart | ✅ |
| 1.6 | Layer 2: buyer/seller profiles (names + source links, curated) | ✅ |
| 1.7 | Layer 3: pellets→JP/KR/EU requirement pages (markdown, cited) | ✅ |
| 1.8 | Watch/alerts (email) + locked-page telemetry | ✅ |
| 1.9 | Payments (single paid tier) | ⬜ |

## Phase 2 — PLANNED — +6 weeks
| # | Task | Status |
|---|------|--------|
| 2.1 | Second vertical (from Stage 0 feedback + locked-page clicks) | ⬜ |
| 2.2 | Tender feed productized (Korean utility + EU TED) | ⬜ |
| 2.3 | Zalo OA alerts | ⬜ |
| 2.4 | Monthly national-stats freshness for covered markets | ⬜ |

## Phase 3 — ongoing
Markets/verticals strictly by locked-page telemetry. Curated-contact upgrade only if users
demand it and manual verification is sustainable.

## Backlog / deferred
- Mirror-side toggle (importer vs GDVC) on Vietnam tiles — plan §15 Q4.
- Legal terms-of-use disclaimer wording for requirement pages — plan §15 Q5.
