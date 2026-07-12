/**
 * prepare-data.mjs — make `npm run dev` self-sufficient (auto-fetch the data snapshot).
 * @context  Runs before `next dev` (npm `predev` hook). Ensures web/public/data/snapshot.json
 *           exists so the app has data with ONE command. Policy:
 *             • missing snapshot  -> run the ETL and WAIT (first render needs data)
 *             • stale (> MAX_AGE) -> refresh in the BACKGROUND (dev starts instantly)
 *             • fresh             -> skip
 *           Never fails the dev start — a network/ETL error just leaves the existing snapshot.
 * @limits   Node script (build tooling). Spawns Python (`python -m tradepulse_etl --source comtrade,census --freq AQ`).
 * @affects  Wired via package.json "predev"; `--force` refreshes regardless of age.
 */
import { spawn, spawnSync } from "node:child_process";
import { existsSync, statSync } from "node:fs";
import path from "node:path";
import process from "node:process";

const MAX_AGE_HOURS = 24 * 7;   // trade data updates monthly; refresh weekly (the ETL is heavy)
const force = process.argv.includes("--force");
const SNAPSHOT = path.join(process.cwd(), "public", "data", "snapshot.json");
const ETL_DIR = path.join(process.cwd(), "..", "etl");
const PY = process.platform === "win32" ? "python" : "python3";
// Everyday refresh = LIGHT: Comtrade annual (global) + US Census, merged + incremental (only the
// revisable window re-fetches). Census skips cleanly without CENSUS_API_KEY. Quarterly (the M/Q/A
// toggle) is a heavier, deliberate run: add `--freq AQ`. See docs/DATA_SOURCES.md.
// baci = local CEPII bulk file (history, no API throttle); skips cleanly if data/baci is empty.
const ETL_ARGS = ["-m", "tradepulse_etl", "--source", "baci,comtrade,census,eurostat,hmrc", "--freq", "A"];

function ageHours(p) {
  return (Date.now() - statSync(p).mtimeMs) / 3_600_000;
}

const missing = !existsSync(SNAPSHOT);
const stale = !missing && ageHours(SNAPSHOT) > MAX_AGE_HOURS;

if (!force && !missing && !stale) {
  console.log(`[prepare-data] snapshot fresh (< ${MAX_AGE_HOURS}h) — skipping fetch.`);
  process.exit(0);
}

if (missing || force) {
  // Block: the app has no data yet (or an explicit refresh was asked for).
  console.log(`[prepare-data] ${missing ? "no snapshot" : "--force"} — fetching real data (this can take a moment)…`);
  const r = spawnSync(PY, ETL_ARGS, { cwd: ETL_DIR, stdio: "inherit" });
  if (r.status !== 0) {
    console.warn("[prepare-data] ETL did not complete; starting anyway (app will show 'run ETL' if empty).");
  }
  process.exit(0);
}

// Stale but present: refresh in the background so dev starts immediately.
console.log(`[prepare-data] snapshot stale (> ${MAX_AGE_HOURS}h) — refreshing in the background…`);
const child = spawn(PY, ETL_ARGS, { cwd: ETL_DIR, detached: true, stdio: "ignore" });
child.on("error", () => console.warn("[prepare-data] background refresh could not start; using existing snapshot."));
child.unref();
process.exit(0);
