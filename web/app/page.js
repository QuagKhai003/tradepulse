/**
 * page.js — home entry (server). Loads the snapshot for the chosen product and hands the covered
 * view to the interactive client hero (flow/lang toggles run client-side, no reload). Uncovered
 * products render a server-side locked "coming soon" page.
 * @limits   Inform-never-match; value/volume only.
 * @affects  Reads lib/snapshot + lib/catalog; renders HeroClient or LockedProduct.
 */
import HeroClient from "./components/HeroClient.js";
import SearchBox from "./components/SearchBox.js";
import LockedProduct from "./components/LockedProduct.js";
import { loadSnapshot } from "./lib/snapshot.js";
import { loadAwards, loadCpvMatch, loadSellers, loadTenders } from "./lib/tenders.js";
import { loadCompanies, FREE_PROFILE_LIMIT } from "./lib/companies.js";
import { getTier } from "./lib/tier.js";
import { lookup } from "./lib/catalog.js";
import { resolveLang, t, VI_ENABLED } from "./lib/i18n.js";

export default async function Page({ searchParams }) {
  const sp = searchParams ? await searchParams : {};
  const lang = resolveLang(sp.lang);
  const flow = ["export", "import"].includes(sp.flow) ? sp.flow : "import";
  const tr = t(lang);
  const snap = await loadSnapshot(sp.hs);
  const tenders = await loadTenders((snap && snap.hs6) || sp.hs);
  // Past orders (awarded contracts) + the sellers derived from them, plus any hand-curated sellers.
  const orders = await loadAwards((snap && snap.hs6) || sp.hs);
  const sellers = await loadSellers((snap && snap.hs6) || sp.hs);
  const cpv = await loadCpvMatch((snap && snap.hs6) || sp.hs);
  const companies = await loadCompanies((snap && snap.hs6) || sp.hs);
  const paid = (await getTier()) === "paid";
  const curatedAll = (companies?.companies || []).filter((c) => c.role === "seller");
  // Free tier opens the first few curated profiles; the gate is decided server-side, never in the client.
  const curatedSellers = paid ? curatedAll : curatedAll.slice(0, FREE_PROFILE_LIMIT);
  if (!snap && !sp.hs) return <main className="page"><div className="empty">{tr.noData}</div></main>;

  const hs = (snap && snap.hs6) || sp.hs || "440131";
  const covered = !!snap && snap.countries?.length > 0;

  if (covered) {
    return <HeroClient snapshot={snap} tenders={tenders} sellers={sellers} orders={orders}
                       curatedSellers={curatedSellers} cpv={cpv} hs={hs} initialLang={lang}
                       initialFlow={flow} />;
  }

  // uncovered product -> locked "coming soon" (server-rendered)
  const entry = lookup(hs) || { hs6: hs, name_en: hs, name_vi: hs };
  const product = lang === "en" ? entry.name_en : entry.name_vi;
  const langHref = `?hs=${hs}&lang=${lang === "en" ? "vi" : "en"}`;
  return (
    <main className="page">
      <header className="topbar">
        <div className="brand"><span className="logo">◈ TradePulse</span><span className="tagline">{tr.tagline}</span></div>
        {VI_ENABLED && <a className="langswitch" href={langHref}>{tr.lang}</a>}
      </header>
      <div className="searchrow"><SearchBox lang={lang} placeholder={tr.searchPlaceholder} /></div>
      <section className="subhead">
        <div className="chips">
          <span className="chip">{tr.product}: <strong>{product}</strong></span>
          <span className="chip hs">HS {hs}</span>
        </div>
      </section>
      <LockedProduct product={entry} lang={lang} />
      <footer className="disclaimer">{tr.disclaimer}</footer>
    </main>
  );
}
