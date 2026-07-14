"""
test_comtrade.py — offline test for the live-source helpers (no network).
@context  Regression for the real-data double-count bug: Comtrade returns the World total broken
          out by transport mode + 2nd partner; only the fully-aggregated row is the true total.
@affects  Covers comtrade._is_world_total + ComtradeSource._normalise + prev_year_period (annual).
"""
import unittest

from tradepulse_etl.signals import prev_year_period
from tradepulse_etl.sources.comtrade import ComtradeMirrorSource, ComtradeSource, _is_total_row, _is_world_total


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


class BatchAnnualTest(unittest.TestCase):
    """cmdCode batching: many products per call, with a split when the row cap truncates."""

    def _src(self, responses):
        src = ComtradeSource(key="k", years=1, pause=0)
        self.calls = []

        def fake_get(url, auth):           # record the cmdCode of every call
            import urllib.parse as up
            q = up.parse_qs(up.urlparse(url).query)
            codes = q["cmdCode"][0].split(",")
            self.calls.append(codes)
            return responses(codes)

        src._get = fake_get
        return src

    def test_batches_products_into_one_call(self):
        src = self._src(lambda codes: [])
        src.CODES_PER_CALL = 10
        src._pull_annual([f"{i:04d}" for i in range(25)])
        self.assertEqual([len(c) for c in self.calls], [10, 10, 5])

    def test_splits_when_row_cap_truncates(self):
        def responses(codes):              # a 4-code call comes back at the cap -> must halve
            n = src.ROW_CAP if len(codes) > 2 else 3
            return [{"reporterCode": 704, "partnerCode": 0, "cmdCode": codes[0], "period": "2025",
                     "flowCode": "X", "primaryValue": 1.0, "netWgt": 1.0}] * n
        src = self._src(responses)
        src.CODES_PER_CALL = 4
        src._pull_annual(["0101", "0102", "0103", "0104"])
        self.assertEqual([len(c) for c in self.calls], [4, 2, 2])   # capped -> split in halves


class MirrorTest(unittest.TestCase):
    """Mirror rebuilds a country's exports from its partners' import reports — for late/non-reporters."""

    def _src(self, data_by_call):
        src = ComtradeMirrorSource(key="k", pause=0)
        self.calls = []
        seq = list(data_by_call)

        def fake_get(url, auth):
            self.calls.append(url)
            return seq.pop(0) if seq else []

        src._get = fake_get
        return src

    def test_sums_partner_imports_into_exporter_rows(self):
        # two reporters (DE, US) each import coffee FROM Vietnam(704) -> VN mirror export = sum
        rows = [{"reporterCode": 276, "partnerCode": 704, "cmdCode": "0901", "flowCode": "M", "primaryValue": 100.0},
                {"reporterCode": 842, "partnerCode": 704, "cmdCode": "0901", "flowCode": "M", "primaryValue": 250.0},
                {"reporterCode": 842, "partnerCode": 0,   "cmdCode": "0901", "flowCode": "M", "primaryValue": 999.0}]  # World partner ignored
        src = self._src([rows])
        out = src._mirror_batch(["0901"], 2024)
        vn = [r for r in out if r["reporterCode"] == 704]
        self.assertEqual(len(vn), 1)
        self.assertEqual(vn[0]["primaryValue"], 350.0)          # 100 + 250, World row excluded
        self.assertEqual(vn[0]["flowCode"], "X")                # imports-from-VN => VN's EXPORT
        self.assertEqual(vn[0]["partnerCode"], 0)               # stored as a World-partner export row
        self.assertIsNone(vn[0]["publishedDate"])               # so direct reports win on freshness ties

    def test_skips_the_thin_frontier_year(self):
        # the most-recent year (current-1) is still too thin to trust; mirror starts at current-2
        from datetime import date
        src = ComtradeMirrorSource(key="k", pause=0)
        seen = []
        src._get = lambda url, auth: seen.append(url) or []
        src.pull(["0901"], [], None)
        blob = " ".join(seen)
        self.assertNotIn(f"period={date.today().year - 1}", blob)   # frontier year skipped
        self.assertIn(f"period={date.today().year - 2}", blob)      # well-covered year pulled


class PreviewFailoverTest(unittest.TestCase):
    """When the keyed /data call fails (throttle), fall over to the keyless /public/v1/preview path."""

    def test_failover_rewrites_url_and_drops_key(self):
        src = ComtradeSource(key="k", pause=0)
        seen = {}

        def fake_open(req, timeout):
            seen["url"] = req.full_url
            seen["has_key"] = "Ocp-Apim-Subscription-Key" in req.headers

            class R:
                def __enter__(s): return s
                def __exit__(s, *a): return False
                def read(s): return b'{"data":[{"reporterCode":704}]}'
            return R()

        import urllib.request
        orig = urllib.request.urlopen
        urllib.request.urlopen = fake_open
        try:
            out = src._preview_fallback(
                "https://comtradeapi.un.org/data/v1/get/C/A/HS?cmdCode=0901", {"x": 1})
        finally:
            urllib.request.urlopen = orig
        self.assertIn("/public/v1/preview/", seen["url"])   # keyed path -> preview path
        self.assertNotIn("/data/v1/get/", seen["url"])
        self.assertFalse(seen["has_key"])                    # preview is keyless
        self.assertEqual(out, [{"reporterCode": 704}])

    def test_failover_skips_non_keyed_urls(self):
        src = ComtradeSource(key="k", pause=0)
        self.assertIsNone(src._preview_fallback("https://example.com/other", {}))
