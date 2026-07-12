"""
baci.py — CEPII BACI bulk source: cleaned global HS6 trade, from a local file (NO API throttle).
@context  Comtrade's free API is rate-limited (~500 calls/day), which caps how many products/years we
          can pull. BACI is a single downloadable file (all ~200 countries x all ~5,600 HS6 products,
          reconciled bilateral trade) — parse it locally, no per-request limit. Lags ~2 years, so it's
          the HISTORY backbone; the Comtrade API + national sources cover recent years. BACI already
          uses Comtrade M49 country codes and USD values, so NO crosswalk and NO FX are needed.
@warn     Values are in THOUSANDS of USD (x1000). k is HS6 (zero-pad to 6). Only HS6 (aggregate HS4 by
          prefix). Download: data/baci/BACI_HS22_V202501.zip from cepii.fr (scripts/prepare-data or manual).
@done     pull() -> World totals per (reporter, HS, flow) as Comtrade-shaped USD rows; _aggregate tested.
@limits   Reads local CSVs (streamed). Skips a whole year if it's already stored + final (incremental).
@affects  Implements base.TradeSource; merged in pipeline. Tested by tests/test_baci.py.
"""
from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

WORLD = 0
BACI_DIR = Path(__file__).resolve().parents[3] / "data" / "baci"
_YEAR_RE = re.compile(r"_Y(\d{4})_")


class BaciSource:
    name = "baci"
    bulk = True     # parse the file ONCE for ALL products (never per-product — see pipeline.run_multi)

    def __init__(self, baci_dir: Path | str = BACI_DIR):
        self.dir = Path(baci_dir)

    def pull(self, hs_codes: list[str], reporters: list[int], partners: list[int] | None,
             skip: frozenset = frozenset()) -> list[dict]:
        hs6 = {h for h in hs_codes if len(h) == 6}
        hs4 = {h for h in hs_codes if len(h) == 4}   # HS4 categories = sum of their HS6
        if not hs6 and not hs4:
            return []
        rows: list[dict] = []
        for path in sorted(self.dir.glob("BACI_HS*_Y*.csv")):
            m = _YEAR_RE.search(path.name)
            if not m:
                continue
            year = m.group(1)
            # Skip the whole file if every covered (hs, year) is already stored + final (incremental).
            if skip and all((hs, year) in skip for hs in (hs6 | hs4)):
                continue
            rows += self._parse_year(path, year, hs6, hs4, skip)
        return rows

    @staticmethod
    def _parse_year(path: Path, year: str, hs6: set, hs4: set, skip: frozenset) -> list[dict]:
        imp: dict = defaultdict(float)   # (country, hs) -> USD
        exp: dict = defaultdict(float)
        with path.open(newline="", encoding="utf-8") as f:
            r = csv.reader(f)
            next(r, None)                # header t,i,j,k,v,q
            for rec in r:
                if len(rec) < 5:
                    continue
                _, i, j, k, v = rec[0], rec[1], rec[2], rec[3], rec[4]
                kk = k.strip().zfill(6)
                p4 = kk[:4]
                hit6 = kk in hs6
                hit4 = p4 in hs4
                if not (hit6 or hit4):
                    continue
                try:
                    usd = float(v) * 1000.0      # BACI value is thousands of USD
                except ValueError:
                    continue
                ii, jj = int(i), int(j)
                if hit6:
                    imp[(jj, kk)] += usd; exp[(ii, kk)] += usd
                if hit4:
                    imp[(jj, p4)] += usd; exp[(ii, p4)] += usd
        return BaciSource._emit(imp, exp, year, skip)

    @staticmethod
    def _emit(imp: dict, exp: dict, year: str, skip: frozenset) -> list[dict]:
        out = []
        for flow, agg in (("M", imp), ("X", exp)):
            for (country, hs), usd in agg.items():
                if (hs, year) in skip or usd <= 0:
                    continue
                out.append({"reporterCode": country, "partnerCode": WORLD, "cmdCode": hs,
                            "period": year, "flowCode": flow, "primaryValue": round(usd, 2),
                            "netWgt": None, "qtyUnitAbbr": None, "publishedDate": f"{year}-12"})
        return out
