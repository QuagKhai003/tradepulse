/**
 * page.js — Layer-1 landing: search + demand map + signal feed, or a locked page (plan §7.1–7.6).
 * @context  Server component. Reads the ETL snapshot; ?hs picks the product (VN-default, ?lang=en).
 *           Covered product -> map screen; uncovered -> "coming soon, request it" (telemetry).
 * @done     Header + search; covered branch (choropleth, tiles, feed); locked branch.
 * @todo     Country drill-down (1.5), watch button (1.8).
 * @limits   Inform-never-match (Golden Rule): data only; no parties, no contacts.
 * @affects  Reads lib/snapshot + lib/catalog; renders SearchBox / WorldMap / SignalFeed / MarketTile / LockedProduct.
 */
import WorldMap from "./components/WorldMap.js";
import SignalFeed from "./components/SignalFeed.js";
import MarketTile from "./components/MarketTile.js";
import SearchBox from "./components/SearchBox.js";
import LockedProduct from "./components/LockedProduct.js";
import { loadSnapshot } from "./lib/snapshot.js";
import { lookup } from "./lib/catalog.js";
import { t } from "./lib/i18n.js";

export default async function Page({ searchParams }) {
  const sp = searchParams ? await searchParams : {};
  const lang = sp.lang === "en" ? "en" : "vi";
  const tr = t(lang);
  const snap = await loadSnapshot();

  if (!snap) {
    return <main className="page"><div className="empty">{tr.noData}</div></main>;
  }

  const hs = sp.hs || snap.hs6;
  const covered = hs === snap.hs6;                       // only the pilot vertical has data today
  const entry = lookup(hs) || { hs6: hs, name_en: hs, name_vi: hs };
  const product = covered
    ? (lang === "en" ? snap.product.name_en : snap.product.name_vi)
    : (lang === "en" ? entry.name_en : entry.name_vi);

  return (
    <main className="page">
      <header className="topbar">
        <div className="brand">
          <span className="logo">◈ TradePulse</span>
          <span className="tagline">{tr.tagline}</span>
        </div>
        <a className="langswitch" href={`?hs=${hs}&lang=${lang === "en" ? "vi" : "en"}`}>{tr.lang}</a>
      </header>

      <div className="searchrow">
        <SearchBox lang={lang} placeholder={tr.searchPlaceholder} />
      </div>

      {snap.is_sample && covered && <div className="samplebar">⚠ {tr.sample}</div>}

      <section className="subhead">
        <h1>{tr.subtitle}</h1>
        <div className="chips">
          <span className="chip">{tr.product}: <strong>{product}</strong></span>
          <span className="chip hs">HS {hs}</span>
          {covered && <span className="chip">{tr.flowImport}</span>}
          {covered && <span className="chip muted">{tr.period} {snap.latest_period}</span>}
          {covered && <a className="chip link" href={`/profiles${lang === "en" ? "?lang=en" : ""}`}>{tr.profilesLink}</a>}
          {covered && <a className="chip link" href={`/requirements${lang === "en" ? "?lang=en" : ""}`}>{tr.reqLink}</a>}
          <a className="chip link" href={`/pricing${lang === "en" ? "?lang=en" : ""}`}>{tr.pricingLink}</a>
        </div>
      </section>

      {covered ? (
        <section className="grid">
          <div className="mapcol">
            <WorldMap markets={snap.markets} />
            <div className="markets">
              <h2>{tr.marketsTitle}</h2>
              <div className="tiles">
                {snap.markets.map((m) => <MarketTile key={m.slug} m={m} lang={lang} t={tr} />)}
              </div>
            </div>
          </div>
          <SignalFeed feed={snap.feed} lang={lang} t={tr} />
        </section>
      ) : (
        <LockedProduct product={entry} lang={lang} />
      )}

      <footer className="disclaimer muted">{tr.disclaimer}</footer>
    </main>
  );
}
