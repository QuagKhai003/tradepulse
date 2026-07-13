/**
 * tenders.js — load the open-tender list for a product (the web/ETL seam).
 * @context  Trade stats say where demand WENT; tenders say where demand IS — a public buyer with an
 *           open deadline. Written by the ETL from EU TED (tenders-<hs>.json), already filtered to
 *           still-open notices.
 * @limits   Server-only (node:fs). Missing file -> [] (product simply has no tender coverage).
 * @affects  Consumed by app/page.js -> HeroClient -> TenderList.
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
