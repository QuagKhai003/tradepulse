"""
test_alerts.py — deterministic test for batch 1.8 (the push engine). No clock/network.
@context  Alerts renew subscriptions; the crossing/rule-change/rollup logic must be pinned exactly.
@affects  Covers alerts.signal_alerts + rule_change_alerts + match_watches + rollup_locked_clicks.
"""
import unittest

from tradepulse_etl.alerts import (
    match_event_watches, match_watches, regulatory_event_alerts, rollup_locked_clicks,
    rule_change_alerts, signal_alerts,
)


def ev(source, eid, hs4, market, kind="rule_change"):
    return {"source": source, "event_id": eid, "hs4": hs4, "market": market, "kind": kind,
            "area": "SPS", "title": "t", "event_date": "2026-07-01", "source_url": "u"}


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


class RegulatoryAlertTest(unittest.TestCase):
    CUR = [ev("wto-eping", "1", "0306", "kr"), ev("eu-rasff", "9", "0306", "eu", "rejection")]

    def test_only_new_events_alert(self):
        prev = {("wto-eping", "1", "0306")}                  # event 1 already seen
        out = regulatory_event_alerts(prev, self.CUR)
        self.assertEqual([a["source"] for a in out], ["eu-rasff"])   # only the new one (9)
        self.assertEqual(out[0]["type"], "regulatory")

    def test_first_load_skips_the_backlog(self):
        self.assertEqual(regulatory_event_alerts(set(), self.CUR), [])   # empty prev -> no spam

    def test_signal_watch_matched_by_family_and_market(self):
        # a watch on shrimp (090111... no, 030617) + Korea (M49 410) gets the KR event, not the EU one.
        alerts = regulatory_event_alerts({("x", "x", "x")}, self.CUR)   # non-empty prev -> both are "new"
        watches = [{"kind": "signal", "hs6": "030617", "market": "410"}]
        matched = match_event_watches(alerts, watches, {410: "kr", 97: "eu"})
        self.assertEqual(len(matched), 1)
        self.assertEqual([e["market"] for e in matched[0]["events"]], ["kr"])

    def test_wrong_market_watch_gets_nothing(self):
        alerts = regulatory_event_alerts({("x", "x", "x")}, self.CUR)
        watches = [{"kind": "signal", "hs6": "030617", "market": "392"}]   # Japan — no JP event here
        self.assertEqual(match_event_watches(alerts, watches, {392: "jp", 410: "kr", 97: "eu"}), [])

    def test_rule_kind_watch_ignored(self):                  # only 'signal' watches take change-alerts
        alerts = regulatory_event_alerts({("x", "x", "x")}, self.CUR)
        watches = [{"kind": "rule", "hs6": "030617", "market": "410"}]
        self.assertEqual(match_event_watches(alerts, watches, {410: "kr"}), [])


if __name__ == "__main__":
    unittest.main()
