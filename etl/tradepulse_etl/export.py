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
from .reference import country_name, m49_by_iso3

BAND_RANK = {"surge": 0, "collapse": 0, "significant": 1, "moderate": 2, "new": 3}
FEED_CAP = 60
DEFAULT_SNAPSHOT = Path(__file__).resolve().parents[2] / "web" / "public" / "data" / "snapshot.json"

# Vietnamese names for the pilot markets (others fall back to the English reference name).
_VI = {m["reporter"]: m["name_vi"] for m in config.MARKETS.values()}
_VI[config.PARTNER_VIETNAM] = "Việt Nam"


def _name_vi(code: int) -> str:
    return _VI.get(code) or country_name(code)


HISTORY_POINTS = 6      # sparkline length; the shared index below makes each point ~6 bytes


def _period_index(flows: list[dict]) -> dict[str, list[str]]:
    """Per grain, the last HISTORY_POINTS periods present — ONE list for the whole file. Slots then
    ship history as bare values aligned to it, instead of repeating period strings 400x per file."""
    by_fq: dict[str, set] = {}
    for r in flows:
        by_fq.setdefault(r.get("freq") or "A", set()).add(r["period"])
    return {fq: sorted(ps)[-HISTORY_POINTS:] for fq, ps in by_fq.items()}


def build_snapshot(conn, generated_at: str, hs6: str = "440131") -> dict:
    flows = _flows(conn, hs6)
    signals = {(s["reporter"], s["flow"], s["period"]): s for s in _signals(conn, hs6)}
    latest = max((r["period"] for r in flows), default=None)
    sources = {r["source"] for r in flows}
    periods = _period_index(flows)

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
                per_freq[fq] = _slot(cur, signals.get((code, flow, cur["period"])), series,
                                     periods.get(fq, []))
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
        "periods": periods, "countries": countries,
    }


def build_tenders(conn, hs6: str, today: str) -> list[dict]:
    """OPEN tenders only, and only the ones actually ABOUT this product. Two filters:
    1. TED's 'ACTIVE' scope means the notice is PUBLISHED, not still open -> drop passed deadlines.
       (No-deadline prior-information notices are kept: an early demand signal, not an error.)
    2. Drop match_kind='basket' — the product is one buried line item of a big mixed contract (a
       school food framework that lists tea among 100 items is not a tea lead). Only a whole
       'contract' or a real 'lot' is biddable. See sources/ted.py @warn.
    Buyer ORGANISATION + official link only (Golden Rule)."""
    from .db import fetch_tenders
    rows = fetch_tenders(conn, hs6)
    out = []
    for r in rows:
        if r["deadline"] and r["deadline"] < today:
            continue
        if (r["match_kind"] or "basket") == "basket":
            continue
        out.append({"id": r["id"], "hs6": r["hs6"], "title": _subject(r["title"]), "buyer": r["buyer"],
                    "buyer_country": r["buyer_country"], "buyer_code": _m49(r["buyer_country"]),
                    "match": r["match_kind"], "cpv": r["cpv"],
                    "deadline": r["deadline"], "published": r["published"], "url": _notice_url(r["id"])})
    return out


# TED titles read "Country – English subject – LOCAL PROJECT NAME" (the tail stays in the buyer's own
# language). We display the English subject only; the full local title is one click away on TED.
def _notice_url(pub: str) -> str:
    """Canonical TED link — the /html view renders in the browser (/pdf downloads; bare path 404s)."""
    return f"https://ted.europa.eu/en/notice/{pub}/html"


def _subject(title: str) -> str:
    parts = [p.strip() for p in (title or "").split("–")]
    return parts[1] if len(parts) >= 3 and parts[1] else (title or "")


_M49_BY_ISO3 = m49_by_iso3()


def _m49(iso3: str | None) -> int | None:
    return _M49_BY_ISO3.get((iso3 or "").upper())


def build_awards(conn, hs6: str) -> list[dict]:
    """PAST ORDERS: awarded contracts for this product. Same on-product filter as tenders — an award
    where the product is one buried line item of a mixed contract tells a seller nothing."""
    from .db import fetch_awards
    out = []
    for r in fetch_awards(conn, hs6):
        if (r["match_kind"] or "basket") == "basket":
            continue
        out.append({"id": r["id"], "hs6": r["hs6"], "title": _subject(r["title"]),
                    "buyer": r["buyer"], "buyer_country": r["buyer_country"],
                    "buyer_code": _m49(r["buyer_country"]),
                    "seller": r["winner"], "seller_country": r["winner_country"],
                    "seller_code": _m49(r["winner_country"]),
                    "match": r["match_kind"], "cpv": r["cpv"], "date": r["award_date"] or r["published"],
                    "value": r["value"], "currency": r["currency"], "url": _notice_url(r["id"])})
    return out


