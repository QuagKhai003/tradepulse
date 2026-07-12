"""
test_baci.py — BACI bulk parse/aggregate (sources/baci.py). Pure, offline (tiny temp CSV).
@context  Proves a BACI year file becomes World totals per (reporter, HS, flow): value x1000 (thousand
          USD -> USD), imports keyed by importer j, exports by exporter i, HS4 = sum of its HS6, codes
          used as-is (BACI already uses Comtrade M49). Incremental skip honoured.
"""
import tempfile
import unittest
from pathlib import Path

from tradepulse_etl.sources.baci import BaciSource

# BACI columns: t,i,j,k,v,q  (v = thousand USD)
CSV = """t,i,j,k,v,q
2023,704,842,090111,5000,100
2023,251,842,090111,2000,40
2023,704,826,090121,1000,20
"""   # US imports 090111 from VN(5000)+FR(2000)=7000k; UK imports 090121 from VN 1000k


class BaciTest(unittest.TestCase):
    def _write(self):
        d = tempfile.mkdtemp()
        p = Path(d) / "BACI_HS22_Y2023_V202501.csv"
        p.write_text(CSV, encoding="utf-8")
        return p

    def test_world_totals_and_units(self):
        rows = BaciSource._parse_year(self._write(), "2023", {"090111", "090121"}, set(), frozenset())
        us_imp = [r for r in rows if r["reporterCode"] == 842 and r["cmdCode"] == "090111" and r["flowCode"] == "M"]
        self.assertEqual(len(us_imp), 1)
        self.assertEqual(us_imp[0]["primaryValue"], 7_000_000.0)     # (5000+2000) x1000
        self.assertEqual(us_imp[0]["partnerCode"], 0)               # World
        # VN(704) is an exporter of 090111 here
        vn_exp = [r for r in rows if r["reporterCode"] == 704 and r["cmdCode"] == "090111" and r["flowCode"] == "X"]
        self.assertEqual(vn_exp[0]["primaryValue"], 5_000_000.0)

    def test_hs4_aggregates_hs6(self):
        # HS4 '0901' should sum 090111 + 090121 for the US import side
        rows = BaciSource._parse_year(self._write(), "2023", set(), {"0901"}, frozenset())
        us_imp4 = [r for r in rows if r["reporterCode"] == 842 and r["cmdCode"] == "0901" and r["flowCode"] == "M"]
        self.assertEqual(us_imp4[0]["primaryValue"], 7_000_000.0)   # only 090111 imported by US (090121->UK)

    def test_skip_final_year(self):
        rows = BaciSource._parse_year(self._write(), "2023", {"090111"}, set(), frozenset({("090111", "2023")}))
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
