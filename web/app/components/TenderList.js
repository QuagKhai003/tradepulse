"use client";
/**
 * TenderList.js — FORWARD demand: public buyers with an open tender for this product (plan §9.2).
 * @context  The signal feed says where demand moved (past). This says who is buying NOW — buyer
 *           organisation, country, deadline, and a link to the official EU TED notice. Clicking a row
 *           opens a detail modal (everything we hold on that notice + the official link).
 * @warn     A tender is either the WHOLE contract for this product ("contract") or ONE LOT of a bigger
 *           one ("lot"). For a lot, TED's headline subject describes the WHOLE contract ("Food,
 *           beverages...") — printing that as the tender's title would imply the buyer wants a food
 *           basket when they want a tea lot. So the row leads with the PRODUCT, and the notice's own
 *           subject is shown as the contract it sits inside. The ETL already dropped "basket" matches
 *           (product buried as one line item of a mixed contract — not a lead). See sources/ted.py.
 * @golden   Inform, never match: public buying ORGANISATION + the official notice link ONLY. No
 *           contact person, no introduction, no brokering. The user acts on the public notice.
 * @limits   Presentation only; the ETL already filtered to still-open, on-product notices.
 * @affects  Rendered in HeroClient's right panel and on the country page.
 */
import { useState } from "react";
import { fmtDeadline } from "../lib/format.js";

export default function TenderList({ tenders, lang, t, tools, product }) {
  const list = tenders || [];
  const [open, setOpen] = useState(null);

  return (
    <div className="col-fill">
      <div className="panel-h">
        <h2><b className="panel-n num">{list.length}</b> {t.tendersTitle}</h2>
        {tools && <div className="panel-h-tools">{tools}</div>}
      </div>

      {list.length === 0 ? (
        <p className="tender-empty muted">{t.tendersNone}</p>
      ) : (
        <ul className="feed-list scrollx">
          {list.map((x) => {
            const due = fmtDeadline(x.deadline, lang);
            const isLot = x.match === "lot";
            return (
              <li key={x.id} className="feed-item">
                <button type="button" className="tender-open" onClick={() => setOpen(x)}>
                  <div className="feed-row1">
                    <span className="feed-link">{x.buyer || x.title}</span>
                    <span className={`tender-due ${due.soon ? "soon" : ""}`}>{due.label}</span>
                  </div>
                  <div className="feed-row2">
                    <span className="flowtag import">{x.buyer_country}</span>
                    <span className={`tender-kind ${isLot ? "lot" : "contract"}`}>
                      {isLot ? t.matchLot : t.matchContract}
                    </span>
                    <span className="tender-title muted">
                      {isLot ? `${product || t.product} · ${t.matchInside} ${x.title}` : x.title}
                    </span>
                  </div>
                </button>
              </li>
            );
          })}
        </ul>
      )}

      {open && <TenderModal tender={open} product={product} lang={lang} t={t} onClose={() => setOpen(null)} />}
    </div>
  );
}

function TenderModal({ tender: x, product, lang, t, onClose }) {
  const due = fmtDeadline(x.deadline, lang);
  const isLot = x.match === "lot";
  return (
    <div className="modal-back" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="modal-x" onClick={onClose} aria-label="Close">×</button>
        <h3 className="modal-title">{x.buyer || x.title}</h3>
        <div className="modal-chips">
          <span className="flowtag import">{x.buyer_country}</span>
          <span className={`tender-kind ${isLot ? "lot" : "contract"}`}>
            {isLot ? t.matchLot : t.matchContract}
          </span>
          <span className={`tender-due ${due.soon ? "soon" : ""}`}>{due.label}</span>
        </div>
        <dl className="modal-dl">
          <dt>{t.mProduct}</dt><dd>{product || "—"}</dd>
          <dt>{t.mContract}</dt><dd>{x.title}</dd>
          <dt>{t.mDeadline}</dt><dd>{x.deadline || t.mNoDeadline}</dd>
          <dt>{t.mPublished}</dt><dd>{x.published || "—"}</dd>
          <dt>{t.mCpv}</dt><dd className="num">{x.cpv}</dd>
          <dt>{t.mNotice}</dt><dd className="num">{x.id}</dd>
        </dl>
        {/* Golden Rule: we hand over the PUBLIC notice, never an introduction. */}
        <p className="modal-note muted">{isLot ? t.mLotNote : t.mContractNote}</p>
        <a className="modal-cta" href={x.url} target="_blank" rel="noopener noreferrer">{t.mOpenTed} ↗</a>
      </div>
    </div>
  );
}
