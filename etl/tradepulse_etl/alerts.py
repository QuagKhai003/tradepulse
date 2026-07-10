"""
alerts.py — the push engine: signal-band crossings, rule changes, telemetry rollup (plan §7.7).
@context  Alerts are what renew subscriptions (plan §5). All alert logic is PURE + deterministic:
          a diff between two stored states, never an AI guess. Delivery (email/Zalo) is a thin
          swap around these events; the MVP writes them to a log.
@done     signal_alerts() (band crossings), rule_change_alerts() (change-log), match_watches()
          (who gets what), rollup_locked_clicks() (the roadmap oracle summary).
@limits   PURE: inputs are plain lists/dicts; no I/O, no clock, no network. Callers persist/deliver.
@affects  Fed by db.fetch signals + content change_logs + the locked-clicks log. Tested offline.
"""
from __future__ import annotations

# Bands worth pushing (plan §6.3: "minor" is suppressed by design).
NOTABLE = {"moderate", "significant", "surge", "collapse", "new"}


def signal_alerts(prev_signals: list[dict], cur_signals: list[dict]) -> list[dict]:
    """Emit an alert when a cell's band CHANGES between two ETL runs and a notable band is involved.
    New cells (absent from prev) are the initial load, not a crossing -> skipped."""
    prev = {_key(s): s["band"] for s in prev_signals}
    out = []
    for s in cur_signals:
        pb = prev.get(_key(s))
        if pb is None or pb == s["band"]:
            continue
        if s["band"] in NOTABLE or pb in NOTABLE:
            out.append({
                "type": "signal", "reporter": s["reporter"], "hs6": s["hs6"], "flow": s["flow"],
                "period": s["period"], "from_band": pb, "to_band": s["band"],
                "yoy_delta": s.get("yoy_delta"),
            })
    return out


def rule_change_alerts(pages: list[dict], since: str | None = None) -> list[dict]:
    """One alert per change-log entry (each edit to a requirement page notifies its watchers)."""
    out = []
    for page in pages:
        for e in page.get("change_log", []):
            if since is not None and e["date"] <= since:
                continue
            out.append({
                "type": "rule_change", "hs6": page.get("hs6"), "market": page.get("market"),
                "date": e["date"], "text_en": e.get("text_en"), "text_vi": e.get("text_vi"),
                "source": e.get("source"),
            })
    return out


def match_watches(events: list[dict], watches: list[dict]) -> list[dict]:
    """Attach each event to the watches it satisfies. A watch = {hs6, market?, reporter?}."""
    out = []
    for w in watches:
        hits = [e for e in events if _matches(e, w)]
        if hits:
            out.append({"watch": w, "events": hits})
    return out


def rollup_locked_clicks(entries: list[dict]) -> list[dict]:
    """Aggregate the locked-page demand log into per-HS view/request counts (roadmap oracle)."""
    agg: dict[str, dict] = {}
    for e in entries:
        hs = e.get("hs6", "")
        a = agg.setdefault(hs, {"hs6": hs, "views": 0, "requests": 0})
        if e.get("event") == "request":
            a["requests"] += 1
        else:
            a["views"] += 1
    return sorted(agg.values(), key=lambda a: (a["requests"], a["views"]), reverse=True)


def _key(s: dict) -> tuple:
    return (s["reporter"], s["hs6"], s["flow"], s["period"])


def _matches(event: dict, watch: dict) -> bool:
    if watch.get("hs6") and event.get("hs6") and watch["hs6"] != event["hs6"]:
        return False
    if watch.get("market") and event.get("market") and watch["market"] != event["market"]:
        return False
    if watch.get("reporter") and event.get("reporter") and watch["reporter"] != event["reporter"]:
        return False
    return True
