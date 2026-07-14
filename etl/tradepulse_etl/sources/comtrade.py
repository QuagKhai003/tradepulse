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

from .. import config

DATA_ANNUAL = "https://comtradeapi.un.org/data/v1/get/C/A/HS"          # authenticated (free key)
DATA_MONTHLY = "https://comtradeapi.un.org/data/v1/get/C/M/HS"        # authenticated (reserved)
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


def _chunks(items: list, n: int) -> list[list]:
    return [items[i:i + n] for i in range(0, len(items), n)]


def _quarter_of(month: str) -> str:
    """'YYYYMM' -> 'YYYY-Qn' (which quarter a month belongs to, for incremental skip)."""
    y, m = month[:4], int(month[4:6])
    return f"{y}-Q{(m - 1) // 3 + 1}"


class ComtradeSource:
    name = "comtrade"
    batched = True          # cmdCode takes a LIST -> pull() wants many products at once, not one

    PERIODS_PER_CALL = 12   # authenticated /data hard limit: "Maximum number of periods is 12"
    MONTHLY_ALL_CHUNK = 1   # all-reporters monthly is heavy -> ONE month per call (12 -> timeout)
    # cmdCode takes a COMMA-SEPARATED list, so one call can cover many products. That is what makes a
    # 1,240-product refresh possible at all on a free key (~500 calls/day): 1 call per 10 products per
    # year instead of 1 per product per year. The API truncates a response at ROW_CAP rows, so a batch
    # that comes back at the cap is re-fetched in halves (silent truncation would drop whole countries).
    CODES_PER_CALL = 40
    MONTHLY_CODES_PER_CALL = 8   # monthly all-reporters is heavy; big batches time out
    ROW_CAP = 100_000
    # server-side equivalent of _is_total_row: the fully-aggregated cell only
    TOTALS_ONLY = {"customsCode": "C00", "motCode": "0", "partner2Code": "0"}

    def __init__(self, key: str | None = None, months: int = 24, years: int = 6,
                 months_sourcing: int = 24, timeout: int = 60, pause: float = 1.2,
                 freqs: tuple[str, ...] = ("A",), quarterly_hs: list[str] | None = None):
        self.key = key
        self.months = months
        self.years = years
        self.months_sourcing = months_sourcing
        self.timeout = timeout
        self.pause = pause
        self.freqs = freqs          # ('A',) annual only; ('A','Q') also monthly->quarterly (fresher)
        self.quarterly_hs = set(quarterly_hs) if quarterly_hs else None   # bound the quarterly pull

    # --- quarterly + all-partner data for a few focus reporters (drill-down sourcing) ---
    def pull_sourcing(self, hs_codes: list[str], reporters: list[int]) -> list[dict]:
        """Monthly, per reporter, ALL partners (no partnerCode) -> quarters. Needs the key."""
        if not self.key:
            return []
        months = self._recent_months(self.months_sourcing)
        monthly: list[dict] = []
        for reporter in reporters:
            for hs in hs_codes:
                for chunk in _chunks(months, self.PERIODS_PER_CALL):
                    params = {"reporterCode": reporter, "cmdCode": hs, "flowCode": "M,X",
                              "period": ",".join(chunk)}   # no partnerCode -> all partners
                    data = self._get(f"{DATA_MONTHLY}?{urllib.parse.urlencode(params)}", auth=True)
                    monthly += [r for r in data if _is_total_row(r)]
                    time.sleep(self.pause)
        return self._to_quarters(monthly)

    def pull(self, hs_codes: list[str], reporters: list[int], partners: list[int] | None,
             skip: frozenset = frozenset()) -> list[dict]:
        if not self.key:
            return self._pull_keyless(",".join(hs_codes), reporters)
        out: list[dict] = []
        if "A" in self.freqs:
            out += self._pull_annual(hs_codes, skip)
        if "Q" in self.freqs:
            out += self._pull_quarterly(hs_codes, skip)
        return out

    # --- authenticated: per HS, ALL reporters, BOTH flows, World partner; ANNUAL (light + global) ---
    def _pull_annual(self, hs_codes: list[str], skip: frozenset = frozenset()) -> list[dict]:
        # One annual call per (HS, year) returns every country, both flows (X+M). Skip (hs, year) pairs
        # already stored + final — that's the incremental win (a re-run only fetches the recent years).
        rows: list[dict] = []
        for year in self._recent_years(self.years):
            todo = [hs for hs in hs_codes if (hs, str(year)) not in skip]
            for chunk in _chunks(todo, self.CODES_PER_CALL):
                rows += self._annual_batch(chunk, year)
        return self._normalise_annual(rows)

    def _annual_batch(self, codes: list[str], year: int) -> list[dict]:
        """One call for many products; halve and retry if the row cap truncated the response."""
        params = {"cmdCode": ",".join(codes), "flowCode": "M,X", "partnerCode": "0", "period": year,
                  **self.TOTALS_ONLY}
        data = self._get(f"{DATA_ANNUAL}?{urllib.parse.urlencode(params)}", auth=True)
        time.sleep(self.pause)
        if len(data) >= self.ROW_CAP and len(codes) > 1:
            mid = len(codes) // 2
            return self._annual_batch(codes[:mid], year) + self._annual_batch(codes[mid:], year)
        return [r for r in data if _is_total_row(r)]

    # --- authenticated: per HS, ALL reporters, World partner, BOTH flows; MONTHLY -> QUARTERS ---
    def _pull_quarterly(self, hs_codes: list[str], skip: frozenset = frozenset()) -> list[dict]:
        # Monthly all-reporters World totals aggregated to COMPLETE quarters (>=3 months). ONE month per
        # call (all-country monthly is heavy; 12-period calls time out). Bounded to core products, and
        # skips months whose quarter is already stored + final (incremental).
        codes = [hs for hs in hs_codes if hs != "TOTAL"
                 and (self.quarterly_hs is None or hs in self.quarterly_hs)]
        if not codes:
            return []
        months = self._recent_months(self.months)
        rows: list[dict] = []
        # One call PER MONTH for the whole product batch (cmdCode is a list), World totals only. Same
        # optimisation as the annual pull: totals-only params drop the customs x transport breakdown we
        # would otherwise download and discard. A month whose quarter is already final for EVERY code is
        # skipped (incremental).
        for m in months:
            todo = [hs for hs in codes if (hs, _quarter_of(m)) not in skip]
            for batch in _chunks(todo, self.MONTHLY_CODES_PER_CALL):
                params = {"cmdCode": ",".join(batch), "flowCode": "M,X", "partnerCode": "0",
                          "period": m, **self.TOTALS_ONLY}
                data = self._get(f"{DATA_MONTHLY}?{urllib.parse.urlencode(params)}", auth=True)
                rows += [r for r in data if _is_world_total(r)]
                time.sleep(self.pause)
        return self._to_quarters(rows)

    def pull_mirror(self, hs_codes: list[str], years: list[int]) -> list[dict]:
        """MIRROR exports: for each (product, year), pull every reporter's imports from every partner
        (one bilateral call), then sum by PARTNER — world imports FROM country E = E's exports as its
        buyers saw them. This is how a late/non-reporter (Vietnam reports Comtrade ~2 years late) still
        gets a recent figure. Emitted as flow 'X', partner=World, so it merges like a direct export row
        but tagged source='comtrade-mirror' (lower priority -> only fills cells no direct source has).
        One product per... no: batched CODES_PER_CALL at a time; a batch at the row cap splits in half."""
        rows: list[dict] = []
        for year in years:
            for chunk in _chunks(hs_codes, self.CODES_PER_CALL):
                rows += self._mirror_batch(chunk, year)
        return rows

    def _mirror_batch(self, codes: list[str], year: int) -> list[dict]:
        params = {"cmdCode": ",".join(c for c in codes if c != "TOTAL"), "flowCode": "M",
                  "period": year, **self.TOTALS_ONLY}          # all reporters, all partners (bilateral)
        if not params["cmdCode"]:
            return []
        data = self._get(f"{DATA_ANNUAL}?{urllib.parse.urlencode(params)}", auth=True)
        time.sleep(self.pause)
        if len(data) >= self.ROW_CAP and len(codes) > 1:
            mid = len(codes) // 2
            return self._mirror_batch(codes[:mid], year) + self._mirror_batch(codes[mid:], year)
        # sum imports by (product, exporter=partner); the exporter becomes the reporter of an export row
        agg: dict[tuple, float] = {}
        for r in data:
            par = r.get("partnerCode")
            if not par or int(par) == 0:                       # skip the World partner + self
                continue
            key = (int(par), str(r.get("cmdCode")), str(year))
            agg[key] = agg.get(key, 0.0) + float(r.get("primaryValue") or 0)
        return [
            {"reporterCode": exp, "partnerCode": 0, "cmdCode": cmd, "period": per, "flowCode": "X",
             "primaryValue": round(v, 2), "netWgt": None, "qtyUnitAbbr": None, "publishedDate": None}
            for (exp, cmd, per), v in agg.items() if v > 0
        ]

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
            flow = r.get("flowCode") or "M"
            key = (r.get("reporterCode"), r.get("partnerCode"), str(r.get("cmdCode")), quarter, flow)
            c = agg.setdefault(key, {"value": 0.0, "wgt": 0.0, "months": set()})
            c["value"] += float(r.get("primaryValue") or 0)
            c["wgt"] += float(r.get("netWgt") or 0)
            c["months"].add(month)
        return [
            {"reporterCode": rep, "partnerCode": par, "cmdCode": cmd, "period": quarter,
             "flowCode": flow, "primaryValue": round(c["value"], 2), "netWgt": round(c["wgt"], 2),
             "qtyUnitAbbr": "kg", "publishedDate": None}
            for (rep, par, cmd, quarter, flow), c in agg.items() if len(c["months"]) >= 3
        ]

    @staticmethod
    def _normalise_annual(rows: list[dict]) -> list[dict]:
        agg: dict[tuple, dict] = {}
        for r in rows:
            flow = r.get("flowCode") or "M"
            key = (r.get("reporterCode"), r.get("partnerCode"), str(r.get("cmdCode")), str(r.get("period")), flow)
            c = agg.setdefault(key, {"value": 0.0, "wgt": 0.0})
            c["value"] += float(r.get("primaryValue") or 0)
            c["wgt"] += float(r.get("netWgt") or 0)
        return [
            {"reporterCode": rep, "partnerCode": par, "cmdCode": cmd, "period": period,
             "flowCode": flow, "primaryValue": round(c["value"], 2), "netWgt": round(c["wgt"], 2),
             "qtyUnitAbbr": "kg", "publishedDate": None}
            for (rep, par, cmd, period, flow), c in agg.items()
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


class ComtradeMirrorSource(ComtradeSource):
    """Recent-year MIRROR exports (see ComtradeSource.pull_mirror). Batched, so run_multi hands it the
    whole product chunk. Recent years only — history is already covered by BACI + direct Comtrade."""
    name = "comtrade-mirror"
    batched = True

    def pull(self, hs_codes: list[str], reporters: list[int], partners: list[int] | None,
             skip: frozenset = frozenset()) -> list[dict]:
        if not self.key:
            return []
        # Fill only years partners have MOSTLY reported. The frontier year (current-1) is still thin
        # (few partners in yet) -> its mirror total understates and fakes a collapse, so we skip it and
        # start at current-2. A late self-reporter still gets ~1 year fresher than it self-reports.
        years = [date.today().year - 1 - k for k in range(1, config.MIRROR_YEARS + 1)]
        return self.pull_mirror(hs_codes, years)
