"""
registry.py — REAL sellers: official registries of companies approved to EXPORT a product.
@context  A "seller" is a company that SELLS/exports a product — not one that won a public contract
          (that is a past order). Sellers do not advertise, but destination markets publish the
          foreign establishments they have APPROVED to export to them. Those lists name real exporters,
          with an approval number and address, and are free + citable — exactly Layer-2 evidence.
@source   EU DG SANTE (TRACES NT) "approved third-country establishments": keyless JSON, animal-origin
          only (so it covers SEAFOOD + honey among our products, not coffee/rice/wood — those come from
          other registries in a later phase). Licence: Commission Decision 2011/833/EU (free reuse +
          credit). One establishment approved for a sector is a seller of every HS that sector maps to.
@golden   Public ORGANISATION name + approval number + official source + verified date. Never a contact
          person, email or phone (the API does not expose them for these records, and we would not show
          them if it did).
@limits   Network in _get only; pure parsing otherwise. Deterministic given a response + a verified date.
@affects  Stored via db.upsert_registry_sellers; exported to sellers-<hs>.json by export.build_sellers_web.
"""
from __future__ import annotations

import json
import time
import urllib.request

from .. import config
from ..reference import m49_by_iso3

# DG SANTE publication API (the same data the public TRACES directory shows).
BASE = "https://webgate.ec.europa.eu/tracesnt/directory/listing/establishment/publication"
# Human-facing citation: the public directory page for a country + section.
CITE = "https://webgate.ec.europa.eu/tracesnt/directory/publication/index"

# ISO2 -> M49 for the countries the app keys on (DG SANTE gives ISO2 + the numeric code inline anyway).
_M49_BY_ISO3 = m49_by_iso3()


class DgSanteSource:
    name = "dgsante"

    def __init__(self, timeout: int = 60, pause: float = 0.3, page_size: int = 100):
        self.timeout = timeout
        self.pause = pause
        self.page_size = page_size

    def pull(self, countries: list[str], sections: list[str], verified_date: str) -> list[dict]:
        """For each (country, section) with approved establishments -> seller rows (capped, see below)."""
        rows: list[dict] = []
        for cc in countries:
            have = self._sections(cc)                      # {section code -> true count} for this country
            for sec in sections:
                total = have.get(sec)
                if not total:
                    continue
                ests = self._establishments(cc, sec)
                if total > len(ests):                      # NOT a silent cap — say what we dropped
                    print(f"[dgsante] {cc}/{sec}: showing {len(ests)} of {total} (API returns max 100/section)")
                for est in ests:
                    row = self._row(est, cc, sec, verified_date)
                    if row:
                        rows.append(row)
        return rows

    def _sections(self, cc: str) -> dict[str, int]:
        data = self._get(f"{BASE}?countryCode={cc}") or []
        out: dict[str, int] = {}
        for s in data:
            code = (((s.get("establishmentListingId") or {}).get("classificationSectionId") or {}).get("code"))
            cnt = s.get("establishmentCount") or s.get("count") or 0
            if code:
                out[code] = int(cnt) if cnt else 1
        return out

    def _establishments(self, cc: str, section: str) -> list[dict]:
        # DG SANTE IGNORES page/size beyond the first block — it returns at most 100 per section. So we
        # fetch ONCE (never loop: paging would spin forever on the same 100). 100 real exporters/section
        # is ample for the MVP; the full list is one click away on the cited source page.
        data = self._get(f"{BASE}/establishments/{cc}/{section}?page=0&size={self.page_size}")
        rows = (data or {}).get("content") if isinstance(data, dict) else data
        return rows or []

    @staticmethod
    def _row(est: dict, cc: str, section: str, verified_date: str) -> dict | None:
        name = est.get("operatorName")
        if not name or est.get("confidential"):            # never surface a record marked confidential
            return None
        city_ref = (est.get("address") or {}).get("cityReference") or {}
        country = city_ref.get("country") or {}
        m49 = country.get("iso31661NumericCode") or _M49_BY_ISO3.get(cc)
        acts = est.get("operatorActivityTypes") or []
        activity = next((a.get("translation") for a in acts if a.get("translation")), None)
        return {
            "seller": name.strip(),                        # organisation, never a person
            "seller_iso": (country.get("code") or cc).upper(),
            "seller_code": int(m49) if m49 else None,
            "approval_no": (est.get("approvalNumber") or "").strip() or None,
            "activity": activity,
            "city": (city_ref.get("name") or "").strip() or None,
            "section": section,
            "source": "dgsante",
            "source_url": f"{CITE}#!/view/{cc}/{section}",
            "verified_date": verified_date,
        }

    def _get(self, url: str):
        req = urllib.request.Request(url, headers={
            "X-Requested-With": "XMLHttpRequest", "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 tradepulse/0.1"})
        for attempt in range(2):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    return json.loads(r.read().decode("utf-8"))
            except Exception as e:  # noqa: BLE001 — transient; back off once
                if attempt == 0:
                    time.sleep(self.pause * 4)
                    continue
                print(f"[dgsante] warn {type(e).__name__} on {url[-40:]}")
                return None
            finally:
                time.sleep(self.pause)
