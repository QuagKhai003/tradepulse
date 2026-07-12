"""
merge.py — collapse multi-source trade rows to ONE number per cell (the overlap/dedupe rule).
@context  Two sources can report the SAME fact (e.g. US-imports-of-coffee-2025 from both Comtrade and
          US Census). We NEVER sum them — we keep exactly one row per cell, chosen deterministically:
          1) a source that is the national AUTHORITY for that reporter wins (each country is the
             authority on its own trade), 2) then the FRESHER row (later published_date), 3) then the
             source PRIORITY rank. A "cell" is (reporter, partner, hs6, period, flow) — grain lives in
             `period`, so monthly/quarterly/annual rows never collide and coexist for the UI toggle.
@done     merge_flows() pure + deterministic; config-driven priority/authority with test overrides.
@limits   PURE: no I/O, no clock. Same rows in -> same winners out.
@affects  Called by pipeline after transform, before upsert. Tested by tests/test_merge.py.
"""
from __future__ import annotations

from . import config


def _cell(row: dict) -> tuple:
    return (row["reporter"], row["partner"], row["hs6"], row["period"], row["flow"])


def _is_authority(source: str, reporter: int, authority: dict[str, set]) -> bool:
    """Is `source` the national customs authority for `reporter`? Comtrade is authority for no one
    (global fallback), so national sources always outrank it for their own country."""
    return reporter in authority.get(source, set())


def _rank(source: str, priority: dict[str, int]) -> int:
    return priority.get(source, config.SOURCE_PRIORITY_DEFAULT)


def _score(row: dict, priority: dict[str, int], authority: dict[str, set]) -> tuple:
    """Higher tuple wins. Authority first, then freshness (ISO dates sort lexicographically, None=''
    is oldest), then lower priority rank (negated so smaller rank scores higher)."""
    return (
        _is_authority(row["source"], row["reporter"], authority),
        row.get("published_date") or "",
        -_rank(row["source"], priority),
    )


def merge_flows(rows: list[dict], *, priority: dict[str, int] | None = None,
                authority: dict[str, set] | None = None) -> list[dict]:
    """One winning row per cell. Order-independent (does not depend on which source loaded first)."""
    priority = config.SOURCE_PRIORITY if priority is None else priority
    authority = config.SOURCE_AUTHORITY if authority is None else authority
    best: dict[tuple, dict] = {}
    for row in rows:
        key = _cell(row)
        cur = best.get(key)
        if cur is None or _score(row, priority, authority) > _score(cur, priority, authority):
            best[key] = row
    return list(best.values())
