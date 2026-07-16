/**
 * jsoncache.js — in-process cache for the ETL data files (perf).
 * @context  The JSON in public/data is STATIC within a running server (rewritten only by the ETL batch).
 *           Re-reading + re-parsing it on every navigation — sourcing-TOTAL.json is ~1.2MB — made route
 *           changes / country browse / product search feel slow. Cache the parsed object per path, keyed
 *           by mtime: a navigation to an already-seen file becomes a stat() instead of a full parse. An
 *           ETL rewrite bumps mtime, so the next read re-parses (stays correct, no restart needed).
 * @limits   Server-only (node:fs). Returns the SHARED parsed object — callers MUST NOT mutate it (build
 *           a new object if you need to reshape; see lib/snapshot.js).
 * @affects  Backs the sourcing/tenders/forward/psd/events/snapshot loaders.
 */
import { readFile, stat } from "node:fs/promises";

const cache = new Map();   // absolute path -> { mtimeMs, data }

// Parse `p` as JSON, served from cache when the file is unchanged since last read. Throws on a
// missing/unreadable/invalid file — callers keep their own try/catch + default.
export async function readJsonCached(p) {
  const { mtimeMs } = await stat(p);
  const hit = cache.get(p);
  if (hit && hit.mtimeMs === mtimeMs) return hit.data;
  const data = JSON.parse(await readFile(p, "utf-8"));
  cache.set(p, { mtimeMs, data });
  return data;
}
