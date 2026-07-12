/**
 * country/[code]/page.js — country drill-down: its export + import signals, then deeper links.
 * @context  Click a country on the map/feed -> this view: both-flow value + YoY band + history, plus
 *           links to the qualification page (if covered) and the profiles directory (plan §7.3–7.5).
 * @limits   Inform-never-match; value/volume only.
 * @affects  Reads lib/snapshot; renders WatchButton.
 */
import Link from "next/link";
import WatchButton from "../../components/WatchButton.js";
import PartnerTable from "../../components/PartnerTable.js";
import SourcingChart from "../../components/SourcingChart.js";
import QualPanel from "../../components/QualPanel.js";
import { loadSnapshot } from "../../lib/snapshot.js";
import { loadSourcing } from "../../lib/sourcing.js";
import { t } from "../../lib/i18n.js";
import { bandArrow, bandColor, bandLabel, fmtPct, fmtPeriod, fmtUSD } from "../../lib/format.js";

function FlowPanel({ title, slot, t: tr, lang }) {
  if (!slot) return <div className="panel"><h2>{title}</h2><p className="muted">—</p></div>;
  const color = bandColor(slot.band, slot.direction);
  const hasSig = slot.band && slot.band !== "none";
  const hist = slot.history || [];
  const max = Math.max(1, ...hist.map((h) => h.value_usd));
  return (
    <div className="panel">
      <h2>{title}</h2>
      <div className="bigval">{fmtUSD(slot.value_usd)}</div>
      <div className="bigmeta">
        {hasSig
          ? <span className="cband" style={{ color }}>{bandArrow(slot.band, slot.direction)} {bandLabel(slot.band, "vi")} · {fmtPct(slot.yoy_delta)}</span>
          : <span className="muted">{tr.noSignal}</span>}
        <span className="muted"> · {fmtPeriod(slot.period, lang)}</span>
      </div>
      <div className="spark">
        {hist.map((h) => (
          <div key={h.period} className="spark-bar" title={`${h.period}: ${fmtUSD(h.value_usd)}`}>
            <div style={{ height: `${Math.round((h.value_usd / max) * 100)}%`, background: color }} />
            <span className="spark-x muted">{h.period.replace("-", " ")}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default async function CountryPage({ params, searchParams }) {
  const { code } = await params;
  const sp = searchParams ? await searchParams : {};
  const lang = sp.lang === "en" ? "en" : "vi";
  const tr = t(lang);
  const snap = await loadSnapshot(sp.hs);
  const hs = (snap && snap.hs6) || sp.hs || "440131";
  const qs = `?hs=${hs}${lang === "en" ? "&lang=en" : ""}`;
  const backHome = `/?hs=${hs}${lang === "en" ? "&lang=en" : ""}`;
  const c = snap?.countries.find((x) => String(x.code) === String(code));

  if (!snap || !c) return <main className="page"><div className="empty">404 · <Link href={backHome}>{tr.backMap}</Link></div></main>;

  const name = lang === "en" ? c.name_en : c.name_vi;
  const product = lang === "en" ? snap.product.name_en : snap.product.name_vi;
  const isPellets = hs === "440131";
  const sourcing = (await loadSourcing(hs))?.[String(c.code)] || null;

  return (
    <main className="page">
      <header className="topbar">
        <div className="brand"><Link className="logo" href={backHome}>◈ TradePulse</Link><span className="tagline">{tr.tagline}</span></div>
        <a className="langswitch" href={`?lang=${lang === "en" ? "vi" : "en"}`}>{tr.lang}</a>
      </header>

      <Link className="back" href={backHome}>{tr.backMap}</Link>

      {snap.is_sample && <div className="samplebar">⚠ {tr.sample}</div>}

      <section className="drillhead">
        <h1>{name} · {product}</h1>
        <div className="chips">
          <span className="chip hs">HS {snap.hs6}</span>
          <span className="chip muted">{tr.period} {snap.latest_period}</span>
        </div>
        <div className="actions">
          <WatchButton watchKey={`signal:${snap.hs6}:${c.code}`} meta={{ hs6: snap.hs6, market: String(c.code), kind: "signal" }}
                       labelOff={tr.watch} labelOn={tr.watching} />
          {isPellets && <a className="chip link" href={`/profiles${lang === "en" ? "?lang=en" : ""}`}>{tr.profilesLink}</a>}
        </div>
      </section>

      <section className="drillgrid">
        <FlowPanel title={tr.exportsLabel} slot={c.exp} t={tr} lang={lang} />
        <FlowPanel title={tr.importsLabel} slot={c.imp} t={tr} lang={lang} />
      </section>

      <QualPanel hs={hs} code={c.code} product={product} country={name} lang={lang} t={tr} />

      {sourcing && ["export", "import"].map((fl) => sourcing[fl] && (
        <section key={fl} className="sourcing-sec">
          <h2>{(fl === "export" ? tr.exportsLabel : tr.importsLabel)} · {tr.sourcingTitle} <span className="muted">(quý · quarterly)</span></h2>
          <div className="drillgrid">
            <div className="panel"><PartnerTable partners={sourcing[fl].partners} lang={lang} t={tr} /></div>
            <div className="panel"><h3 className="muted small">{tr.sourcingOverTime}</h3><SourcingChart sourcing={sourcing[fl]} lang={lang} /></div>
          </div>
        </section>
      ))}

      <footer className="disclaimer muted">{tr.disclaimer}</footer>
    </main>
  );
}
