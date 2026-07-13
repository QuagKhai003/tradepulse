"""
test_ted.py — TED notice -> tender row (sources/ted.py). Pure, offline.
@context  Proves the multilingual fields collapse to English, a missing deadline is OK (prior-info
          notices have none), the official notice URL is built, and only the buying ORGANISATION is
          kept — never a contact person (Golden Rule).
"""
import unittest

from tradepulse_etl.sources.ted import TedSource, _text

NOTICE = {
    "publication-number": "8046-2026",
    "notice-title": {"hun": "Lettország – Tüzelőanyagok", "eng": "Latvia – Wood fuels – supply"},
    "buyer-name": {"lav": ['Valsts centrs "Latgale"'], "eng": ["Latgale State Centre"]},
    "buyer-country": ["LVA"],
    "publication-date": "2026-01-08+01:00",
    "classification-cpv": ["09000000", "09111400"],
}


class TedTest(unittest.TestCase):
    def test_notice_to_row(self):
        r = TedSource._notice(NOTICE, "440131", "09111400", "2026-07-14T00:00:00Z")
        self.assertEqual(r["id"], "8046-2026")
        self.assertEqual(r["hs6"], "440131")
        self.assertEqual(r["title"], "Latvia – Wood fuels – supply")     # English preferred
        self.assertEqual(r["buyer"], "Latgale State Centre")             # organisation
        self.assertEqual(r["buyer_country"], "LVA")
        self.assertEqual(r["published"], "2026-01-08")                   # date only
        self.assertIsNone(r["deadline"])                                 # prior-info notice: no deadline
        self.assertEqual(r["url"], "https://ted.europa.eu/en/notice/8046-2026")

    def test_deadline_trimmed_to_date(self):
        n = {**NOTICE, "deadline-receipt-tender-date-lot": ["2026-09-30+02:00"]}
        self.assertEqual(TedSource._notice(n, "440131", "09111400", "t")["deadline"], "2026-09-30")

    def test_untitled_notice_dropped(self):
        self.assertIsNone(TedSource._notice({"publication-number": "1-2026"}, "440131", "09111400", "t"))

    def test_multilingual_fallback(self):
        self.assertEqual(_text({"fra": ["Bois"]}), "Bois")   # no English -> first available
        self.assertIsNone(_text(None))


if __name__ == "__main__":
    unittest.main()
