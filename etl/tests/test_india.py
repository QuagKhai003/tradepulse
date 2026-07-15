"""
test_india.py — India DGCI&S TRADESTAT parse (sources/india.py). Pure, offline.
@context  A fragile national source (HTML + CSRF) that refreshes India's own cell (reporter 699). These
          pin the table parse (serial-then-HS4 columns, US$M -> USD), pilot scope, the emitted row shape,
          and the incremental skip — the network (_table) is stubbed.
@limits   Offline. A failed fetch -> no rows (never a wrong number).
@affects  tradepulse_etl/sources/india.py + pipeline.get_source('india')
"""
import unittest

from tradepulse_etl.sources.india import IndiaSource
from tradepulse_etl.transform import transform_all

# A cut of the real table: a leading serial column, HS4 in column 2, current-year US$M in column 6.
TABLE = """
<table>
<tr><td>1</td><td>0901</td><td>COFFEE</td><td>823.42</td><td>0.19</td><td>1,244.28</td><td>0.28</td></tr>
<tr><td>2</td><td>1006</td><td>RICE</td><td>10,416.71</td><td>2.38</td><td>12,472.47</td><td>2.85</td></tr>
<tr><td>3</td><td>8458</td><td>LATHES</td><td>51.68</td><td>0.01</td><td>47.20</td><td>0.01</td></tr>
</table>
"""


class ParseTest(unittest.TestCase):
    def test_hs_in_second_column_and_usd_millions(self):
        t = IndiaSource._parse(TABLE)
        self.assertEqual(t["0901"], 1_244_280_000.0)        # 1,244.28 US$M -> USD
        self.assertEqual(t["1006"], 12_472_470_000.0)
        self.assertIn("8458", t)                            # every HS row parses (scope filter is later)


class PullTest(unittest.TestCase):
    def _src(self):
        s = IndiaSource()
        s._tables = {"X": {"0901": 1_244_280_000.0, "1006": 12_472_470_000.0, "8458": 47_200_000.0},
                     "M": {"0901": 50_000_000.0}}
        return s

    def test_emits_india_rows_for_pilots_only(self):
        rows = self._src().pull(["0901", "1006", "8458"], [], None)
        hs = sorted({r["cmdCode"] for r in rows})
        self.assertEqual(hs, ["0901", "1006"])              # 8458 (lathes) is not a pilot -> dropped
        r = next(x for x in rows if x["cmdCode"] == "1006" and x["flowCode"] == "X")
        self.assertEqual(r["reporterCode"], 699)
        self.assertEqual(r["partnerCode"], 0)
        self.assertEqual(r["primaryValue"], 12_472_470_000.0)
        self.assertEqual(transform_all([r], "india")[0]["reporter"], 699)

    def test_skip_incremental(self):
        rows = self._src().pull(["0901"], [], None, skip={("0901", "2024")})
        self.assertEqual([r["flowCode"] for r in rows], [])  # both flows for 0901/2024 already stored


if __name__ == "__main__":
    unittest.main()
