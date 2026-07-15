"""
test_eping.py — WTO ePing regulatory-event parsing (sources/eping.py) + the events lane. Pure, offline.
@context  The qualification-tab EVENTS lane (ADR-0007): a rule-change is an event, never a number. These
          pin the row shape, the HS-vs-keyword confidence, market resolution, HTML stripping, the HS4-
          family fetch, and — above all — the Golden Rule (public act + source only, never a contact).
@limits   Offline; no network (EpingSource._row/_text are static/pure; build_events uses an in-mem DB).
@affects  tradepulse_etl/sources/eping.py + db.regulatory_events + export.build_events
"""
import json
import unittest

from tradepulse_etl.db import connect, fetch_regulatory_events, upsert_regulatory_events
from tradepulse_etl.export import build_events
from tradepulse_etl.sources.eping import EpingSource, _text

# A recent SPS notification WITH a structured HS tag (matches shrimp 0306), from a pilot market (Korea).
ITEM_HS = {
    "id": 118548, "area": "SPS", "distributionDate": "2026-07-02T00:00:00+00:00",
    "commentDeadlineDate": "2026-09-01T00:00:00+00:00",
    "notifyingMember": "Korea, Republic of", "documentSymbol": " G/SPS/N/KOR/1",
    "title": "<p style=\"margin:2px\">Amendments to Standards for Frozen Shrimps</p>",
    "description": "<p>New maximum residue limits for antibiotics in imported frozen shrimps and prawns.</p>",
    "productsFreeText": "<p>Frozen shrimps and prawns</p>",
    "hsCodes": [{"id": 44595, "code": "030617", "name": "030617 - Frozen shrimps and prawns"}],
}
# An older TBT notification WITHOUT an HS tag, from a non-pilot member (keyword match only).
ITEM_KW = {
    "id": 52218, "area": "TBT", "distributionDate": "2025-09-18T00:00:00+00:00",
    "commentDeadlineDate": None, "notifyingMember": "Grenada",
    "title": "<p>Rice – Specification</p>", "description": "<p>Standard for grades of milled rice.</p>",
    "productsFreeText": "<p>milled rice</p>", "hsCodes": [],
}


class RowTest(unittest.TestCase):
    def test_hs_tag_gives_strong_match_and_full_fields(self):
        r = EpingSource._row(ITEM_HS, "0306", "2026-07-15")
        self.assertEqual(r["match_kind"], "hs")              # structured HS tag confirmed it
        self.assertEqual(r["market"], "kr")                 # pilot market resolved
        self.assertEqual(r["market_name"], "Korea, Republic of")
        self.assertEqual(r["kind"], "rule_change")
        self.assertEqual(r["area"], "SPS")
        self.assertEqual(r["event_date"], "2026-07-02")
        self.assertEqual(r["deadline"], "2026-09-01")       # forward-looking comment deadline
        self.assertIn("viewData=118548", r["source_url"])   # citable official source
        self.assertNotIn("<", r["title"])                   # HTML stripped

    def test_no_hs_tag_falls_back_to_keyword_confidence(self):
        r = EpingSource._row(ITEM_KW, "1006", "2026-07-15")
        self.assertEqual(r["match_kind"], "keyword")
        self.assertIsNone(r["market"])                      # Grenada is not a pilot market
        self.assertEqual(r["market_name"], "Grenada")
        self.assertIsNone(r["deadline"])

    def test_eu_member_folds_to_eu_market(self):
        r = EpingSource._row({**ITEM_HS, "notifyingMember": "Germany"}, "0306", "d")
        self.assertEqual(r["market"], "eu")

    def test_hs4_key_matches_hs6_tag(self):                 # product '440131' vs tag '4401'
        it = {**ITEM_HS, "hsCodes": [{"code": "4401"}]}
        self.assertEqual(EpingSource._row(it, "440131", "d")["match_kind"], "hs")

    def test_golden_rule_never_carries_a_contact(self):
        noisy = {**ITEM_HS, "contactPoint": "Jane Doe", "email": "a@b.c", "phone": "+82 2 123"}
        blob = json.dumps(EpingSource._row(noisy, "0306", "d"))
        self.assertNotIn("Jane Doe", blob)
        self.assertNotIn("a@b.c", blob)
        self.assertNotIn("+82", blob)


class TextTest(unittest.TestCase):
    def test_strips_tags_and_unescapes(self):
        self.assertEqual(_text("<p>Tea &amp; coffee</p>"), "Tea & coffee")

    def test_truncates_long_text(self):
        out = _text("x" * 500, limit=100)
        self.assertTrue(out.endswith("…"))
        self.assertLessEqual(len(out), 101)

    def test_empty_is_none(self):
        self.assertIsNone(_text(""))
        self.assertIsNone(_text(None))


class BuildEventsTest(unittest.TestCase):
    def _rows(self):
        base = {"source": "wto-eping", "market": "kr", "market_name": "Korea, Republic of",
                "deadline": None, "kind": "rule_change", "area": "SPS", "title": "t", "detail": "d",
                "match_kind": "hs", "source_url": "u", "verified_date": "d"}
        return [
            {**base, "event_id": "1", "hs4": "0901", "event_date": "2026-01-01"},
            {**base, "event_id": "2", "hs4": "090111", "event_date": "2026-05-01"},
            {**base, "event_id": "1", "hs4": "090111", "event_date": "2026-01-01"},   # same notice, child HS
        ]

    def test_family_fetch_dedup_and_newest_first(self):
        conn = connect(":memory:")
        upsert_regulatory_events(conn, self._rows())
        out = build_events(conn, "090111")                 # opening the HS6 child
        self.assertEqual([e["id"] for e in out], ["2", "1"])   # deduped to 2 events, newest first
        self.assertEqual(out[0]["date"], "2026-05-01")

    def test_uncovered_product_is_empty(self):
        conn = connect(":memory:")
        self.assertEqual(build_events(conn, "8703"), [])   # cars — no regulatory coverage, honest empty

    def test_family_prefix_matches_heading_and_children(self):
        conn = connect(":memory:")
        upsert_regulatory_events(conn, self._rows())
        self.assertEqual(len(fetch_regulatory_events(conn, "0901")), 3)   # heading sees all in family


if __name__ == "__main__":
    unittest.main()
