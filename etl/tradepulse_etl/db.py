"""
db.py — SQLite schema + access (the persistence seam for the MVP).
@context  Star schema over trade flows (plan §10.2). SQLite now; Postgres later behind the
          same functions so callers don't change (CONVENTIONS §11).
@done     Schema for trade_flows + signals; connect(); upsert_trade_flows(); read helpers.
@todo     Swap impl to Postgres in production; add companies/requirement tables in later batches.
@limits   Only tables this MVP needs. Value/volume only — never order counts (plan §4.2).
@affects  Written by pipeline (trade_flows) + signals (signals). Read by the web snapshot export.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

# Repo-root/data/tradepulse.sqlite (gitignored — it is derived, re-buildable state).
DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "tradepulse.sqlite"

SCHEMA = """
CREATE TABLE IF NOT EXISTS trade_flows (
    reporter        INTEGER NOT NULL,
    partner         INTEGER NOT NULL,
    hs6             TEXT    NOT NULL,
    period          TEXT    NOT NULL,   -- 'YYYY' | 'YYYY-Qn' | 'YYYYMM' (grain lives here)
    freq            TEXT,               -- 'A' | 'Q' | 'M' (label for the UI toggle)
    flow            TEXT    NOT NULL,    -- 'M' import / 'X' export
    value_usd       REAL    NOT NULL,
    quantity        REAL,
    qty_unit        TEXT,
    source          TEXT    NOT NULL,   -- winning source after merge (freshness stamp)
    published_date  TEXT,
    PRIMARY KEY (reporter, partner, hs6, period, flow)
);

-- The snapshot export reads one product at a time; without this it scanned the whole table per product.
CREATE INDEX IF NOT EXISTS ix_flows_hs6_partner ON trade_flows (hs6, partner);

CREATE TABLE IF NOT EXISTS signals (
    reporter        INTEGER NOT NULL,
    hs6             TEXT    NOT NULL,
    flow            TEXT    NOT NULL,
    period          TEXT    NOT NULL,
    value_usd       REAL    NOT NULL,
    base_usd        REAL    NOT NULL,
    yoy_delta       REAL    NOT NULL,
    band            TEXT    NOT NULL,
    computed_at     TEXT    NOT NULL,
    PRIMARY KEY (reporter, hs6, flow, period)
);

CREATE INDEX IF NOT EXISTS ix_signals_hs6 ON signals (hs6);

-- Forward demand (plan §10.2, Phase 2.2): public procurement notices = who is buying RIGHT NOW.
-- Public buyer ORGANISATION + official link only — never a named contact (Golden Rule).
CREATE TABLE IF NOT EXISTS tenders (
    id              TEXT    NOT NULL,   -- source notice id (TED publication-number)
    hs6             TEXT    NOT NULL,   -- the covered product this notice was matched to
    source          TEXT    NOT NULL,   -- 'ted'
    cpv             TEXT,               -- the classification that matched
    match_kind      TEXT,               -- 'contract' | 'lot' | 'basket' (basket = buried line item)
    title           TEXT    NOT NULL,
    buyer           TEXT,               -- buying ORGANISATION (never a person)
    buyer_country   TEXT,               -- ISO3
    published       TEXT,
    deadline        TEXT,               -- nullable (prior-information notices have none)
    url             TEXT    NOT NULL,
    scraped_at      TEXT    NOT NULL,
    PRIMARY KEY (id, hs6)
);

CREATE INDEX IF NOT EXISTS ix_tenders_hs6 ON tenders (hs6);

