/**
 * profiles/page.js — Layer-2 buyer/seller directory (plan §7.4).
 * @context  SSR list of curated public profiles for the pilot vertical. Names + cited sources only;
 *           no contacts (Golden Rule). Free tier shows FREE_PROFILE_LIMIT full, rest blurred (§11).
 * @limits   Inform-never-match: this page never introduces parties or brokers a contact.
 * @affects  Reads lib/companies; renders CompanyCard.
 */
import Link from "next/link";
import CompanyCard from "../components/CompanyCard.js";
import { loadCompanies, FREE_PROFILE_LIMIT } from "../lib/companies.js";
import { getTier } from "../lib/tier.js";
import { t } from "../lib/i18n.js";

export default async function ProfilesPage({ searchParams }) {
  const sp = searchParams ? await searchParams : {};
  const lang = sp.lang === "en" ? "en" : "vi";
  const tr = t(lang);
  const qs = lang === "en" ? "?lang=en" : "";
  const data = await loadCompanies();

  if (!data) {
    return <main className="page"><div className="empty">{tr.noProfiles}</div></main>;
  }

  const paid = (await getTier()) === "paid";
  const buyers = data.companies.filter((c) => c.role === "buyer");
  const sellers = data.companies.filter((c) => c.role === "seller");
  // Free-tier gating: first N open, rest blurred; paid unlocks all (plan §11).
  const openIds = new Set(
    (paid ? data.companies : data.companies.slice(0, FREE_PROFILE_LIMIT)).map((c) => c.id)
  );

  const section = (title, list) => (
    <section className="prof-section">
      <h2>{title} <span className="muted">({list.length})</span></h2>
      <div className="companies">
        {list.map((c) => (
          <CompanyCard key={c.id} c={c} lang={lang} t={tr} locked={!openIds.has(c.id)} />
        ))}
      </div>
    </section>
  );

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
        <h1>{tr.profilesTitle} · {lang === "en" ? "Wood pellets" : "Viên nén gỗ"}</h1>
        <p className="muted small">{tr.profilesNote}</p>
      </section>

      {data.is_sample && <div className="samplebar">⚠ {tr.sampleProfiles}</div>}

      {section(tr.buyers, buyers)}
      {section(tr.sellers, sellers)}

      <footer className="disclaimer muted">{tr.disclaimer}</footer>
    </main>
  );
}
