/**
 * market/[slug]/page.js — country drill-down (plan §7.3).
 * @context  Click a destination market -> within-country view: top partner countries with shares +
 *           YoY, and a sourcing chart over time. SSR from the same snapshot (seam). VN highlighted.
 * @limits   Inform-never-match: shows public trade data only. Importer-reported side.
 * @affects  Reads lib/snapshot; renders PartnerTable + SourcingChart.
 */
import Link from "next/link";
import PartnerTable from "../../components/PartnerTable.js";
import SourcingChart from "../../components/SourcingChart.js";
import WatchButton from "../../components/WatchButton.js";
import { loadSnapshot } from "../../lib/snapshot.js";
import { t } from "../../lib/i18n.js";
import { fmtPct, fmtUSD, bandArrow, bandColor, bandLabel } from "../../lib/format.js";

export default async function MarketPage({ params, searchParams }) {
  const { slug } = await params;
  const sp = searchParams ? await searchParams : {};
  const lang = sp.lang === "en" ? "en" : "vi";
  const tr = t(lang);
  const snap = await loadSnapshot();
  const qs = lang === "en" ? "?lang=en" : "";

  const m = snap?.markets.find((x) => x.slug === slug);
  if (!snap || !m) {
    return (
      <main className="page">
        <div className="empty">404 · <Link href={`/${qs}`}>{tr.backMap}</Link></div>
      </main>
    );
  }

  const marketName = lang === "en" ? m.name_en : m.name_vi;
  const product = lang === "en" ? snap.product.name_en : snap.product.name_vi;

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

      {snap.is_sample && <div className="samplebar">⚠ {tr.sample}</div>}

      <section className="drillhead">
        <h1>{marketName} · {product}</h1>
        <div className="chips">
          <span className="chip hs">HS {snap.hs6}</span>
          <span className="tile-badge" style={{ background: bandColor(m.band, m.direction) }}>
            {bandArrow(m.band, m.direction)} {bandLabel(m.band, lang)}
          </span>
          <span className="chip">{fmtUSD(m.value_usd)} · {m.band !== "none" ? fmtPct(m.yoy_delta) : tr.noSignal}</span>
          <span className="chip muted">{tr.period} {m.period}{m.published_date ? ` · ${tr.published} ${m.published_date}` : ""}</span>
        </div>
        <p className="muted small">{tr.flowImport}</p>
        <div className="actions">
          <WatchButton watchKey={`signal:${snap.hs6}:${slug}`} meta={{ hs6: snap.hs6, market: slug, kind: "signal" }}
                       labelOff={tr.watch} labelOn={tr.watching} />
          {["jp", "kr", "eu"].includes(slug) && (
            <a className="chip link" href={`/requirements/${slug}${qs}`}>{tr.reqLink}</a>
          )}
        </div>
      </section>

      {m.partners && m.partners.length > 0 ? (
        <section className="drillgrid">
          <div className="panel">
            <h2>{tr.sourcingTitle}</h2>
            <PartnerTable partners={m.partners} lang={lang} t={tr} />
          </div>
          <div className="panel">
            <h2>{tr.sourcingOverTime}</h2>
            {m.sourcing && <SourcingChart sourcing={m.sourcing} lang={lang} />}
          </div>
        </section>
      ) : (
        <div className="locked"><p className="locked-p">{tr.noPartners}</p></div>
      )}

      <footer className="disclaimer muted">{tr.disclaimer}</footer>
    </main>
  );
}