--- PAST ORDERS (plan §7.4): awarded contracts — who WON, from whom, for how much.
--- Sellers do not advertise; a won contract is the only public record that a company SELLS a product.
--- The SELLERS list is derived from this table. Winner + buyer ORGANISATION only — TED also exposes
--- winner-email / winner-person, and we never store or show them (Golden Rule).
CREATE TABLE IF NOT EXISTS awards (
    id              TEXT    NOT NULL,   -- TED publication-number
    hs6             TEXT    NOT NULL,
    winner          TEXT    NOT NULL,   -- the SELLER (organisation)
    source          TEXT    NOT NULL,
    cpv             TEXT,
    match_kind      TEXT,               -- 'contract' | 'lot' | 'basket'
    title           TEXT    NOT NULL,
    buyer           TEXT,
    buyer_country   TEXT,               -- ISO3
    winner_country  TEXT,               -- ISO3
    award_date      TEXT,
    value           REAL,               -- notice total; NULL when TED reports several lot values
    currency        TEXT,
    published       TEXT,
    url             TEXT    NOT NULL,
    scraped_at      TEXT    NOT NULL,
    PRIMARY KEY (id, hs6, winner)
);

CREATE INDEX IF NOT EXISTS ix_awards_hs6 ON awards (hs6);

--- SELLERS = real exporters, from approval registries (ADR-0006). A "seller" is a company APPROVED to
--- export a product (DG SANTE etc.), NOT a contract winner (that is `awards`/past orders). One row per
--- (source, approval_no, seller, seller_code). Public org + approval + source + verified date only.
CREATE TABLE IF NOT EXISTS registry_sellers (
    source          TEXT    NOT NULL,   -- 'dgsante' | 'ukdefra' | 'usda-organic' | ...
    approval_no     TEXT,               -- official approval/registration number (nullable)
    seller          TEXT    NOT NULL,   -- organisation
    seller_iso      TEXT,               -- ISO2
    seller_code     INTEGER,            -- M49
    activity        TEXT,               -- e.g. 'Processing Plant'
    city            TEXT,
    section         TEXT,               -- registry section code (mapped to HS in config.SELLER_SECTIONS)
    source_url      TEXT    NOT NULL,
    verified_date   TEXT    NOT NULL,
    PRIMARY KEY (source, approval_no, seller, seller_code)
);

CREATE INDEX IF NOT EXISTS ix_sellers_section ON registry_sellers (section);

--- REGULATORY EVENTS = public acts that change a market's qualification requirements (ADR-0007):
--- an import-rule change (WTO ePing SPS/TBT) or a border rejection (EU RASFF). Feeds the Layer-3
--- qualification tab + change-alerts. A SEPARATE lane — never merged into trade_flows. One row per
--- (source, event_id, hs4). Golden Rule: public act + official source URL only, never a party/contact.
CREATE TABLE IF NOT EXISTS regulatory_events (
    source          TEXT    NOT NULL,   -- 'wto-eping' | 'eu-rasff' | ...
    event_id        TEXT    NOT NULL,   -- the source's notification/notice id
    hs4             TEXT    NOT NULL,   -- product this event maps to (HS4; a product key in PRODUCTS)
    market          TEXT,               -- slug of the notifying/deciding market (jp|kr|eu|us|gb|<iso2>)
    market_name     TEXT,               -- human name of that market
    event_date      TEXT,               -- distribution/decision date (ISO)
    deadline        TEXT,               -- comment deadline (ePing) — forward-looking; nullable
    kind            TEXT    NOT NULL,   -- 'rule_change' (TBT/SPS) | 'rejection' (RASFF)
    area            TEXT,               -- 'TBT' | 'SPS' | hazard category
    title           TEXT,
    detail          TEXT,               -- measure / hazard / reason (plain text)
    match_kind      TEXT,               -- 'hs' (structured HS tag) | 'keyword' (freetext) — confidence
    source_url      TEXT    NOT NULL,
    verified_date   TEXT    NOT NULL,
    PRIMARY KEY (source, event_id, hs4)
);

CREATE INDEX IF NOT EXISTS ix_regevents_hs4 ON regulatory_events (hs4);

