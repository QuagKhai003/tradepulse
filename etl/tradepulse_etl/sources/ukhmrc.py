"""
ukhmrc.py — UK source (HMRC uktradeinfo OTS): UK total trade per HS, GBP converted to USD.
@context  Fresher + authoritative for the UK (reporter 826) than Comtrade. HMRC OTS reports monthly by
          CN8 commodity x partner; we sum to the UK annual total per HS6/HS4, both flows, and convert
          GBP -> USD via fx.to_usd so it merges with the rest. Keyless (OData) but WAF-guarded, so a
          browser User-Agent is required. Verified: no all-country sentinel row, so summing is safe.
@warn     Flow split is EU/Non-EU: imports = FlowTypeId 1+3, exports = 2+4. Value is in GBP (pounds).
@done     pull() -> Comtrade-shaped raw rows (reporter=826, partner=World); _aggregate() pure + tested.
@limits   Network in _get + ECBFx. Annual now; skips TOTAL; honours the incremental `skip` set.
@affects  Implements base.TradeSource; merged in pipeline. Tested by tests/test_ukhmrc.py.
"""
from __future__ import annotations

import json
import time
import urllib.request
from datetime import date
from urllib.parse import quote

from ..fx import ECBFx, to_usd

UK_REPORTER = 826
WORLD = 0
BASE = "https://api.uktradeinfo.com/OTS"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
IMPORT_FLOWS = {1, 3}   # EU + Non-EU imports
EXPORT_FLOWS = {2, 4}   # EU + Non-EU exports


class UKHmrcSource:
    name = "hmrc"

    def __init__(self, years: int = 6, timeout: int = 60, pause: float = 0.6, fx: dict | None = None):
        self.years = years
        self.timeout = timeout
        self.pause = pause
        self._fx = fx

    def _rates(self) -> dict:
        if self._fx is None:
            self._fx = ECBFx().rates(freqs=("A",), currencies=("USD", "GBP"))
        return self._fx

    def pull(self, hs_codes: list[str], reporters: list[int], partners: list[int] | None,
             skip: frozenset = frozenset()) -> list[dict]:
        fx = self._rates()
        usd, gbp = fx.get("USD", {}), fx.get("GBP", {})
        years = [str(y) for y in range(date.today().year - self.years, date.today().year)]
        rows: list[dict] = []
        for hs in hs_codes:
            if hs == "TOTAL":
                continue
            field = "Hs4Code" if len(hs) == 4 else "Hs6Code"
            for year in years:
                if (hs, year) in skip:
                    continue
                data = self._get_year(hs, field, year)
                rows += self._aggregate(data, hs, year, usd, gbp)
                time.sleep(self.pause)
        return rows

    def _get_year(self, hs: str, field: str, year: str) -> list[dict]:
        filt = f"MonthId ge {year}01 and MonthId le {year}12 and Commodity/{field} eq '{hs}'"
        url = f"{BASE}?$filter={quote(filt, safe='/')}&$select=FlowTypeId,Value&$top=40000"
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        for attempt in range(2):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    return json.loads(r.read().decode("utf-8")).get("value", []) or []
            except Exception as e:  # noqa: BLE001 — WAF/transient; back off once
                if attempt == 0:
                    time.sleep(self.pause * 4)
                    continue
                print(f"[hmrc] warn: {type(e).__name__}:{getattr(e, 'code', '')} for {url[:80]}")
                return []

    # --- pure: HMRC month rows -> one UK World row per flow (annual), GBP converted via the FX step ---
    @staticmethod
    def _aggregate(rows: list[dict], hs: str, year: str, usd_per_eur: dict, gbp_per_eur: dict) -> list[dict]:
        imp = exp = 0.0
        for r in rows:
            f, v = r.get("FlowTypeId"), (r.get("Value") or 0)
            if f in IMPORT_FLOWS:
                imp += v
            elif f in EXPORT_FLOWS:
                exp += v
        out = []
        for gbp_val, flow in ((imp, "M"), (exp, "X")):
            usd_v = to_usd(gbp_val, "GBP", year, usd_per_eur, gbp_per_eur)
            if usd_v and usd_v > 0:
                out.append({"reporterCode": UK_REPORTER, "partnerCode": WORLD, "cmdCode": hs,
                            "period": year, "flowCode": flow, "primaryValue": round(usd_v, 2),
                            "netWgt": None, "qtyUnitAbbr": None, "publishedDate": f"{year}-12"})
        return out
