"""
eurostat.py — EU source (Eurostat Comext DS-045409): EU27 extra-EU trade per HS, EUR converted to USD.
@context  Fresher + authoritative for the EU (reporter 97) than Comtrade. Comext reports the EU as one
          (`EU27_2020`) trading with the rest of the world (`EXT_EU27_2020` = extra-EU), which is exactly
          our World-partner demand measure. Values are EUR -> converted to USD via fx.to_usd so they
          merge with Comtrade/Census. Keyless. Annual now; quarterly/monthly are a later increment.
@warn     Use partner EXT_EU27_2020 (extra-EU), NOT the all-partner total (that includes intra-EU).
@done     pull() -> Comtrade-shaped raw rows (reporter=97, partner=World); _parse() pure + tested.
@limits   Network in _get + ECBFx. Skips TOTAL (leave to Comtrade). Honours the incremental `skip` set.
@affects  Implements base.TradeSource; merged in pipeline. Tested by tests/test_eurostat.py.
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from datetime import date

from ..fx import ECBFx, to_usd

EU_REPORTER = 97
WORLD = 0
BASE = "https://ec.europa.eu/eurostat/api/comext/dissemination/sdmx/2.1/data/DS-045409"
_FLOW = {"1": "M", "2": "X"}   # Comext flow code -> our flow (import / export)


class EurostatSource:
    name = "eurostat"

    def __init__(self, years: int = 6, timeout: int = 60, pause: float = 0.4, fx: dict | None = None):
        self.years = years
        self.timeout = timeout
        self.pause = pause
        self._fx = fx          # {"USD": {period: rate}}; fetched once if not injected

    def _usd_per_eur(self) -> dict:
        if self._fx is None:
            self._fx = ECBFx().rates(freqs=("A",), currencies=("USD",))
        return self._fx.get("USD", {})

    def pull(self, hs_codes: list[str], reporters: list[int], partners: list[int] | None,
             skip: frozenset = frozenset()) -> list[dict]:
        usd = self._usd_per_eur()
        years = [str(y) for y in range(date.today().year - self.years, date.today().year)]
        rows: list[dict] = []
        for hs in hs_codes:
            if hs == "TOTAL":
                continue
            wanted = {y for y in years if (hs, y) not in skip}   # incremental
            if not wanted:
                continue
            lo, hi = min(wanted), max(wanted)
            for flow_code, flow in _FLOW.items():
                key = f"A.EU27_2020.EXT_EU27_2020.{hs}.{flow_code}.VALUE_IN_EUROS"
                params = {"format": "JSON", "startPeriod": lo, "endPeriod": hi}
                data = self._get(f"{BASE}/{key}?{urllib.parse.urlencode(params)}")
                rows += self._parse(data, hs, flow, usd, wanted)
                time.sleep(self.pause)
        return rows

    # --- pure: JSON-stat -> USD raw rows (one per period), EUR converted via the FX step ---
    @staticmethod
    def _parse(data: dict | None, hs: str, flow: str, usd_per_eur: dict, wanted: set) -> list[dict]:
        if not data or "value" not in data:
            return []
        tcat = data.get("dimension", {}).get("time", {}).get("category", {}).get("index", {})
        vals = data.get("value", {})
        out = []
        for period, idx in tcat.items():
            if period not in wanted:
                continue
            v = vals.get(str(idx))
            if v is None:
                continue
            usd_v = to_usd(float(v), "EUR", period, usd_per_eur, {})
            if not usd_v or usd_v <= 0:
                continue
            out.append({"reporterCode": EU_REPORTER, "partnerCode": WORLD, "cmdCode": hs,
                        "period": period, "flowCode": flow, "primaryValue": round(usd_v, 2),
                        "netWgt": None, "qtyUnitAbbr": None, "publishedDate": f"{period}-12"})
        return out

    def _get(self, url: str) -> dict | None:
        req = urllib.request.Request(url, headers={"User-Agent": "tradepulse/0.1"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001 — no-data years 404; skip
            print(f"[eurostat] warn: {type(e).__name__}:{getattr(e, 'code', '')} for {url[:80]}")
            return None