--- COMMODITY PRICES = the FORWARD lane's world price trend (ADR-0007), from IMF PCPS. A SEPARATE lane,
--- never merged into trade_flows (a $/unit world price is a different measure than a customs total).
--- One row per (source, hs4, period). Only products with an honest direct IMF series are stored.
CREATE TABLE IF NOT EXISTS commodity_prices (
    source          TEXT    NOT NULL,   -- 'imf-pcps'
    hs4             TEXT    NOT NULL,   -- product key (the series is world-level, shown on every country)
    indicator       TEXT,               -- IMF series code (e.g. PCOFFROB) — makes the proxy explicit
    period          TEXT    NOT NULL,   -- 'YYYY-MM'
    value           REAL,               -- world USD price level (for the trend shape + YoY)
    verified_date   TEXT    NOT NULL,
    PRIMARY KEY (source, hs4, period)
);

CREATE INDEX IF NOT EXISTS ix_prices_hs4 ON commodity_prices (hs4);
"""


def connect(db_path: Path | str = DEFAULT_DB) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """Add columns that post-date an existing dev DB (the sqlite is derived + rebuildable)."""
    tcols = {r[1] for r in conn.execute("PRAGMA table_info(tenders)")}
    if tcols and "match_kind" not in tcols:
        conn.execute("ALTER TABLE tenders ADD COLUMN match_kind TEXT")
    cols = {r[1] for r in conn.execute("PRAGMA table_info(trade_flows)")}
    if "freq" not in cols:
        conn.execute("ALTER TABLE trade_flows ADD COLUMN freq TEXT")
    # Rows written before the column existed carry freq=NULL — derive it from the period so the UI's
    # grain toggle sees them (annual 'YYYY', quarterly 'YYYY-Qn', monthly 'YYYYMM').
    conn.execute("""UPDATE trade_flows SET freq = CASE
                      WHEN length(period) = 4 THEN 'A'
                      WHEN period LIKE '%-Q%' THEN 'Q'
                      ELSE 'M' END
                    WHERE freq IS NULL""")
    conn.commit()


def upsert_trade_flows(conn: sqlite3.Connection, rows: list[dict]) -> int:
    """Idempotent upsert on the natural key. Re-running a pull overwrites, never duplicates."""
    sql = """
        INSERT INTO trade_flows
            (reporter, partner, hs6, period, freq, flow, value_usd, quantity, qty_unit, source, published_date)
        VALUES
            (:reporter, :partner, :hs6, :period, :freq, :flow, :value_usd, :quantity, :qty_unit, :source, :published_date)
        ON CONFLICT(reporter, partner, hs6, period, flow) DO UPDATE SET
            freq=excluded.freq, value_usd=excluded.value_usd, quantity=excluded.quantity,
            qty_unit=excluded.qty_unit, source=excluded.source, published_date=excluded.published_date
    """
    with conn:
        conn.executemany(sql, rows)
    return len(rows)


def count_trade_flows(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM trade_flows").fetchone()[0]


def fill_trade_flows(conn: sqlite3.Connection, rows: list[dict]) -> int:
    """Insert ONLY where the cell is empty — ON CONFLICT DO NOTHING. Used for mirror estimates, which
    are the lowest-priority source: they fill a country/period no direct report covered, and must never
    overwrite a real self-reported figure. (Fast: the DB does the skip, no Python-side lookup set.)"""
    sql = """
        INSERT INTO trade_flows
            (reporter, partner, hs6, period, freq, flow, value_usd, quantity, qty_unit, source, published_date)
        VALUES
            (:reporter, :partner, :hs6, :period, :freq, :flow, :value_usd, :quantity, :qty_unit, :source, :published_date)
        ON CONFLICT(reporter, partner, hs6, period, flow) DO NOTHING
    """
    with conn:
        cur = conn.executemany(sql, rows)
    return len(rows)

def upsert_registry_sellers(conn: sqlite3.Connection, rows: list[dict]) -> int:
    """Idempotent on (source, approval_no, seller, seller_code). Re-pulling refreshes verified_date."""
    sql = """
        INSERT INTO registry_sellers
            (source, approval_no, seller, seller_iso, seller_code, activity, city, section, source_url, verified_date)
        VALUES
            (:source, :approval_no, :seller, :seller_iso, :seller_code, :activity, :city, :section, :source_url, :verified_date)
        ON CONFLICT(source, approval_no, seller, seller_code) DO UPDATE SET
            seller_iso=excluded.seller_iso, activity=excluded.activity, city=excluded.city,
            section=excluded.section, source_url=excluded.source_url, verified_date=excluded.verified_date
    """
    with conn:
        conn.executemany(sql, rows)
    return len(rows)


def fetch_registry_sellers(conn: sqlite3.Connection, sections: list[str]) -> list[dict]:
    if not sections:
        return []
    q = ",".join("?" * len(sections))
    sql = f"SELECT * FROM registry_sellers WHERE section IN ({q}) ORDER BY seller"
    return [dict(r) for r in conn.execute(sql, sections).fetchall()]


def upsert_regulatory_events(conn: sqlite3.Connection, rows: list[dict]) -> int:
    """Idempotent on (source, event_id, hs4). Re-pulling refreshes dates/market/detail."""
    sql = """
        INSERT INTO regulatory_events
            (source, event_id, hs4, market, market_name, event_date, deadline, kind, area,
             title, detail, match_kind, source_url, verified_date)
        VALUES
            (:source, :event_id, :hs4, :market, :market_name, :event_date, :deadline, :kind, :area,
             :title, :detail, :match_kind, :source_url, :verified_date)
        ON CONFLICT(source, event_id, hs4) DO UPDATE SET
            market=excluded.market, market_name=excluded.market_name, event_date=excluded.event_date,
            deadline=excluded.deadline, kind=excluded.kind, area=excluded.area, title=excluded.title,
            detail=excluded.detail, match_kind=excluded.match_kind, source_url=excluded.source_url,
            verified_date=excluded.verified_date
    """
    with conn:
        conn.executemany(sql, rows)
    return len(rows)


def fetch_regulatory_event_keys(conn: sqlite3.Connection) -> set:
    """All (source, event_id, hs4) already stored — the 'seen' set for firing change-alerts on new ones."""
    return {(r[0], r[1], r[2])
            for r in conn.execute("SELECT source, event_id, hs4 FROM regulatory_events")}


def fetch_regulatory_events(conn: sqlite3.Connection, hs: str) -> list[dict]:
    """Events for a product, newest first. Matches the whole HS4 FAMILY (the heading + its children),
    so opening coffee '0901' or '090111' both surface the product's changes. Empty = honest 'no changes'."""
    family = (hs or "")[:4]
    sql = ("SELECT * FROM regulatory_events WHERE hs4 LIKE ? "
           "ORDER BY (event_date IS NULL), event_date DESC")
    return [dict(r) for r in conn.execute(sql, (family + "%",)).fetchall()]


