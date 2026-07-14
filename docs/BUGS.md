# BUGS & LIMITATIONS

> Log it the moment you hit it. Don't wait, don't rely on memory. Each entry: an id, the
> symptom, the cause if known, status, and where it's handled.

Format: `L-NNN` (limitation) / `B-NNN` (bug) / `S-NNN` (security/launch risk).

---

## L-001 — Trade data lags 1–6 months
- **Symptom:** figures shown are never real-time; Comtrade lags 1–6 mo, national sources 1–2 mo.
- **Cause:** inherent to free/official trade statistics + revisions.
- **Status:** addressed-by-design (dormant until Phase 1).
- **Where:** plan §6.4; every figure must carry a publication-period + date label. `signals`/UI.
- **Notes:** re-pull trailing 4 quarters on every refresh (revisions). Never imply real-time.

## L-002 — Mirror discrepancies (exporter vs importer reported)
- **Symptom:** exporter-reported and importer-reported values differ (freight, misclassification).
- **Cause:** two independent customs systems report the same flow.
- **Status:** addressed-by-design; also USED as a fix (2026-07-14) — see below.
- **Where:** plan §6.4. Default importer-reported per view; state it in a tooltip.
- **Notes:** Vietnam-tile headline side (GDVC vs importer) still open — plan §15 Q4.
- **Mirror-as-fix (2026-07-14):** late/non-reporters (Vietnam self-reports to Comtrade ~2y late) were
  frozen at 2023 and vanished from the latest view. `ComtradeMirrorSource` rebuilds a country's exports
  from its partners' import reports (imports-from-E summed = E's mirror exports). Mirror is CIF (~5-10%
  above the exporter's FOB), so it ranks BELOW every direct report and fills gaps only (DO NOTHING),
  skips the thin frontier year, and every mirror value is badged `est.` in the UI. Fixed "Vietnam
  missing from coffee": VN now shows 2024 ($4.36B), ranks coffee #4 / rice #3 / cashew #1.

## L-003 — Comtrade free preview: annual World-only (no quarterly, no partners)
- **Symptom:** live `--source comtrade` returns ANNUAL World totals only; drill-down shows "no
  sourcing data"; signals are annual YoY, not quarterly.
- **Cause:** the keyless preview endpoint rejects multi-period requests (HTTP 400) and rate-limits
  bursts (HTTP 429), so monthly→quarter aggregation across markets × partners is infeasible without
  a subscription key. Also returns the World total split by transport-mode/2nd-partner — only the
  canonical `motCode=0, partner2Code=0` row is the true total (double-count bug, now filtered + tested).
- **Status:** RESOLVED (2026-07-11) with a free key. `comtrade.py` DUAL-MODE: `etl/.env` key →
  authenticated monthly `/data` (periods chunked ≤12/call — the endpoint caps at 12) → quarter
  aggregation + all-partner breakdown = full design. Verified live: flows=346, latest 2026-Q1,
  quarterly signals + partner sourcing charts. No key → keyless annual World-only fallback.
- **Where:** `etl/tradepulse_etl/sources/comtrade.py`, `settings.py` (.env loader).
- **Notes:** free key at https://comtradedeveloper.un.org/ (`etl/.env.example`). No paid tier / scraping.

## S-001 — Accuracy liability (outdated requirement → rejected container)
- **Symptom:** a stale Layer-3 requirement could cause a user's shipment to be rejected at port.
- **Cause:** Layer 3 is a curation business; sources change.
- **Status:** mitigated (live). Layer-2 profiles + Layer-3 requirement pages are now REAL curated
  (2026-07-11) from official sources — EUDR (Reg 2023/1115, applies 30 Dec 2026), Japan FIT +
  lifecycle-GHG reporting (from 1 Apr 2026), Korea legality + 2025 REC reform. Every item carries an
  official source_url + verified_date; the loader drops any unsourced item; disclaimer says official
  sources govern. **Residual risk:** rules change — needs a quarterly re-review (verified dates age).
- **Where:** plan §14, §8; `content/requirements/*.json`, `content/companies/pellets.json`.
- **Notes:** hard cap ≤20 requirement pages until revenue (maintenance burden, plan §14). Set a
  quarterly review calendar; the "last review" date per page surfaces staleness.

## L-004 — A CPV search returns notices where the product is one buried line item
**Found:** 2026-07-14 (owner: *"the product is tea but I see many buyers — do you guarantee those are buying tea?"*).
TED matches a notice if the CPV appears ANYWHERE in it. A school buying a 100-item food framework
lists tea among the lots, so it came back under "tea" — the feed showed buyers of *Bread* and
*Mineral water*. Correct match, worthless lead, and it implied a promise we could not keep.
**Handled:** every notice is classified against the searched CPV (`sources/ted.py::_match_kind`):
`contract` (the notice's main CPV is this product) · `lot` (a lot's main CPV is) · `basket` (buried).
Baskets are dropped at export. Measured: 1,574 scraped -> 923 basket / 343 lot / 308 contract.
**Residual:** a "lot" is real but partial — the buyer wants this product *inside* a bigger contract.
The UI labels it and shows the contract it sits inside.

## L-005 — The HS->CPV map is verified, but not always the identical good
**Found:** 2026-07-14, building tender coverage for all 1,240 products.
No official HS<->CPV crosswalk exists. `reference/_gen_cpv.py` proposes a CPV from the HS heading's
text and verifies it against live TED, so a code that returns nothing real is dropped (810 -> 654).
But a verified match can still be a *neighbour*: HS "Vegetables, dried" lands on CPV "Frozen
vegetables"; HS "Meat of sheep" on CPV "Sheep".
**Handled:** the matched CPV + label ship in `cpv-match.json` and the UI prints them per product
("matched to the nearest CPV category: Frozen vegetables"). The 18 pilot products are hand-checked
and flagged `exact`. Two guards keep the proposal sane: an HS-chapter -> CPV-division rule (without it
"Cashew nuts" matched CPV 44531600, *fastener* nuts) and a 0.6 score floor (at 0.5 "Crude oil" matched
"Oil paints"). A weak match is worse than none — the product simply gets no feed.
**Fix path:** hand-check the mappings for the products we actually sell; tighten HS6 children to their
narrower CPV (black tea 090240 -> 15863200 rather than the parent tea code).

## L-006 — Tenders, sellers and past orders are EU public procurement only
**Found:** 2026-07-14 (owner: *"where is my seller tab"* on a non-EU country).
Our tender/award source is EU TED. A Chinese buyer, a US buyer, or a seller who has never won an EU
public contract simply does not appear. Absence is a **coverage limit, not a verdict on the company** —
and if the UI just shows an empty box, a factory owner reads it as "no demand".
**Handled:** the country page states the limit, shows the product's tenders elsewhere when this
country has none, and never hides a tab (an empty tab explains itself).
**Fix path:** US SAM.gov awards, UK Contracts Finder, World Bank / UN awards. Same shape (a winner
named on a public award), so the same pipeline absorbs them.
