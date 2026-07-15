"""
thaimoc.py — fresh national primary: Thailand Ministry of Commerce trade stats (keyless JSON).
@context  Comtrade lags; some national customs publish fresher. Thailand MOC exposes HS x partner
          import/export in clean JSON, fresh to ~1 month — so Thailand's own map cell (reporter 764)
          can show 2026 while Comtrade still sits on 2024. The app sums the per-partner rows into a
          World total, exactly like Census does for the US. Merges one-number-per-cell (national
          authority), so it OVERRIDES Comtrade for Thailand.
@scope    Pilot products only (config.THAI_HS) — a per-product API over all 1,240 would be tens of
          thousands of calls. Only COMPLETE quarters are emitted (a 1–2 month quarter would understate).
@nonuse   NOT used to rebuild Vietnam's world total — Thailand is a single buyer, so that alone would
          badly understate VN, a wrong number we will not show (Golden Rule).
@limits   Network in _get only; pure aggregation otherwise. Deterministic given responses + a clock.
@affects  Implements the TradeSource pull() shape; transformed by transform_all, merged by merge_flows.
"""
from __future__ import annotations

import json
import time
import urllib.request
from datetime import date

from .. import config

BASE = "https://tradereport.moc.go.th/api"
FLOWS = [("importharmonizecountries", "M"), ("exportharmonizecountries", "X")]


class ThaiMocSource:
    name = "thaimoc"

    def __init__(self, months: int = 18, timeout: int = 45, pause: float = 0.25):
        self.months = months
        self.timeout = timeout
        self.pause = pause

    def pull(self, hs_codes: list[str], reporters, partners, skip=None, today: date | None = None) -> list[dict]:
        codes = [h for h in hs_codes if h in config.THAI_HS]      # scope: pilots only
        if not codes:
            return []
        skip = skip or frozenset()
        window = self._window(today or date.today())
        rows: list[dict] = []
        for hs in codes:
            for endpoint, flow in FLOWS:
                monthly = {}
                for y, m in window:
                    data = self._get(endpoint, y, m, hs)
                    if data:
                        monthly[f"{y}-{m:02d}"] = sum(float(r["value_usd"]) for r in data
                                                      if r.get("value_usd"))
                for period, val in self._to_quarters(monthly).items():
                    if (hs, period) in skip:
                        continue
                    rows.append({"reporterCode": config.THAILAND_M49, "partnerCode": 0, "cmdCode": hs,
                                 "period": period, "flowCode": flow, "primaryValue": round(val, 2),
                                 "netWgt": None, "qtyUnitAbbr": None, "publishedDate": None})
        return rows

    def _window(self, today: date) -> list[tuple[int, int]]:
        """The last `months` (year, month) pairs, oldest first."""
        out = []
        y, m = today.year, today.month
        for _ in range(self.months):
            out.append((y, m))
            m -= 1
            if m == 0:
                y, m = y - 1, 12
        return list(reversed(out))

    @staticmethod
    def _to_quarters(monthly: dict[str, float]) -> dict[str, float]:
        """Monthly totals -> quarter totals, keeping ONLY complete quarters (all 3 months present);
        a partial quarter would understate the figure, so it is dropped, not shown."""
        by_q: dict[str, list[float]] = {}
        for ym, v in monthly.items():
            y, m = int(ym[:4]), int(ym[5:7])
            by_q.setdefault(f"{y}-Q{(m - 1) // 3 + 1}", []).append(v)
        return {q: round(sum(vs), 2) for q, vs in by_q.items() if len(vs) == 3}

    def _get(self, endpoint: str, year: int, month: int, hs: str) -> list[dict]:
        url = f"{BASE}/{endpoint}?year={year}&month={month}&hs_code={hs}&limit=1000"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 tradepulse/0.1"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                data = json.loads(r.read().decode("utf-8"))
            return data if isinstance(data, list) else []
        except Exception as e:  # noqa: BLE001 — a missing month is normal (future / not yet published)
            print(f"[thaimoc] warn {type(e).__name__} on {endpoint} {year}-{month:02d} {hs}")
            return []
        finally:
            time.sleep(self.pause)
