/**
 * companies.js — load curated Layer-2 profiles (plan §7.4). Names + public sources only.
 * @context  Reads repo content/companies/<vertical>.json (tracked source, hand-curated — not
 *           generated). Golden Rule: never contacts, never matching. Each profile cites a public
 *           source + verified date, exactly like the requirement pages.
 * @limits   Server-only (fs). Presentation gating (free vs paid) is applied in the page.
 * @affects  Consumed by app/profiles/page.js.
 */
import { contentRef, readJsonCached } from "./jsoncache.js";

// Free tier shows this many full profiles; the rest are blurred until upgrade (plan §11).
export const FREE_PROFILE_LIMIT = 3;

export async function loadCompanies(hs6 = "440131") {
  try {
    const data = await readJsonCached(contentRef("companies/pellets.json"));
    return data.hs6 === hs6 ? data : null;
  } catch {
    return null;
  }
}
