"""
test_census.py — US Census aggregation (sources/census.py). Pure, offline (no network).
@context  The Census query is UNGROUPED (no CTY_CODE) so the response is the single all-country total
          — proves _aggregate parses it into ONE World raw row per (hs, year, flow), Comtrade-shaped.
          (Grouping by CTY_CODE would mix in overlapping region aggregates → triple-count; see census.py.)
"""
import unittest

from tradepulse_etl.sources.census import USCensusSource

# Census ungrouped response: header, then the all-country total row.
TABLE = [["ALL_VAL_YR"], ["6190000000"]]


class CensusTest(unittest.TestCase):
    def test_world_total(self):
        out = USCensusSource._aggregate(TABLE, "090111", 2025, "X", "ALL_VAL_YR")
        self.assertEqual(len(out), 1)
        row = out[0]
        self.assertEqual(row["reporterCode"], 842)
        self.assertEqual(row["partnerCode"], 0)               # World
        self.assertEqual(row["cmdCode"], "090111")
        self.assertEqual(row["period"], "2025")
        self.assertEqual(row["flowCode"], "X")
        self.assertEqual(row["primaryValue"], 6_190_000_000.0)
        self.assertEqual(row["publishedDate"], "2025-12")

    def test_empty_or_headeronly_yields_nothing(self):
        self.assertEqual(USCensusSource._aggregate([], "090111", 2025, "X", "ALL_VAL_YR"), [])
        self.assertEqual(USCensusSource._aggregate([["ALL_VAL_YR"]], "090111", 2025, "X", "ALL_VAL_YR"), [])

    def test_zero_total_dropped(self):
        table = [["GEN_VAL_YR"], ["0"]]
        self.assertEqual(USCensusSource._aggregate(table, "440131", 2024, "M", "GEN_VAL_YR"), [])


if __name__ == "__main__":
    unittest.main()


class CensusQuarterlyTest(unittest.TestCase):
    """Monthly US values -> complete-quarter rows (fresh, independent of Comtrade)."""

    def test_complete_quarter_sums_three_months(self):
        mv = {("0901", "M", "202601"): 1.0, ("0901", "M", "202602"): 2.0, ("0901", "M", "202603"): 3.0}
        out = USCensusSource._to_quarters(mv)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["period"], "2026-Q1")
        self.assertEqual(out[0]["primaryValue"], 6.0)
        self.assertEqual(out[0]["reporterCode"], 842)

    def test_incomplete_quarter_is_dropped(self):
        mv = {("0901", "M", "202601"): 1.0, ("0901", "M", "202602"): 2.0}   # only 2 of 3 months
        self.assertEqual(USCensusSource._to_quarters(mv), [])

    def test_month_value_sums_the_value_column(self):
        table = [["GEN_VAL_MO", "MONTH"], ["100", "01"], ["50", "01"]]
        self.assertEqual(USCensusSource._month_value(table, "GEN_VAL_MO"), 150.0)
