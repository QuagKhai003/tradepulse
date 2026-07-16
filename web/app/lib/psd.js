/**
 * psd.js — load a product's FORWARD OUTLOOK lane: USDA PSD supply/demand forecast (ADR-0007).
 * @context  A SEPARATE lane from customs value — a QUANTITY forecast by market year (who is forecast to
 *           produce/import/export/consume/hold stocks), keyed by market. Shown as its own outlook panel,
 *           never merged into a signal. Written by the ETL (psd-<hs>.json); null when the product is not
 *           an ag commodity PSD covers (same honest-empty behaviour as the IMF price lane).
 * @limits   Server-only (node:fs). Missing/null file -> null (the UI simply shows no outlook).
 * @affects  Consumed by country/[code]/page.js -> PsdPanel.
 */
import path from "node:path";
import { readJsonCached } from "./jsoncache.js";

export async function loadPsd(hs) {
  if (!hs) return null;
  const p = path.join(process.cwd(), "public", "data", `psd-${hs}.json`);
  try {
    const d = await readJsonCached(p);
    return d && typeof d === "object" && Object.keys(d).length ? d : null;
  } catch {
    return null;
  }
}
