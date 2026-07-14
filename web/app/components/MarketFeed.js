"use client";
/**
 * MarketFeed.js — the parties behind a product in one market: buyers, sellers, past orders.
 * @context  Master–detail. Left: a tab rail + compact scannable rows, each one organisation. Right: the
 *           full public record for the row you picked, held in view while you keep scanning the list —
 *           a modal would hide the list every time you compared two companies, and comparing is the job.
 * @warn     The three tabs ALWAYS render, for every product and country. The layout is a constant; only
 *           its contents change. An empty tab says WHY it is empty (no coverage / nothing on record /
 *           aggregate heading) instead of vanishing — a disappearing tab reads as "nothing exists" when
 *           it means "we have no coverage here", and those are very different facts to a factory owner.
 * @golden   Inform, never match. Every row is an ORGANISATION plus the public notice that evidences it.
 *           Never a contact person, an email or a phone — TED publishes those; we do not carry them.
 * @limits   Presentation + tab/selection state. The paywall (locked rows) is decided SERVER-side and
 *           passed in as openCount: a locked row blurs the WHOLE row (owner's call) and cannot be
 *           selected — it links to /pricing instead. The count stays visible, so the tab still tells
 *           the truth about how much is there.
 * @affects  Rendered by country/[code]/page.js. Rows built from lib/tenders (tenders, sellers, awards).
 */
import { useState } from "react";
import Link from "next/link";
import { fmtDeadline, fmtMoney } from "../lib/format.js";
import { lookup } from "../lib/catalog.js";

const CAP = 60;   // rows rendered; the rollup holds thousands and the rest are locked teasers anyway

const productName = (hs) => (hs ? (lookup(hs)?.name_en || `HS ${hs}`) : "");

export default function MarketFeed({ tenders = [], sellers = [], orders = [], product, country,
                                     cpv, hs, lang, t, openCount = Infinity }) {
  const [tab, setTab] = useState("buyers");
  const [pick, setPick] = useState(0);

  // "All products" is not a good anyone tenders for — but the answer it owes is real: everything,
  // across every product. So it is a rollup, and each row names the product it belongs to.
  const isAggregate = hs === "TOTAL" || cpv?.aggregate;
  const noCoverage = !isAggregate && !cpv;

  const items = { buyers: tenders, sellers, orders }[tab] || [];
  const rows = items.slice(0, CAP).map((x, i) => toRow(tab, x, i >= openCount, isAggregate, lang, t));
  const chosen = rows[Math.min(pick, rows.length - 1)];

  const tabs = [
    { v: "buyers", label: t.tabBuyers, n: tenders.length },
    { v: "sellers", label: t.tabSellers, n: sellers.length },
    { v: "orders", label: t.tabOrders, n: orders.length },
  ];

  function choose(v) {
    setTab(v);
    setPick(0);
  }

  return (
    <section className="mfeed">
      <header className="mfeed-head">
        <div>
          <h2 className="mfeed-title">{t.marketFeed}</h2>
          <p className="mfeed-sub muted">{country} · {product}</p>
        </div>
        <div className="mfeed-tabs">
          {tabs.map((x) => (
            <button key={x.v} type="button" className={`ctab ${tab === x.v ? "on" : ""}`}
                    onClick={() => choose(x.v)}>
              {x.label} <b className="num">{x.n}</b>
            </button>
          ))}
        </div>
      </header>

      {noCoverage ? (
        <p className="mfeed-empty muted">{t.noCpvNote}</p>
      ) : rows.length === 0 ? (
        <p className="mfeed-empty muted">{emptyLine(tab, product, country, t)}</p>
      ) : (
        <div className="mfeed-body">
          <div className="mfeed-list">
            <ul>
              {rows.map((r, i) => (
                <li key={r.key}>
                  {r.locked ? (
                    // Locked: the whole row blurs and cannot be selected — it goes to /pricing. The tab
                    // COUNT still shows the real total, so the paywall hides the rows, never the truth
                    // about how many there are.
                    <Link className="mrow locked" href="/pricing">
                      <span className="mrow-blur">
                        <span className="mrow-name">{r.name}</span>
                        <span className="mrow-meta">
                          <span className="mrow-cty">{r.country}</span>
                          <span className="mrow-fact">{r.rowFact}</span>
                        </span>
                      </span>
                      <span className="mrow-lock">🔒 {t.upgrade}</span>
                    </Link>
                  ) : (
                    <button type="button" className={`mrow ${i === Math.min(pick, rows.length - 1) ? "on" : ""}`}
                            onClick={() => setPick(i)}>
                      <span className="mrow-name">{r.name}</span>
                      <span className="mrow-meta">
                        <span className="mrow-cty">{r.country}</span>
                        <span className="mrow-fact">{r.rowFact}</span>
                      </span>
                    </button>
                  )}
                </li>
              ))}
            </ul>
            <div className="mfeed-foot muted">
              {items.length > CAP && <p>{t.showingOf.replace("{n}", CAP).replace("{total}", items.length)}</p>}
              {isAggregate && <p>{t.aggregateNote}</p>}
              {cpv && !cpv.exact && cpv.label && (
                <p>{t.cpvNear} <b>{cpv.label}</b> <span className="num">({cpv.cpv})</span></p>
              )}
              {cpv?.exact && <p>{t.cpvExact} <span className="num">{cpv.cpv}</span></p>}
              <p className="mfeed-src">{t.tenderSource}</p>
            </div>
          </div>

          <aside className="mfeed-detail">
            {chosen && !chosen.locked ? (
              <>
                <div className="mdet-tags">
                  <span className={`tender-kind ${chosen.tagKind}`}>{chosen.tag}</span>
                  <span className="flowtag import">{chosen.country}</span>
                </div>
                <h3 className="mdet-name">{chosen.name}</h3>
                <dl className="modal-dl">
                  {chosen.facts.map(([k, v]) => (
                    <div key={k} className="mdet-row"><dt>{k}</dt><dd>{v}</dd></div>
                  ))}
                </dl>
                {/* Golden Rule: the public record is the only thing we hand over. */}
                <p className="modal-note muted">{chosen.note}</p>
                <a className="modal-cta" href={chosen.url} target="_blank" rel="noopener noreferrer">
                  {chosen.cta} ↗
                </a>
              </>
            ) : (
              <p className="muted mdet-empty">{t.pickOne}</p>
            )}
          </aside>
        </div>
      )}
    </section>
  );
}

