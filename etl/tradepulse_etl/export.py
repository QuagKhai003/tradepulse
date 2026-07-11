"""
export.py — build the country-centric web snapshot (map-first, both flows).
@context  The Next.js app reads this JSON (seam). One product at a time (default the pilot HS, or
          any covered HS). Per COUNTRY: export (X) + import (M) value + YoY band, so the world map
          can colour either flow and the feed can list global signals (moderate+) for both.
@done     build_snapshot(conn, generated_at, hs6); write_snapshot(). Honest labels travel with data.
@limits   Serialisation only; signal math is in signals.py. generated_at passed in.
@affects  Reads trade_flows + signals. Writes web/public/data/snapshot.json (gitignored artifact).
"""
from __future__ import annotations

import json
from pathlib import Path

from . import config
from .reference import country_name

BAND_RANK = {"surge": 0, "collapse": 0, "significant": 1, "moderate": 2, "new": 3}
FEED_CAP = 60
DEFAULT_SNAPSHOT = Path(__file__).resolve().parents[2] / "web" / "public" / "data" / "snapshot.json"

# Vietnamese names for the pilot markets (others fall back to the English reference name).
_VI = {m["reporter"]: m["name_vi"] for m in config.MARKETS.values()}
_VI[config.PARTNER_VIETNAM] = "Việt Nam"


def _name_vi(code: int) -> str:
    return _VI.get(code) or country_name(code)


def build_snapshot(conn, generated_at: str, hs6: str = "440131") -> dict:
    flows = [r for r in _flows(conn) if r["hs6"] == hs6 and r["partner"] == config.PARTNER_WORLD]
    signals = {(s["reporter"], s["flow"], s["period"]): s for s in _signals(conn, hs6)}
    latest = max((r["period"] for r in flows), default=None)
    sources = {r["source"] for r in flows}

    # reporter -> {flow -> sorted series}
    by_rep: dict[int, dict[str, list]] = {}
    for r in flows:
        by_rep.setdefault(r["reporter"], {}).setdefault(r["flow"], []).append(r)

    countries, feed = [], []
    for code, flows_by in by_rep.items():
        entry = {"code": code, "name_en": country_name(code), "name_vi": _name_vi(code),
                 "exp": None, "imp": None}
        for flow, slot in ((config.FLOW_EXPORT, "exp"), (config.FLOW_IMPORT, "imp")):
            series = sorted(flows_by.get(flow, []), key=lambda r: r["period"])
            if not series:
                continue
            cur = series[-1]
            sig = signals.get((code, flow, cur["period"]))
            band = sig["band"] if sig else "none"
            yoy = sig["yoy_delta"] if sig else None
            direction = (_direction(yoy) if sig and band != "new" else None)
            entry[slot] = {"value_usd": cur["value_usd"], "period": cur["period"],
                           "yoy_delta": yoy, "band": band, "direction": direction,
                           "history": [{"period": r["period"], "value_usd": r["value_usd"]} for r in series]}
            if band in BAND_RANK:
                feed.append({"code": code, "name_en": entry["name_en"], "name_vi": entry["name_vi"],
                             "flow": "export" if flow == config.FLOW_EXPORT else "import",
                             "value_usd": cur["value_usd"], "yoy_delta": yoy, "band": band,
                             "direction": direction, "period": cur["period"]})
        if entry["exp"] or entry["imp"]:
            countries.append(entry)

    countries.sort(key=lambda c: max((c["exp"] or {}).get("value_usd", 0),
                                     (c["imp"] or {}).get("value_usd", 0)), reverse=True)
    feed.sort(key=lambda f: (BAND_RANK[f["band"]], -f["value_usd"]))
    product = config.PRODUCTS.get(hs6, {"name_en": hs6, "name_vi": hs6})
    return {
        "generated_at": generated_at, "hs6": hs6, "product": product,
        "latest_period": latest, "is_sample": ("fixture" in sources), "sources": sorted(sources),
        "countries": countries, "feed": feed[:FEED_CAP],
    }


def write_snapshot(snapshot: dict, path: Path | str = DEFAULT_SNAPSHOT) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def _direction(yoy: float) -> str:
    return "up" if (yoy or 0) >= 0 else "down"


def _flows(conn):
    from .db import fetch_flows
    return fetch_flows(conn)


def _signals(conn, hs6):
    return [dict(r) for r in conn.execute("SELECT * FROM signals WHERE hs6=?", (hs6,)).fetchall()]
