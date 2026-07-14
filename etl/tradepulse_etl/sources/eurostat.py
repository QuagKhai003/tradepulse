"""
eurostat.py — EU source via Eurostat Comext dataset DS-059341 (the live successor to the retired
DS-045409). API only, NO bulk download.
@context  Fresher + authoritative for each EU MEMBER STATE than the Comtrade API. Comext reports every
          member individually (declarant); we query each with partner=WORLD (total trade) so it overrides
          Comtrade for Germany, France, ... (see config.SOURCE_AUTHORITY['eurostat'] = the 27 M49 codes).
          Monthly -> quarters + years. Values are EUR -> USD via fx.to_usd (merge with Comtrade/Census/KCS).
@warn     The OLD dataset DS-045409 now faults (140); DS-059341 is the current one (dims:
          freq.reporter.partner.product.flow.indicators; indicator VALUE_EUR). Product accepts HS4 or HS6.
          The API rejects a query with too many reporter values, so members are queried in small chunks.
@done     pull() -> Comtrade-shaped raw rows (reporter=<member M49>, partner=World); _parse() pure + tested.
@limits   Network in _get + ECBFx. Skips TOTAL (Comtrade covers it). SDMX-CSV (stdlib csv). Keyless.
@affects  Implements the source protocol; merged in the pipeline. Tested by tests/test_eurostat.py.
"""
from __future__ import annotations

import csv
import io
import time
import urllib.parse
import urllib.request
from datetime import date

from ..fx import ECBFx, to_usd

WORLD = 0
BASE = "https://ec.europa.eu/eurostat/api/comext/dissemination/sdmx/2.1/data/DS-059341"
_FLOW = {"1": "M", "2": "X"}      # Comext flow code -> our flow
MEMBERS_PER_CALL = 4              # DS-059341 rejects a query with too many reporter values (14 fails)

# Each EU member reported INDIVIDUALLY (declarant ISO2, EL=Greece) -> our M49 reporter code, verified
# against reference/countries.json. Query each with partner=WORLD (total trade) so it overrides the
# Comtrade API for that country. This splits the old EU27 bloc into Germany, France, ... separately.
EU27 = {"AT": 40, "BE": 58, "BG": 100, "HR": 191, "CY": 196, "CZ": 203, "DK": 208, "EE": 233,
        "FI": 246, "FR": 251, "DE": 276, "EL": 300, "HU": 348, "IE": 372, "IT": 380, "LV": 428,
        "LT": 440, "LU": 442, "MT": 470, "NL": 528, "PL": 616, "PT": 620, "RO": 642, "SK": 703,
        "SI": 705, "ES": 724, "SE": 752}


class EurostatSource:
    name = "eurostat"

    def __init__(self, years: int = 3, timeout: int = 60, pause: float = 0.4,
                 freqs: tuple[str, ...] = ("A",), fx: dict | None = None):
        self.years = years
        self.timeout = timeout
        self.pause = pause
        self.freqs = freqs
        self._fx = fx

    def _usd_per_eur(self) -> dict:
        if self._fx is None:
            self._fx = ECBFx().rates(freqs=("A",), currencies=("USD",))
        return self._fx.get("USD", {})

    def pull(self, hs_codes: list[str], reporters: list[int], partners: list[int] | None,
             skip: frozenset = frozenset()) -> list[dict]:
        usd = self._usd_per_eur()
        start = f"{date.today().year - self.years}-01"
        members = list(EU27)
        batches = [members[i:i + MEMBERS_PER_CALL] for i in range(0, len(members), MEMBERS_PER_CALL)]
        rows: list[dict] = []
        for hs in hs_codes:
            if hs == "TOTAL":
                continue
            for batch in batches:                              # each EU member individually, in chunks
                key = f"M.{'+'.join(batch)}.WORLD.{hs}..VALUE_EUR"
                url = f"{BASE}/{key}?" + urllib.parse.urlencode({"format": "SDMX-CSV", "startPeriod": start})
                text = self._get(url)
                if text:
                    rows += self._parse(text, hs, usd, self.freqs)
                time.sleep(self.pause)
        return rows

    # --- pure: SDMX-CSV (many EU members) -> USD rows, monthly EUR aggregated to quarters + years,
    #     PER member (each row's `reporter` ISO2 -> M49) ---
    @staticmethod
    def _parse(text: str, hs: str, usd_per_eur: dict, freqs: tuple) -> list[dict]:
        month_eur: dict[tuple, float] = {}     # (m49, flow, 'YYYY-MM') -> EUR
        for r in csv.DictReader(io.StringIO(text)):
            m49 = EU27.get((r.get("reporter") or "").strip())
            flow = _FLOW.get((r.get("flow") or "").strip())
            period = (r.get("TIME_PERIOD") or "").strip()      # 'YYYY-MM'
            if not m49 or not flow or len(period) != 7:
                continue
            try:
                eur = float(r.get("OBS_VALUE") or 0)
            except ValueError:
                continue
            if eur > 0:
                month_eur[(m49, flow, period)] = month_eur.get((m49, flow, period), 0.0) + eur

        out: list[dict] = []

        def emit(m49: int, flow: str, period: str, eur: float) -> None:
            # FX table is annual (keyed by year); convert with the period's YEAR (quarter/year period).
            usd = to_usd(eur, "EUR", period[:4], usd_per_eur, {})
            if usd and usd > 0:
                out.append({"reporterCode": m49, "partnerCode": WORLD, "cmdCode": hs,
                            "period": period, "flowCode": flow, "primaryValue": round(usd, 2),
                            "netWgt": None, "qtyUnitAbbr": None, "publishedDate": None})

        if "Q" in freqs:
            q: dict[tuple, list] = {}
            for (m49, flow, ym), v in month_eur.items():
                y, m = ym.split("-")
                q.setdefault((m49, flow, f"{y}-Q{(int(m) - 1) // 3 + 1}"), []).append(v)
            for (m49, flow, period), vals in q.items():
                if len(vals) >= 3:                              # complete quarter only
                    emit(m49, flow, period, sum(vals))
        if "A" in freqs:
            yr: dict[tuple, list] = {}
            for (m49, flow, ym), v in month_eur.items():
                yr.setdefault((m49, flow, ym[:4]), []).append(v)
            for (m49, flow, period), vals in yr.items():
                if len(vals) >= 12:                             # complete year only
                    emit(m49, flow, period, sum(vals))
        return out

    def _get(self, url: str) -> str | None:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        for attempt in range(2):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    return r.read().decode("utf-8")
            except Exception as e:  # noqa: BLE001 — no-data products 404; skip
                if attempt == 0:
                    time.sleep(self.pause * 3)
                    continue
                print(f"[eurostat] warn: {type(e).__name__}:{getattr(e, 'code', '')} for {url[:70]}")
                return None