def build_events(conn, hs: str) -> list[dict]:
    """REGULATORY CHANGES for a product (ADR-0007): the qualification-tab EVENTS lane. Public import-
    rule changes (WTO ePing SPS/TBT) touching this product's HS4 family, newest first. A SEPARATE lane
    — an event, never a number, never merged into a signal. Deduped by notice id (an HS4 heading and
    its children can carry the same notice). Golden Rule: public act + official source URL only, no
    party/contact. `match` = 'hs' (structured HS tag confirmed) vs 'keyword' (freetext) so the UI ranks."""
    from .db import fetch_regulatory_events
    by: dict[str, dict] = {}
    for r in fetch_regulatory_events(conn, hs):
        by.setdefault(r["event_id"], {
            "id": r["event_id"], "source": r["source"], "kind": r["kind"], "area": r["area"],
            "market": r["market"], "market_name": r["market_name"],
            "date": r["event_date"], "deadline": r["deadline"],
            "title": r["title"], "detail": r["detail"], "match": r["match_kind"],
            "url": r["source_url"], "verified": r["verified_date"]})
    out = list(by.values())
    out.sort(key=lambda e: e["date"] or "", reverse=True)     # newest first; undated last
    return out


def build_forward(conn, hs: str) -> dict | None:
    """FORWARD lane (ADR-0007): the product's world PRICE trend from IMF PCPS. Returns latest level, the
    year-on-year % move + a direction cue, and a ~24-month series for a sparkline — or None when there
    is no honest price series for this product (wood pellets, cashew: no direct IMF series -> no line).
    A SEPARATE lane: a $/unit world price, never merged into the customs total (different measure)."""
    from .db import fetch_commodity_prices
    rows = fetch_commodity_prices(conn, hs)
    if not rows:
        return None
    ind = rows[-1]["indicator"]
    series = [{"period": r["period"], "value": r["value"]} for r in rows if r["value"] is not None]
    if not series:
        return None
    latest = series[-1]
    by_period = {s["period"]: s["value"] for s in series}
    # YoY: same month a year earlier (exact match only — never interpolate a price we cannot stand behind).
    py, pm = int(latest["period"][:4]) - 1, latest["period"][5:7]
    prev = by_period.get(f"{py}-{pm}")
    yoy = round((latest["value"] - prev) / prev * 100, 1) if prev else None
    direction = None if yoy is None else ("up" if yoy > 2 else "down" if yoy < -2 else "flat")
    label = config.PRICE_LABEL.get(ind, {})
    return {"hs": hs, "source": "imf-pcps", "indicator": ind,
            "label_en": label.get("en", ind), "label_vi": label.get("vi", ind),
            "latest_period": latest["period"], "latest_value": latest["value"],
            "yoy_pct": yoy, "direction": direction,
            "series": series[-24:],
            "url": "https://www.imf.org/en/Research/commodity-prices",
            "verified": rows[-1]["verified_date"]}


def build_all(conn, today: str) -> tuple[list, list, list]:
    """'All products' (HS TOTAL) is not a good — nothing tenders for it — but the ANSWER a user wants
    from it is real: everything, across every product. So TOTAL is a ROLLUP, not an empty page.

    One notice can match several of our products (an HS4 heading and its HS6 children share a CPV), so
    tenders dedupe on the notice id and awards on (notice, winner) — otherwise the same contract would
    be counted, and shown, three times. Each row keeps the HS it was matched under, so the aggregate
    view can say WHICH product every line is for.
    """
    tenders, awards = {}, {}
    for hs in config.TENDER_CPV:
        for t in build_tenders(conn, hs, today):
            tenders.setdefault(t["id"], t)
        for a in build_awards(conn, hs):
            awards.setdefault((a["id"], a["seller"]), a)
    tl = sorted(tenders.values(), key=lambda t: (t["deadline"] is None, t["deadline"] or ""))
    al = sorted(awards.values(), key=lambda a: (a["date"] or ""), reverse=True)
    return tl, al, build_sellers(al)


def _sections_for(hs6: str) -> list[str]:
    """Which registry sections cover this product (reverse of config.SELLER_SECTIONS)."""
    return [sec for sec, codes in config.SELLER_SECTIONS.items() if hs6 in codes]


def build_sellers_web(conn, hs6: str) -> list[dict]:
    """SELLERS for the web = real exporters from approval registries (ADR-0006), NOT award winners.
    An establishment approved for a section that covers this product is a seller of it. Deduped by
    (organisation, country) across sections/sources; ranked by country then name (deterministic)."""
    from .db import fetch_registry_sellers
    rows = fetch_registry_sellers(conn, _sections_for(hs6))
    by: dict[tuple, dict] = {}
    for r in rows:
        key = (r["seller"], r["seller_code"])
        cur = by.get(key)
        if cur is None:
            by[key] = {"seller": r["seller"], "seller_country": r["seller_iso"],
                       "seller_code": r["seller_code"], "approval_no": r["approval_no"],
                       "activity": r["activity"], "city": r["city"], "source": r["source"],
                       "url": r["source_url"], "verified": r["verified_date"]}
    out = list(by.values())
    out.sort(key=lambda x: (x["seller_country"] or "", x["seller"]))
    return out


