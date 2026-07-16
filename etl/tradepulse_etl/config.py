"""
config.py — pilot-scope constants for the ETL.
@context  Single source of the pilot vertical, destination markets, and signal thresholds.
          Everything scope-related lives here so widening a vertical is a config edit (plan §3).
@done     HS codes, market->reporter map (VN/EN names), partner codes, flow default, noise
          floors + signal bands (plan §6).
@todo     Add second vertical + markets when Stage 0 GO picks them.
@limits   Constants + the bundled product catalog (reference/products.json). Stdlib only.
@affects  Consumed by pipeline, transform, signals, and the web snapshot export.
"""
import json
from pathlib import Path

# --- Covered products (plan §3, §7.2). Each gets its own snapshot; the map switches per product. ---
HS_PELLETS = ["440131"]  # pilot vertical (kept for the fixture/tests)

# Product CATALOG (search/browse): TOTAL + every HS4 heading (1,229, official HS-2022 titles) + the
# curated HS6 pilot products. Generated into reference/products.json; the curated entries keep their
# Vietnamese names, the new HS4 headings are English-only for now (VN to come from Vietnam's HS list).
_PRODUCTS_PATH = Path(__file__).resolve().parent / "reference" / "products.json"
PRODUCTS: dict = json.loads(_PRODUCTS_PATH.read_text(encoding="utf-8"))

# CATALOG vs COVERAGE are deliberately different:
#   PRODUCTS   = the searchable catalog (1,240: TOTAL + every HS4 heading + curated HS6).
#   COVERED_HS = the products we actually build a snapshot for (the ETL writes one JSON per product).
# A full snapshot averages ~310KB (country names repeated per file + 6-pt history + by_freq duplication),
# so all 1,240 would be ~390MB of static JSON — far too heavy. Until the snapshot format is slimmed
# (shared country names, no by_freq duplication, history moved out), coverage stays on the curated set;
# search still lists all 1,240 and uncovered products fall through to the "not covered yet" path.
CURATED_HS = [c for c, v in PRODUCTS.items() if c == "TOTAL" or v["name_vi"] != v["name_en"]]
COVERED_HS = list(PRODUCTS.keys())      # all 1,240 — the slim snapshot format (~48KB) makes this ship

# Sourcing (quarterly partner drill-down) is heavy — only the core products get it; the rest still
# get the map/signals + annual history.
# Both the HS4 HEADING (what search/catalog resolves a commodity to, e.g. coffee -> 0901) AND the curated
# HS6 child, so the partner tables show for whichever the user lands on — same UI everywhere, real data.
SOURCING_HS = ["TOTAL", "4401", "440131", "4407", "0901", "090111", "0902", "090240",
               "0306", "030617", "0801", "080131", "1006", "100630"]

# Quarterly (monthly->quarters) is heavier per call — all-reporters monthly must be pulled ONE month
# at a time (12-period all-country calls time out). So only the core products get quarterly (excl.
# TOTAL, whose all-commodity payload is too big). This feeds the M/Q/A toggle for these products.
# Products that get monthly->quarterly (the Year/Quarter toggle): the pilot commodities + the top
# ~150 by trade value (the headings users actually open). The rest show a greyed 'Quarter' (option 2).
_QHS_PATH = Path(__file__).resolve().parent / "reference" / "quarterly_hs.json"
try:
    _QHS_EXTRA = set(json.loads(_QHS_PATH.read_text(encoding="utf-8")))
except FileNotFoundError:
    _QHS_EXTRA = set()
QUARTERLY_HS = sorted(({hs for hs in CURATED_HS if hs != "TOTAL"} | _QHS_EXTRA) - {"TOTAL"})

# Focus countries for the quarterly partner-sourcing drill-down (all-countries quarterly is too
# heavy). Vietnam (exporter) + the pilot import markets. Others show annual history only.
FOCUS_REPORTERS = [704, 392, 410, 842, 826]

