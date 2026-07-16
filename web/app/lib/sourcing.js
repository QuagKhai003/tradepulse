/**
 * sourcing.js — load the quarterly partner-sourcing file for a product (plan §7.3).
 * @context  Reads web/public/data/sourcing-<hs>.json (focus reporters only). Returns null if the
 *           product/reporter has no sourcing (the country page then shows annual history instead).
 * @limits   Server-only (fs).
 * @affects  Consumed by app/country/[code]/page.js.
 */
import { dataRef, readJsonCached } from "./jsoncache.js";

export async function loadSourcing(hs) {
  if (!hs) return null;
  try {
    return await readJsonCached(dataRef(`sourcing-${hs}.json`));
  } catch {
    return null;
  }
}
