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
    cols = {r[1] for r in conn.execute("PRAGMA table_info(trade_flows)")}
    if "freq" not in cols:
        conn.execute("ALTER TABLE trade_flows ADD COLUMN freq TEXT")
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


def fetch_flows(conn: sqlite3.Connection, flow: str | None = None) -> list[dict]:
    """All trade_flows rows (optionally one flow direction) as plain dicts."""
    sql = "SELECT * FROM trade_flows"
    params: tuple = ()
    if flow is not None:
        sql += " WHERE flow = ?"
        params = (flow,)
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


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
