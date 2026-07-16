/**
 * forward.js — load a product's FORWARD lane: the world PRICE trend (ADR-0007).
 * @context  A SEPARATE lane from customs value — a $/unit world price (IMF PCPS), shown BESIDE the flow
 *           chart as a direction cue ("robusta price falling"). Never merged into a signal. Written by
 *           the ETL (forward-<hs>.json); null when there is no honest price series for the product.
 * @limits   Server-only (node:fs). Missing/null file -> null (the UI simply shows no price line).
 * @affects  Consumed by country/[code]/page.js -> PricePanel.
 */
import path from "node:path";
import { readJsonCached } from "./jsoncache.js";

export async function loadForward(hs) {
  if (!hs) return null;
  const p = path.join(process.cwd(), "public", "data", `forward-${hs}.json`);
  try {
    const d = await readJsonCached(p);
    return d && d.series && d.series.length ? d : null;
  } catch {
    return null;
  }
}
