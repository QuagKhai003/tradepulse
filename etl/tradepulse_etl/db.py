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
