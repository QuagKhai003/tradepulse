"""
test_merge.py — the overlap/dedupe rule (docs/DATA_SOURCES §0, merge.py).
@context  Proves two sources reporting the SAME cell collapse to ONE number, chosen deterministically
          (national authority > freshness > priority), never summed, and order-independent. Different
          grains (annual vs monthly) coexist. No network, no clock.
"""
import unittest

from tradepulse_etl.config import freq_of
from tradepulse_etl.merge import merge_flows


def cell(source, reporter=842, partner=0, hs6="090111", period="2025", flow="M",
         value=100.0, pub=None):
    return {"reporter": reporter, "partner": partner, "hs6": hs6, "period": period, "flow": flow,
            "value_usd": value, "source": source, "published_date": pub}


class MergeTest(unittest.TestCase):
    def test_authority_beats_comtrade_for_its_own_country(self):
        # US coffee 2025 from BOTH Comtrade and US Census -> Census (authority for 842) wins.
        rows = [cell("comtrade", value=90.0), cell("census", value=100.0, pub="2025-12")]
        out = merge_flows(rows)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["source"], "census")
        self.assertEqual(out[0]["value_usd"], 100.0)      # the winner's number, NOT the sum (190)

    def test_order_independent(self):
        a = [cell("comtrade", value=90.0), cell("census", value=100.0, pub="2025-12")]
        b = [cell("census", value=100.0, pub="2025-12"), cell("comtrade", value=90.0)]
        self.assertEqual(merge_flows(a)[0]["source"], merge_flows(b)[0]["source"])

    def test_comtrade_wins_where_no_authority(self):
        # Japan (392): Census isn't authoritative, Comtrade is the only real source -> Comtrade.
        rows = [cell("comtrade", reporter=392, value=50.0), cell("fixture", reporter=392, value=1.0)]
        out = merge_flows(rows)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["source"], "comtrade")

    def test_freshness_breaks_ties_between_peers(self):
        # Two peer sources, neither authoritative here: fresher published_date wins.
        pr = {"a": 10, "b": 10}
        auth: dict = {}
        rows = [cell("a", reporter=392, value=1.0, pub="2025-06"),
                cell("b", reporter=392, value=2.0, pub="2026-03")]
        out = merge_flows(rows, priority=pr, authority=auth)
        self.assertEqual(out[0]["source"], "b")

    def test_different_grain_coexists(self):
        # Annual and monthly for the same country/product/flow are different cells -> both kept.
        rows = [cell("census", period="2025", value=100.0),
                cell("census", period="202601", value=9.0)]
        out = merge_flows(rows)
        self.assertEqual(len(out), 2)

    def test_freq_of(self):
        self.assertEqual(freq_of("2025"), "A")
        self.assertEqual(freq_of("2025-Q1"), "Q")
        self.assertEqual(freq_of("202603"), "M")


if __name__ == "__main__":
    unittest.main()
