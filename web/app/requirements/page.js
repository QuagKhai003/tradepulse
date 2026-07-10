/**
 * requirements/page.js — index of Layer-3 requirement pages (plan §7.5).
 * @context  Lists covered product × market qualification pages; uncovered pairs are locked
 *           (telemetry lives on the map's locked products). Qualification exists only at
 *           product × market granularity (plan §4.8) — never country-level alone.
 * @affects  Reads lib/requirements; links to /requirements/[market].
 */
import Link from "next/link";
import { loadRequirementIndex } from "../lib/requirements.js";
import { t } from "../lib/i18n.js";

export default async function RequirementsIndex({ searchParams }) {
  const sp = searchParams ? await searchParams : {};
  const lang = sp.lang === "en" ? "en" : "vi";
  const tr = t(lang);
  const qs = lang === "en" ? "?lang=en" : "";
  const pages = await loadRequirementIndex();

  return (
    <main className="page">
      <header className="topbar">
        <div className="brand">
          <Link className="logo" href={`/${qs}`}>◈ TradePulse</Link>
          <span className="tagline">{tr.tagline}</span>
        </div>
        <a className="langswitch" href={`?lang=${lang === "en" ? "vi" : "en"}`}>{tr.lang}</a>
      </header>

      <Link className="back" href={`/${qs}`}>{tr.backMap}</Link>

      <section className="drillhead">
        <h1>{tr.reqIndexTitle}</h1>
        <p className="muted small">{tr.reqIndexNote}</p>
      </section>

      <div className="reqcards">
        {pages.map((p) => (
          <Link key={p.market} className="reqcard" href={`/requirements/${p.market}${qs}`}>
            <div className="reqcard-h">{lang === "en" ? "Wood pellets" : "Viên nén gỗ"} → {lang === "en" ? p.name_en : p.name_vi}</div>
            <div className="muted small">{p.count} {tr.requirementsWord} · {tr.lastReview}: {p.last_full_review}</div>
            <div className="tile-cta">{tr.openPage} →</div>
          </Link>
        ))}
      </div>

      <footer className="disclaimer muted">{tr.disclaimerReq}</footer>
    </main>
  );
}
