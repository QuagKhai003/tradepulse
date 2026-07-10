"use client";
/**
 * WatchButton.js — "Watch this" toggle (plan §7.7, the rented product).
 * @context  The push engine's front door: the user asks to be alerted when a signal band crosses
 *           or a rule changes. MVP stores the watch client-side + logs it to /api/watch; real
 *           delivery (email, then Zalo) swaps in behind that. No login yet -> anonymous watch.
 * @limits   Client island (localStorage + fetch). Best-effort logging.
 * @affects  Placed on the market drill-down + requirement pages.
 */
import { useEffect, useState } from "react";

export default function WatchButton({ watchKey, meta, labelOff, labelOn }) {
  const [on, setOn] = useState(false);
  const storeKey = `tp_watch_${watchKey}`;

  useEffect(() => {
    setOn(typeof window !== "undefined" && localStorage.getItem(storeKey) === "1");
  }, [storeKey]);

  async function toggle() {
    const next = !on;
    setOn(next);
    try {
      localStorage.setItem(storeKey, next ? "1" : "0");
      await fetch("/api/watch", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ key: watchKey, action: next ? "watch" : "unwatch", ...meta }),
      });
    } catch { /* best-effort */ }
  }

  return (
    <button type="button" className={`watchbtn ${on ? "on" : ""}`} onClick={toggle} aria-pressed={on}>
      {on ? `★ ${labelOn}` : `☆ ${labelOff}`}
    </button>
  );
}
