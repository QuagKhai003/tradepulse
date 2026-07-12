"""
test_incremental.py — only re-fetch the revisable window (config.is_final + pipeline skip). Offline.
@context  Production must not re-pull frozen history every run. Proves old periods are 'final' (skipped)
          while recent ones are re-fetched, and that run_multi passes the right skip set to sources.
"""
import tempfile
import unittest
from datetime import date
from pathlib import Path

from tradepulse_etl.config import is_final
from tradepulse_etl.db import connect, upsert_trade_flows
from tradepulse_etl.pipeline import run_multi

TODAY = date(2026, 7, 1)


def row(hs, period, freq, flow="M", value=100.0):
    return {"reporter": 842, "partner": 0, "hs6": hs, "period": period, "freq": freq, "flow": flow,
            "value_usd": value, "quantity": None, "qty_unit": None, "source": "comtrade", "published_date": None}


class Recording:
    """A source that records the skip set it was handed and fetches nothing."""
    name = "rec"

    def __init__(self):
        self.skip = None

    def pull(self, hs_codes, reporters, partners, skip=frozenset()):
        self.skip = skip
        return []


class IsFinalTest(unittest.TestCase):
    def test_annual(self):
        self.assertTrue(is_final("2021", TODAY))          # >2y old -> frozen
        self.assertTrue(is_final("2023", TODAY))
        self.assertFalse(is_final("2025", TODAY))         # within revision window -> re-fetch
        self.assertFalse(is_final("2024", TODAY))

    def test_quarterly(self):
        self.assertTrue(is_final("2025-Q1", TODAY))       # 16 months old
        self.assertFalse(is_final("2026-Q1", TODAY))      # recent

    def test_monthly(self):
        self.assertTrue(is_final("202512", TODAY))        # 7 months old
        self.assertFalse(is_final("202602", TODAY))       # recent


class PipelineSkipTest(unittest.TestCase):
    def test_pipeline_skips_only_final_stored(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        conn = connect(Path(tmp.name) / "t.sqlite")
        self.addCleanup(conn.close)
        # already stored: an old final year + a recent quarter for the same product
        upsert_trade_flows(conn, [row("090111", "2021", "A"), row("090111", "2026-Q1", "Q")])

        rec = Recording()
        run_multi([rec], conn, raw_dir=Path(tmp.name) / "raw", today=TODAY)

        self.assertIn(("090111", "2021"), rec.skip)        # frozen -> skipped
        self.assertNotIn(("090111", "2026-Q1"), rec.skip)  # revisable -> re-fetched


if __name__ == "__main__":
    unittest.main()