# NOTE (2026-07-13): Japan (e-Stat) + Korea (data.go.kr) national sources are NOT used — e-Stat's trade
# tables use Japan's 概況品 classification (not HS) and KCS's key/endpoint is unreliable. Comtrade
# already covers Japan (392) + Korea (410) in HS, so nothing is lost; only the "fresher monthly" bonus
# is skipped for those two. The fresh national primaries are US (census), EU (eurostat), UK (hmrc).

# --- Destination markets (plan §3): slug -> codes + bilingual names ---
# reporter = the importing country whose customs report the flow (importer-reported default, §6.4).
MARKETS = {
    "jp": {"name_en": "Japan",          "name_vi": "Nhật Bản",           "reporter": 392},
    "kr": {"name_en": "South Korea",    "name_vi": "Hàn Quốc",           "reporter": 410},
    "eu": {"name_en": "European Union", "name_vi": "Liên minh châu Âu",  "reporter": 97},
    "us": {"name_en": "United States",  "name_vi": "Hoa Kỳ",             "reporter": 842},
    "gb": {"name_en": "United Kingdom", "name_vi": "Anh",                "reporter": 826},
}

# --- Tenders + awards (plan §9.2): FORWARD demand (who is buying now) and PAST ORDERS (who won). ---
# EU TED classifies by CPV, not HS, and no official HS<->CPV crosswalk exists. Two layers:
#   1. TENDER_CPV_MANUAL below — hand-mapped and hand-checked for the pilot products. Authoritative.
#   2. reference/cpv_by_hs.json — generated for every other product by _gen_cpv.py, which proposes a
#      CPV from the HS heading's text and then VERIFIES it live against TED (a code is kept only if
#      TED really files on-product notices under it). The manual map always wins on conflict.
# Golden Rule: public BUYER/WINNER ORGANISATION + the official notice link only — never a contact person.
TENDER_CPV_MANUAL = {
    "440131": ["09111400"],              # wood pellets  -> wood fuels
    "4401":   ["09111400"],              # wood fuel
    "4407":   ["03410000"],              # sawn wood     -> wood
    "0901":   ["15861000"],              # coffee
    "090111": ["15861000"],
    "090121": ["15861000"],
    "0902":   ["15863000"],              # tea
    "090240": ["15863000"],
    "090210": ["15863000"],
    "1006":   ["03211300"],              # rice
    "100630": ["03211300"],
    "100640": ["03211300"],
    "0306":   ["03310000"],              # crustaceans   -> fish & aquatic products
    "030617": ["03310000"],
    "0801":   ["03222000"],              # nuts          -> fruit & nuts
    "080131": ["03222000"],
    "080132": ["03222000"],
    "0904":   ["15872100"],              # pepper
}

_CPV_MAP_PATH = Path(__file__).resolve().parent / "reference" / "cpv_by_hs.json"
try:
    _CPV_GENERATED = json.loads(_CPV_MAP_PATH.read_text(encoding="utf-8"))
except FileNotFoundError:                # not generated yet -> the pilot products still work
    _CPV_GENERATED = {}

# hand-checked codes override the generated ones; everything else comes from the verified map
TENDER_CPV = {hs: v["cpv"] for hs, v in _CPV_GENERATED.items()}
TENDER_CPV.update(TENDER_CPV_MANUAL)

TENDER_LOOKBACK_DAYS = 365
# Awards look back further: a past order stays evidence that a company SELLS this product long after
# the contract closed — that is the point of the sellers list.
AWARD_LOOKBACK_DAYS = 730               # how far back to ask TED for still-ACTIVE notices

# Product -> English keywords for keyword-based procurement search (US USAspending; and local matching
# on the OCDS feeds that have no server-side product filter). Pilots first; grows with coverage.
PROCUREMENT_KW = {
    "440131": ["wood pellet"],
    "4401":   ["wood pellet", "fuel wood"],
    "4407":   ["sawn wood", "lumber", "timber"],
    "0901":   ["coffee"],
    "0902":   ["tea"],
    "1006":   ["rice"],
    "0306":   ["shrimp", "prawn"],
    "0801":   ["cashew"],
    "0904":   ["pepper", "peppercorn"],
}

