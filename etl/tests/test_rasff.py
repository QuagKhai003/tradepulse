"""
test_rasff.py — EU RASFF border-rejection parsing (sources/rasff.py). Pure, offline.
@context  The qualification tab's 2nd event source (kind='rejection', ADR-0007). These pin the row
          shape, the date reformat, the CATEGORY-narrowed-by-keyword filter (a broad category must never
          dump unrelated products), the Vietnam-origin signal in the detail, and the Golden Rule.
@limits   Offline; no network (_search is stubbed; _row/_date are static/pure).
@affects  tradepulse_etl/sources/rasff.py + db.regulatory_events + export.build_events
"""
import json
import unittest

from tradepulse_etl.sources.rasff import RasffSource, _date

TEA = {"notifId": 111, "subject": "unauthorized colours in green tea from Vietnam",
       "ecValidationDate": "06-07-2026 09:00:00", "notifyingCountry": {"organizationName": "Belgium"},
       "riskDecision": {"description": "not serious"},
       "originCountries": [{"organizationName": "Vietnam", "isoCode": "VN"}]}
COCOA = {"notifId": 222, "subject": "cadmium in cocoa powder from the Netherlands",
         "ecValidationDate": "13-07-2026 12:00:00", "notifyingCountry": {"organizationName": "Belgium"},
         "riskDecision": {"description": "serious"}, "originCountries": [{"organizationName": "Netherlands"}]}


class DateTest(unittest.TestCase):
    def test_reformat(self):
        self.assertEqual(_date("13-07-2026 17:14:00"), "2026-07-13")
        self.assertIsNone(_date(None))
        self.assertIsNone(_date("bad"))


class RowTest(unittest.TestCase):
    def test_fields_and_vietnam_origin(self):
        r = RasffSource._row(TEA, "0902", "2026-07-15")
        self.assertEqual(r["kind"], "rejection")
        self.assertEqual(r["market"], "eu")
        self.assertEqual(r["market_name"], "Belgium")       # the notifying member
        self.assertEqual(r["event_date"], "2026-07-06")
        self.assertIn("origin: Vietnam", r["detail"])        # the seller's warning
        self.assertIn("risk: not serious", r["detail"])
        self.assertIn("111", r["source_url"])
        self.assertIsNone(r["deadline"])                     # a rejection has no comment period

    def test_drops_without_subject_or_id(self):
        self.assertIsNone(RasffSource._row({"notifId": 1}, "0902", "d"))
        self.assertIsNone(RasffSource._row({"subject": "x"}, "0902", "d"))

    def test_never_carries_a_contact(self):                  # Golden Rule
        noisy = {**TEA, "contactPerson": "Jane Doe", "email": "a@b.c"}
        blob = json.dumps(RasffSource._row(noisy, "0902", "d"))
        self.assertNotIn("Jane Doe", blob)
        self.assertNotIn("a@b.c", blob)


class KeywordFilterTest(unittest.TestCase):
    def _src(self, notifs):
        s = RasffSource()
        s._search = lambda cat: notifs                       # stub the network
        return s

    def test_category_is_narrowed_by_product_term(self):
        # cocoa/coffee/tea category returns tea + cocoa; a query for TEA must keep only the tea row.
        rows = self._src([TEA, COCOA]).pull({"0902": 18435}, {"0902": ["tea"]}, "d", 3650)
        self.assertEqual([r["event_id"] for r in rows], ["111"])

    def test_family_keyword_fallback(self):
        # 090240 has no own keyword here -> must fall back to its HS4 family (0902 -> 'tea'), still filter.
        rows = self._src([TEA, COCOA]).pull({"090240": 18435}, {"0902": ["tea"]}, "d", 3650)
        self.assertEqual([r["event_id"] for r in rows], ["111"])

    def test_no_keyword_skips_rather_than_dumping(self):
        rows = self._src([TEA, COCOA]).pull({"9999": 18435}, {}, "d", 3650)
        self.assertEqual(rows, [])                            # never dump an unfiltered category


if __name__ == "__main__":
    unittest.main()
