"""
test_alerts.py — deterministic test for batch 1.8 (the push engine). No clock/network.
@context  Alerts renew subscriptions; the crossing/rule-change/rollup logic must be pinned exactly.
@affects  Covers alerts.signal_alerts + rule_change_alerts + match_watches + rollup_locked_clicks.
"""
import unittest

from tradepulse_etl.alerts import (
    match_watches, rollup_locked_clicks, rule_change_alerts, signal_alerts,
)


def sig(reporter, band, period="2026-Q1", yoy=0.4):
    return {"reporter": reporter, "hs6": "440131", "flow": "M", "period": period,
            "band": band, "yoy_delta": yoy}


class SignalAlertsTest(unittest.TestCase):
    def test_new_cells_are_not_crossings(self):
        # First load: prev empty -> no alerts (avoid spamming every cell on initial build).
        self.assertEqual(signal_alerts([], [sig(392, "significant")]), [])

    def test_band_change_emits(self):
        prev = [sig(392, "moderate")]
        cur = [sig(392, "surge")]
        out = signal_alerts(prev, cur)
        self.assertEqual(len(out), 1)
        self.assertEqual((out[0]["from_band"], out[0]["to_band"]), ("moderate", "surge"))

    def test_notable_to_minor_still_alerts(self):
        # Demand cooling (significant -> minor) is a signal too.
        out = signal_alerts([sig(392, "significant")], [sig(392, "minor")])
        self.assertEqual(len(out), 1)

    def test_unchanged_band_silent(self):
        self.assertEqual(signal_alerts([sig(392, "moderate")], [sig(392, "moderate")]), [])


class RuleChangeTest(unittest.TestCase):
    pages = [{"hs6": "440131", "market": "jp", "change_log": [
        {"date": "2026-06-15", "text_en": "SBP tightened", "source": "sbp"},
        {"date": "2026-02-10", "text_en": "FIT schedule", "source": "meti"},
    ]}]

    def test_all_then_since(self):
        self.assertEqual(len(rule_change_alerts(self.pages)), 2)
        recent = rule_change_alerts(self.pages, since="2026-03-01")
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]["date"], "2026-06-15")


class MatchAndRollupTest(unittest.TestCase):
    def test_match_watches(self):
        events = [{"type": "signal", "hs6": "440131", "reporter": 392},
                  {"type": "signal", "hs6": "440131", "reporter": 410}]
        watches = [{"hs6": "440131", "reporter": 392}]
        matched = match_watches(events, watches)
        self.assertEqual(len(matched), 1)
        self.assertEqual(len(matched[0]["events"]), 1)
        self.assertEqual(matched[0]["events"][0]["reporter"], 392)

    def test_rollup(self):
        entries = [{"hs6": "090240", "event": "request"}, {"hs6": "090240", "event": "view"},
                   {"hs6": "030617", "event": "view"}]
        roll = rollup_locked_clicks(entries)
        self.assertEqual(roll[0]["hs6"], "090240")            # most requests first
        self.assertEqual(roll[0]["requests"], 1)
        self.assertEqual(roll[0]["views"], 1)


if __name__ == "__main__":
    unittest.main()