# OCDS publishers for market-specific public buyers beyond EU TED (sources/ocds.py). Each is one country;
# bulk-paged (no server-side product filter) and matched LOCALLY to TENDER_CPV. (name, base_url, iso3).
# Only feeds that page newest-first via OCDS links.next go here; date-path/cursor feeds are added per-source.
OCDS_PUBLISHERS = [
    ("uk-cf",   "https://www.contractsfinder.service.gov.uk/Published/Notices/OCDS/Search?limit=100", "GBR"),
    ("uk-fts",  "https://www.find-tender.service.gov.uk/api/1.0/ocdsReleasePackages?limit=100",        "GBR"),
    ("uk-scot", "https://api.publiccontractsscotland.gov.uk/v1/Notices?dateFrom={since}",              "GBR"),
]
OCDS_MAX_PAGES = 30                      # bound the bulk scan (our products are niche)

# Korea KONEPS has no product filter -> match the KOREAN bid-notice title locally (sources/koneps.py).
KONEPS_KW = {
    "440131": ["펠릿", "목재펠릿", "우드펠릿"],
    "4401":   ["펠릿", "목재펠릿", "우드펠릿"],
    "4407":   ["제재목"],
    "0901":   ["커피", "원두"],
    "0902":   ["녹차", "홍차"],
    "1006":   ["백미", "현미"],
    "0306":   ["새우"],
    "0801":   ["캐슈"],
    "0904":   ["후추"],
}

# --- Regulatory-event lane (ADR-0007): the qualification tab / change-alerts ---------------------
# A SEPARATE lane from trade_flows (never merged). Pilot products -> the search terms ePing files them
# under (ePing has no HS<->term index; its own hsCodes[] tag confirms a match when present). HS4 keys
# are keys in PRODUCTS. Kept to the pilots first (wood pellets/wood, coffee, tea, rice, shrimp, cashew).
REGULATORY_HS = {
    "440131": ["wood pellet", "wood fuel"],
    "4401":   ["wood pellet", "wood fuel", "fuel wood"],
    "4407":   ["sawnwood", "sawn wood", "lumber", "timber"],
    "0901":   ["coffee"],
    "090111": ["coffee"],
    "0902":   ["tea"],
    "090240": ["tea"],
    "1006":   ["rice"],
    "100630": ["rice"],
    "0306":   ["shrimp", "prawn"],
    "030617": ["shrimp", "prawn"],
    "0801":   ["cashew"],
    "080131": ["cashew"],
}
REGULATORY_LOOKBACK_DAYS = 1095      # keep rule-changes from the last ~3y (requirements age slowly)

# EU RASFF border-REJECTIONS -> the qualification tab (a 2nd event source, kind='rejection'). A rejected
# shipment at the EU border is a live warning to a seller ("EU found antibiotic in shrimp from VN"). Maps
# a product to its RASFF product-CATEGORY id; because a category is broad (18434 = all cereals), a row is
# kept only if the notification SUBJECT also contains one of the product's REGULATORY_HS keywords. Food/
# feed only -> no wood. Vietnam-origin rejections are the sharpest signal (surfaced in the detail line).
RASFF_CAT = {
    "0901": 18435, "090111": 18435, "090121": 18435,      # cocoa/coffee/tea
    "0902": 18435, "090240": 18435, "090210": 18435,
    "1006": 18434, "100630": 18434, "100640": 18434,      # cereals and bakery
    "0306": 18438, "030617": 18438,                        # crustaceans
    "0801": 18427, "080131": 18427, "080132": 18427,      # nuts, nut products and seeds
}
RASFF_LOOKBACK_DAYS = 540            # a border rejection is a timely warning -> ~18-month window

# ePing notifyingMember (a country NAME) -> our market slug, for the qualification tab's per-market
# view. EU members all fold to 'eu' (the pilot treats the EU as one market). Names not here keep their
# own name and slug=None (still shown on the product-wide qualification view, just not pinned to a pilot).
_EU27 = {"Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czech Republic", "Czechia", "Denmark",
         "Estonia", "Finland", "France", "Germany", "Greece", "Hungary", "Ireland", "Italy", "Latvia",
         "Lithuania", "Luxembourg", "Malta", "Netherlands", "Poland", "Portugal", "Romania", "Slovak Republic",
         "Slovakia", "Slovenia", "Spain", "Sweden", "European Union"}
