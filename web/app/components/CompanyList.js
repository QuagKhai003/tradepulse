"use client";
/**
 * CompanyList.js — Layer-2 directory in the hero panel: who publicly buys and sells this product.
 * @context  The third panel tab. Signals = where demand moved; tenders = who is buying now;
 *           companies = the named public players. Clicking a row opens a detail modal (role, country,
 *           the evidence we hold, and the public source it came from).
 * @golden   Inform, never match. Names + PUBLIC sources + verified date only — never a contact person,
 *           an email, a phone number, or an introduction. Curated by hand in content/companies/.
 * @limits   Presentation. Free tier opens the first FREE_PROFILE_LIMIT; the rest stay locked (plan §11).
 *           The directory is only curated for wood pellets so far — every other product gets an
 *           honest empty state rather than a blank tab.
 * @affects  Rendered in HeroClient's right panel; data from lib/companies.
 */
import { useState } from "react";

export default function CompanyList({ data, product, openIds, lang, t, tools }) {
  const [open, setOpen] = useState(null);
  const list = data?.companies || [];

  if (!list.length) {
    return (
      <div className="col-fill">
        <div className="panel-h"><h2>{t.companiesTitle}</h2>{tools && <div className="panel-h-tools">{tools}</div>}</div>
        <p className="tender-empty muted">
          {t.companiesNone} <b>{product}</b>. {t.companiesOnlyPellets}
        </p>
      </div>
    );
  }

  const sellers = list.filter((c) => c.role === "seller");
  const buyers = list.filter((c) => c.role === "buyer");
  const isOpen = (c) => !openIds || openIds.includes(c.id);

  const rows = (title, items) => items.length > 0 && (
    <>
      <li className="co-group muted">{title} ({items.length})</li>
      {items.map((c) => (
        <li key={c.id} className="feed-item">
          <button type="button" className={`tender-open ${isOpen(c) ? "" : "co-locked"}`}
                  onClick={() => isOpen(c) && setOpen(c)}>
            <div className="feed-row1">
              <span className="feed-link">{isOpen(c) ? c.name : "•••••••••"}</span>
              <span className="tender-due">{isOpen(c) ? c.country : t.locked}</span>
            </div>
            <div className="feed-row2">
              <span className={`tender-kind ${c.role === "seller" ? "contract" : "lot"}`}>
                {c.role === "seller" ? t.roleSeller : t.roleBuyer}
              </span>
              <span className="tender-title muted">
                {isOpen(c) ? c.evidence_source : t.lockedNote}
              </span>
            </div>
          </button>
        </li>
      ))}
    </>
  );

  return (
    <div className="col-fill">
      <div className="panel-h">
        <h2><b className="panel-n num">{list.length}</b> {t.companiesTitle}</h2>
        {tools && <div className="panel-h-tools">{tools}</div>}
      </div>
      <ul className="feed-list scrollx">
        {rows(t.roleSellers, sellers)}
        {rows(t.roleBuyers, buyers)}
      </ul>
      {open && <CompanyModal c={open} t={t} onClose={() => setOpen(null)} />}
    </div>
  );
}

function CompanyModal({ c, t, onClose }) {
  return (
    <div className="modal-back" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="modal-x" onClick={onClose} aria-label="Close">×</button>
        <h3 className="modal-title">{c.name}</h3>
        <div className="modal-chips">
          <span className={`tender-kind ${c.role === "seller" ? "contract" : "lot"}`}>
            {c.role === "seller" ? t.roleSeller : t.roleBuyer}
          </span>
          <span className="flowtag import">{c.country}</span>
        </div>
        <dl className="modal-dl">
          <dt>{t.mProduct}</dt><dd className="num">HS {(c.hs6 || []).join(", ")}</dd>
          <dt>{t.cEvidence}</dt><dd>{c.evidence_source}</dd>
          <dt>{t.cVerified}</dt><dd className="num">{c.verified_date}</dd>
        </dl>
        {/* Golden Rule: a public source link is the ONLY thing we hand over. No contact, no intro. */}
        <p className="modal-note muted">{t.cNoContact}</p>
        <div className="modal-chips">
          {c.evidence_url && (
            <a className="modal-cta" href={c.evidence_url} target="_blank" rel="noopener noreferrer">
              {t.cOpenSource} ↗
            </a>
          )}
          {c.profile_url && (
            <a className="chip link" href={c.profile_url} target="_blank" rel="noopener noreferrer">
              {t.cOpenRegistry} ↗
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
