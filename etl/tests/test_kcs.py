"""
test_kcs.py — Korea Customs Service source: parsing + aggregation are pure + tested.
@context  Korea national primary (reporter 410), monthly, fresh to ~last month. Values are USD.
@limits   Offline; no network (aggregation is static).
@affects  tradepulse_etl/sources/kcs.py
"""
import unittest
import xml.etree.ElementTree as ET

from tradepulse_etl.sources.kcs import KcsSource

# a minimal KCS response: a grand-total row (year=총계, hsCd=-) that must be SKIPPED, plus two real
# per-country months of the same HS6 child that must SUM into Korea's World total.
XML = """<response><body><items>
  <item><year>총계</year><hsCd>-</hsCd><expDlr>9</expDlr><impDlr>99</impDlr></item>
  <item><year>2026.01</year><hsCd>090111</hsCd><statCd>US</statCd><expDlr>10</expDlr><impDlr>100</impDlr></item>
  <item><year>2026.01</year><hsCd>090111</hsCd><statCd>BR</statCd><expDlr>5</expDlr><impDlr>50</impDlr></item>
</items></body></response>"""


class ParseTest(unittest.TestCase):
    def test_skips_grand_total_and_sums_partners(self):
        src = KcsSource(key="k")
        src._get = lambda url: XML                       # stub the network
        mv = src._pull_hs("0901", "202601", "202601")
        self.assertEqual(mv[("M", "202601")], 150.0)     # 100 + 50, the 총계 row (99) excluded
        self.assertEqual(mv[("X", "202601")], 15.0)      # 10 + 5


class AggregateTest(unittest.TestCase):
    def test_complete_quarter_and_year(self):
        mv = {("M", f"2025{m:02d}"): 1.0 for m in range(1, 13)}   # all 12 months
        out = KcsSource._aggregate("0901", mv, ("A", "Q"))
        by = {(r["period"], r["flowCode"]): r["primaryValue"] for r in out}
        self.assertEqual(by[("2025-Q1", "M")], 3.0)              # 3 months summed
        self.assertEqual(by[("2025", "M")], 12.0)               # full year
        self.assertTrue(all(r["reporterCode"] == 410 for r in out))

    def test_incomplete_quarter_and_year_dropped(self):
        mv = {("M", "202601"): 1.0, ("M", "202602"): 1.0}       # 2 months only
        out = KcsSource._aggregate("0901", mv, ("A", "Q"))
        self.assertEqual(out, [])                                # no complete quarter or year


class WindowTest(unittest.TestCase):
    def test_windows_are_within_12_months(self):
        src = KcsSource(key="k", years=2)
        for start, end in src._windows():
            self.assertEqual(start[4:], "01")                   # each window starts in January
            self.assertLessEqual(int(end[4:]), 12)              # ...and ends within the same year


if __name__ == "__main__":
    unittest.main()
