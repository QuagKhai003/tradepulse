"""
prozorro.py — Ukraine ProZorro public procurement: market-specific buyers (UA market).
@context  Ukraine's open procurement API. No product filter + no inline classification in the list feed,
          so it's list-then-fetch: page tender IDs newest-first, then GET each tender for its buyer +
          items. Ukraine classifies by ДК021 — literal CPV codes — so it reuses our CPV crosswalk
          (sources/ocds.match_hs via the CPV allowlist). Keyless. Public buyer org + portal link only.
@warn     N+1 (one detail request per tender). `max_details` bounds the recent window scanned; the batch
          re-runs periodically, so coverage accretes. Governments tender across most product categories,
          so the match rate over the full HS catalog is high (not niche-only).
@golden   Buyer ORGANISATION + the official ProZorro portal link only — never a contact person.
@limits   Network in _get only; mapping is pure and reuses ocds.parse_release.
@affects  Rows share TED's shape -> db.upsert_tenders / upsert_awards.
"""
from __future__ import annotations

import json
import time
import urllib.request

from .ocds import parse_release

LIST = "https://public.api.openprocurement.org/api/2.5/tenders?descending=1"
DETAIL = "https://public.api.openprocurement.org/api/2.5/tenders/{}"
PORTAL = "https://prozorro.gov.ua/tender/{}"


class ProzorroSource:
    name = "ua-prozorro"

    def __init__(self, timeout: int = 40, pause: float = 0.2, max_details: int = 400):
        self.timeout = timeout
        self.pause = pause
        self.max_details = max_details

    def pull(self, cpv_by_hs: dict[str, list[str]], since: str, scraped_at: str) -> tuple[list[dict], list[dict]]:
        """`since` = 'YYYY-MM-DD'. Page newest-first tender IDs, fetch each, match its ДК021/CPV items."""
        tenders: list[dict] = []
        awards: list[dict] = []
        url, fetched = LIST, 0
        while fetched < self.max_details:
            page = self._get(url)
            ids = [(d.get("id"), d.get("dateModified")) for d in (page or {}).get("data", []) or []]
            if not ids:
                break
            for tid, dm in ids:
                if fetched >= self.max_details:
                    break
                if dm and dm[:10] < since:                  # newest-first: past the window -> stop
                    return tenders, awards
                fetched += 1
                det = self._get(DETAIL.format(tid))
                data = (det or {}).get("data")
                if not data:
                    continue
                t, a = parse_release(self._as_release(data), "UKR", self.name, cpv_by_hs, scraped_at)
                tenders += t
                awards += a
                time.sleep(self.pause)
            url = ((page.get("next_page") or {}).get("uri")) if isinstance(page, dict) else None
            if not url:
                break
        print(f"[ua-prozorro] scanned {fetched} tenders -> {len(tenders)} matched (UKR)")
        return tenders, awards

    @staticmethod
    def _as_release(data: dict) -> dict:
        """ProZorro's tender object -> the OCDS-release shape ocds.parse_release expects (buyer under
        procuringEntity, items with ДК021 classification, a portal URL it can pick up)."""
        tid = data.get("tenderID") or data.get("id")
        return {
            "ocid": str(data.get("id") or tid),
            "date": data.get("dateModified") or data.get("date"),
            "tender": {
                "title": data.get("title") or (data.get("items") or [{}])[0].get("description") or "Tender",
                "procuringEntity": data.get("procuringEntity"),
                "items": data.get("items"),
                "tenderPeriod": data.get("tenderPeriod"),
                "documents": [{"url": PORTAL.format(tid)}],   # openable ProZorro portal link
            },
        }

    def _get(self, url: str) -> dict | None:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 tradepulse/0.1",
                                                   "Accept": "application/json"})
        for attempt in range(2):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    return json.loads(r.read().decode("utf-8"))
            except Exception as e:  # noqa: BLE001 — transient; back off once
                if attempt == 0:
                    time.sleep(self.pause * 6)
                    continue
                print(f"[ua-prozorro] warn {type(e).__name__}:{getattr(e, 'code', '')}")
                return None
