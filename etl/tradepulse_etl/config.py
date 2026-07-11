"""
config.py — pilot-scope constants for the ETL.
@context  Single source of the pilot vertical, destination markets, and signal thresholds.
          Everything scope-related lives here so widening a vertical is a config edit (plan §3).
@done     HS codes, market->reporter map (VN/EN names), partner codes, flow default, noise
          floors + signal bands (plan §6).
@todo     Add second vertical + markets when Stage 0 GO picks them.
@limits   PURE data. No I/O, no imports beyond stdlib typing.
@affects  Consumed by pipeline, transform, signals, and the web snapshot export.
"""

# --- Covered products (plan §3, §7.2). Each gets its own snapshot; the map switches per product. ---
HS_PELLETS = ["440131"]  # pilot vertical (kept for the fixture/tests)

# HS-6 -> bilingual product name (everyday words). Add a code here to cover a new category.
PRODUCTS = {
    "440131": {"name_en": "Wood pellets",     "name_vi": "Viên nén gỗ"},
    "440710": {"name_en": "Sawn wood",        "name_vi": "Gỗ xẻ"},
    "090240": {"name_en": "Black tea",        "name_vi": "Chè (trà) đen"},
    "090111": {"name_en": "Coffee",           "name_vi": "Cà phê"},
    "030617": {"name_en": "Frozen shrimp",    "name_vi": "Tôm đông lạnh"},
    "080131": {"name_en": "Cashew (in shell)", "name_vi": "Hạt điều"},
    "100630": {"name_en": "Milled rice",      "name_vi": "Gạo"},
}

# The list the ETL pulls + exports a snapshot for. First = the landing default.
COVERED_HS = ["440131", "440710", "090240", "090111", "030617", "080131", "100630"]

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
