/**
 * pricing/page.js — the single paid tier + test-mode checkout (plan §11).
 * @context  One free tier, one paid tier. SMEs pay for alerts + full requirements/profiles, not
 *           dashboards (plan §11 reality check). Price is the 200k VND/mo hypothesis to test.
 * @limits   Test-mode only (no real charge). Inform-never-match holds — nothing here brokers a deal.
 * @affects  Posts to /api/checkout; reads getTier for current state.
 */
import Link from "next/link";
import { getTier, PRICE_VND } from "../lib/tier.js";
import { t } from "../lib/i18n.js";

export default async function PricingPage({ searchParams }) {
  const sp = searchParams ? await searchParams : {};
  const lang = sp.lang === "en" ? "en" : "vi";
  const tr = t(lang);
  const qs = lang === "en" ? "?lang=en" : "";
  const tier = await getTier();
  const price = PRICE_VND.toLocaleString("vi-VN");

  const rows = [
    [tr.rowMap, true, true],
    [tr.rowDrill, true, true],
    [tr.rowProfiles, "3", "∞"],
    [tr.rowReq, tr.snapshotTitle, tr.rowReqFull],
    [tr.rowWatch, "1", "∞"],
    [tr.rowAlerts, false, true],
  ];

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

      <section className="drillhead">
        <h1>{tr.pricingTitle}</h1>
        <p className="muted small">{tr.pricingNote}</p>
        {sp.upgraded && <div className="locked-ok">✓ {tr.upgraded}</div>}
        {sp.downgraded && <p className="muted">{tr.downgraded}</p>}
      </section>

      <div className="pricegrid">
        <div className="pricecol">
          <h2>{tr.tierFree}</h2>
          <div className="price">0₫</div>
          <p className="muted small">{tr.freeSub}</p>
        </div>
        <div className="pricecol paid">
          <h2>{tr.tierPaid}</h2>
          <div className="price">{price}₫<span className="permo">/{tr.perMonth}</span></div>
          <p className="muted small">{tr.paidSub}</p>
        </div>
      </div>

      <table className="feattable">
        <thead><tr><th></th><th>{tr.tierFree}</th><th className="paidcol">{tr.tierPaid}</th></tr></thead>
        <tbody>
          {rows.map(([label, f, p], i) => (
            <tr key={i}>
              <td>{label}</td>
              <td>{cell(f)}</td>
              <td className="paidcol">{cell(p)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="checkout">
        {tier === "paid" ? (
          <form method="post" action="/api/checkout">
            <div className="locked-ok">★ {tr.current}: {tr.tierPaid}</div>
            <input type="hidden" name="action" value="cancel" />
            <button className="langswitch" type="submit">{tr.downgrade}</button>
          </form>
        ) : (
          <form method="post" action="/api/checkout">
            <input type="hidden" name="action" value="upgrade" />
            <button className="locked-btn" type="submit">{tr.startPaid} ({tr.testMode})</button>
          </form>
        )}
      </div>

      <footer className="disclaimer muted">{tr.disclaimer}</footer>
    </main>
  );
}

function cell(v) {
  if (v === true) return <span className="yes">✓</span>;
  if (v === false) return <span className="no">—</span>;
  return <span>{v}</span>;
}
