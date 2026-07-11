/**
 * QualPanel.js — market-entry qualifications for a product×country (plan §7.5, Layer 3 entry point).
 * @context  On a country drill, shows what it takes to bring the product INTO that market (the
 *           exporter's gate). Covered pairs (pellets→JP/KR/EU) show the snapshot + a sourced teaser
 *           + a link to the full checklist; uncovered pairs show "request it" (demand telemetry §7.6).
 * @limits   Inform-never-match; every shown item is source-backed (loader drops unsourced).
 * @affects  Rendered by country/[code]/page.js. Reads lib/requirements.
 */
import Link from "next/link";
import RequestQual from "./RequestQual.js";
import { loadRequirement } from "../lib/requirements.js";

const REQ_MARKET = { 392: "jp", 410: "kr", 97: "eu" };
const MANDATORY = { "yes": "req-yes", "de-facto": "req-def", "phasing-in": "req-phase" };

export default async function QualPanel({ hs, code, product, country, lang, t }) {
  const slug = hs === "440131" ? REQ_MARKET[code] : null;
  const d = slug ? await loadRequirement(slug) : null;
  const qs = lang === "en" ? "?lang=en" : "";

  if (!d) {
    return (
      <section className="panel qual">
        <h2>{t.qualTitle}</h2>
        <RequestQual hs={hs} market={String(code)} product={product} country={country} lang={lang} />
      </section>
    );
  }

  const snapshot = lang === "en" ? d.snapshot_en : d.snapshot_vi;
  const items = d.requirements.slice(0, 3);
  return (
    <section className="panel qual">
      <h2>{t.qualTitle} <span className="muted">· {product} → {country}</span></h2>
      <p className="muted small">{t.qualEnter} · {t.lastReview}: {d.last_full_review}</p>
      <p>{snapshot}</p>
      <ul className="qual-list">
        {items.map((r) => (
          <li key={r.seq}>
            <span className={`req-badge ${MANDATORY[r.mandatory] || "req-def"}`}>{r.mandatory}</span>
            <span className="qual-text">{lang === "en" ? r.text_en : r.text_vi}</span>
            <a href={r.source_url} target="_blank" rel="noopener noreferrer">{r.source}</a>
            <span className="muted small"> · {r.verified_date}</span>
          </li>
        ))}
      </ul>
      <Link className="chip link" href={`/requirements/${slug}${qs}`}>{t.qualViewFull}</Link>
    </section>
  );
}
