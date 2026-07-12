"""
test_eurostat.py — EU Comext JSON-stat parse + EUR->USD (sources/eurostat.py). Pure, offline.
@context  Proves _parse turns a JSON-stat response into Comtrade-shaped USD rows for the EU (reporter
          97, World partner), converting EUR via the FX rate, one row per wanted period.
"""
import unittest

from tradepulse_etl.sources.eurostat import EurostatSource

# Two-period JSON-stat (as Eurostat returns): time index maps to positions in `value`.
DATA = {
    "value": {"0": 10_000_000_000, "1": 11_859_180_813},
    "dimension": {"time": {"category": {"index": {"2023": 0, "2024": 1}}}},
}
USD_PER_EUR = {"2023": 1.05, "2024": 1.0824}


class EurostatTest(unittest.TestCase):
    def test_parse_eur_to_usd(self):
        out = EurostatSource._parse(DATA, "090111", "M", USD_PER_EUR, {"2023", "2024"})
        self.assertEqual(len(out), 2)
        r24 = next(r for r in out if r["period"] == "2024")
        self.assertEqual(r24["reporterCode"], 97)          # EU
        self.assertEqual(r24["partnerCode"], 0)            # World (extra-EU)
        self.assertEqual(r24["flowCode"], "M")
        self.assertAlmostEqual(r24["primaryValue"], round(11_859_180_813 * 1.0824, 2))  # EUR->USD
        self.assertEqual(r24["publishedDate"], "2024-12")

    def test_wanted_filters_periods(self):
        out = EurostatSource._parse(DATA, "090111", "M", USD_PER_EUR, {"2024"})
        self.assertEqual([r["period"] for r in out], ["2024"])

    def test_missing_rate_drops_row(self):
        out = EurostatSource._parse(DATA, "090111", "M", {"2024": 1.08}, {"2023", "2024"})
        self.assertEqual([r["period"] for r in out], ["2024"])   # 2023 has no rate -> dropped

    def test_empty(self):
        self.assertEqual(EurostatSource._parse(None, "090111", "M", USD_PER_EUR, {"2024"}), [])


if __name__ == "__main__":
    unittest.main()
