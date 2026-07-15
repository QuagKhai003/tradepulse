"""
rasff.py — EU RASFF border-REJECTIONS: the qualification tab's 2nd event source (kind='rejection').
@context  A shipment stopped at the EU border is a live warning to a seller: "the EU just found a banned
          antibiotic in shrimp from Vietnam." Feeds the SAME events lane as ePing (ADR-0007) but as a
          rejection, not a rule-change — a separate lane, never a number. Vietnam-origin rejections are
          the sharpest signal, so origin is carried in the detail line.
@source   EU RASFF Window consolidated search — keyless JSON POST. Maps a product to its RASFF product
          CATEGORY; because a category is broad, a row is kept only if the notification SUBJECT also
          contains one of the product's keywords. Food/feed only (no wood). Licence: EU public reuse.
@golden   Public act (a border decision) + official notification link only. No party, no contact.
@limits   Network in _search only; pure parsing otherwise. Deterministic given a response + a cutoff.
@affects  Stored via db.upsert_regulatory_events; exported to events-<hs>.json by export.build_events.
"""
from __future__ import annotations

import json
import time
import urllib.request

BASE = "https://webgate.ec.europa.eu/rasff-window/backend/public/notification/search/consolidated/en/"
CITE = "https://webgate.ec.europa.eu/rasff-window/screen/notification/{}"


def _date(s: str | None) -> str | None:
    """RASFF 'dd-mm-yyyy hh:mm:ss' -> 'yyyy-mm-dd'."""
    if not s or len(s) < 10:
        return None
    d, m, y = s[:10].split("-")
    return f"{y}-{m}-{d}"


class RasffSource:
    name = "eu-rasff"

    def __init__(self, timeout: int = 60, pause: float = 0.4, page_size: int = 100):
        self.timeout = timeout
        self.pause = pause
        self.page_size = page_size

    def pull(self, rasff_cat: dict[str, int], keywords: dict[str, list[str]], verified_date: str,
             lookback_days: int, today=None) -> list[dict]:
        from datetime import date, timedelta
        cutoff = ((today or date.today()) - timedelta(days=lookback_days)).isoformat()
        # Fetch each product CATEGORY once (several products share one), then split by keyword-in-subject.
        cats: dict[int, list[str]] = {}
        for hs, cat in rasff_cat.items():
            cats.setdefault(cat, []).append(hs)
        rows: list[dict] = []
        seen: set[tuple[str, str]] = set()
        for cat, hslist in cats.items():
            notifs = self._search(cat)
            for hs in hslist:
                # A broad category (cereals, cocoa/coffee/tea) MUST be narrowed by the product term, so a
                # missing keyword is never "keep everything" — fall back to the HS4-family keywords.
                kws = [k.lower() for k in (keywords.get(hs) or keywords.get(hs[:4]) or [])]
                if not kws:                                   # no term at all -> skip (don't dump a category)
                    print(f"[rasff] {hs}: no keyword, skipped (would dump the whole category)")
                    continue
                kept = 0
                for nt in notifs:
                    subj = (nt.get("subject") or "")
                    if kws and not any(k in subj.lower() for k in kws):   # category is broad -> require the term
                        continue
                    row = self._row(nt, hs, verified_date)
                    if not row or (row["event_date"] and row["event_date"] < cutoff):
                        continue
                    key = (row["event_id"], hs)
                    if key in seen:
                        continue
                    seen.add(key)
                    rows.append(row)
                    kept += 1
                print(f"[rasff] {hs} (cat {cat}): {kept} rejections in window ({len(notifs)} scanned)")
        return rows

    def _search(self, category: int) -> list[dict]:
        body = json.dumps({"parameters": {"pageNumber": 1, "itemsPerPage": self.page_size},
                           "productCategory": [category]}).encode("utf-8")
        req = urllib.request.Request(BASE, data=body, method="POST", headers={
            "Content-Type": "application/json", "Accept": "application/json",
            "Referer": "https://webgate.ec.europa.eu/rasff-window/screen/list",
            "User-Agent": "Mozilla/5.0 tradepulse/0.1"})
        for attempt in range(2):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    return json.loads(r.read().decode("utf-8")).get("notifications", []) or []
            except Exception as e:  # noqa: BLE001 — transient; back off once
                if attempt == 0:
                    time.sleep(self.pause * 4)
                    continue
                print(f"[rasff] warn {type(e).__name__} on category {category}")
                return []
            finally:
                time.sleep(self.pause)

    @staticmethod
    def _row(nt: dict, hs: str, verified_date: str) -> dict | None:
        nid = nt.get("notifId")
        subject = (nt.get("subject") or "").strip()
        if not nid or not subject:
            return None
        origins = [o.get("organizationName") for o in (nt.get("originCountries") or []) if o.get("organizationName")]
        risk = ((nt.get("riskDecision") or {}).get("description")
                or (nt.get("notificationClassification") or {}).get("description"))
        notifier = (nt.get("notifyingCountry") or {}).get("organizationName")
        detail = " · ".join(x for x in [
            f"risk: {risk}" if risk else None,
            f"origin: {', '.join(origins)}" if origins else None,
            f"notified by {notifier}" if notifier else None] if x)
        return {
            "source": "eu-rasff",
            "event_id": str(nid),
            "hs4": hs,
            "market": "eu",                                   # RASFF is an EU-border decision
            "market_name": notifier or "EU",
            "event_date": _date(nt.get("ecValidationDate")),
            "deadline": None,                                 # a rejection has no comment period
            "kind": "rejection",
            "area": None,
            "title": subject,
            "detail": detail or None,
            "match_kind": "keyword",                          # kept because the subject named the product
            "source_url": CITE.format(nid),
            "verified_date": verified_date,
        }
