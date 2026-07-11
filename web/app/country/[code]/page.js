/**
 * country/[code]/page.js — country drill-down: its export + import signals, then deeper links.
 * @context  Click a country on the map/feed -> this view: both-flow value + YoY band + history, plus
 *           links to the qualification page (if covered) and the profiles directory (plan §7.3–7.5).
 * @limits   Inform-never-match; value/volume only.
 * @affects  Reads lib/snapshot; renders WatchButton.
 */
import Link from "next/link";
import WatchButton from "../../components/WatchButton.js";
import { loadSnapshot } from "../../lib/snapshot.js";
import { t } from "../../lib/i18n.js";
import { bandArrow, bandColor, bandLabel, fmtPct, fmtUSD } from "../../lib/format.js";

const REQ_MARKET = { 392: "jp", 410: "kr", 97: "eu" };

function FlowPanel({ title, slot, t: tr }) {
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
        <span className="muted"> · {slot.period}</span>
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
  const qs = lang === "en" ? "?lang=en" : "";
  const snap = await loadSnapshot();
  const c = snap?.countries.find((x) => String(x.code) === String(code));

  if (!snap || !c) return <main className="page"><div className="empty">404 · <Link href={`/${qs}`}>{tr.backMap}</Link></div></main>;

  const name = lang === "en" ? c.name_en : c.name_vi;
  const product = lang === "en" ? snap.product.name_en : snap.product.name_vi;
  const reqMarket = REQ_MARKET[c.code];

  return (
    <main className="page">
      <header className="topbar">
        <div className="brand"><Link className="logo" href={`/${qs}`}>◈ TradePulse</Link><span className="tagline">{tr.tagline}</span></div>
        <a className="langswitch" href={`?lang=${lang === "en" ? "vi" : "en"}`}>{tr.lang}</a>
      </header>

      <Link className="back" href={`/${qs}`}>{tr.backMap}</Link>

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
          <a className="chip link" href={`/profiles${qs}`}>{tr.profilesLink}</a>
          {reqMarket && <a className="chip link" href={`/requirements/${reqMarket}${qs}`}>{tr.reqLink}</a>}
        </div>
      </section>

      <section className="drillgrid">
        <FlowPanel title={tr.exportsLabel} slot={c.exp} t={tr} />
        <FlowPanel title={tr.importsLabel} slot={c.imp} t={tr} />
      </section>

      <footer className="disclaimer muted">{tr.disclaimer}</footer>
    </main>
  );
}
