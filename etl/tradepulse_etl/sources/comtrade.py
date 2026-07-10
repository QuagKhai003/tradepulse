"""
comtrade.py — live UN Comtrade source (the production impl of the seam).
@context  Real trade flows from the free Comtrade preview API (plan §9.1, keyless, rate-limited to
          ONE period per request + low burst). To stay within that, v1 pulls ANNUAL World totals
          (partner 0) per reporter — enough for the map, signals, tiles, and feed. Quarterly +
          partner breakdown need a subscription key (documented upgrade); drill-down degrades
          gracefully to "no sourcing data" until then.
@done     Per reporter × recent year: one keyless request, client-side filter to partner=0, sum,
          emit fixture-shaped raw records with annual periods ('YYYY').
@todo     Add subscription key -> monthly pull + quarter aggregation + partner breakdown.
@limits   Network I/O; ~3s between calls to respect the burst limit. Not used in the fast test loop.
@affects  Implements base.TradeSource; selected by pipeline when --source=comtrade.
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from datetime import date

BASE_ANNUAL = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"


def _is_world_total(r: dict) -> bool:
    """The single fully-aggregated World row (all transport modes, no 2nd partner)."""
    return (
        r.get("partnerCode") == 0
        and (r.get("partner2Code") in (0, None))
        and str(r.get("motCode") or "0") == "0"
        and str(r.get("customsCode") or "C00") == "C00"
    )


class ComtradeSource:
    name = "comtrade"

    def __init__(self, years: int = 6, timeout: int = 45, pause: float = 3.0):
        self.years = years
        self.timeout = timeout
        self.pause = pause

    def pull(self, hs_codes: list[str], reporters: list[int], partners: list[int] | None) -> list[dict]:
        hs = ",".join(hs_codes)
        rows: list[dict] = []
        for reporter in reporters:
            for year in self._recent_years(self.years):
                rows += self._fetch_world(reporter, hs, year)
                time.sleep(self.pause)
        return self._normalise(rows)

    def _fetch_world(self, reporter: int, hs: str, year: int) -> list[dict]:
        params = {"reporterCode": reporter, "cmdCode": hs, "flowCode": "M",
                  "partnerCode": "0", "period": year}
        url = f"{BASE_ANNUAL}?{urllib.parse.urlencode(params)}"
        for attempt in range(2):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "tradepulse/0.1"})
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8")).get("data", []) or []
                # Keep ONLY the fully-aggregated World total. Comtrade returns the same total broken
                # out by transport mode (motCode) + 2nd partner (partner2Code); summing them all
                # multi-counts. The canonical row has both at their "all" value.
                return [r for r in data if _is_world_total(r)]
            except Exception as e:  # noqa: BLE001 — 429/transient; back off once
                if attempt == 0:
                    time.sleep(self.pause * 3)
                    continue
                print(f"[comtrade] warn: reporter={reporter} year={year} failed: {type(e).__name__}"
                      f":{getattr(e, 'code', '')}")
                return []

    @staticmethod
    def _normalise(rows: list[dict]) -> list[dict]:
        # Sum any duplicate rows per (reporter, partner, year) into one annual record.
        agg: dict[tuple, dict] = {}
        for r in rows:
            key = (r.get("reporterCode"), r.get("partnerCode"), str(r.get("cmdCode")), str(r.get("period")))
            c = agg.setdefault(key, {"value": 0.0, "wgt": 0.0})
            c["value"] += float(r.get("primaryValue") or 0)
            c["wgt"] += float(r.get("netWgt") or 0)
        return [
            {"reporterCode": rep, "partnerCode": par, "cmdCode": cmd, "period": period,
             "flowCode": "M", "primaryValue": round(c["value"], 2), "netWgt": round(c["wgt"], 2),
             "qtyUnitAbbr": "kg", "publishedDate": None}
            for (rep, par, cmd, period), c in agg.items()
        ]

    @staticmethod
    def _recent_years(n: int) -> list[int]:
        y = date.today().year
        return list(range(y - n, y))   # e.g. 2026 -> 2020..2025
