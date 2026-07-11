/**
 * page.js — immersive map-first landing: a real 3D signal globe hero + global feed (plan §7.1).
 * @context  Server component. The hero is a dark, cinematic WebGL globe (GlobeHero) coloured by the
 *           selected product+flow signal; a glass rail carries the headline, search, flow toggle,
 *           legend and the live feed. Below the fold: top-country tiles on the light system.
 *           Click a country (globe or feed) to drill in. Uncovered products show a locked page.
 * @limits   Inform-never-match; value/volume only.
 * @affects  Reads lib/snapshot + lib/catalog; renders GlobeHero / GlobalFeed / CountryTile / Legend / SearchBox.
 */
import GlobeHero from "./components/GlobeHero.js";
import GlobalFeed from "./components/GlobalFeed.js";
import TopCountries from "./components/TopCountries.js";
import SearchBox from "./components/SearchBox.js";
import LockedProduct from "./components/LockedProduct.js";
import { loadSnapshot } from "./lib/snapshot.js";
import { lookup } from "./lib/catalog.js";
import { t } from "./lib/i18n.js";

const FLOWS = ["export", "import"];   // only import/export; import = demand (the app's core)

export default async function Page({ searchParams }) {
  const sp = searchParams ? await searchParams : {};
  const lang = sp.lang === "en" ? "en" : "vi";
  const flow = FLOWS.includes(sp.flow) ? sp.flow : "import";
  const tr = t(lang);
  const snap = await loadSnapshot(sp.hs);
  if (!snap && !sp.hs) return <main className="page"><div className="empty">{tr.noData}</div></main>;

  const hs = (snap && snap.hs6) || sp.hs || "440131";
  const covered = !!snap && snap.countries?.length > 0;
  const entry = lookup(hs) || { hs6: hs, name_en: hs, name_vi: hs };
  const product = covered
    ? (lang === "en" ? snap.product.name_en : snap.product.name_vi)
    : (lang === "en" ? entry.name_en : entry.name_vi);
  const qsl = lang === "en" ? "&lang=en" : "";
  const langHref = `?flow=${flow}&hs=${hs}&lang=${lang === "en" ? "vi" : "en"}`;

  if (!covered) {
    return (
      <main className="page">
        <header className="topbar">
          <div className="brand"><span className="logo">◈ TradePulse</span><span className="tagline">{tr.tagline}</span></div>
          <a className="langswitch" href={langHref}>{tr.lang}</a>
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

  const metric = flow === "export" ? "exp" : "imp";
  const flowLabel = (f) => f === "export" ? tr.flowExport : tr.flowImport;
  const isTotal = hs === "TOTAL";

  const flowToggle = (
    <div className="flowbar dark">
      {FLOWS.map((f) => (
        <a key={f} className={`flowbtn ${f === flow ? "on" : ""}`} href={`/?flow=${f}&hs=${hs}${qsl}`}>{flowLabel(f)}</a>
      ))}
    </div>
  );

  return (
    <main className="home">
      <section className="hero">
        <div className="hero-glow" aria-hidden />

        <header className="hero-top">
          <div className="brand"><span className="logo">◈ TradePulse</span><span className="tagline">{tr.tagline}</span></div>
          <div className="hero-search-top"><SearchBox lang={lang} placeholder={tr.searchPlaceholder} /></div>
          <div className="hero-top-right">
            <span className="chip on-dark strong">{product}</span>
            {!isTotal && <span className="chip hs">HS {hs}</span>}
            <span className="chip on-dark muted">{snap.latest_period}</span>
            {hs === "440131" && <a className="chip link on-dark" href={`/profiles${lang === "en" ? "?lang=en" : ""}`}>{tr.profilesLink}</a>}
            {hs === "440131" && <a className="chip link on-dark" href={`/requirements${lang === "en" ? "?lang=en" : ""}`}>{tr.reqLink}</a>}
            <a className="chip link on-dark" href={`/pricing${lang === "en" ? "?lang=en" : ""}`}>{tr.pricingLink}</a>
            <a className="langswitch on-dark" href={langHref}>{tr.lang}</a>
          </div>
        </header>

        <div className="hero-body">
          <aside className="glasscol">
            <TopCountries countries={snap.countries} lang={lang} t={tr} hs={hs} />
          </aside>

          <div className="hero-globe">
            <GlobeHero countries={snap.countries} metric={metric} hs={hs} lang={lang} />
            <p className="hero-hint">{tr.clickCountry} · <span className="num">{snap.countries.length}</span> {tr.allCountries}</p>
            {snap.is_sample && <div className="hero-sample">⚠ {tr.sample}</div>}
          </div>

          <aside className="glasscol">
            <GlobalFeed feed={snap.feed} flow={flow} lang={lang} t={tr} hs={hs} toggle={flowToggle} />
          </aside>
        </div>
      </section>
    </main>
  );
}
