"""
ted.py — EU TED tenders: FORWARD demand (who is buying right now), plan §9.2 / Phase 2.2.
@context  Trade stats say where demand WENT. Tenders say where demand IS — a public buyer with an open
          deadline. TED is the EU's procurement journal: keyless REST, structured, and explicitly
          reusable (notice metadata CC0, content CC BY 4.0), so we can cache + show derived listings.
@warn     TED classifies by CPV, not HS -> config.TENDER_CPV maps each covered product to the CPV(s)
          that actually return its notices (each verified live). Titles/buyers are MULTILINGUAL dicts
          (prefer English). Prior-information notices have NO deadline — that's valid, not an error.
@warn     A CPV search matches a notice if the code appears ANYWHERE in it — including as one buried
          line item of a 100-item food framework. A school buying a food basket that happens to list
          tea is NOT a tea lead. So every notice is classified against the searched CPV:
            contract = the notice's MAIN cpv is this product  (a real, biddable contract)
            lot      = a LOT's main cpv is this product       (a real, biddable lot)
            basket   = the code only appears in the additional/full list (noise -> dropped at export)
          Measured 2026-07-14: tea = 0 contract / 19 lot / 60 basket; wood fuel = 85 / 1 / 14.
@golden   We surface the buying ORGANISATION + the official notice link only. Never a contact person.
@done     pull() -> tender rows; _notice() pure + tested.
@limits   Network in _post only. Deterministic given a response (scraped_at is passed in).
@affects  Stored via db.upsert_tenders; exported to the web by export.write_tenders.
"""
from __future__ import annotations

import json
import time
import urllib.request

API = "https://api.ted.europa.eu/v3/notices/search"
NOTICE_URL = "https://ted.europa.eu/en/notice/{}"
FIELDS = ["publication-number", "notice-title", "buyer-name", "buyer-country",
          "deadline-receipt-tender-date-lot", "publication-date", "classification-cpv",
          "main-classification-proc", "main-classification-lot"]


def _stem(cpv: str) -> str:
    """CPV is hierarchical with trailing zeros: 15863000 (tea) is the parent of 15863200 (black tea).
    Strip the zeros and a child is any code starting with the stem."""
    return cpv.rstrip("0") or cpv


def _match_kind(notice: dict, cpv: str) -> str:
    """How this product relates to the notice — see the @warn above."""
    stem = _stem(cpv)
    hit = lambda field: any(str(c).startswith(stem) for c in (notice.get(field) or []))
    if hit("main-classification-proc"):
        return "contract"
    if hit("main-classification-lot"):
        return "lot"
    return "basket"


def _text(v) -> str | None:
    """TED returns multilingual dicts ({'eng': [...], 'fra': [...]}) — prefer English, else anything."""
    if v is None:
        return None
    if isinstance(v, str):
        return v.strip() or None
    if isinstance(v, list):
        return _text(v[0]) if v else None
    if isinstance(v, dict):
        for key in ("eng", "ENG", "en"):
            if v.get(key):
                return _text(v[key])
        for val in v.values():
            t = _text(val)
            if t:
                return t
    return None


class TedSource:
    name = "ted"

    def __init__(self, timeout: int = 60, pause: float = 0.5, page_size: int = 100):
        self.timeout = timeout
        self.pause = pause
        self.page_size = page_size

    def pull(self, cpv_by_hs: dict[str, list[str]], since: str, scraped_at: str) -> list[dict]:
        """`since` = 'YYYYMMDD'. One search per (product, CPV); ACTIVE notices only."""
        rows: list[dict] = []
        for hs6, cpvs in cpv_by_hs.items():
            for cpv in cpvs:
                q = f"classification-cpv IN ({cpv}) AND publication-date>={since}"
                data = self._post({"query": q, "fields": FIELDS, "page": 1,
                                   "limit": self.page_size, "scope": "ACTIVE"})
                for n in (data or {}).get("notices", []) or []:
                    row = self._notice(n, hs6, cpv, scraped_at)
                    if row:
                        rows.append(row)
                time.sleep(self.pause)
        return rows

    # --- pure: one TED notice -> one tender row (buyer ORG + link only) ---
    @staticmethod
    def _notice(n: dict, hs6: str, cpv: str, scraped_at: str) -> dict | None:
        pub = _text(n.get("publication-number"))
        title = _text(n.get("notice-title"))
        if not pub or not title:
            return None
        return {
            "id": pub,
            "hs6": hs6,
            "source": "ted",
            "cpv": cpv,
            "match_kind": _match_kind(n, cpv),
            "title": title,
            "buyer": _text(n.get("buyer-name")),                 # organisation, never a person
            "buyer_country": _text(n.get("buyer-country")),
            "published": (_text(n.get("publication-date")) or "")[:10] or None,
            "deadline": (_text(n.get("deadline-receipt-tender-date-lot")) or "")[:10] or None,
            "url": NOTICE_URL.format(pub),
            "scraped_at": scraped_at,
        }

    def _post(self, body: dict) -> dict | None:
        req = urllib.request.Request(
            API, data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "tradepulse/0.1"})
        for attempt in range(2):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    return json.loads(r.read().decode("utf-8"))
            except Exception as e:  # noqa: BLE001 — transient; back off once
                if attempt == 0:
                    time.sleep(self.pause * 4)
                    continue
                print(f"[ted] warn: {type(e).__name__}:{getattr(e, 'code', '')}")
                return None
