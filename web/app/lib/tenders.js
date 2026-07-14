/**
 * tenders.js — load a product's tenders, past orders and sellers (the web/ETL seam).
 * @context  Trade stats say where demand WENT; tenders say where demand IS — a public buyer with an
 *           open deadline. Written by the ETL from EU TED (tenders-<hs>.json), already filtered to
 *           still-open notices.
 * @limits   Server-only (node:fs). Missing file -> [] (product simply has no tender coverage).
 * @affects  Consumed by country/[code]/page.js -> MarketFeed.
 */
import { readFile } from "node:fs/promises";
import path from "node:path";

export async function loadTenders(hs) {
  if (!hs) return [];
  const p = path.join(process.cwd(), "public", "data", `tenders-${hs}.json`);
  try {
    const list = JSON.parse(await readFile(p, "utf-8"));
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}

// PAST ORDERS: awarded contracts (who won, from whom, for how much).
export async function loadAwards(hs) {
  return loadList(hs, "awards");
}

// SELLERS: derived from those awards by the ETL — an organisation that has WON an on-product contract.
// Sellers never advertise; a won contract is the only public record that a company sells this product.
export async function loadSellers(hs) {
  return loadList(hs, "sellers");
}

async function loadList(hs, kind) {
  if (!hs) return [];
  const p = path.join(process.cwd(), "public", "data", `${kind}-${hs}.json`);
  try {
    const list = JSON.parse(await readFile(p, "utf-8"));
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}

// What CPV category this product's tender/award feed was matched to. `exact: false` means the match is
// a verified TEXT match to a related CPV label (e.g. HS "Vegetables, dried" -> CPV "Frozen
// vegetables") — the UI says so, because a related-category tender is not the same as your product.
export async function loadCpvMatch(hs) {
  if (!hs) return null;
  const p = path.join(process.cwd(), "public", "data", "cpv-match.json");
  try {
    const map = JSON.parse(await readFile(p, "utf-8"));
    return map[hs] || null;
  } catch {
    return null;
  }
}