def upsert_commodity_prices(conn: sqlite3.Connection, rows: list[dict]) -> int:
    """Idempotent on (source, hs4, period). Re-pulling refreshes the value + verified_date."""
    sql = """
        INSERT INTO commodity_prices (source, hs4, indicator, period, value, verified_date)
        VALUES (:source, :hs4, :indicator, :period, :value, :verified_date)
        ON CONFLICT(source, hs4, period) DO UPDATE SET
            indicator=excluded.indicator, value=excluded.value, verified_date=excluded.verified_date
    """
    with conn:
        conn.executemany(sql, rows)
    return len(rows)


def fetch_commodity_prices(conn: sqlite3.Connection, hs: str) -> list[dict]:
    """Price series for a product, oldest->newest. Matches the exact HS key (the map is per-key, so an
    HS4 heading and its children each carry their own copy). Empty = no honest price series."""
    sql = "SELECT * FROM commodity_prices WHERE hs4 = ? ORDER BY period"
    return [dict(r) for r in conn.execute(sql, (hs,)).fetchall()]


def fetch_flows(conn: sqlite3.Connection, flow: str | None = None,
                hs6: str | None = None) -> list[dict]:
    """All trade_flows rows (optionally one flow direction and/or one product) as plain dicts."""
    sql = "SELECT * FROM trade_flows"
    where, params = [], []
    if flow is not None:
        where.append("flow = ?"); params.append(flow)
    if hs6 is not None:
        where.append("hs6 = ?"); params.append(hs6)
    if where:
        sql += " WHERE " + " AND ".join(where)
    return [dict(r) for r in conn.execute(sql, tuple(params)).fetchall()]


