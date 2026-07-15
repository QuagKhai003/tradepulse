"""
eping.py — REGULATORY CHANGES: WTO ePing SPS/TBT notifications (the qualification-tab EVENTS lane).
@context  A destination market changing an import rule (a new standard, a stricter limit, a labelling
          requirement) is a change to what it takes to QUALIFY to sell there — Layer-3, and forward-
          looking (each notification carries a comment deadline). This is a SEPARATE lane from trade
          flows (ADR-0007): an event, never a number, never merged into a signal.
@source   WTO ePing `azureSearch/getAll` — keyless JSON. Each notification carries area (TBT/SPS), the
          notifying member, dates, and (recent ones) a structured hsCodes[] tag we match against our
          products. Public act + official source URL only (Golden Rule) — no party, no contact.
@limits   Network in _search only; pure parsing otherwise. ePing does NOT sort by date (it returns its
          own relevance order), so we fetch a page and sort/window client-side — a buried very-recent
          notification past the page can be missed until the next run (logged, honest). Deterministic
          given a response + a cutoff + a verified date.
@affects  Stored via db.upsert_regulatory_events; exported to events-<hs>.json by export.build_events.
"""
from __future__ import annotations

import html
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta

from .. import config

BASE = "https://epingalert.org/api/v1/azureSearch/getAll"
CITE = "https://epingalert.org/en/Search?viewData={}"      # verified 200 — the public notification view
_TAG = re.compile(r"<[^>]+>")


def _text(s: str | None, limit: int = 400) -> str | None:
    """Strip ePing's inline HTML + unescape entities to plain text (titles/descriptions arrive as HTML)."""
    if not s:
        return None
    out = html.unescape(_TAG.sub(" ", s)).replace("\xa0", " ")
    out = re.sub(r"\s+", " ", out).strip()
    return (out[:limit].rstrip() + "…") if len(out) > limit else (out or None)


class EpingSource:
    name = "wto-eping"

    def __init__(self, timeout: int = 60, pause: float = 0.4, page_size: int = 100):
        self.timeout = timeout
        self.pause = pause
        self.page_size = page_size

    def pull(self, products: dict[str, list[str]], verified_date: str,
             lookback_days: int = config.REGULATORY_LOOKBACK_DAYS, today: date | None = None) -> list[dict]:
        """For each pilot product, search ePing for its terms -> regulatory-event rows within the window."""
        cutoff = (today or date.today()) - timedelta(days=lookback_days)
        rows: list[dict] = []
        seen: set[tuple[str, str]] = set()             # (event_id, hs4) — dedupe across keyword queries
        for hs4, keywords in products.items():
            items = self._search(keywords)
            kept = dropped_old = 0
            for it in items:
                row = self._row(it, hs4, verified_date)
                if not row:
                    continue
                if row["event_date"] and row["event_date"] < cutoff.isoformat():
                    dropped_old += 1
                    continue
                key = (row["event_id"], hs4)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(row)
                kept += 1
            print(f"[eping] {hs4}: {kept} events in window ({dropped_old} older than {lookback_days}d, "
                  f"{len(items)} scanned)")
        return rows

    def _search(self, keywords: list[str]) -> list[dict]:
        """Query each keyword, merge + dedupe by notification id. ePing's own order is relevance, not
        date, so callers window by date afterwards."""
        by_id: dict[str, dict] = {}
        for kw in keywords:
            params = {"freeText": kw, "language": "1", "pageIndex": "0", "pageSize": str(self.page_size)}
            data = self._get(f"{BASE}?{urllib.parse.urlencode(params)}")
            for it in (data or {}).get("items", []) or []:
                if it.get("id"):
                    by_id[str(it["id"])] = it
        return list(by_id.values())

    @staticmethod
    def _row(it: dict, hs4: str, verified_date: str) -> dict | None:
        eid = it.get("id")
        if not eid:
            return None
        # STRONG match when ePing's structured HS tag covers our product; else the freeText term matched
        # somewhere in the notice (kept, but flagged lower-confidence so the UI can rank it).
        codes = [str((c or {}).get("code") or "") for c in (it.get("hsCodes") or [])]
        match_kind = "hs" if any(c.startswith(hs4) or hs4.startswith(c) for c in codes if c) else "keyword"
        member = (it.get("notifyingMember") or "").strip() or None
        dist = it.get("distributionDate")
        deadline = it.get("commentDeadlineDate")
        return {
            "source": "wto-eping",
            "event_id": str(eid),
            "hs4": hs4,
            "market": config.MARKET_BY_ENAME.get(member),          # pilot slug or None (product-wide only)
            "market_name": member,
            "event_date": dist[:10] if dist else None,
            "deadline": deadline[:10] if deadline else None,
            "kind": "rule_change",
            "area": (it.get("area") or "").strip() or None,        # TBT | SPS
            "title": _text(it.get("title"), 200),
            "detail": _text(it.get("description")) or _text(it.get("productsFreeText")),
            "match_kind": match_kind,
            "source_url": CITE.format(eid),
            "verified_date": verified_date,
        }

    def _get(self, url: str):
        req = urllib.request.Request(url, headers={
            "Accept": "application/json", "User-Agent": "Mozilla/5.0 tradepulse/0.1"})
        for attempt in range(2):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    return json.loads(r.read().decode("utf-8"))
            except Exception as e:  # noqa: BLE001 — transient; back off once
                if attempt == 0:
                    time.sleep(self.pause * 4)
                    continue
                print(f"[eping] warn {type(e).__name__} on {url[-48:]}")
                return None
            finally:
                time.sleep(self.pause)
