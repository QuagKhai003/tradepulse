"""
fx.py — convert national trade values (EUR/GBP) to USD so multi-source merge compares like with like.
@context  US Census + Comtrade are USD; Eurostat is EUR, HMRC is GBP. Before a non-USD national row
          can override Comtrade for its country, its value must be in USD. Rates are ECB reference
          exchange rates (public, keyless, deterministic), matched to the row's period + grain.
@done     to_usd() PURE + tested; ECBFx.rates() fetches EUR->USD and EUR->GBP at A/Q/M grain.
@limits   to_usd is pure (no I/O); only network is ECBFx._get. USD passthrough; EUR/GBP supported.
@affects  Used by national EUR/GBP source adapters before they hand rows to transform/merge.
"""
from __future__ import annotations

import csv
import io
import urllib.request

ECB = "https://data-api.ecb.europa.eu/service/data/EXR"   # SDMX; {FREQ}.{CUR}.EUR.SP00.A


def ecb_period(period: str) -> str:
    """Our period -> ECB TIME_PERIOD. '2025'->'2025', '2025-Q1'->'2025-Q1', '202501'->'2025-01'."""
    p = str(period)
    if "-Q" in p:
        return p
    if len(p) == 6 and p.isdigit():
        return f"{p[:4]}-{p[4:]}"
    return p


def to_usd(value, currency, period, usd_per_eur: dict, gbp_per_eur: dict):
    """PURE. Convert `value` in `currency` to USD using ECB per-EUR rates for the row's period.
    usd_per_eur/gbp_per_eur: {ecb_period: rate}. Returns None if no rate exists (caller drops the row
    rather than guess). USD passes through unchanged."""
    if value is None:
        return None
    cur = (currency or "USD").upper()
    if cur == "USD":
        return value
    p = ecb_period(period)
    usd = usd_per_eur.get(p)
    if usd is None:
        return None
    if cur == "EUR":
        return value * usd
    if cur == "GBP":
        gbp = gbp_per_eur.get(p)          # GBP per EUR -> GBP->USD = (USD/EUR) / (GBP/EUR)
        return (value * usd / gbp) if gbp else None
    return None


class ECBFx:
    """Fetch ECB reference rates (EUR base) at the grains we store."""

    def __init__(self, timeout: int = 60):
        self.timeout = timeout

    def rates(self, freqs: tuple[str, ...] = ("A", "Q", "M"),
              currencies: tuple[str, ...] = ("USD", "GBP"), start: str = "2018") -> dict[str, dict]:
        out: dict[str, dict] = {c: {} for c in currencies}
        for freq in freqs:
            for cur in currencies:
                url = f"{ECB}/{freq}.{cur}.EUR.SP00.A?format=csvdata&startPeriod={start}"
                out[cur].update(self._parse(self._get(url)))
        return out

    def _get(self, url: str) -> str:
        req = urllib.request.Request(url, headers={"User-Agent": "tradepulse/0.1"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return r.read().decode("utf-8")

    @staticmethod
    def _parse(text: str) -> dict[str, float]:
        rows: dict[str, float] = {}
        for row in csv.DictReader(io.StringIO(text)):
            p, v = row.get("TIME_PERIOD"), row.get("OBS_VALUE")
            if p and v:
                try:
                    rows[p] = float(v)
                except ValueError:
                    pass
        return rows
