"""
test_imf_pcps.py — IMF PCPS price parse (sources/imf_pcps.py) + the forward lane. Pure, offline.
@context  The FORWARD lane (ADR-0007): a world price trend, a SEPARATE lane never merged into customs
          value. These pin the SDMX parse (world/monthly/USD only), the period normalisation, and the
          YoY + direction math in build_forward — plus the honest empty (no series -> no line).
@limits   Offline; no network (_series parses a fixture; build_forward uses an in-mem DB).
@affects  tradepulse_etl/sources/imf_pcps.py + db.commodity_prices + export.build_forward
"""
import unittest

from tradepulse_etl.db import connect, upsert_commodity_prices
from tradepulse_etl.export import build_forward
from tradepulse_etl.sources.imf_pcps import ImfPcpsSource, _period

# Minimal structure-specific SDMX: one world/monthly/USD coffee series + one NON-world series that must
# be ignored, so the filter (COUNTRY G001, FREQUENCY M, DATA_TRANSFORMATION USD) is actually exercised.
SDMX = """<?xml version='1.0'?>
<message:StructureSpecificData xmlns:message="urn:m">
 <message:DataSet>
  <Series COUNTRY="G001" INDICATOR="PCOFFROB" DATA_TRANSFORMATION="USD" FREQUENCY="M" SCALE="0">
    <Obs TIME_PERIOD="2025-M06" OBS_VALUE="196.3"/>
    <Obs TIME_PERIOD="2026-M06" OBS_VALUE="169.4"/>
  </Series>
  <Series COUNTRY="G001" INDICATOR="PCOFFROB" DATA_TRANSFORMATION="INDEX" FREQUENCY="M" SCALE="0">
    <Obs TIME_PERIOD="2026-M06" OBS_VALUE="99.9"/>
  </Series>
  <Series COUNTRY="US" INDICATOR="PCOFFROB" DATA_TRANSFORMATION="USD" FREQUENCY="M" SCALE="0">
    <Obs TIME_PERIOD="2026-M06" OBS_VALUE="999.0"/>
  </Series>
 </message:DataSet>
</message:StructureSpecificData>"""


class ParseTest(unittest.TestCase):
    def test_period_normalises(self):
        self.assertEqual(_period("2026-M06"), "2026-06")

    def test_keeps_only_world_monthly_usd(self):
        src = ImfPcpsSource()
        src._get = lambda url: SDMX.encode("utf-8")     # stub the network
        got = src._series("x")
        self.assertEqual(set(got), {"PCOFFROB"})        # INDEX + non-world dropped
        self.assertEqual(got["PCOFFROB"], {"2025-06": 196.3, "2026-06": 169.4})   # USD only, not 99.9/999


class BuildForwardTest(unittest.TestCase):
    def _prices(self, hs, pairs, ind="PCOFFROB"):
        return [{"source": "imf-pcps", "hs4": hs, "indicator": ind, "period": p, "value": v,
                 "verified_date": "2026-07-15"} for p, v in pairs]

    def test_yoy_and_direction_down(self):
        conn = connect(":memory:")
        upsert_commodity_prices(conn, self._prices("090111", [("2025-06", 196.3), ("2026-06", 169.4)]))
        f = build_forward(conn, "090111")
        self.assertEqual(f["latest_period"], "2026-06")
        self.assertEqual(f["latest_value"], 169.4)
        self.assertEqual(f["yoy_pct"], -13.7)           # (169.4-196.3)/196.3*100
        self.assertEqual(f["direction"], "down")
        self.assertEqual(f["label_en"], "Coffee (robusta)")

    def test_flat_band_within_two_percent(self):
        conn = connect(":memory:")
        upsert_commodity_prices(conn, self._prices("4407", [("2025-06", 100.0), ("2026-06", 101.0)], "PSAWMAL"))
        self.assertEqual(build_forward(conn, "4407")["direction"], "flat")   # +1% -> flat

    def test_yoy_none_when_no_year_ago_point(self):
        conn = connect(":memory:")
        upsert_commodity_prices(conn, self._prices("090111", [("2026-05", 170.0), ("2026-06", 169.4)]))
        f = build_forward(conn, "090111")
        self.assertIsNone(f["yoy_pct"])                 # never interpolate a price we can't stand behind
        self.assertIsNone(f["direction"])

    def test_no_series_is_none(self):                    # wood pellets: no honest price -> no line
        self.assertIsNone(build_forward(connect(":memory:"), "440131"))


if __name__ == "__main__":
    unittest.main()
