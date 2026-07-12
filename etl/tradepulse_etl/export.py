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
    flows = _flows(conn, hs6)
    signals = {(s["reporter"], s["flow"], s["period"]): s for s in _signals(conn, hs6)}
    latest = max((r["period"] for r in flows), default=None)
    sources = {r["source"] for r in flows}

    # reporter -> {flow -> sorted series}
    by_rep: dict[int, dict[str, list]] = {}
    for r in flows:
        by_rep.setdefault(r["reporter"], {}).setdefault(r["flow"], []).append(r)

    countries = []
    for code, flows_by in by_rep.items():
        # SHORT keys (c/e/i) + names NOT stored per product (they'd repeat in all 1,240 files — see
        # countries.json). The web loader expands both back, so components are unchanged.
        entry = {"c": code, "e": None, "i": None}
        for flow, slot in ((config.FLOW_EXPORT, "e"), (config.FLOW_IMPORT, "i")):
            rows = flows_by.get(flow, [])
            if not rows:
                continue
            # Build one sub-slot per grain (A/Q/M) so the UI can toggle; default = annual (stable),
            # else the freshest available. Each grain keeps its OWN latest value + history + signal.
            by_fq: dict[str, list] = {}
            for r in rows:
                by_fq.setdefault(r.get("freq") or "A", []).append(r)
            per_freq = {}
            for fq, rws in by_fq.items():
                series = sorted(rws, key=lambda r: r["period"])
                cur = series[-1]
                per_freq[fq] = _slot(cur, signals.get((code, flow, cur["period"])), series)
            default_fq = "A" if "A" in per_freq else sorted(per_freq)[0]
            d = per_freq[default_fq]
            # `bf` holds ONLY the non-default grains — never a copy of the default (that duplication
            # doubled every file). The web's slotFor() falls back to the top-level slot for the default.
            others = {fq: s for fq, s in per_freq.items() if fq != default_fq}
            entry[slot] = {**d, **({"bf": others} if others else {})}
        if entry["e"] or entry["i"]:
            countries.append(entry)

    countries.sort(key=lambda c: max((c["e"] or {}).get("v", 0), (c["i"] or {}).get("v", 0)), reverse=True)
    product = config.PRODUCTS.get(hs6, {"name_en": hs6, "name_vi": hs6})
    # No `feed` array: the web derives the signal feed from `countries` at the chosen grain, so shipping
    # it again was pure duplication.
    return {
        "generated_at": generated_at, "hs6": hs6, "product": product,
        "latest_period": latest, "is_sample": ("fixture" in sources), "sources": sorted(sources),
        "countries": countries,
    }


def write_countries(conn, path: Path | str) -> Path:
    """Country names ONCE, shared by every product snapshot (they used to repeat in all 1,240 files)."""
    from .db import fetch_flows
    codes = sorted({r["reporter"] for r in fetch_flows(conn)})
    data = {str(c): {"name_en": country_name(c), "name_vi": _name_vi(c)} for c in codes}
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def write_snapshot(snapshot: dict, path: Path | str = DEFAULT_SNAPSHOT) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def _slot(cur: dict, sig: dict | None, series: list) -> dict:
    """One grain's display slot. SLIM: history is bare values (`h`) aligned to the snapshot-level
    `periods[freq]` list, and country names live in the shared countries.json — the web loader
    rehydrates both, so components see the same shape. Keeps 1,240 products shippable."""
    band = sig["band"] if sig else "none"
    yoy = sig["yoy_delta"] if sig else None
    direction = _direction(yoy) if sig and band != "new" else None
    # Only what the MAP renders, with SHORT keys (the loader expands them back, so components are
    # unchanged). No history (the 6-pt series was the biggest cost x 226 countries x 2 flows x 1,240
    # files) and no source/published_date (never displayed — the freshness stamp uses `period`).
    return {"v": round(cur["value_usd"]), "p": cur["period"], "f": cur.get("freq"),
            "y": (round(yoy, 4) if yoy is not None else None), "b": band, "d": direction}


def _direction(yoy: float) -> str:
    return "up" if (yoy or 0) >= 0 else "down"


def _flows(conn, hs6: str):
    """Only this product's World rows — an INDEXED query. (Reading the whole table per product turned
    1,240 exports into ~1e9 row reads.)"""
    sql = "SELECT * FROM trade_flows WHERE hs6 = ? AND partner = ?"
    return [dict(r) for r in conn.execute(sql, (hs6, config.PARTNER_WORLD)).fetchall()]


def _signals(conn, hs6):
    return [dict(r) for r in conn.execute("SELECT * FROM signals WHERE hs6=?", (hs6,)).fetchall()]
