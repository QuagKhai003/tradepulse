"use client";
/**
 * HeroClient.js — the interactive home hero (client state, no page reloads).
 * @context  Holds flow (export/import) + lang (vi/en) as client state, so toggling them updates the
 *           globe colour, feed, top-20 and labels INSTANTLY — no navigation, no globe remount. Both
 *           toggles are animated segmented pills (framer-motion sliding fill). Product change still
 *           navigates (different data) via the search box, preserving the current language.
 * @limits   Presentation + state; data comes pre-loaded from the server page.
 * @affects  Wraps GlobeHero / TopCountries / GlobalFeed / SearchBox / MotionPanel.
 */
import { useState } from "react";
import { motion } from "framer-motion";
import GlobeHero from "./GlobeHero.js";
import GlobalFeed from "./GlobalFeed.js";
import TopCountries from "./TopCountries.js";
import SearchBox from "./SearchBox.js";
import MotionPanel from "./MotionPanel.js";
import { t } from "../lib/i18n.js";

function Segmented({ options, value, onChange, idBase, size = "md" }) {
  return (
    <div className={`seg seg-${size}`}>
      {options.map((o) => (
        <button key={o.v} type="button" className={`seg-opt ${value === o.v ? "on" : ""}`} onClick={() => onChange(o.v)}>
          {value === o.v && (
            <motion.span layoutId={idBase} className="seg-ind" transition={{ type: "spring", stiffness: 430, damping: 34 }} />
          )}
          <span className="seg-label">{o.label}</span>
        </button>
      ))}
    </div>
  );
}

export default function HeroClient({ snapshot, hs, initialLang, initialFlow }) {
  const [lang, setLang] = useState(initialLang);
  const [flow, setFlow] = useState(initialFlow);
  const tr = t(lang);
  const metric = flow === "export" ? "exp" : "imp";
  const isTotal = hs === "TOTAL";
  const product = lang === "en" ? snapshot.product.name_en : snapshot.product.name_vi;

  const flowToggle = (
    <Segmented idBase="flow-ind" value={flow} onChange={setFlow} size="sm"
      options={[{ v: "export", label: tr.flowExport }, { v: "import", label: tr.flowImport }]} />
  );

  return (
    <main className="home">
      <section className="hero">
        <div className="hero-glow" aria-hidden />
        <div className="hero-globe-bg"><GlobeHero countries={snapshot.countries} metric={metric} hs={hs} lang={lang} /></div>

        <header className="hero-top">
          <div className="brand"><span className="logo">◈ TradePulse</span><span className="tagline">{tr.tagline}</span></div>
          <div className="hero-search-top"><SearchBox lang={lang} placeholder={tr.searchPlaceholder} /></div>
          <nav className="hero-top-right">
            <a className="authbtn ghost" href="#">{tr.login}</a>
            <a className="authbtn primary" href="#">{tr.signup}</a>
            <Segmented idBase="lang-ind" value={lang} onChange={setLang}
              options={[{ v: "vi", label: "VI" }, { v: "en", label: "EN" }]} />
          </nav>
        </header>

        <MotionPanel from="left" className="panel-col left glasscol">
          <TopCountries countries={snapshot.countries} lang={lang} t={tr} hs={hs} />
        </MotionPanel>

        <MotionPanel from="right" delay={0.05} className="panel-col right glasscol">
          <GlobalFeed feed={snapshot.feed} flow={flow} lang={lang} t={tr} hs={hs} toggle={flowToggle} />
        </MotionPanel>

        <div className="hero-foot">
          <span className="chip on-dark strong">{product}</span>
          {!isTotal && <span className="chip hs">HS {hs}</span>}
          <span className="foot-hint">{tr.clickCountry} · <b className="num">{snapshot.countries.length}</b> {tr.allCountries}</span>
        </div>
        {snapshot.is_sample && <div className="hero-sample">⚠ {tr.sample}</div>}
      </section>
    </main>
  );
}
