/**
 * jsoncache.js — in-process cache + source switch for the ETL data files.
 * @context  The per-product JSON in public/data is STATIC within a running server (rewritten only by the
 *           ETL batch). Re-reading/re-parsing it every navigation — sourcing-TOTAL.json is ~1.2MB — was
 *           the main nav cost, so parses are cached. TWO sources, chosen by env:
 *             • LOCAL (default): read from public/data via node:fs, cache keyed by mtime (an ETL rewrite
 *               bumps mtime → auto re-parse). This is dev + `next start` on your own box.
 *             • REMOTE (DATA_BASE_URL set): fetch `${DATA_BASE_URL}/<file>` over HTTP — for serverless
 *               hosts (Vercel) where the ~894MB of generated data can't ship in the function bundle and
 *               instead lives on object storage (Cloudflare R2 / S3 / any static host). Data is immutable
 *               per deploy, so a fetched file is cached for the life of the instance.
 * @limits   Server-only. Returns the SHARED parsed object — callers MUST NOT mutate it (build a new
 *           object to reshape; see lib/snapshot.js).
 * @affects  Backs the sourcing/tenders/forward/psd/events/snapshot loaders.
 */
import { readFile, stat } from "node:fs/promises";
import path from "node:path";

// DATA_BASE_URL = e.g. "https://tradepulse-data.pages.dev" (no trailing slash). Unset → local filesystem.
const REMOTE = (process.env.DATA_BASE_URL || "").replace(/\/$/, "") || null;
const LOCAL_DIR = path.join(process.cwd(), "public", "data");

// FEED_BASE_URL (optional) hosts the VOLATILE market-feed files (procurement/regulatory/price) on a
// SEPARATE store so a scheduled job can refresh them without touching — or being able to break — the
// heavy BACI trade data (map + partner tables) on DATA_BASE_URL. Unset → feed served from REMOTE too
// (backward compatible; one store). These are the files the `--tenders` ETL step regenerates.
const FEED = (process.env.FEED_BASE_URL || "").replace(/\/$/, "") || REMOTE;
const FEED_FILE = /^(awards|tenders|sellers|events|forward|psd|cpv-match)/;

export const IS_REMOTE_DATA = !!REMOTE;

// Resolve a bare filename ("sourcing-TOTAL.json") to a fetchable URL or an absolute fs path. In remote
// mode, volatile feed files go to FEED, everything else (snapshots/sourcing/countries) to REMOTE.
export function dataRef(file) {
  if (!REMOTE) return path.join(LOCAL_DIR, file);
  return `${FEED_FILE.test(file) ? FEED : REMOTE}/${file}`;
}

// Curated Layer-3 content lives in the repo's ../content dir (outside web/), so on a serverless host it
// must come from the same remote base under a content/ prefix. `sub` = "requirements/pellets-jp.json".
export function contentRef(sub) {
  return REMOTE ? `${REMOTE}/content/${sub}` : path.join(process.cwd(), "..", "content", sub);
}

const cache = new Map();   // ref -> { key, data }   (key = mtimeMs locally; absent when remote/immutable)

// Parse `ref` (a URL in REMOTE mode or an fs path in LOCAL mode) as JSON, served from the in-process
// cache when unchanged. Throws on a missing/unreadable/invalid file/response — callers keep their own
// try/catch + default.
export async function readJsonCached(ref) {
  if (ref.startsWith("http://") || ref.startsWith("https://")) {
    const hit = cache.get(ref);
    if (hit) return hit.data;                       // immutable per deploy → cache for the instance's life
    const res = await fetch(ref);
    if (!res.ok) throw new Error(`data fetch ${res.status} ${ref}`);
    const data = await res.json();
    cache.set(ref, { data });
    return data;
  }
  const { mtimeMs } = await stat(ref);
  const hit = cache.get(ref);
  if (hit && hit.key === mtimeMs) return hit.data;
  const data = JSON.parse(await readFile(ref, "utf-8"));
  cache.set(ref, { key: mtimeMs, data });
  return data;
}
