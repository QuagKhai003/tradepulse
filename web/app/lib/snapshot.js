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
import { access } from "node:fs/promises";
import path from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { readJsonCached } from "./jsoncache.js";

const dataPath = (f) => path.join(process.cwd(), "public", "data", f);

async function readJson(file) {
  try {
    return await readJsonCached(dataPath(file));
  } catch {
    return null;
  }
}

// --- Lazy per-product build (owner's request): don't pre-build all 1,240 products at startup. A
// product's files are built the FIRST time someone opens it — from the STORED DB (fast, no network;
// the DB is the cache, refreshed by a periodic batch). Concurrent opens of the same product share one
// build. If the build fails, loadSnapshot just returns null (the page shows its no-data state). ---
const pexec = promisify(execFile);
const PY = process.platform === "win32" ? "python" : "python3";
const ETL_DIR = path.join(process.cwd(), "..", "etl");
const building = new Map();   // hs -> in-flight build promise (dedupes concurrent requests)

async function fileExists(p) {
  try { await access(p); return true; } catch { return false; }
}

async function ensureProduct(hs) {
  // The landing default + the TOTAL rollup are batch artifacts, not lazily built per product.
  if (!hs || hs === "TOTAL") return;
  if (await fileExists(dataPath(`snapshot-${hs}.json`))) return;   // cached -> serve instantly
  if (!building.has(hs)) {
    const job = pexec(PY, ["-m", "tradepulse_etl", "--only", hs, "--export-only"],
                      { cwd: ETL_DIR, timeout: 90_000 })
      .catch((e) => { console.warn(`[lazy-build] ${hs} failed: ${e.message}`); })
      .finally(() => building.delete(hs));
    building.set(hs, job);
  }
  await building.get(hs);
}

// Expand a short-key slot {v,p,f,y,b,d,h,bf} back to the shape components render. `h` is bare values
// aligned to the snapshot's shared periods index for that grain (a null = this country reported
// nothing that period, so the point is skipped rather than sliding the series left).
function hydrateSlot(s, periods = {}) {
  if (!s) return null;
  const index = periods[s.f || "A"] || [];
  const out = {
    value_usd: s.v, period: s.p, freq: s.f,
    yoy_delta: s.y ?? null, band: s.b, direction: s.d ?? null,
    estimated: s.m === 1,   // value rebuilt from partner reports (a late/non-reporter), not self-reported
    history: (s.h || []).map((v, i) => (v == null ? null : { period: index[i], value_usd: v }))
                        .filter((x) => x && x.period),
  };
  if (s.bf) {
    out.by_freq = Object.fromEntries(Object.entries(s.bf).map(([f, x]) => [f, hydrateSlot(x, periods)]));
  }
  return out;
}

// hs -> per-product snapshot (snapshot-<hs>.json); no hs -> the landing default (snapshot.json).
export async function loadSnapshot(hs) {
  await ensureProduct(hs);   // build this product's files on first open (from the stored DB), then read
  const snap = await readJson(hs ? `snapshot-${hs}.json` : "snapshot.json");
  if (!snap) return null;
  const names = (await readJson("countries.json")) || {};
  const nm = (code) => names[String(code)] || {};

  // `snap` is the SHARED cached parse (jsoncache) — build a NEW object rather than mutating it, or the
  // next read would get already-hydrated countries and re-hydrate garbage.
  return {
    ...snap,
    countries: (snap.countries || []).map((c) => ({
      code: c.c,
      name_en: nm(c.c).name_en ?? String(c.c),
      name_vi: nm(c.c).name_vi ?? String(c.c),
      exp: hydrateSlot(c.e, snap.periods),
      imp: hydrateSlot(c.i, snap.periods),
    })),
    feed: [],   // the feed is derived from countries at the chosen grain (GlobalFeed)
  };
}