def build_sellers(awards: list[dict]) -> list[dict]:
    """SELLERS, derived from past orders. A seller never publishes 'I sell tea' — but a public buyer
    publishes who WON its tea contract. So a seller here is exactly: an organisation that has won at
    least one on-product contract. Ranked by wins, then by most recent — deterministic, no judgement.
    Value is summed only across awards sharing ONE currency; mixed currencies -> no total (never a
    number we cannot stand behind)."""
    by: dict[tuple, dict] = {}
    for a in awards:
        if not a["seller"]:
            continue
        key = (a["seller"], a["seller_country"])
        s = by.setdefault(key, {"seller": a["seller"], "seller_country": a["seller_country"],
                                "seller_code": a["seller_code"], "wins": 0, "last": None,
                                "buyers": [], "value": 0.0, "currency": None, "mixed": False,
                                "url": a["url"]})
        s["wins"] += 1
        if a["date"] and (s["last"] is None or a["date"] > s["last"]):
            s["last"] = a["date"]
            s["url"] = a["url"]                       # link to the most recent win
        if a["buyer"] and a["buyer"] not in s["buyers"]:
            s["buyers"].append(a["buyer"])
        if a["value"]:
            if s["currency"] and a["currency"] != s["currency"]:
                s["mixed"] = True
            s["currency"] = s["currency"] or a["currency"]
            s["value"] += a["value"]
    out = []
    for s in by.values():
        if s["mixed"] or not s["value"]:
            s["value"], s["currency"] = None, None
        out.append(s)
    out.sort(key=lambda s: (-s["wins"], s["last"] or ""), reverse=False)
    out.sort(key=lambda s: (s["wins"], s["last"] or ""), reverse=True)
    return out


def build_cpv_match() -> dict:
    """What CPV each product's tender feed is matched to, and whether that match is EXACT.

    Coverage across 1,240 products is only honest if the user can see what it was matched to: the
    generated map is a verified text match, so "Vegetables, dried" can land on CPV "Frozen vegetables"
    — the right domain, not the same thing. Hand-mapped pilot products are exact. The UI prints the
    label and flags the approximate ones, so nobody reads a related-category tender as their product.
    """
    out = {"TOTAL": {"cpv": None, "label": None, "exact": False, "aggregate": True}}
    for hs, cpvs in config.TENDER_CPV.items():
        gen = config._CPV_GENERATED.get(hs)
        exact = hs in config.TENDER_CPV_MANUAL
        out[hs] = {"cpv": cpvs[0],
                   "label": (gen or {}).get("label") if not exact else None,
                   "exact": exact}
    return out


def write_json(data, path: Path | str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def write_tenders(tenders: list[dict], path: Path | str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(tenders, ensure_ascii=False), encoding="utf-8")
    return path


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


def _slot(cur: dict, sig: dict | None, series: list, index: list[str]) -> dict:
    """One grain's display slot, SHORT keys (the web loader expands them back, so components are
    unchanged). History is bare values aligned to the snapshot's shared `periods[freq]` index — a
    country with no figure for an indexed period gets null there. Keeps 1,240 products shippable."""
    band = sig["band"] if sig else "none"
    yoy = sig["yoy_delta"] if sig else None
    direction = _direction(yoy) if sig and band != "new" else None
    vals = {r["period"]: round(r["value_usd"]) for r in series}
    hist = [vals.get(p) for p in index]
    est = cur.get("source") == "comtrade-mirror"      # rebuilt from partner reports, not self-reported
    return {"v": round(cur["value_usd"]), "p": cur["period"], "f": cur.get("freq"),
            "y": (round(yoy, 4) if yoy is not None else None), "b": band, "d": direction,
            **({"h": hist} if any(v is not None for v in hist) else {}),
            **({"m": 1} if est else {})}


def _direction(yoy: float) -> str:
    return "up" if (yoy or 0) >= 0 else "down"


def _flows(conn, hs6: str):
    """Only this product's World rows — an INDEXED query. (Reading the whole table per product turned
    1,240 exports into ~1e9 row reads.)"""
    sql = "SELECT * FROM trade_flows WHERE hs6 = ? AND partner = ?"
    return [dict(r) for r in conn.execute(sql, (hs6, config.PARTNER_WORLD)).fetchall()]


def _signals(conn, hs6):
    return [dict(r) for r in conn.execute("SELECT * FROM signals WHERE hs6=?", (hs6,)).fetchall()]
