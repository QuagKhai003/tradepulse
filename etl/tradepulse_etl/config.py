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
SOURCING_HS = ["TOTAL", "440131", "4407", "090240", "090111", "030617", "080131", "100630"]

# Quarterly (monthly->quarters) is heavier per call — all-reporters monthly must be pulled ONE month
# at a time (12-period all-country calls time out). So only the core products get quarterly (excl.
# TOTAL, whose all-commodity payload is too big). This feeds the M/Q/A toggle for these products.
QUARTERLY_HS = [hs for hs in SOURCING_HS if hs != "TOTAL"]

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
    "eurostat": {m["reporter"] for m in MARKETS.values() if m.get("reporter") == 97},  # EU (add members later)
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
