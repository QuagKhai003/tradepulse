# DATA_SOURCES — verified free data sources (research log)

> What we use, and what we've verified is available for later. Every source here was checked LIVE
> (2026-07-14) unless marked otherwise. Boundary (never crossed): free + public/official + citable;
> no paid providers (Panjiva/Volza/ImportGenius/Tridge/Trading Economics), no paywall/login bypass.
> Undocumented-but-public endpoints (a portal's keyless XHR API) are fair game; auth bypass is not.

## Layer 1 — trade flows (value/volume by HS product × country × period)

### In use
- **UN Comtrade** (`comtradeapi.un.org/data/v1`) — keyed. Annual all-countries + monthly→quarterly for
  the pilot products. The backbone. Rate-limited; the heavy monthly all-reporters query times out in
  big batches (use `MONTHLY_CODES_PER_CALL`).
- **CEPII BACI** (bulk file) — reconciled bilateral history, all HS6, no throttle. Ends ~2 years back
  (currently 2023), so it's the HISTORY spine; Comtrade + national sources cover recent years.
- **Comtrade MIRROR** (`ComtradeMirrorSource`) — a late/non-reporter's exports rebuilt from partners'
  imports. Fills Vietnam (reports annual + ~2y late) and others. Marked `est.` in the UI.

### Verified available (not yet wired) — freshness + redundancy
| Source | Endpoint | Auth | Fresh to | HS×country? | Independent? |
|---|---|---|---|---|---|
| **Comtrade preview** | `comtradeapi.un.org/public/v1/preview/C/{A\|M}/HS` | **none** | May 2026 (M) | yes | same data, SEPARATE throttle → **rate-limit failover** |
| **Eurostat** | `ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{id}` | **none** | **Apr 2026** | monthly at BEC/SITC via JSON API; HS6 via free Comext bulk | ✅ EU customs |
| **US Census** | `api.census.gov/data/timeseries/intltrade/{exports\|imports}/hs` | free key | monthly | HS10 × country | ✅ US customs |
| **Japan e-Stat** | `api.e-stat.go.jp/rest/3.0/app/json/getStatsData` (statsCode 00350300) | free appId | **May 2026** | 9-digit → truncate to HS6 | ✅ JP customs |
| **Korea KCS** | `apis.data.go.kr/1220000/nitemtrade/getNitemtradeList` (data.go.kr #15100475) | free key | **Jun/Jul 2026** | HS 2/4/6/10 × country (XML) | ✅ KR customs. Web viewer: tradedata.go.kr (no login) |
| IMF DOTS | IMF JSON | none | monthly | value only, **no HS** | ✅ (backstop signal) |
| OEC.world / WITS / BACI-API | oec.world `olap-proxy`, wits.worldbank.org | none | annual | yes | ❌ Comtrade re-served — NOT independent, no help in an outage |
| HMRC uktradeinfo | `api.uktradeinfo.com` (OData) | none by design | monthly | HS × country | ✅ UK — but WAF-blocks datacenter IPs; may work from the user's own/UK server |
| Trading Economics | — | PAID | — | — | ❌ off-limits |

**Recommendation:** (1) `/public/v1/preview` as an automatic failover when the keyed API throttles —
cheapest, same schema. (2) Eurostat + US Census + Japan e-Stat + Korea KCS give every pilot market a
free, independent, ~monthly source. **Vietnam has no quarterly source anywhere** (reports annual + late)
— its freshest is the mirror estimate; that's a data reality, not fixable.

## Layer 2 — parties (buyers / sellers / past orders)

### In use
- **EU TED** (`api.ted.europa.eu/v3`) — keyless. Open tenders (**Buyers**) + award notices (**Past
  orders**). CPV-classified; on-product filter (contract/lot kept, basket dropped). Notice link needs a
  format segment: `/notice/<id>/html` (the bare path 404s).
- **EU DG SANTE / TRACES NT** (`webgate.ec.europa.eu/tracesnt/directory/listing/establishment/publication`)
  — keyless. **Sellers** = approved third-country exporters (ADR-0006). Animal-origin → seafood + honey.
  Caps 100/section (page param ignored). Live: 2,219 exporters, 137 Vietnamese.

### Verified available (not yet wired) — Sellers Phase 2 + wider awards
- **USDA Organic INTEGRITY** — certified organic operators incl. Vietnam (coffee/tea/cashew/rice
  SELLERS). Free api.data.gov key + monthly full dataset. Best for the non-seafood pilot products.
- **Korea MFDS** overseas-manufacturer registry (data.go.kr, free key) — foreign food exporters to KR.
- **UK Defra** approved-establishment XLSX (CKAN, keyless) — names foreign incl. VN exporters (seafood).
- **Vietnam MOIT** licensed rice exporters (.xls, 151 rows); **PPD/MARD** packing-house codes;
  **NAFIQAD** seafood DL codes — origin-side registries naming Vietnamese exporters.
- **US SAM.gov / USASpending** (free, USASpending keyless) + **UK Contracts Finder / Find a Tender**
  (keyless OCDS) — contract AWARDS beyond the EU → widen Past orders to US/UK. Product code = NAICS/PSC
  (US) or CPV (UK); needs a small crosswalk to our products.
- **FSC / PEFC** certificate directories (non-governmental but citable) — the only seller-ish signal for
  wood pellets, which no official approval registry covers.

### Not usable (recorded so we don't re-chase)
- **Named-IMPORTER / private shipment data** (who BOUGHT what) is essentially all PAID (US bill-of-lading
  via Panjiva/Volza/ImportGenius; India/LATAM resellers). Free named-importer data appears only in
  violation/recall lists (Japan MHLW, Korea recalls, US FDA import refusals) — a detention-biased sample.
- **Free named-shipment customs data** is scarce: Chile/Ecuador publish shipment-level but DE-IDENTIFIED
  (no company name); only **Paraguay DNA** + **Peru SUNAT** name both parties, and both are
  Latin-American-import lenses (marginal to Vietnamese pilot products). JP/KR/EU/US/UK publish NO free
  named-importer shipment data.
