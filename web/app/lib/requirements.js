/**
 * requirements.js — load Layer-3 requirement pages (plan §8, the paid core).
 * @context  Reads curated content/requirements/pellets-<market>.json (tracked source; git history =
 *           the audit trail). ENFORCES the rule "no source link + verified date = the item does not
 *           ship" by dropping any incomplete requirement before it ever reaches the UI.
 * @limits   Server-only (fs). Free/paid gating is applied in the page, not here.
 * @affects  Consumed by app/requirements/[market]/page.js + the index.
 */
import { readFile } from "node:fs/promises";
import path from "node:path";

export const REQ_MARKETS = ["jp", "kr", "eu"];

function reqPath(market) {
  return path.join(process.cwd(), "..", "content", "requirements", `pellets-${market}.json`);
}

export async function loadRequirement(market) {
  if (!REQ_MARKETS.includes(market)) return null;
  try {
    const data = JSON.parse(await readFile(reqPath(market), "utf-8"));
    // Golden Rule / plan §8: an item without an official source + verified date does not ship.
    const kept = (data.requirements || []).filter((r) => r.source_url && r.verified_date);
    const dropped = (data.requirements || []).length - kept.length;
    return { ...data, requirements: kept, dropped };
  } catch {
    return null;
  }
}

export async function loadRequirementIndex() {
  const out = [];
  for (const m of REQ_MARKETS) {
    const d = await loadRequirement(m);
    if (d) out.push({ market: m, name_en: d.market_name_en, name_vi: d.market_name_vi,
                      last_full_review: d.last_full_review, count: d.requirements.length });
  }
  return out;
}
