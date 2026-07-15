"""
test_thaimoc.py — Thailand MOC national primary parse (sources/thaimoc.py). Pure, offline.
@context  A fresh national source that refreshes Thailand's own cell (reporter 764). These pin the
          partner-sum -> World total, the COMPLETE-quarter rule (a partial quarter is dropped, never
          shown understated), the pilot-only scope, and the emitted trade-flow row shape.
@limits   Offline; _get is stubbed. Deterministic given a clock passed to pull().
@affects  tradepulse_etl/sources/thaimoc.py + pipeline.get_source('thai')
"""
import unittest
from datetime import date

from tradepulse_etl.sources.thaimoc import ThaiMocSource
from tradepulse_etl.transform import transform_all


class QuarterTest(unittest.TestCase):
    def test_complete_quarter_summed_partial_dropped(self):
        monthly = {"2026-01": 10.0, "2026-02": 20.0, "2026-03": 30.0,   # Q1 complete -> 60
                   "2026-04": 5.0, "2026-05": 5.0}                       # Q2 partial (2 mo) -> dropped
        q = ThaiMocSource._to_quarters(monthly)
        self.assertEqual(q, {"2026-Q1": 60.0})

    def test_window_is_oldest_first_and_right_length(self):
        w = ThaiMocSource(months=4)._window(date(2026, 2, 15))
        self.assertEqual(w, [(2025, 11), (2025, 12), (2026, 1), (2026, 2)])


class PullTest(unittest.TestCase):
    def _src(self):
        s = ThaiMocSource(months=3)
        # Stub the network: two partners per (import) month so the World total = the sum. Only Jan-Mar
        # 2026 return data (a complete Q1); other months empty.
        def fake_get(endpoint, year, month, hs):
            if year == 2026 and month in (1, 2, 3) and endpoint.startswith("import"):
                return [{"country_code": "VN", "value_usd": "100"},
                        {"country_code": "CN", "value_usd": "50"}]
            return []
        s._get = fake_get
        return s

    def test_emits_world_total_row_for_thailand(self):
        rows = self._src().pull(["0901"], [], None, today=date(2026, 3, 20))
        imp = [r for r in rows if r["flowCode"] == "M"]
        self.assertEqual(len(imp), 1)
        r = imp[0]
        self.assertEqual(r["reporterCode"], 764)          # Thailand
        self.assertEqual(r["partnerCode"], 0)             # summed to World
        self.assertEqual(r["period"], "2026-Q1")
        self.assertEqual(r["primaryValue"], 450.0)        # (100+50) * 3 months
        # and it transforms into a valid trade_flow row
        tf = transform_all([r], "thaimoc")[0]
        self.assertEqual(tf["reporter"], 764)
        self.assertEqual(tf["freq"], "Q")

    def test_scope_is_pilots_only(self):
        self.assertEqual(self._src().pull(["8703"], [], None, today=date(2026, 3, 20)), [])  # cars: not a pilot

    def test_skip_incremental(self):
        rows = self._src().pull(["0901"], [], None, skip={("0901", "2026-Q1")}, today=date(2026, 3, 20))
        self.assertEqual(rows, [])                         # already stored -> not re-emitted


if __name__ == "__main__":
    unittest.main()
