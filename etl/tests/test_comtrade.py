"""
test_comtrade.py — offline test for the live-source helpers (no network).
@context  Regression for the real-data double-count bug: Comtrade returns the World total broken
          out by transport mode + 2nd partner; only the fully-aggregated row is the true total.
@affects  Covers comtrade._is_world_total + ComtradeSource._normalise + prev_year_period (annual).
"""
import unittest

from tradepulse_etl.signals import prev_year_period
from tradepulse_etl.sources.comtrade import ComtradeSource, _is_total_row, _is_world_total


class WorldTotalFilterTest(unittest.TestCase):
    def test_only_canonical_total_kept(self):
        rows = [
            {"partnerCode": 0, "partner2Code": 0, "motCode": "0", "customsCode": "C00", "primaryValue": 100},  # keep
            {"partnerCode": 0, "partner2Code": 0, "motCode": "2100", "customsCode": "C00", "primaryValue": 60},  # drop (mode split)
            {"partnerCode": 0, "partner2Code": 792, "motCode": "0", "customsCode": "C00", "primaryValue": 40},   # drop (2nd partner)
            {"partnerCode": 704, "partner2Code": 0, "motCode": "0", "customsCode": "C00", "primaryValue": 55},   # drop (not World)
        ]
        kept = [r for r in rows if _is_world_total(r)]
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["primaryValue"], 100)

    def test_missing_keys_default_to_total(self):
        # A response without the breakdown keys is itself the total.
        self.assertTrue(_is_world_total({"partnerCode": 0, "primaryValue": 10}))

    def test_partner_total_filter_keeps_canonical_per_partner(self):
        # Authenticated path keeps each partner's canonical total (Vietnam here), drops splits.
        rows = [
            {"partnerCode": 704, "partner2Code": 0, "motCode": "0", "customsCode": "C00", "primaryValue": 90},  # keep
            {"partnerCode": 704, "partner2Code": 0, "motCode": "2100", "customsCode": "C00", "primaryValue": 50},  # drop
            {"partnerCode": 704, "partner2Code": 792, "motCode": "0", "customsCode": "C00", "primaryValue": 40},   # drop
        ]
        kept = [r for r in rows if _is_total_row(r)]
        self.assertEqual([r["primaryValue"] for r in kept], [90])

    def test_to_quarters_aggregates_complete_quarters_only(self):
        # 3 months -> one quarter; a lone month -> dropped (incomplete).
        rows = [
            {"reporterCode": 392, "partnerCode": 0, "cmdCode": "440131", "period": "202401", "primaryValue": 10, "netWgt": 1},
            {"reporterCode": 392, "partnerCode": 0, "cmdCode": "440131", "period": "202402", "primaryValue": 20, "netWgt": 2},
            {"reporterCode": 392, "partnerCode": 0, "cmdCode": "440131", "period": "202403", "primaryValue": 30, "netWgt": 3},
            {"reporterCode": 392, "partnerCode": 0, "cmdCode": "440131", "period": "202404", "primaryValue": 99, "netWgt": 9},
        ]
        out = ComtradeSource._to_quarters(rows)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["period"], "2024-Q1")
        self.assertEqual(out[0]["primaryValue"], 60)


class NormaliseTest(unittest.TestCase):
    def test_sums_duplicates_into_annual_record(self):
        raw = [
            {"reporterCode": 392, "partnerCode": 0, "cmdCode": "440131", "period": 2024, "primaryValue": 100, "netWgt": 5},
            {"reporterCode": 392, "partnerCode": 0, "cmdCode": "440131", "period": 2024, "primaryValue": 50, "netWgt": 2},
        ]
        out = ComtradeSource._normalise_annual(raw)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["primaryValue"], 150)
        self.assertEqual(out[0]["period"], "2024")
        self.assertEqual(out[0]["flowCode"], "M")

    def test_recent_years_shape(self):
        yrs = ComtradeSource._recent_years(6)
        self.assertEqual(len(yrs), 6)
        self.assertEqual(yrs[-1], yrs[0] + 5)


class AnnualPeriodTest(unittest.TestCase):
    def test_prev_year_annual_and_quarterly(self):
        self.assertEqual(prev_year_period("2024"), "2023")
        self.assertEqual(prev_year_period("2026-Q1"), "2025-Q1")


if __name__ == "__main__":
    unittest.main()
