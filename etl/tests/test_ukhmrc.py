"""
test_ukhmrc.py — HMRC OTS aggregation + GBP->USD (sources/ukhmrc.py). Pure, offline.
@context  Proves _aggregate sums the EU/Non-EU flow split correctly (imports=1+3, exports=2+4) into
          one UK World row per flow, converting GBP to USD via the FX rate.
"""
import unittest

from tradepulse_etl.sources.ukhmrc import UKHmrcSource

# HMRC OTS month rows (FlowTypeId, Value in GBP): 1=EU imp,2=EU exp,3=Non-EU imp,4=Non-EU exp.
ROWS = [
    {"FlowTypeId": 1, "Value": 3_000_000}, {"FlowTypeId": 3, "Value": 37_000_000},   # imports = 40M
    {"FlowTypeId": 2, "Value": 9_000_000}, {"FlowTypeId": 4, "Value": 1_000_000},     # exports = 10M
]
USD, GBP = {"2024": 1.28}, {"2024": 1.0}   # 1 EUR = 1.28 USD = 1.00 GBP -> GBP->USD = 1.28


class HmrcTest(unittest.TestCase):
    def test_flow_split_and_fx(self):
        out = UKHmrcSource._aggregate(ROWS, "090111", "2024", USD, GBP)
        by = {r["flowCode"]: r for r in out}
        self.assertEqual(by["M"]["reporterCode"], 826)          # UK
        self.assertEqual(by["M"]["partnerCode"], 0)             # World
        self.assertAlmostEqual(by["M"]["primaryValue"], 40_000_000 * 1.28)   # imports GBP->USD
        self.assertAlmostEqual(by["X"]["primaryValue"], 10_000_000 * 1.28)   # exports GBP->USD
        self.assertEqual(by["M"]["period"], "2024")

    def test_zero_flow_dropped(self):
        out = UKHmrcSource._aggregate([{"FlowTypeId": 1, "Value": 5_000_000}], "090111", "2024", USD, GBP)
        self.assertEqual([r["flowCode"] for r in out], ["M"])   # no exports -> only the import row

    def test_missing_rate_drops(self):
        self.assertEqual(UKHmrcSource._aggregate(ROWS, "090111", "1999", USD, GBP), [])


if __name__ == "__main__":
    unittest.main()