MARKET_BY_ENAME = {**{n: "eu" for n in _EU27},
                   "Japan": "jp",
                   "Korea, Republic of": "kr", "Republic of Korea": "kr", "Korea": "kr",
                   "United States of America": "us", "United States": "us",
                   "United Kingdom": "gb", "United Kingdom of Great Britain and Northern Ireland": "gb"}

# --- Forward lane (ADR-0007): world commodity PRICE trend (IMF PCPS) -----------------------------
# A SEPARATE lane from customs value (different unit — a $/unit world price, not a trade total), shown
# BESIDE the flow chart as a direction signal ("price of this commodity is rising -> demand firm"). Not
# a forecast of volume; a price is deterministic + published monthly + fresher than customs stats. Only
# products with a HONEST direct IMF series get a line — no misleading proxies (no wood-pellet or cashew
# price exists, so those show none). Coffee uses ROBUSTA (Vietnam is the world's #1 robusta exporter).
PRICE_HS = {
    "0901": "PCOFFROB", "090111": "PCOFFROB", "090121": "PCOFFROB",
    "0902": "PTEA", "090240": "PTEA", "090210": "PTEA",
    "1006": "PRICENPQ", "100630": "PRICENPQ", "100640": "PRICENPQ",
    "0306": "PSHRI", "030617": "PSHRI",
    "4407": "PSAWMAL",
}
PRICE_LABEL = {                          # human name of the IMF series (shown so the proxy is explicit)
    "PCOFFROB": {"en": "Coffee (robusta)", "vi": "Cà phê (robusta)"},
    "PTEA":     {"en": "Tea", "vi": "Trà"},
    "PRICENPQ": {"en": "Rice (Thai 5%)", "vi": "Gạo (Thái 5%)"},
    "PSHRI":    {"en": "Shrimp", "vi": "Tôm"},
    "PSAWMAL":  {"en": "Sawnwood (Malaysia)", "vi": "Gỗ xẻ (Malaysia)"},
}
PRICE_MONTHS = 26                        # months of history to pull (enough for a 24-mo trend + YoY)

# --- USDA FAS PSD FORWARD OUTLOOK (ADR-0007 separate lane): global supply/demand FORECAST by market
# year for the AG commodities in our catalog. A forward lane like IMF price, but quantities not $/unit —
# who is forecast to produce/import/consume next market year. Endpoint api.fas.usda.gov, X-Api-Key header
# (USDA_API_KEY). Only ag products map; the rest honestly show none. See sources/psd.py. ---
PSD_HS = {                               # our HS heading -> PSD commodityCode
    "0901": "0711100",   # Coffee, Green
    "1006": "0422110",   # Rice, Milled
    "1001": "0410000",   # Wheat
    "1005": "0440000",   # Corn
    "1201": "2222000",   # Oilseed, Soybean
    "1511": "4243000",   # Oil, Palm
    "1701": "0612000",   # Sugar, Centrifugal
    "5201": "2631000",   # Cotton
    "0207": "0114200",   # Poultry, Meat, Broiler
}
PSD_MARKETS = {                          # our M49 market code -> PSD country code (0 = World balance)
    0: "00", 842: "US", 392: "JA", 410: "KS", 826: "UK", 97: "E4", 704: "VM", 156: "CH",
}
PSD_ATTRS = {                            # attributeId -> (en, vi); the headline supply/demand line items
    28:  ("Production", "Sản lượng"),
    57:  ("Imports", "Nhập khẩu"),
    88:  ("Exports", "Xuất khẩu"),
    125: ("Domestic consumption", "Tiêu thụ nội địa"),
    176: ("Ending stocks", "Tồn kho cuối kỳ"),
}
PSD_YEARS = 5                            # recent market years to pull (spans history + the forecast year)

