/**
 * page.js — map-first landing: world signal map + export/import/all toggle + global feed (plan §7.1).
 * @context  Server component. The map is the hero: every country coloured by its export OR import
 *           signal for the selected product; a global feed lists moderate+ signals both flows; the
 *           flow toggle (?flow) and product search (?hs) reshape it. Click a country to drill in.
 * @done     Map + toggle + top-country tiles (both flows) + global feed + search; locked for uncovered HS.
 * @todo     Deeper country view + qualifications tab per flow (batch 3.4/3.5).
 * @limits   Inform-never-match; value/volume only.
 * @affects  Reads lib/snapshot + lib/catalog; renders WorldMap / GlobalFeed / CountryTile / SearchBox / LockedProduct.
 */
import WorldMap from "./components/WorldMap.js";
import GlobalFeed from "./components/GlobalFeed.js";
import CountryTile from "./components/CountryTile.js";
import SearchBox from "./components/SearchBox.js";
import LockedProduct from "./components/LockedProduct.js";
import { loadSnapshot } from "./lib/snapshot.js";
import { lookup } from "./lib/catalog.js";
import { t } from "./lib/i18n.js";

const FLOWS = ["all", "export", "import"];

export default async function Page({ searchParams }) {
  const sp = searchParams ? await searchParams : {};
  const lang = sp.lang === "en" ? "en" : "vi";
  const flow = FLOWS.includes(sp.flow) ? sp.flow : "all";
  const tr = t(lang);
  const snap = await loadSnapshot(sp.hs);       // no hs -> landing default (snapshot.json)
  if (!snap && !sp.hs) return <main className="page"><div className="empty">{tr.noData}</div></main>;

  const hs = (snap && snap.hs6) || sp.hs || "440131";
  const covered = !!snap && snap.countries?.length > 0;
  const entry = lookup(hs) || { hs6: hs, name_en: hs, name_vi: hs };
  const product = covered
    ? (lang === "en" ? snap.product.name_en : snap.product.name_vi)
    : (lang === "en" ? entry.name_en : entry.name_vi);
  const qsl = lang === "en" ? "&lang=en" : "";

  const metric = flow === "export" ? "exp" : "imp";
  const emphasis = flow === "export" ? "exp" : flow === "import" ? "imp" : null;
  const flowVal = (c) => flow === "export" ? (c.exp?.value_usd || 0)
    : flow === "import" ? (c.imp?.value_usd || 0)
    : Math.max(c.exp?.value_usd || 0, c.imp?.value_usd || 0);
  const top = covered ? [...snap.countries].sort((a, b) => flowVal(b) - flowVal(a)).slice(0, 12) : [];

  return (
    <main className="page">
      <header className="topbar">
        <div className="brand">
          <span className="logo">◈ TradePulse</span>
          <span className="tagline">{tr.tagline}</span>
        </div>
        <a className="langswitch" href={`?flow=${flow}&hs=${hs}&lang=${lang === "en" ? "vi" : "en"}`}>{tr.lang}</a>
      </header>

      <div className="searchrow"><SearchBox lang={lang} placeholder={tr.searchPlaceholder} /></div>

      {snap?.is_sample && covered && <div className="samplebar">⚠ {tr.sample}</div>}

      <section className="subhead">
        <h1>{tr.subtitle}</h1>
        <div className="chips">
          <span className="chip">{tr.product}: <strong>{product}</strong></span>
          <span className="chip hs">HS {hs}</span>
          {covered && <span className="chip muted">{tr.period} {snap.latest_period}</span>}
          {hs === "440131" && <a className="chip link" href={`/profiles${lang === "en" ? "?lang=en" : ""}`}>{tr.profilesLink}</a>}
          {hs === "440131" && <a className="chip link" href={`/requirements${lang === "en" ? "?lang=en" : ""}`}>{tr.reqLink}</a>}
          <a className="chip link" href={`/pricing${lang === "en" ? "?lang=en" : ""}`}>{tr.pricingLink}</a>
        </div>
      </section>

      {covered ? (
        <>
          <div className="flowbar">
            {FLOWS.map((f) => (
              <a key={f} className={`flowbtn ${f === flow ? "on" : ""}`} href={`/?flow=${f}&hs=${hs}${qsl}`}>
                {f === "all" ? tr.flowAll : f === "export" ? tr.flowExport : tr.flowImport}
              </a>
            ))}
          </div>

          <section className="grid">
            <div className="mapcol">
              <WorldMap countries={snap.countries} metric={metric} lang={lang} />
              <p className="maphint muted">{tr.clickCountry}</p>
              <div className="markets">
                <h2>{tr.topCountries} · {snap.countries.length} {tr.allCountries}</h2>
                <div className="ctiles">
                  {top.map((c) => <CountryTile key={c.code} c={c} lang={lang} t={tr} emphasis={emphasis} hs={hs} />)}
                </div>
              </div>
            </div>
            <GlobalFeed feed={snap.feed} flow={flow} lang={lang} t={tr} hs={hs} />
          </section>
        </>
      ) : (
        <LockedProduct product={entry} lang={lang} />
      )}

      <footer className="disclaimer muted">{tr.disclaimer}</footer>
    </main>
  );
}
