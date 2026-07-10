/**
 * requirements/[market]/page.js — Layer-3 requirement page (plan §8, the paid core).
 * @context  Per product × destination market. Free tier sees the Snapshot only; the checklist +
 *           sources + sections are paid (plan §11). `?tier=paid` unlocks for the demo. Change log
 *           powers "rule changed" alerts (batch 1.8).
 * @limits   Inform-never-match; every shown item is source-backed (loader guarantees it).
 * @affects  Reads lib/requirements; renders RequirementChecklist.
 */
import Link from "next/link";
import RequirementChecklist from "../../components/RequirementChecklist.js";
import WatchButton from "../../components/WatchButton.js";
import { loadRequirement } from "../../lib/requirements.js";
import { getTier } from "../../lib/tier.js";
import { t } from "../../lib/i18n.js";

export default async function RequirementPage({ params, searchParams }) {
  const { market } = await params;
  const sp = searchParams ? await searchParams : {};
  const lang = sp.lang === "en" ? "en" : "vi";
  const paid = (await getTier()) === "paid";
  const tr = t(lang);
  const qs = lang === "en" ? "?lang=en" : "";
  const d = await loadRequirement(market);

  if (!d) return <main className="page"><div className="empty">404 · <Link href={`/${qs}`}>{tr.backMap}</Link></div></main>;

  const marketName = lang === "en" ? d.market_name_en : d.market_name_vi;
  const product = lang === "en" ? d.product_en : d.product_vi;
  const snapshot = lang === "en" ? d.snapshot_en : d.snapshot_vi;
  const gate = (v) => (paid ? v : null);

  return (
    <main className="page">
      <header className="topbar">
        <div className="brand">
          <Link className="logo" href={`/${qs}`}>◈ TradePulse</Link>
          <span className="tagline">{tr.tagline}</span>
        </div>
        <a className="langswitch" href={`/pricing${qs}`}>{paid ? tr.tierPaid : tr.viewPaid}</a>
      </header>

      <Link className="back" href={`/requirements${qs}`}>{tr.backReq}</Link>

      <section className="drillhead">
        <h1>{product} → {marketName}</h1>
        <div className="chips">
          <span className="chip hs">HS {d.hs6}</span>
          <span className="chip muted">{tr.lastReview}: {d.last_full_review}</span>
          <span className={`chip ${paid ? "" : "link"}`}>{paid ? tr.tierPaid : tr.tierFree}</span>
        </div>
        <div className="actions">
          <WatchButton watchKey={`rule:${d.hs6}:${market}`} meta={{ hs6: d.hs6, market, kind: "rule" }}
                       labelOff={tr.watchRule} labelOn={tr.watchingRule} />
        </div>
      </section>

      {d.is_sample && <div className="samplebar">⚠ {tr.sampleReq}</div>}

      <section className="panel">
        <h2>{tr.snapshotTitle}</h2>
        <p>{snapshot}</p>
      </section>

      {!paid && (
        <div className="paywall">
          <div className="paywall-lock">🔒</div>
          <p>{tr.paywall}</p>
          <a className="locked-btn" href={`/pricing${qs}`}>{tr.viewPaid}</a>
        </div>
      )}

      {gate(
        <>
          <section className="panel">
            <h2>{tr.checklistTitle} <span className="muted">({d.requirements.length})</span></h2>
            <RequirementChecklist items={d.requirements} lang={lang} t={tr} />
          </section>

          <section className="panel">
            <h2>{tr.buyerExp}</h2>
            <p>{lang === "en" ? d.buyer_expectations_en : d.buyer_expectations_vi}</p>
          </section>

          <section className="panel">
            <h2>{tr.demandHow}</h2>
            <p>{lang === "en" ? d.demand_en : d.demand_vi}{" "}
              <a href={d.demand_url} target="_blank" rel="noopener noreferrer">{tr.livePortal} →</a></p>
          </section>

          <section className="panel">
            <h2>{tr.priceCtx}</h2>
            <p>{lang === "en" ? d.price_en : d.price_vi}{" "}
              <span className="muted small">({d.price_source} · {d.price_date})</span></p>
          </section>

          <section className="panel">
            <h2>{tr.changeLog}</h2>
            <ul className="changelog">
              {d.change_log.map((e, i) => (
                <li key={i}><span className="cl-date muted">{e.date}</span>
                  {lang === "en" ? e.text_en : e.text_vi} <span className="muted small">— {e.source}</span></li>
              ))}
            </ul>
          </section>
        </>
      )}

      <footer className="disclaimer muted">{tr.disclaimerReq}</footer>
    </main>
  );
}