# M49 country code -> market slug, for matching a SIGNAL watch (country + product) to the regulatory
# events of that market (change-alerts). The EU is the aggregate (97) AND each member state.
_EU27_M49 = [40, 56, 100, 191, 196, 203, 208, 233, 246, 250, 276, 300, 348, 372, 380,
             428, 440, 442, 470, 528, 616, 620, 642, 703, 705, 724, 752]
MARKET_SLUG_BY_M49 = {m["reporter"]: slug for slug, m in MARKETS.items()}
MARKET_SLUG_BY_M49.update({c: "eu" for c in _EU27_M49})

# --- Fresh national ASIA primary: Thailand MOC (keyless HS×partner JSON, fresh to ~1 month) ----------
# Refreshes THAILAND's own map cell (reporter 764), like Census does for the US — the app sums the
# per-partner rows into a World total. Scoped to the pilot products (a per-product API over all 1,240
# would be tens of thousands of calls). NOT used to rebuild Vietnam's world total: Thailand is one buyer,
# so that alone would badly understate VN — a wrong number we will not show (Golden Rule).
THAI_HS = ["0901", "0902", "1006", "0306", "0801", "4407", "440131"]
THAILAND_M49 = 764

# India DGCI&S TRADESTAT (keyless, CSRF-token + session — no login). One POST returns India's whole
# HS4 export (or import) table for a fiscal year in US$ million. Refreshes INDIA's own cell (reporter
# 699). India's FY runs Apr–Mar, so FY2024-25 is labelled period '2024' (the FY start) — a fiscal year,
# not calendar; it still merges as India's own authority over Comtrade. Same non-use as Thailand: not
# for rebuilding VN's world total. Pilots only (the table is fetched whole, then filtered).
INDIA_HS = ["0901", "0902", "1006", "0306", "0801", "4407"]
INDIA_M49 = 699
INDIA_FY = "2024"      # EidbYear param -> FY2024-25 (latest reliable); labelled period '2024'

PARTNER_WORLD = 0      # aggregate of all partners
PARTNER_VIETNAM = 704  # for VN import-share on drill-down (plan §7.3)

# Partner (exporter) code -> bilingual name, for the sourcing drill-down (plan §7.3).
COUNTRY_NAMES = {
    0:   {"en": "World",         "vi": "Thế giới"},
    704: {"en": "Vietnam",       "vi": "Việt Nam"},
    360: {"en": "Indonesia",     "vi": "Indonesia"},
    458: {"en": "Malaysia",      "vi": "Malaysia"},
    124: {"en": "Canada",        "vi": "Canada"},
    842: {"en": "United States", "vi": "Hoa Kỳ"},
    643: {"en": "Russia",        "vi": "Nga"},
}

FLOW_IMPORT = "M"      # importer-reported is the consistent default side (plan §6.4)
FLOW_EXPORT = "X"

# --- Signal thresholds (plan §6.2, §6.3). Config, not code — tune with real data. ---
NOISE_MIN_VALUE = 10_000_000   # >= $10M this quarter for the country x product cell
NOISE_MIN_BASE = 2_000_000     # >= $2M same period last year (kills divide-by-tiny)
NOISE_MIN_HISTORY = 4          # >= 4 quarters of data for the cell
NEW_LANE_MIN = 5_000_000       # base ~ 0 and now >= $5M => new trade lane

# YoY band edges (fraction). (-0.15, 0.15) is suppressed ("minor", excluded by design).
BAND_MODERATE = 0.15
BAND_SIGNIFICANT = 0.30
BAND_SURGE = 0.60

