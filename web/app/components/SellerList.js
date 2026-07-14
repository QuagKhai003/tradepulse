"use client";
/**
 * SellerList.js — who SELLS this product, evidenced by contracts they have WON.
 * @context  Sellers do not advertise ("I sell wood pellets" is not published anywhere). The only
 *           public record that a company sells a product is a contract award naming it as the winner.
 *           So this list is DERIVED from past orders: a seller here = an organisation that won at
 *           least one on-product contract. Ranked by wins, then recency. Curated profiles (hand-checked,
 *           content/companies) are merged in and badged, so a seller can appear from either evidence.
 * @golden   Inform, never match. Organisation names + the public notice that proves the win. No contact
 *           person, no email, no introduction — TED exposes those and we never store or show them.
 * @limits   Presentation. EU public procurement only: a seller that has never won an EU public contract
 *           will not appear, which is a coverage limit, NOT a judgement about the company.
 * @affects  Rendered in HeroClient's right panel + the country page; data from lib/tenders loadSellers.
 */
import { useState } from "react";
import CpvNote from "./CpvNote.js";
import PartyCard from "./PartyCard.js";
// Rendering every row is pointless and slow: "All products" rolls up thousands, and past the first
// screen they are locked teasers anyway. Cap the DOM and SAY what was capped — a silent truncation
// reads as "that is all there is".
const CAP = 60;

import { fmtMoney } from "../lib/format.js";

export default function SellerList({ sellers = [], curated = [], product, t, tools, cpv = null,
                                     openCount = Infinity }) {
  const [open, setOpen] = useState(null);
  const total = sellers.length + curated.length;

  if (!total) {
    return (
      <div className="col-fill">
        <div className="panel-h"><h2>{t.tabSellers}</h2>{tools && <div className="panel-h-tools">{tools}</div>}</div>
        <p className="tender-empty muted">{t.sellersNone} <b>{product}</b>. {t.sellersWhy}</p>
      </div>
    );
  }

  return (
    <div className="col-fill">
      <div className="panel-h">
        <h2><b className="panel-n num">{total}</b> {t.tabSellers}</h2>
        {tools && <div className="panel-h-tools">{tools}</div>}
      </div>
      <div className="companies">
        {curated.map((c, i) => (
          <PartyCard key={c.id} t={t} locked={i >= openCount}
            tag={t.sellerCurated} tagKind="contract" country={c.country} name={c.name}
            meta={<span className="muted">{c.evidence_source}</span>}
            note={`${t.cVerified} ${c.verified_date}`}
            onClick={() => setOpen({ curated: c })} />
        ))}
        {sellers.slice(0, CAP).map((x, i) => (
          <PartyCard key={`${x.seller}-${x.seller_country}`} t={t}
            locked={curated.length + i >= openCount}
            tag={`${x.wins} ${x.wins === 1 ? t.sellerWin : t.sellerWins}`} tagKind="lot"
            country={x.seller_country} name={x.seller}
            meta={<span className="muted">{x.value ? `${fmtMoney(x.value, x.currency)} · ` : ""}{t.sellerLast} {x.last || "—"}</span>}
            note={(x.buyers || []).slice(0, 2).join(", ")}
            onClick={() => setOpen({ seller: x })} />
        ))}
      </div>
      {sellers.length > CAP && <p className="muted tender-note">{t.showingOf.replace("{n}", CAP).replace("{total}", sellers.length)}</p>}
      <CpvNote match={cpv} t={t} />
      {open && <SellerModal x={open} product={product} t={t} onClose={() => setOpen(null)} />}
    </div>
  );
}

function SellerModal({ x, product, t, onClose }) {
  const s = x.seller;
  const c = x.curated;
  return (
    <div className="modal-back" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="modal-x" onClick={onClose} aria-label="Close">×</button>
        <h3 className="modal-title">{s ? s.seller : c.name}</h3>
        <div className="modal-chips">
          <span className="tender-kind contract">{t.roleSeller}</span>
          <span className="flowtag import">{s ? s.seller_country : c.country}</span>
        </div>
        {s ? (
          <dl className="modal-dl">
            <dt>{t.mProduct}</dt><dd>{product}</dd>
            <dt>{t.sellerWinsLabel}</dt><dd className="num">{s.wins}</dd>
            <dt>{t.sellerValue}</dt><dd className="num">{s.value ? fmtMoney(s.value, s.currency) : t.sellerNoValue}</dd>
            <dt>{t.sellerLastLabel}</dt><dd className="num">{s.last || "—"}</dd>
            <dt>{t.sellerBuyers}</dt><dd>{(s.buyers || []).slice(0, 6).join(", ") || "—"}</dd>
          </dl>
        ) : (
          <dl className="modal-dl">
            <dt>{t.mProduct}</dt><dd className="num">HS {(c.hs6 || []).join(", ")}</dd>
            <dt>{t.cEvidence}</dt><dd>{c.evidence_source}</dd>
            <dt>{t.cVerified}</dt><dd className="num">{c.verified_date}</dd>
          </dl>
        )}
        {/* Golden Rule: the public record is the only thing we hand over. */}
        <p className="modal-note muted">{s ? t.sellerNote : t.cNoContact}</p>
        <a className="modal-cta" href={s ? s.url : (c.evidence_url || c.profile_url)}
           target="_blank" rel="noopener noreferrer">
          {s ? t.sellerOpenAward : t.cOpenSource} ↗
        </a>
      </div>
    </div>
  );
}
