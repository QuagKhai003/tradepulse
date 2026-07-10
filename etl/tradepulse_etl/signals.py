"""
signals.py — deterministic YoY signal computation (plan §6). THE MOAT.
@context  Turns trade_flows into signal bands with a reproducible formula. Golden Rule: an LLM
          never touches this path — pure arithmetic over stored data only.
@done     classify_band(); compute_signals() over World-partner aggregates, YoY vs same quarter
          last year, with the §6.2 noise floors and §6.3 bands (incl. new-lane + suppressed 'minor').
@todo     Emit band-crossing diffs vs the previous run for signal alerts (batch 1.8).
@limits   PURE + DETERMINISTIC: no I/O, no network, no clock. `now_iso` is passed in by the caller.
@affects  Input: trade_flows rows (db.fetch_flows). Output: signal dicts (db.upsert_signals).
"""
from __future__ import annotations

from . import config


def prev_year_period(period: str) -> str:
    """Same period one year earlier (YoY, never QoQ — plan §6.1).
    Quarterly '2026-Q1' -> '2025-Q1'; annual '2024' -> '2023'."""
    if "-Q" in period:
        year, quarter = period.split("-")
        return f"{int(year) - 1}-{quarter}"
    return str(int(period) - 1)


def classify_band(yoy: float) -> str:
    """Magnitude -> band name (plan §6.3). Direction is carried by the sign of yoy."""
    a = abs(yoy)
    if a < config.BAND_MODERATE:
        return "minor"          # -15%..+15% suppressed by design
    if a < config.BAND_SIGNIFICANT:
        return "moderate"
    if a < config.BAND_SURGE:
        return "significant"
    return "surge" if yoy > 0 else "collapse"


def compute_signals(flows: list[dict], now_iso: str) -> list[dict]:
    """
    flows: trade_flows rows (dicts). Only World-partner aggregates form country signals.
    Returns one signal dict per (reporter, hs6, flow, period) that clears the floors, plus
    new-lane rows. 'minor' rows are kept (map tiles need YoY); the feed filters them out.
    """
    # Index: (reporter, hs6, flow) -> {period: value_usd}
    cells: dict[tuple, dict[str, float]] = {}
    for r in flows:
        if r["partner"] != config.PARTNER_WORLD:
            continue
        key = (r["reporter"], r["hs6"], r["flow"])
        cells.setdefault(key, {})[r["period"]] = float(r["value_usd"])

    out: list[dict] = []
    for (reporter, hs6, flow), by_period in cells.items():
        history = len(by_period)
        for period, value in by_period.items():
            base = by_period.get(prev_year_period(period))

            # No year-ago data at all -> can't form a YoY signal (insufficient history).
            if base is None:
                continue

            # New trade lane: the year-ago period exists but is (near-)zero, now above the
            # new-lane floor (plan §6.3). Does not require the 4-quarter history floor.
            if base < config.NOISE_MIN_BASE:
                if value >= config.NEW_LANE_MIN:
                    out.append(_row(reporter, hs6, flow, period, value, 0.0, "new", now_iso, base))
                continue

            # Standard signal: all noise floors must pass (plan §6.2).
            if value < config.NOISE_MIN_VALUE or history < config.NOISE_MIN_HISTORY:
                continue

            yoy = (value - base) / base
            out.append(_row(reporter, hs6, flow, period, value, yoy, classify_band(yoy), now_iso, base))
    return out


def _row(reporter, hs6, flow, period, value, yoy, band, now_iso, base=0.0) -> dict:
    return {
        "reporter": reporter, "hs6": hs6, "flow": flow, "period": period,
        "value_usd": value, "base_usd": base, "yoy_delta": yoy,
        "band": band, "computed_at": now_iso,
    }
