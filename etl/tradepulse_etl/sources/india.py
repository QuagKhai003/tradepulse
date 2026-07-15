"""
india.py — fresh national primary: India DGCI&S TRADESTAT (keyless, CSRF-token + session, no login).
@context  India's official trade databank. One POST (after grabbing the page's _token + session cookie)
          returns the whole HS4 export or import table for a fiscal year, in US$ million. Refreshes
          INDIA's own map cell (reporter 699) with India's own authority, fresher/firmer than Comtrade.
@shape    The table is HTML: rows of [serial, HS4, commodity, prev-yr US$M, %share, cur-yr US$M, ...].
          We take the current fiscal year's value (config.INDIA_FY -> FY2024-25). Fetched ONCE and cached
          (one call has every commodity), then filtered to the pilots.
@caveat   India's FY is Apr–Mar; period is labelled by the FY start year (config.INDIA_FY). A fiscal year
          is not a calendar year — a known, documented approximation, like the mirror's 'est.' tag.
@nonuse   Not for rebuilding VN's world total (India is one buyer -> would understate VN, Golden Rule).
@limits   Network in _table only; pure parsing otherwise. Fragile by nature (HTML + CSRF) — a failed
          fetch yields no rows (Comtrade still covers India), never a wrong number.
@affects  Implements the TradeSource pull() shape; transformed by transform_all, merged by merge_flows.
"""
from __future__ import annotations

import html
import http.cookiejar
import re
import urllib.parse
import urllib.request

from .. import config

BASE = "https://tradestat.commerce.gov.in/eidb/"
_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
_TOKEN = re.compile(r'name="_token" value="([^"]+)"')
_HS4 = re.compile(r"^\d{4}$")


class IndiaSource:
    name = "india"

    def __init__(self, timeout: int = 60):
        self.timeout = timeout
        self._tables: dict[str, dict[str, float]] | None = None

    def pull(self, hs_codes: list[str], reporters, partners, skip=None) -> list[dict]:
        codes = [h for h in hs_codes if h in config.INDIA_HS]
        if not codes:
            return []
        skip = skip or frozenset()
        tables = self._load()
        period = config.INDIA_FY
        rows: list[dict] = []
        for hs in codes:
            for flow, tbl in tables.items():
                v = tbl.get(hs)
                if v is None or (hs, period) in skip:
                    continue
                rows.append({"reporterCode": config.INDIA_M49, "partnerCode": 0, "cmdCode": hs,
                             "period": period, "flowCode": flow, "primaryValue": round(v, 2),
                             "netWgt": None, "qtyUnitAbbr": None, "publishedDate": None})
        return rows

    def _load(self) -> dict[str, dict[str, float]]:
        if self._tables is None:
            self._tables = {"X": self._table("commodity_wise_export", "e"),
                            "M": self._table("commodity_wise_import", "i")}
        return self._tables

    def _table(self, endpoint: str, sfx: str) -> dict[str, float]:
        """GET the page (session cookie + _token), POST for all HS4 rows, parse -> {hs4: USD}."""
        try:
            cj = http.cookiejar.CookieJar()
            op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
            op.addheaders = [("User-Agent", "Mozilla/5.0 tradepulse/0.1")]
            page = op.open(BASE + endpoint, timeout=self.timeout).read().decode("utf-8", "replace")
            tok = _TOKEN.search(page).group(1)
            body = urllib.parse.urlencode({
                "_token": tok, f"EidbYearCw{sfx}": config.INDIA_FY, "comType": "all",
                f"EidbComLevelCw{sfx}": "4", "commodityType": "all", f"Eidb_ReportCw{sfx}": "2",
            }).encode()
            req = urllib.request.Request(BASE + endpoint, data=body, headers={"X-CSRF-TOKEN": tok})
            resp = op.open(req, timeout=self.timeout).read().decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001 — fragile source; Comtrade still covers India
            print(f"[india] warn {type(e).__name__} on {endpoint}")
            return {}
        return self._parse(resp)

    @staticmethod
    def _parse(text: str) -> dict[str, float]:
        out: dict[str, float] = {}
        for r in _ROW.findall(text):
            c = [html.unescape(re.sub(r"<[^>]+>", "", x)).strip() for x in _CELL.findall(r)]
            # [serial, HS4, name, prev US$M, %share, CUR US$M, ...] — take the current fiscal year value.
            if len(c) >= 6 and _HS4.match(c[1]):
                try:
                    out[c[1]] = float(c[5].replace(",", "")) * 1_000_000     # US$M -> USD
                except ValueError:
                    continue
        return out
