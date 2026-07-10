"""
comtrade.py — live UN Comtrade source (the production impl of the seam). DUAL-MODE.
@context  Real trade flows from UN Comtrade (plan §9.1).
          • WITH a free API key  -> authenticated /data endpoint: monthly, multi-period + all
            partners in one call per reporter -> quarter aggregation + partner breakdown (full design).
          • WITHOUT a key        -> keyless preview: annual World-only (one call per reporter×year),
            the tested fallback. Preview rejects multi-period (400) and rate-limits bursts (429).
@done     Both paths; Comtrade splits every total by transport-mode/2nd-partner -> keep only the
          canonical (motCode=0, partner2Code=0) row per (reporter, partner). Fixture-shaped output.
@todo     Wider history / bulk endpoint if we outgrow the free tier.
@limits   Network I/O. Authenticated path needs COMTRADE_SUBSCRIPTION_KEY (etl/.env). Not in test loop.
@affects  Implements base.TradeSource; selected by pipeline when --source=comtrade.
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from datetime import date

DATA_MONTHLY = "https://comtradeapi.un.org/data/v1/get/C/M/HS"        # authenticated (free key)
PREVIEW_ANNUAL = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"  # keyless fallback


def _is_total_row(r: dict) -> bool:
    """The fully-aggregated row for a partner (all transport modes, no 2nd partner)."""
    return (
        (r.get("partner2Code") in (0, None))
        and str(r.get("motCode") or "0") == "0"
        and str(r.get("customsCode") or "C00") == "C00"
    )


def _is_world_total(r: dict) -> bool:
    return r.get("partnerCode") == 0 and _is_total_row(r)


class ComtradeSource:
    name = "comtrade"

    def __init__(self, key: str | None = None, months: int = 30, years: int = 6,
                 timeout: int = 60, pause: float = 1.2):
        self.key = key
        self.months = months
        self.years = years
        self.timeout = timeout
        self.pause = pause

    def pull(self, hs_codes: list[str], reporters: list[int], partners: list[int] | None) -> list[dict]:
        hs = ",".join(hs_codes)
        return self._pull_authenticated(hs, reporters) if self.key else self._pull_keyless(hs, reporters)

    # --- authenticated: monthly, all partners, one call per reporter -> quarters ---
    def _pull_authenticated(self, hs: str, reporters: list[int]) -> list[dict]:
        months = ",".join(self._recent_months(self.months))
        monthly: list[dict] = []
        for reporter in reporters:
            params = {"reporterCode": reporter, "cmdCode": hs, "flowCode": "M", "period": months}
            rows = self._get(f"{DATA_MONTHLY}?{urllib.parse.urlencode(params)}", auth=True)
            monthly += [r for r in rows if _is_total_row(r)]   # keep every partner's canonical total
            time.sleep(self.pause)
        return self._to_quarters(monthly)

    # --- keyless: annual World-only, one call per reporter×year (tested fallback) ---
    def _pull_keyless(self, hs: str, reporters: list[int]) -> list[dict]:
        rows: list[dict] = []
        for reporter in reporters:
            for year in self._recent_years(self.years):
                params = {"reporterCode": reporter, "cmdCode": hs, "flowCode": "M",
                          "partnerCode": "0", "period": year}
                data = self._get(f"{PREVIEW_ANNUAL}?{urllib.parse.urlencode(params)}", auth=False)
                rows += [r for r in data if _is_world_total(r)]
                time.sleep(3.0)                      # respect the preview burst limit
        return self._normalise_annual(rows)

    def _get(self, url: str, auth: bool) -> list[dict]:
        headers = {"User-Agent": "tradepulse/0.1"}
        if auth and self.key:
            headers["Ocp-Apim-Subscription-Key"] = self.key
        for attempt in range(2):
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read().decode("utf-8")).get("data", []) or []
            except Exception as e:  # noqa: BLE001 — transient/rate-limit; back off once
                if attempt == 0:
                    time.sleep(self.pause * 4)
                    continue
                print(f"[comtrade] warn: {type(e).__name__}:{getattr(e, 'code', '')} for {url[:80]}")
                return []

    # --- monthly rows -> complete-quarter records (keeps the partner dimension) ---
    @staticmethod
    def _to_quarters(rows: list[dict]) -> list[dict]:
        agg: dict[tuple, dict] = {}
        for r in rows:
            period = str(r.get("period", ""))
            if len(period) != 6:
                continue
            year, month = period[:4], int(period[4:6])
            quarter = f"{year}-Q{(month - 1) // 3 + 1}"
            key = (r.get("reporterCode"), r.get("partnerCode"), str(r.get("cmdCode")), quarter)
            c = agg.setdefault(key, {"value": 0.0, "wgt": 0.0, "months": set()})
            c["value"] += float(r.get("primaryValue") or 0)
            c["wgt"] += float(r.get("netWgt") or 0)
            c["months"].add(month)
        return [
            {"reporterCode": rep, "partnerCode": par, "cmdCode": cmd, "period": quarter,
             "flowCode": "M", "primaryValue": round(c["value"], 2), "netWgt": round(c["wgt"], 2),
             "qtyUnitAbbr": "kg", "publishedDate": None}
            for (rep, par, cmd, quarter), c in agg.items() if len(c["months"]) >= 3
        ]

    @staticmethod
    def _normalise_annual(rows: list[dict]) -> list[dict]:
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
    def _recent_months(n: int) -> list[str]:
        y, m = date.today().year, date.today().month
        out = []
        for _ in range(n):
            m -= 1
            if m == 0:
                m, y = 12, y - 1
            out.append(f"{y}{m:02d}")
        return out

    @staticmethod
    def _recent_years(n: int) -> list[int]:
        y = date.today().year
        return list(range(y - n, y))
