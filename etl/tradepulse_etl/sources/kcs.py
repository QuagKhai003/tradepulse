"""
kcs.py — Korea Customs Service trade statistics (data.go.kr #15100475). Fresh national primary for KR.
@context  Korea is the authority on its own trade, monthly, fresh to ~last month (fresher than Comtrade
          annual). One call covers a whole YYYYMM range × all partner countries for an HS, so it's cheap.
          Merge lets it OVERRIDE Comtrade for reporter=410 (config.SOURCE_AUTHORITY['kcs']).
@warn     Values (expDlr/impDlr) are in US DOLLARS — verified against Korea's known ~$1.7B 2025 coffee
          imports (NOT thousand-USD). Response rows are per (HS6 child × partner country × month); the
          'year=총계' grand-total rows and hsCd='-' rows are aggregates — skip them. We sum the children
          of the queried HS over all partners -> Korea's World total per (product, month).
@golden   Public national statistics; value/volume only.
@limits   Network in _get only; XML parsing pure. Needs KCS_SERVICE_KEY (free data.go.kr key, and the
          #15100475 service must be approved for that key — a 403 means not-yet-approved).
@affects  Implements the source protocol; merged with Comtrade in the pipeline. reporter fixed = 410.
"""
from __future__ import annotations

import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date

KR_REPORTER = 410
WORLD = 0
BASE = "https://apis.data.go.kr/1220000/nitemtrade/getNitemtradeList"


class KcsSource:
    name = "kcs"

    def __init__(self, key: str | None = None, years: int = 2, timeout: int = 60, pause: float = 0.5,
                 freqs: tuple[str, ...] = ("A",)):
        self.key = key
        self.years = years
        self.timeout = timeout
        self.pause = pause
        self.freqs = freqs

    def pull(self, hs_codes: list[str], reporters: list[int], partners: list[int] | None,
             skip: frozenset = frozenset()) -> list[dict]:
        if not self.key:
            print("[kcs] no KCS_SERVICE_KEY — skipping")
            return []
        rows: list[dict] = []
        for hs in hs_codes:
            if hs == "TOTAL":
                continue
            month_val: dict[tuple, float] = {}
            for start, end in self._windows():           # the API caps a query at ~12 months
                self._merge(month_val, self._pull_hs(hs, start, end))
            if month_val:
                rows += self._aggregate(hs, month_val, self.freqs)
        return rows

    @staticmethod
    def _merge(into: dict, more: dict) -> None:
        for k, v in more.items():
            into[k] = into.get(k, 0.0) + v

    def _windows(self) -> list[tuple[str, str]]:
        """[(strtYymm, endYymm)] in <=12-month (per-calendar-year) chunks — the API rejects longer."""
        t = date.today()
        out = []
        for y in range(t.year - self.years, t.year + 1):
            end_m = t.month if y == t.year else 12
            out.append((f"{y}01", f"{y}{end_m:02d}"))
        return out

    def _pull_hs(self, hs: str, start: str, end: str) -> dict:
        url = f"{BASE}?serviceKey={self.key}&" + urllib.parse.urlencode(
            {"strtYymm": start, "endYymm": end, "hsSgn": hs})
        body = self._get(url)
        if not body:
            return {}
        month_val: dict[tuple, float] = {}
        for it in ET.fromstring(body).findall(".//item"):
            y = it.findtext("year")
            if not y or y == "총계" or it.findtext("hsCd") in ("-", None):   # skip grand-total rows
                continue
            ym = y.replace(".", "")                       # '2026.01' -> '202601'
            if len(ym) != 6:
                continue
            exp = _num(it.findtext("expDlr"))
            imp = _num(it.findtext("impDlr"))
            if exp:
                month_val[("X", ym)] = month_val.get(("X", ym), 0.0) + exp
            if imp:
                month_val[("M", ym)] = month_val.get(("M", ym), 0.0) + imp
        return month_val

    @staticmethod
    def _aggregate(hs: str, month_val: dict, freqs: tuple) -> list[dict]:
        """Monthly Korea World totals -> quarter rows (complete quarters) and/or annual (complete years)."""
        out: list[dict] = []
        if "Q" in freqs:
            q: dict[tuple, list] = {}
            for (flow, ym), v in month_val.items():
                key = (flow, f"{ym[:4]}-Q{(int(ym[4:]) - 1) // 3 + 1}")
                q.setdefault(key, []).append(v)
            for (flow, period), vals in q.items():
                if len(vals) >= 3:                        # complete quarter only
                    out.append(_row(hs, period, flow, sum(vals)))
        if "A" in freqs:
            yr: dict[tuple, list] = {}
            for (flow, ym), v in month_val.items():
                yr.setdefault((flow, ym[:4]), []).append(v)
            for (flow, period), vals in yr.items():
                if len(vals) >= 12:                       # complete year only
                    out.append(_row(hs, period, flow, sum(vals)))
        return out

    def _range(self) -> tuple[str, str]:
        t = date.today()
        return f"{t.year - self.years}01", f"{t.year}{t.month:02d}"

    def _get(self, url: str) -> str | None:
        for attempt in range(2):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return resp.read().decode("utf-8")
            except Exception as e:  # noqa: BLE001 — transient; 403 = service not approved for the key
                if attempt == 0:
                    time.sleep(self.pause * 3)
                    continue
                print(f"[kcs] warn: {type(e).__name__}:{getattr(e, 'code', '')} for {url[:70]}")
                return None


def _num(s) -> float:
    try:
        return float(s)
    except (TypeError, ValueError):
        return 0.0


def _row(hs: str, period: str, flow: str, value: float) -> dict:
    return {"reporterCode": KR_REPORTER, "partnerCode": WORLD, "cmdCode": hs, "period": period,
            "flowCode": flow, "primaryValue": round(value, 2), "netWgt": None, "qtyUnitAbbr": None,
            "publishedDate": None}