def fetch_signals(conn: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM signals").fetchall()]


def upsert_signals(conn: sqlite3.Connection, rows: list[dict]) -> int:
    """Recompute is a full replace for the cells touched — idempotent on the natural key."""
    sql = """
        INSERT INTO signals
            (reporter, hs6, flow, period, value_usd, base_usd, yoy_delta, band, computed_at)
        VALUES
            (:reporter, :hs6, :flow, :period, :value_usd, :base_usd, :yoy_delta, :band, :computed_at)
        ON CONFLICT(reporter, hs6, flow, period) DO UPDATE SET
            value_usd=excluded.value_usd, base_usd=excluded.base_usd, yoy_delta=excluded.yoy_delta,
            band=excluded.band, computed_at=excluded.computed_at
    """
    with conn:
        conn.executemany(sql, rows)
    return len(rows)


def upsert_tenders(conn: sqlite3.Connection, rows: list[dict]) -> int:
    """Idempotent on (id, hs6) — re-scraping a notice refreshes it, never duplicates."""
    sql = """
        INSERT INTO tenders
            (id, hs6, source, cpv, match_kind, title, buyer, buyer_country, published, deadline, url,
             scraped_at)
        VALUES
            (:id, :hs6, :source, :cpv, :match_kind, :title, :buyer, :buyer_country, :published,
             :deadline, :url, :scraped_at)
        ON CONFLICT(id, hs6) DO UPDATE SET
            match_kind=excluded.match_kind,
            title=excluded.title, buyer=excluded.buyer, buyer_country=excluded.buyer_country,
            published=excluded.published, deadline=excluded.deadline, url=excluded.url,
            scraped_at=excluded.scraped_at
    """
    with conn:
        conn.executemany(sql, rows)
    return len(rows)


def upsert_awards(conn: sqlite3.Connection, rows: list[dict]) -> int:
    """Idempotent on (id, hs6, winner) — one award notice can name several winners."""
    sql = """
        INSERT INTO awards
            (id, hs6, winner, source, cpv, match_kind, title, buyer, buyer_country, winner_country,
             award_date, value, currency, published, url, scraped_at)
        VALUES
            (:id, :hs6, :winner, :source, :cpv, :match_kind, :title, :buyer, :buyer_country,
             :winner_country, :award_date, :value, :currency, :published, :url, :scraped_at)
        ON CONFLICT(id, hs6, winner) DO UPDATE SET
            match_kind=excluded.match_kind, title=excluded.title, buyer=excluded.buyer,
            buyer_country=excluded.buyer_country, winner_country=excluded.winner_country,
            award_date=excluded.award_date, value=excluded.value, currency=excluded.currency,
            published=excluded.published, url=excluded.url, scraped_at=excluded.scraped_at
    """
    with conn:
        conn.executemany(sql, rows)
    return len(rows)


def fetch_awards(conn: sqlite3.Connection, hs6: str) -> list[dict]:
    sql = "SELECT * FROM awards WHERE hs6 = ? ORDER BY (award_date IS NULL), award_date DESC, published DESC"
    return [dict(r) for r in conn.execute(sql, (hs6,)).fetchall()]


def fetch_tenders(conn: sqlite3.Connection, hs6: str) -> list[dict]:
    sql = "SELECT * FROM tenders WHERE hs6 = ? ORDER BY (deadline IS NULL), deadline, published DESC"
    return [dict(r) for r in conn.execute(sql, (hs6,)).fetchall()]
