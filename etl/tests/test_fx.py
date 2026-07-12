"""
test_fx.py — currency conversion for non-USD national sources (fx.py). Pure, offline.
@context  EUR/GBP national values must become USD before the merge. Proves USD passthrough, EUR and
          GBP (cross-rate) conversion, period mapping, and the drop-on-missing-rate rule.
"""
import unittest

from tradepulse_etl.fx import ecb_period, to_usd

USD_PER_EUR = {"2025": 1.08, "2025-Q1": 1.05, "2025-03": 1.0807}
GBP_PER_EUR = {"2025": 0.85, "2025-Q1": 0.84, "2025-03": 0.836}


class FxTest(unittest.TestCase):
    def test_usd_passthrough(self):
        self.assertEqual(to_usd(100.0, "USD", "2025", USD_PER_EUR, GBP_PER_EUR), 100.0)
        self.assertEqual(to_usd(100.0, None, "2025", USD_PER_EUR, GBP_PER_EUR), 100.0)

    def test_eur_to_usd(self):
        self.assertAlmostEqual(to_usd(100.0, "EUR", "2025", USD_PER_EUR, GBP_PER_EUR), 108.0)

    def test_gbp_to_usd_cross(self):
        # 100 GBP * (1.08 USD/EUR) / (0.85 GBP/EUR) = 127.06 USD
        self.assertAlmostEqual(to_usd(100.0, "GBP", "2025", USD_PER_EUR, GBP_PER_EUR), 100.0 * 1.08 / 0.85)

    def test_period_mapping(self):
        self.assertEqual(ecb_period("2025"), "2025")
        self.assertEqual(ecb_period("2025-Q1"), "2025-Q1")
        self.assertEqual(ecb_period("202503"), "2025-03")
        # monthly value uses the monthly rate
        self.assertAlmostEqual(to_usd(10.0, "EUR", "202503", USD_PER_EUR, GBP_PER_EUR), 10.0 * 1.0807)

    def test_missing_rate_drops(self):
        self.assertIsNone(to_usd(100.0, "EUR", "1999", USD_PER_EUR, GBP_PER_EUR))
        self.assertIsNone(to_usd(100.0, "GBP", "2025", USD_PER_EUR, {}))  # no GBP rate


if __name__ == "__main__":
    unittest.main()
