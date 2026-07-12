"use client";
/**
 * HeroClient.js — the interactive home hero (client state, no page reloads).
 * @context  Holds flow (export/import), lang (vi/en) and feed sort as client state — toggling any
 *           updates the globe/feed/labels instantly (no navigation, no globe remount). Toggles are
 *           animated segmented pills. Product change navigates (different data) via search, keeping lang.
 * @limits   Presentation + state; data comes pre-loaded from the server page.
 * @affects  Wraps GlobeHero / TopCountries / GlobalFeed / SearchBox / BrowseCountries / SortMenu.
 */
import { useState } from "react";
import GlobeHero from "./GlobeHero.js";
import GlobalFeed from "./GlobalFeed.js";
import TopCountries from "./TopCountries.js";
import SearchBox from "./SearchBox.js";
import BrowseCountries from "./BrowseCountries.js";
import SortMenu from "./SortMenu.js";
import MotionPanel from "./MotionPanel.js";
import { t } from "../lib/i18n.js";

// Segmented pill with a CSS-transitioned sliding fill (no motion lib). Options are equal-width, so the
// indicator just translates to the active index.
function Segmented({ options, value, onChange, size = "md" }) {
  const idx = Math.max(0, options.findIndex((o) => o.v === value));
  return (
    <div className={`seg seg-${size}`}>
      <span className="seg-ind" style={{ width: `calc((100% - 6px) / ${options.length})`, transform: `translateX(${idx * 100}%)` }} />
      {options.map((o) => (
        <button key={o.v} type="button" className={`seg-opt ${value === o.v ? "on" : ""}`} onClick={() => onChange(o.v)}>
          <span className="seg-label">{o.label}</span>
        </button>
      ))}
    </div>
  );
}

export default function HeroClient({ snapshot, hs, initialLang, initialFlow }) {
  const [lang, setLang] = useState(initialLang);
  const [flow, setFlow] = useState(initialFlow);
  const [sort, setSort] = useState("value-desc");
  const [freq, setFreq] = useState("A");
  const tr = t(lang);
  const metric = flow === "export" ? "exp" : "imp";
  const isTotal = hs === "TOTAL";
  // Only offer the grain toggle when this product actually has quarterly data (bounded to core products).
  const hasQuarterly = snapshot.countries.some((c) => c.exp?.by_freq?.Q || c.imp?.by_freq?.Q);
  const product = lang === "en" ? snapshot.product.name_en : snapshot.product.name_vi;
  const updated = snapshot.generated_at
    ? new Date(snapshot.generated_at).toLocaleDateString(lang === "en" ? "en-GB" : "vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" })
    : snapshot.latest_period;

  const flowToggle = (
    <Segmented idBase="flow-ind" value={flow} onChange={setFlow} size="sm"
      options={[{ v: "export", label: tr.flowExport }, { v: "import", label: tr.flowImport }]} />
  );
  const freqToggle = hasQuarterly ? (
    <Segmented idBase="freq-ind" value={freq} onChange={setFreq} size="sm"
      options={[{ v: "A", label: tr.freqYear }, { v: "Q", label: tr.freqQuarter }]} />
  ) : null;
  const feedTools = (<><SortMenu value={sort} onChange={setSort} t={tr} />{freqToggle}{flowToggle}</>);

  return (
    <main className="home">
      <section className="hero">
        <div className="hero-glow" aria-hidden />
        <div className="hero-globe-bg"><GlobeHero countries={snapshot.countries} metric={metric} hs={hs} lang={lang} freq={freq} /></div>

        <header className="hero-top">
          <div className="brand"><span className="logo">◈ TradePulse</span></div>
          <div className="hero-search-top">
            <SearchBox lang={lang} placeholder={tr.searchPlaceholder} />
            <BrowseCountries countries={snapshot.countries} lang={lang} hs={hs} label={tr.browseCountries} />
          </div>
          <nav className="hero-top-right">
            <a className="authbtn ghost" href="#">{tr.login}</a>
            <a className="authbtn primary" href="#">{tr.signup}</a>
            <Segmented idBase="lang-ind" value={lang} onChange={setLang}
              options={[{ v: "vi", label: "VI" }, { v: "en", label: "EN" }]} />
          </nav>
        </header>

        <MotionPanel from="left" className="panel-col left glasscol">
          <TopCountries countries={snapshot.countries} lang={lang} t={tr} hs={hs} freq={freq} />
        </MotionPanel>

        <MotionPanel from="right" delay={0.05} className="panel-col right glasscol">
          <GlobalFeed countries={snapshot.countries} flow={flow} freq={freq} lang={lang} t={tr} hs={hs} sort={sort} tools={feedTools} />
        </MotionPanel>

        <div className="hero-foot">
          {!isTotal && <span className="chip on-dark strong">{product}</span>}
          <span className="foot-hint">{tr.dataUpdated} {updated} · <b className="num">{snapshot.countries.length}</b> {tr.allCountries}</span>
        </div>
        {snapshot.is_sample && <div className="hero-sample">⚠ {tr.sample}</div>}
      </section>
    </main>
  );
}
