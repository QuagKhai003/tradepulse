/**
 * country/[code]/page.js — country drill-down: its export + import signals, then deeper links.
 * @context  Click a country on the map/feed -> this view: both-flow value + YoY band + history, plus
 *           links to the qualification page (if covered) and the profiles directory (plan §7.3–7.5).
 * @limits   Inform-never-match; value/volume only.
 * @affects  Reads lib/snapshot; renders WatchButton.
 */
import Link from "next/link";
import SearchBox from "../../components/SearchBox.js";
import WatchButton from "../../components/WatchButton.js";
import PartnerTable from "../../components/PartnerTable.js";
import SourcingChart from "../../components/SourcingChart.js";
import QualPanel from "../../components/QualPanel.js";
import CountryTabs from "../../components/CountryTabs.js";
import { loadSnapshot } from "../../lib/snapshot.js";
import { loadSourcing } from "../../lib/sourcing.js";
import { loadAwards, loadCpvMatch, loadSellers, loadTenders } from "../../lib/tenders.js";
import { resolveLang, t, VI_ENABLED } from "../../lib/i18n.js";
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
          ? <span className="cband" style={{ color }}>{bandArrow(slot.band, slot.direction)} {bandLabel(slot.band, lang)} · {fmtPct(slot.yoy_delta)}</span>
          : <span className="muted">{tr.noSignal}</span>}
        <span className="muted"> · {fmtPeriod(slot.period, lang)}</span>
      </div>
      {hist.length > 1 && <div className="spark">
        {hist.map((h) => (
          <div key={h.period} className="spark-bar" title={`${h.period}: ${fmtUSD(h.value_usd)}`}>
            <div style={{ height: `${Math.round((h.value_usd / max) * 100)}%`, background: color }} />
            <span className="spark-x muted">{h.period.replace("-", " ")}</span>
          </div>
        ))}
      </div>}
    </div>
  );
}

export default async function CountryPage({ params, searchParams }) {
  const { code } = await params;
  const sp = searchParams ? await searchParams : {};
  const lang = resolveLang(sp.lang);
  const tr = t(lang);
  const snap = await loadSnapshot(sp.hs);
  const hs = (snap && snap.hs6) || sp.hs || "440131";
  const qs = `?hs=${hs}${lang === "en" ? "&lang=en" : ""}`;
  const backHome = `/?hs=${hs}${lang === "en" ? "&lang=en" : ""}`;
  const c = snap?.countries.find((x) => String(x.code) === String(code));

  // Switching product from THIS page can land on a product the country doesn't trade — that's a normal
  // empty state, not a 404. Keep the header + search so the user can pick another product right here.
  if (snap && !c) {
    const prod = lang === "en" ? snap.product.name_en : snap.product.name_vi;
    return (
      <main className="page">
        <header className="topbar">
          <div className="brand"><Link className="logo" href={backHome}>◈ TradePulse</Link></div>
          <div className="country-search"><SearchBox lang={lang} placeholder={tr.searchHere} countryCode={code} /></div>
          {VI_ENABLED && <a className="langswitch" href={`?lang=${lang === "en" ? "vi" : "en"}`}>{tr.lang}</a>}
        </header>
        <Link className="back" href={backHome}>{tr.backMap}</Link>
        <div className="empty">{tr.noCountryProduct} <b>{prod}</b>.</div>
      </main>
    );
  }
  if (!snap || !c) return <main className="page"><div className="empty">404 · <Link href={backHome}>{tr.backMap}</Link></div></main>;

  const name = lang === "en" ? c.name_en : c.name_vi;
  const product = lang === "en" ? snap.product.name_en : snap.product.name_vi;
  const isPellets = hs === "440131";
  const sourcing = (await loadSourcing(hs))?.[String(c.code)] || null;
  // Open tenders for THIS PRODUCT — this country's own buyers first, the rest below. Filtering to the
  // country alone hid the section entirely for every non-EU country (TED covers EU public buyers only),
  // which reads as "no demand" when it actually means "no coverage here".
  const allTenders = await loadTenders(hs);
  const tHere = allTenders.filter((x) => String(x.buyer_code) === String(c.code));
  const tElse = allTenders.filter((x) => String(x.buyer_code) !== String(c.code));
  // Sellers BASED here, and every past order this country took part in — as the buyer OR the seller.
  // Both are the country-scoped slice of the same evidence the globe view shows for the product.
  const sellersHere = (await loadSellers(hs)).filter((x) => String(x.seller_code) === String(c.code));
  const allOrders = await loadAwards(hs);
  const cpv = await loadCpvMatch(hs);
  const ordersHere = allOrders.filter((x) => String(x.buyer_code) === String(c.code)
                                          || String(x.seller_code) === String(c.code));
  // The country's OWN latest period — not the snapshot-wide max, which reads as a lie next to figures
  // from an earlier year (the map's newest country can be a year ahead of this one).
  const asOf = [c.exp?.period, c.imp?.period].filter(Boolean).sort().pop() || snap.latest_period;

  return (
    <main className="page">
      <header className="topbar">
        <div className="brand"><Link className="logo" href={backHome}>◈ TradePulse</Link></div>
        {/* Switch product WITHOUT going back to the globe — stays on this country. */}
        <div className="country-search"><SearchBox lang={lang} placeholder={tr.searchHere} countryCode={c.code} /></div>
        {VI_ENABLED && <a className="langswitch" href={`?lang=${lang === "en" ? "vi" : "en"}`}>{tr.lang}</a>}
      </header>

      <Link className="back" href={backHome}>{tr.backMap}</Link>

      {snap.is_sample && <div className="samplebar">⚠ {tr.sample}</div>}

      <section className="drillhead">
        <h1>{name} · {product}</h1>
        <div className="chips">
          <span className="chip hs">HS {snap.hs6}</span>
          <span className="chip muted">{tr.asOf} {asOf}</span>
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

      {/* who buys, who sells, and what has already been sold — for THIS product in THIS country */}
      <CountryTabs tHere={tHere} tElse={tElse} sellers={sellersHere} orders={ordersHere}
                   product={product} country={name} cpv={cpv} lang={lang} t={tr} />

      <QualPanel hs={hs} code={c.code} product={product} country={name} lang={lang} t={tr} />

      {sourcing && ["export", "import"].map((fl) => sourcing[fl] && (
        <section key={fl} className="sourcing-sec">
          <h2>{(fl === "export" ? tr.exportsLabel : tr.importsLabel)} · {tr.sourcingTitle} <span className="muted">(quarterly)</span></h2>
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