function emptyLine(tab, product, country, t) {
  if (tab === "buyers") return t.emptyBuyers;
  if (tab === "sellers") return t.emptySellers;
  return t.emptyOrders;
}

// One shape for all three tabs: an organisation + the record that proves it.
function toRow(tab, x, locked, isAggregate, lang, t) {
  const prod = isAggregate ? productName(x.hs6) : null;

  if (tab === "buyers") {
    const due = fmtDeadline(x.deadline, lang);
    const isLot = x.match === "lot";
    return {
      key: x.id, locked, name: x.buyer || x.title, country: x.buyer_country,
      rowFact: due.label, tag: prod || (isLot ? t.matchLot : t.matchContract),
      tagKind: isLot ? "lot" : "contract",
      facts: [[t.mProduct, prod || t.product], [t.mContract, x.title],
              [t.mDeadline, x.deadline || t.mNoDeadline], [t.mPublished, x.published || "—"],
              [t.mCpv, x.cpv], [t.mNotice, x.id]],
      note: isLot ? t.mLotNote : t.mContractNote, url: x.url, cta: t.mOpenTed,
    };
  }

  if (tab === "sellers") {
    return {
      key: `${x.seller}-${x.seller_country}`, locked, name: x.seller, country: x.seller_country,
      rowFact: `${x.wins} ${x.wins === 1 ? t.sellerWin : t.sellerWins}`,
      tag: t.roleSeller, tagKind: "contract",
      facts: [[t.sellerWinsLabel, String(x.wins)],
              [t.sellerValue, x.value ? fmtMoney(x.value, x.currency) : t.sellerNoValue],
              [t.sellerLastLabel, x.last || "—"],
              [t.sellerBuyers, (x.buyers || []).slice(0, 6).join(", ") || "—"]],
      note: t.sellerNote, url: x.url, cta: t.sellerOpenAward,
    };
  }

  return {
    key: `${x.id}-${x.seller}`, locked, name: x.seller, country: `${x.seller_country} → ${x.buyer_country}`,
    rowFact: x.value ? fmtMoney(x.value, x.currency) : (x.date || ""),
    tag: prod || (x.match === "lot" ? t.matchLot : t.matchContract),
    tagKind: x.match === "lot" ? "lot" : "contract",
    facts: [[t.mProduct, prod || t.product], [t.roleSeller, `${x.seller} (${x.seller_country})`],
            [t.roleBuyer, `${x.buyer} (${x.buyer_country})`],
            [t.orderValue, x.value ? fmtMoney(x.value, x.currency) : t.sellerNoValue],
            [t.orderDate, x.date || "—"], [t.mContract, x.title], [t.mCpv, x.cpv]],
    note: t.orderNote, url: x.url, cta: t.mOpenTed,
  };
}
