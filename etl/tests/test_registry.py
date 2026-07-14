"""
test_registry.py — real sellers from approval registries (DG SANTE). Parsing is pure + tested.
@context  A seller = a company APPROVED to export a product, not a contract winner (ADR-0006). These
          tests pin the row shape and, above all, the Golden Rule: organisation + approval only, never
          a contact person.
@limits   Offline; no network (DgSanteSource._row is static/pure).
@affects  tradepulse_etl/sources/registry.py + export.build_sellers_web
"""
import json
import unittest

from tradepulse_etl.db import connect, upsert_registry_sellers
from tradepulse_etl.export import _sections_for, build_sellers_web
from tradepulse_etl.sources.registry import DgSanteSource

EST = {
    "operatorName": "TASIFISH JSC",
    "approvalNumber": "TS 1278",
    "confidential": False,
    "operatorActivityTypes": [{"translation": "Processing Plant"}],
    "address": {"cityReference": {"name": "Vĩnh Long",
                "country": {"code": "VN", "iso31661NumericCode": "704"}}},
}


class RowTest(unittest.TestCase):
    def test_names_org_approval_activity_city_m49(self):
        r = DgSanteSource._row(EST, "VN", "FFP", "2026-07-14")
        self.assertEqual(r["seller"], "TASIFISH JSC")
        self.assertEqual(r["approval_no"], "TS 1278")
        self.assertEqual(r["activity"], "Processing Plant")
        self.assertEqual(r["city"], "Vĩnh Long")
        self.assertEqual(r["seller_code"], 704)          # M49 for the country join
        self.assertEqual(r["seller_iso"], "VN")
        self.assertIn("VN/FFP", r["source_url"])         # citable source
        self.assertEqual(r["verified_date"], "2026-07-14")

    def test_confidential_record_is_dropped(self):
        self.assertIsNone(DgSanteSource._row({**EST, "confidential": True}, "VN", "FFP", "d"))

    def test_no_name_dropped(self):
        self.assertIsNone(DgSanteSource._row({"approvalNumber": "X"}, "VN", "FFP", "d"))

    def test_never_carries_a_contact(self):              # Golden Rule
        noisy = {**EST, "email": "a@b.c", "phone": "+84 1", "contactPerson": "Jane Doe"}
        r = DgSanteSource._row(noisy, "VN", "FFP", "d")
        blob = json.dumps(r)
        self.assertNotIn("a@b.c", blob)
        self.assertNotIn("Jane Doe", blob)
        self.assertNotIn("+84", blob)


class SectionMappingTest(unittest.TestCase):
    def test_shrimp_is_a_fishery_product(self):
        self.assertIn("FFP", _sections_for("0306"))
        self.assertIn("FFP", _sections_for("030617"))

    def test_coffee_has_no_registry_section(self):       # honest empty until a Phase-2 source covers it
        self.assertEqual(_sections_for("0901"), [])


class BuildSellersWebTest(unittest.TestCase):
    def test_dedupes_by_org_and_country_across_sections(self):
        conn = connect(":memory:")
        rows = [
            {"source": "dgsante", "approval_no": "TS 1", "seller": "ACME", "seller_iso": "VN",
             "seller_code": 704, "activity": "Processing Plant", "city": "HCMC", "section": "FFP",
             "source_url": "u", "verified_date": "d"},
            {"source": "dgsante", "approval_no": "LB 2", "seller": "ACME", "seller_iso": "VN",
             "seller_code": 704, "activity": "Processing Plant", "city": "HCMC", "section": "LBM",
             "source_url": "u", "verified_date": "d"},
        ]
        upsert_registry_sellers(conn, rows)
        out = build_sellers_web(conn, "0307")            # 0307 is covered by both FFP and LBM
        self.assertEqual(len(out), 1)                    # one ACME, not two
        self.assertEqual(out[0]["seller"], "ACME")
        self.assertEqual(out[0]["approval_no"], "TS 1")

    def test_uncovered_product_is_empty(self):
        conn = connect(":memory:")
        self.assertEqual(build_sellers_web(conn, "0901"), [])


if __name__ == "__main__":
    unittest.main()
