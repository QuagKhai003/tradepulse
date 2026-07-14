"use client";
/**
 * OrderList.js — PAST ORDERS: contracts already awarded for this product (who bought from whom).
 * @context  The third leg of demand. Signals = where trade moved (aggregate, anonymous). Tenders =
 *           who is buying now (buyer named, no seller yet). Past orders = a completed deal with BOTH
 *           sides named and, where TED reports one unambiguous figure, the value. This is what the
 *           SELLERS list is derived from.
 * @golden   Inform, never match. Both parties are named ONLY because the award notice is a public
 *           record; we link to it and hand over nothing else — no contact, no introduction.
 * @limits   Presentation. EU public procurement only, and a value is shown ONLY when the notice
 *           reports a single total — multi-lot notices report per-lot figures we cannot attribute.
 * @affects  Rendered in HeroClient's right panel + the country page; data from lib/tenders loadAwards.
 */
import { useState } from "react";
import CpvNote from "./CpvNote.js";
import PartyCard from "./PartyCard.js";
// Rendering every row is pointless and slow: "All products" rolls up thousands, and past the first
// screen they are locked teasers anyway. Cap the DOM and SAY what was capped — a silent truncation
// reads as "that is all there is".
const CAP = 60;

import { fmtMoney } from "../lib/format.js";
import { lookup } from "../lib/catalog.js";

const productName = (hs) => (hs ? (lookup(hs)?.name_en || `HS ${hs}`) : "");

export default function OrderList({ orders = [], product, t, tools, cpv = null, showProduct = false,
                                    openCount = Infinity }) {
  const [open, setOpen] = useState(null);

  if (!orders.length) {
    return (
      <div className="col-fill">
        <div className="panel-h"><h2>{t.tabOrders}</h2>{tools && <div className="panel-h-tools">{tools}</div>}</div>
        <p className="tender-empty muted">{t.ordersNone} <b>{product}</b>.</p>
      </div>
    );
  }

  return (
    <div className="col-fill">
      <div className="panel-h">
        <h2><b className="panel-n num">{orders.length}</b> {t.tabOrders}</h2>
        {tools && <div className="panel-h-tools">{tools}</div>}
      </div>
      <div className="companies">
        {orders.slice(0, CAP).map((o, i) => (
          <PartyCard key={`${o.id}-${o.seller}`} t={t} locked={i >= openCount}
            tag={showProduct ? productName(o.hs6) : (o.match === "lot" ? t.matchLot : t.matchContract)}
            tagKind={o.match === "lot" ? "lot" : "contract"}
            country={`${o.seller_country} → ${o.buyer_country}`}
            name={o.seller}
            /* the arrow IS the fact: this seller sold to this buyer, per the public award notice */
            meta={<span className="muted">→ {o.buyer}</span>}
            note={`${o.value ? fmtMoney(o.value, o.currency) + " · " : ""}${o.date || ""}`}
            onClick={() => setOpen(o)} />
        ))}
      </div>
      {orders.length > CAP && <p className="muted tender-note">{t.showingOf.replace("{n}", CAP).replace("{total}", orders.length)}</p>}
      <CpvNote match={cpv} t={t} />
      {open && <OrderModal o={open} product={product} t={t} onClose={() => setOpen(null)} />}
    </div>
  );
}

function OrderModal({ o, product, t, onClose }) {
  return (
    <div className="modal-back" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="modal-x" onClick={onClose} aria-label="Close">×</button>
        <h3 className="modal-title">{o.seller} → {o.buyer}</h3>
        <div className="modal-chips">
          <span className={`tender-kind ${o.match === "lot" ? "lot" : "contract"}`}>
            {o.match === "lot" ? t.matchLot : t.matchContract}
          </span>
          <span className="flowtag import">{o.seller_country} → {o.buyer_country}</span>
        </div>
        <dl className="modal-dl">
          <dt>{t.mProduct}</dt><dd>{product}</dd>
          <dt>{t.roleSeller}</dt><dd>{o.seller} ({o.seller_country})</dd>
          <dt>{t.roleBuyer}</dt><dd>{o.buyer} ({o.buyer_country})</dd>
          <dt>{t.orderValue}</dt><dd className="num">{o.value ? fmtMoney(o.value, o.currency) : t.sellerNoValue}</dd>
          <dt>{t.orderDate}</dt><dd className="num">{o.date || "—"}</dd>
          <dt>{t.mContract}</dt><dd>{o.title}</dd>
          <dt>{t.mCpv}</dt><dd className="num">{o.cpv}</dd>
        </dl>
        <p className="modal-note muted">{t.orderNote}</p>
        <a className="modal-cta" href={o.url} target="_blank" rel="noopener noreferrer">{t.mOpenTed} ↗</a>
      </div>
    </div>
  );
}
