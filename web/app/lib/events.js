/**
 * events.js — load a product's REGULATORY CHANGES (the qualification-tab EVENTS lane, ADR-0007).
 * @context  A SEPARATE lane from trade stats: a destination market changing an import rule is a change
 *           to what it takes to QUALIFY to sell there — forward-looking (each carries a comment
 *           deadline). Written by the ETL from WTO ePing (events-<hs>.json). Never a number, never
 *           merged into a signal; here purely to be shown beside the requirements, each with its source.
 * @limits   Server-only (node:fs). Missing file -> [] (product has no regulatory coverage yet).
 * @affects  Consumed by QualPanel on country/[code]/page.js.
 */
import path from "node:path";
import { readJsonCached } from "./jsoncache.js";

// M49 country code -> our pilot market slug (mirrors config.MARKETS on the ETL side). The EU is both
// the aggregate (97) and each member state, so a member's own country page also resolves to 'eu' — its
// RASFF/ePing entries pin as "in this market" and it shows the EU foundation guidance.
const EU27 = [40, 56, 100, 191, 196, 203, 208, 233, 246, 250, 276, 300, 348, 372, 380,
              428, 440, 442, 470, 528, 616, 620, 642, 703, 705, 724, 752];
export const MARKET_SLUG = { 392: "jp", 410: "kr", 97: "eu", 842: "us", 826: "gb",
                            ...Object.fromEntries(EU27.map((c) => [c, "eu"])) };

export async function loadEvents(hs) {
  if (!hs) return [];
  const p = path.join(process.cwd(), "public", "data", `events-${hs}.json`);
  try {
    const list = await readJsonCached(p);
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}
