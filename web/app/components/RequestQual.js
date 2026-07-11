"use client";
/**
 * RequestQual.js — "requirements coming soon — request it" for an uncovered product×country (plan §7.6).
 * @context  Every uncovered qualification pair is telemetry: view + request are logged as demand
 *           evidence (the roadmap oracle) via /api/locked-click. No data faked.
 * @limits   Client island (logs on mount + on request). Best-effort.
 * @affects  Rendered by QualPanel when no requirement page exists for the pair.
 */
import { useEffect, useState } from "react";

export default function RequestQual({ hs, market, product, country, lang }) {
  const [done, setDone] = useState(false);
  useEffect(() => { log({ hs6: hs, market, event: "view" }); }, [hs, market]);

  const tx = lang === "en"
    ? { p: `Market-entry requirements for ${product} → ${country} are coming soon.`,
        b: "Request this pair", ok: "Thanks — your request is logged." }
    : { p: `Yêu cầu vào thị trường cho ${product} → ${country} sắp có.`,
        b: "Yêu cầu cặp này", ok: "Cảm ơn — yêu cầu đã được ghi nhận." };

  return (
    <div className="qual-locked">
      <span className="qual-lock">🔒</span>
      <p className="muted">{tx.p}</p>
      {done
        ? <div className="locked-ok">✓ {tx.ok}</div>
        : <button type="button" className="locked-btn" onClick={async () => { await log({ hs6: hs, market, event: "request" }); setDone(true); }}>{tx.b}</button>}
    </div>
  );
}

async function log(payload) {
  try {
    await fetch("/api/locked-click", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(payload) });
  } catch { /* best-effort */ }
}
