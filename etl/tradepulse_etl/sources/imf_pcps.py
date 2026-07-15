"""
imf_pcps.py — FORWARD lane: world commodity PRICE trend (IMF Primary Commodity Prices).
@context  Customs stats say where demand WENT (months ago). A world price moving now is a live signal
          of demand pressure ("robusta price climbing -> buyers competing"). A SEPARATE lane (ADR-0007)
          — a $/unit world price, never merged into the customs total (different unit), shown beside the
          flow chart as a direction cue. Deterministic (published monthly) and fresher than customs.
@source   IMF PCPS via api.imf.org SDMX 2.1 — keyless. One call returns every commodity; we keep the
          world series (COUNTRY G001), monthly (FREQUENCY M), USD level (DATA_TRANSFORMATION USD) for
          the indicators our pilots map to (config.PRICE_HS). SDMX-ML (no JSON offered), parsed with
          xml.etree. Licence: IMF terms (attribution).
@limits   Network in _get only; pure parsing otherwise. Only products with a HONEST direct series get a
          line (no wood-pellet/cashew price exists — those show none). Deterministic given a response.
@affects  Stored via db.upsert_commodity_prices; exported to forward-<hs>.json by export.build_forward.
"""
from __future__ import annotations

import urllib.request
import xml.etree.ElementTree as ET
from datetime import date

from .. import config

BASE = "https://api.imf.org/external/sdmx/2.1/data/PCPS/"
CITE = "https://www.imf.org/en/Research/commodity-prices"       # human-facing citation


def _local(tag: str) -> str:
    return tag.split("}")[-1]


def _period(p: str) -> str:
    """IMF 'YYYY-Mmm' -> 'YYYY-MM' (our period convention)."""
    return p.replace("-M", "-") if "-M" in p else p


class ImfPcpsSource:
    name = "imf-pcps"

    def __init__(self, timeout: int = 60):
        self.timeout = timeout

    def pull(self, price_hs: dict[str, str], verified_date: str,
             months: int = config.PRICE_MONTHS, today: date | None = None) -> list[dict]:
        """One SDMX call -> world USD monthly price rows for every pilot indicator, expanded per HS key."""
        today = today or date.today()
        start = f"{today.year - (months // 12) - 1}-01"          # generous start; we trim client-side
        by_ind = self._series(f"{BASE}?startPeriod={start}")
        wanted = set(price_hs.values())
        cutoff_ym = (today.year * 12 + today.month) - months
        rows: list[dict] = []
        for hs, ind in price_hs.items():
            for period, value in sorted(by_ind.get(ind, {}).items()):
                y, m = int(period[:4]), int(period[5:7])
                if y * 12 + m < cutoff_ym:
                    continue
                rows.append({"hs4": hs, "indicator": ind, "period": period, "value": value,
                             "source": "imf-pcps", "verified_date": verified_date})
        got = sorted({r["indicator"] for r in rows})
        missing = sorted(wanted - set(got))
        print(f"[imf-pcps] {len(rows)} price points; indicators={got}"
              + (f"; NO DATA for {missing}" if missing else ""))
        return rows

    def _series(self, url: str) -> dict[str, dict[str, float]]:
        """Parse SDMX -> {INDICATOR: {period: value}} for world (G001), monthly, USD-level series."""
        raw = self._get(url)
        if raw is None:
            return {}
        out: dict[str, dict[str, float]] = {}
        for s in ET.fromstring(raw).iter():
            if _local(s.tag) != "Series":
                continue
            a = s.attrib
            if a.get("COUNTRY") != "G001" or a.get("FREQUENCY") != "M" or a.get("DATA_TRANSFORMATION") != "USD":
                continue
            ind = a.get("INDICATOR")
            if not ind:
                continue
            for o in s:
                if _local(o.tag) != "Obs":
                    continue
                p, v = o.attrib.get("TIME_PERIOD"), o.attrib.get("OBS_VALUE")
                if p and v not in (None, ""):
                    try:
                        out.setdefault(ind, {})[_period(p)] = float(v)
                    except ValueError:
                        pass
        return out

    def _get(self, url: str) -> bytes | None:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 tradepulse/0.1"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 — one shot; a missing forward line is not fatal
            print(f"[imf-pcps] warn {type(e).__name__} on PCPS pull")
            return None