# --- Multi-source merge (docs/DATA_SOURCES.md). One number per cell; never sum two sources. ---
# A source is the AUTHORITY for the reporters it natively reports (each country owns its own customs
# data). Comtrade is authority for NO ONE → it's the global fallback everyone else outranks.
SOURCE_AUTHORITY = {
    "census":   {842},          # US Census Bureau — US only
    # Eurostat is authoritative for each EU27 MEMBER STATE (M49), reported individually — it overrides
    # the Comtrade API for Germany, France, ... (matches sources/eurostat.EU27).
    "eurostat": {40, 58, 100, 191, 196, 203, 208, 233, 246, 251, 276, 300, 348, 372, 380, 428, 440,
                 442, 470, 528, 616, 620, 642, 703, 705, 724, 752},
    "hmrc":     {826},          # UK HMRC
    "estat":    {392},          # Japan e-Stat
    "kcs":      {410},          # Korea Customs
}
# Final tiebreak when authority + freshness are equal: LOWER rank wins. National primaries beat
# Comtrade; the offline fixture always loses to any real source.
SOURCE_PRIORITY = {
    "census": 10, "eurostat": 10, "hmrc": 10, "estat": 10, "kcs": 10,
    "baci": 40,        # cleaned/reconciled global bulk — preferred over the raw Comtrade API
    "comtrade": 50,
    # Mirror = a country's exports rebuilt from its PARTNERS' import reports. An ESTIMATE (importers
    # report CIF, ~5-10% above the exporter's FOB), so it ranks BELOW every direct self-report and only
    # ever wins a cell no direct source filled — i.e. recent years a country hasn't reported yet.
    "comtrade-mirror": 55,
    "fixture": 99,
}
SOURCE_PRIORITY_DEFAULT = 90    # an unknown source ranks just above the fixture


def freq_of(period: str) -> str:
    """Grain label from the period string: 'A' annual (YYYY), 'Q' quarterly (YYYY-Qn), 'M' monthly
    (YYYYMM). Lets the UI offer a monthly/quarterly/annual toggle without a separate dimension."""
    p = str(period)
    if "-Q" in p:
        return "Q"
    if len(p) == 6 and p.isdigit():
        return "M"
    return "A"


# --- Incremental refresh (production): only re-fetch the REVISABLE window; final periods stay put.
# Trade data is revised for a while then frozen — so 2021 is fetched once, but recent periods keep
# updating each run. Cuts a full re-pull down to a few recent periods after the first run. ---
REVISION_YEARS = 2      # always re-pull the latest ~2 years (annual figures get revised that long)
MIRROR_YEARS = 2        # rebuild the latest ~2 years from partner reports (fills late/non-reporters)
REVISION_MONTHS = 6     # always re-pull the latest ~6 months (recent quarters get revised)


def _period_end_ym(period: str) -> tuple[int, int]:
    """(year, month) of the period's LAST month: annual->Dec, 'YYYY-Qn'->quarter end, 'YYYYMM'->itself."""
    p = str(period)
    if "-Q" in p:
        y, q = p.split("-Q")
        return int(y), int(q) * 3
    if len(p) == 6 and p.isdigit():
        return int(p[:4]), int(p[4:])
    return int(p), 12


def is_final(period: str, today) -> bool:
    """A stored period is 'final' — won't be re-fetched — once it is older than the revision window."""
    ey, em = _period_end_ym(period)
    months_ago = (today.year - ey) * 12 + (today.month - em)
    if freq_of(period) == "A":
        return months_ago > REVISION_YEARS * 12
    return months_ago > REVISION_MONTHS


# --- Sellers = REAL exporters, from approval registries (plan §7.4; ADR-0006). Phase 1: EU DG SANTE
# (animal-origin, keyless) -> seafood + honey. A DG SANTE "section" maps to the HS products it covers;
# an establishment approved for that section is a seller of each of those products. ---
SELLER_SECTIONS = {
    "FFP": ["0301", "0302", "0303", "0304", "0305", "0306", "030617", "0307", "0308", "1604", "1605"],
    "LBM": ["0307", "0308"],          # live bivalve molluscs
    "HON": ["0409"],                  # honey
}
# Exporter countries to pull (major seafood exporters + the pilot origin). DG SANTE lists every
# third country approved to export to the EU; we bound the pull to the ones a user would care about.
SELLER_COUNTRIES = ["VN", "IN", "EC", "ID", "CN", "TH", "BD", "AR", "CL", "PE", "MA", "TR",
                    "VE", "MX", "PH", "LK", "MY", "SN", "NG", "GH"]
