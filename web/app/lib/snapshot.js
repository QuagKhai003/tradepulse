/**
 * snapshot.js — load the ETL-generated Layer-1 snapshot (the web/ETL seam).
 * @context  Reads web/public/data/snapshot-<hs>.json at request time so re-running the ETL shows up
 *           without a rebuild. The FILE is slim so 1,240 products can ship: country names live once in
 *           countries.json, history is bare values (`h`) + periods (`hp`), and by_freq holds only the
 *           NON-default grains. This loader REHYDRATES those back into the shape components expect
 *           ({name_en, name_vi, history:[{period,value_usd}]}), so no component had to change.
 * @limits   Server-only (node:fs). Returns null when the file is missing (page tells the user to run ETL).
 * @affects  Consumed by app/page.js + country/[code]. Contract in docs/DATA_MODEL.md.
 */
import { readFile } from "node:fs/promises";
import path from "node:path";

const dataPath = (f) => path.join(process.cwd(), "public", "data", f);

async function readJson(file) {
  try {
    return JSON.parse(await readFile(dataPath(file), "utf-8"));
  } catch {
    return null;
  }
}

// Expand a short-key slot {v,p,f,y,b,d,bf} back to the shape components render. The map snapshot
// carries no history (dropped so 1,240 products fit) — sparklines get an empty list and skip it.
function hydrateSlot(s) {
  if (!s) return null;
  const out = {
    value_usd: s.v, period: s.p, freq: s.f,
    yoy_delta: s.y ?? null, band: s.b, direction: s.d ?? null,
    history: [],
  };
  if (s.bf) out.by_freq = Object.fromEntries(Object.entries(s.bf).map(([f, x]) => [f, hydrateSlot(x)]));
  return out;
}

// hs -> per-product snapshot (snapshot-<hs>.json); no hs -> the landing default (snapshot.json).
export async function loadSnapshot(hs) {
  const snap = await readJson(hs ? `snapshot-${hs}.json` : "snapshot.json");
  if (!snap) return null;
  const names = (await readJson("countries.json")) || {};
  const nm = (code) => names[String(code)] || {};

  snap.countries = (snap.countries || []).map((c) => ({
    code: c.c,
    name_en: nm(c.c).name_en ?? String(c.c),
    name_vi: nm(c.c).name_vi ?? String(c.c),
    exp: hydrateSlot(c.e),
    imp: hydrateSlot(c.i),
  }));
  snap.feed = [];   // the feed is derived from countries at the chosen grain (GlobalFeed)
  return snap;
}
