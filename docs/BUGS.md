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
- **Status:** addressed-by-design.
- **Where:** plan §6.4. Default importer-reported per view; state it in a tooltip.
- **Notes:** Vietnam-tile headline side (GDVC vs importer) still open — plan §15 Q4.

## L-003 — Comtrade free preview: annual World-only (no quarterly, no partners)
- **Symptom:** live `--source comtrade` returns ANNUAL World totals only; drill-down shows "no
  sourcing data"; signals are annual YoY, not quarterly.
- **Cause:** the keyless preview endpoint rejects multi-period requests (HTTP 400) and rate-limits
  bursts (HTTP 429), so monthly→quarter aggregation across markets × partners is infeasible without
  a subscription key. Also returns the World total split by transport-mode/2nd-partner — only the
  canonical `motCode=0, partner2Code=0` row is the true total (double-count bug, now filtered + tested).
- **Status:** RESOLVED-when-keyed. `comtrade.py` is now DUAL-MODE: a FREE Comtrade API key
  (`etl/.env` → `COMTRADE_SUBSCRIPTION_KEY`) switches to the authenticated monthly `/data` endpoint
  (multi-period + all partners in one call) → quarter aggregation + partner breakdown = full design.
  Without a key it falls back to the tested keyless annual World-only path.
- **Where:** `etl/tradepulse_etl/sources/comtrade.py` (both paths), `settings.py` (.env loader).
- **Notes:** free key registration — https://comtradedeveloper.un.org/ (see `etl/.env.example`).
  No paid tier or scraping needed. Regression tests cover the total-row filter + quarter aggregation.

## S-001 — Accuracy liability (outdated requirement → rejected container)
- **Symptom:** a stale Layer-3 requirement could cause a user's shipment to be rejected at port.
- **Cause:** Layer 3 is a curation business; sources change.
- **Status:** open — mitigations mandated before any Layer-3 ships.
- **Where:** plan §14, §8. Source link + verified date per item; "last full review" per page;
  change log; "official sources govern" disclaimer.
- **Notes:** hard cap ≤20 requirement pages until revenue (maintenance burden, plan §14).
