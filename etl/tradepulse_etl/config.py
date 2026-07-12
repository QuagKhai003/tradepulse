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
    "TOTAL":  {"name_en": "All products",     "name_vi": "Tất cả sản phẩm"},   # every commodity
    # --- categories (HS-4 headings) ---
    "0901":   {"name_en": "Coffee",           "name_vi": "Cà phê"},
    "0902":   {"name_en": "Tea",              "name_vi": "Chè (trà)"},
    "1006":   {"name_en": "Rice",             "name_vi": "Gạo"},
    "0306":   {"name_en": "Crustaceans",      "name_vi": "Giáp xác (tôm, cua)"},
    "0801":   {"name_en": "Nuts (cashew/coconut)", "name_vi": "Hạt (điều, dừa)"},
    "4401":   {"name_en": "Wood fuel",        "name_vi": "Nhiên liệu gỗ"},
    # --- specific products (HS-6) ---
    "440131": {"name_en": "Wood pellets",     "name_vi": "Viên nén gỗ"},
    "4407":   {"name_en": "Sawn wood",        "name_vi": "Gỗ xẻ"},
    "090240": {"name_en": "Black tea",        "name_vi": "Trà đen"},
    "090210": {"name_en": "Green tea",        "name_vi": "Trà xanh"},
    "090111": {"name_en": "Coffee, green",    "name_vi": "Cà phê nhân"},
    "090121": {"name_en": "Coffee, roasted",  "name_vi": "Cà phê rang"},
    "030617": {"name_en": "Frozen shrimp",    "name_vi": "Tôm đông lạnh"},
    "080131": {"name_en": "Cashew (in shell)", "name_vi": "Điều thô"},
    "080132": {"name_en": "Cashew (shelled)", "name_vi": "Điều nhân"},
    "100630": {"name_en": "Milled rice",      "name_vi": "Gạo xát"},
    "100640": {"name_en": "Broken rice",      "name_vi": "Tấm (gạo tấm)"},
    # broader set (Vietnam exports + global majors) — categories
    "8517":   {"name_en": "Phones & telecom", "name_vi": "Điện thoại & viễn thông"},
    "8542":   {"name_en": "Integrated circuits", "name_vi": "Vi mạch (IC)"},
    "6109":   {"name_en": "T-shirts",         "name_vi": "Áo thun"},
    "6110":   {"name_en": "Knitwear",         "name_vi": "Áo len dệt kim"},
    "6403":   {"name_en": "Leather footwear", "name_vi": "Giày da"},
    "9403":   {"name_en": "Furniture",        "name_vi": "Đồ nội thất"},
    "4001":   {"name_en": "Natural rubber",   "name_vi": "Cao su tự nhiên"},
    "0904":   {"name_en": "Pepper",           "name_vi": "Hạt tiêu"},
    "0304":   {"name_en": "Fish fillets",     "name_vi": "Phi lê cá"},
    "0803":   {"name_en": "Bananas",          "name_vi": "Chuối"},
    "2709":   {"name_en": "Crude oil",        "name_vi": "Dầu thô"},
    "8703":   {"name_en": "Cars",             "name_vi": "Ô tô"},
    "1201":   {"name_en": "Soybeans",         "name_vi": "Đậu tương"},
    "1511":   {"name_en": "Palm oil",         "name_vi": "Dầu cọ"},
}

# The list the ETL pulls + exports a snapshot for. First = the landing default (all products).
COVERED_HS = list(PRODUCTS.keys())

# Sourcing (quarterly partner drill-down) is heavy — only the core products get it; the rest still
# get the map/signals + annual history.
SOURCING_HS = ["TOTAL", "440131", "4407", "090240", "090111", "030617", "080131", "100630"]

# Focus countries for the quarterly partner-sourcing drill-down (all-countries quarterly is too
# heavy). Vietnam (exporter) + the pilot import markets. Others show annual history only.
FOCUS_REPORTERS = [704, 392, 410, 842, 826]

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
