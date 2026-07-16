/**
 * foundation.js — load the qualification tab's FOUNDATION informed-list (not a checklist).
 * @context  The baseline things a Vietnamese exporter needs to KNOW before shipping a product to a
 *           market — commercial invoice, certificate of origin, phytosanitary/health certs, meeting
 *           destination limits. Framed as general guidance, NOT product-specific requirements. Golden
 *           Rule: every item cites an official portal (the source where the user confirms the specifics
 *           for their exact shipment). Content in content/requirements/foundation.json (git = audit).
 * @limits   Server-only (fs). Returns null when the destination is not a pilot market (no verified
 *           portal) or the product has no baseline category — an honest omission, never a fake list.
 * @affects  Consumed by QualPanel. Category resolver is tested implicitly via SSR.
 */
import { contentRef, readJsonCached } from "./jsoncache.js";

// HS chapter -> the baseline categories that decide which items apply. Wood is a plant product (phyto);
// seafood is animal-origin food (health cert). Kept to the pilots + near neighbours; broaden later.
const BY_CHAPTER = { "44": ["wood", "plant"], "03": ["seafood", "food"], "08": ["nuts", "food", "plant"] };
const FOOD_PLANT = new Set(["07", "09", "10", "11", "12", "15", "18", "20", "21"]);

export function categoriesFor(hs) {
  const ch = String(hs || "").slice(0, 2);
  if (BY_CHAPTER[ch]) return BY_CHAPTER[ch];
  if (FOOD_PLANT.has(ch)) return ["food", "plant"];
  return [];                                   // no baseline category -> no foundation (honest)
}

export async function loadFoundation(hs, slug) {
  if (!slug) return null;                      // non-pilot destination -> no verified portal to cite
  const cats = categoriesFor(hs);
  if (!cats.length) return null;
  let data;
  try {
    data = await readJsonCached(contentRef("requirements/foundation.json"));
  } catch {
    return null;
  }
  const market = data.markets[slug];
  if (!market) return null;
  const has = new Set(cats);
  const items = data.items
    .filter((it) => (!it.market_only || it.market_only === slug)
                 && (it.applies.includes("all") || it.applies.some((a) => has.has(a))))
    .map((it) => ({ id: it.id, label_en: it.label_en, label_vi: it.label_vi,
                    note_en: it.note_en, note_vi: it.note_vi, source: it.source || market }));
  return { framing_en: data.framing_en, framing_vi: data.framing_vi, market, items };
}
