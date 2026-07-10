/**
 * route.js — POST /api/watch: record a watch/unwatch (plan §7.7).
 * @context  The recurring-revenue engine's capture point. Appends to ../data/watches.ndjson; an
 *           ETL step turns watches + alert events into deliveries (batch: email/Zalo). No login yet.
 * @limits   Append-only NDJSON, best-effort. Never blocks the UI.
 * @affects  Called by components/WatchButton.js.
 */
import { appendFile, mkdir } from "node:fs/promises";
import path from "node:path";

const LOG = path.join(process.cwd(), "..", "data", "watches.ndjson");

export async function POST(request) {
  let body = {};
  try { body = await request.json(); } catch { /* ignore */ }
  const entry = {
    ts: new Date().toISOString(),
    key: String(body.key || ""),
    action: body.action === "unwatch" ? "unwatch" : "watch",
    hs6: body.hs6 ? String(body.hs6) : null,
    market: body.market ? String(body.market) : null,
    kind: body.kind ? String(body.kind) : null,
  };
  try {
    await mkdir(path.dirname(LOG), { recursive: true });
    await appendFile(LOG, JSON.stringify(entry) + "\n", "utf-8");
  } catch {
    return Response.json({ ok: false }, { status: 200 });
  }
  return Response.json({ ok: true });
}
