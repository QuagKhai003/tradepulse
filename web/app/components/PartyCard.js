/**
 * PartyCard.js — one public party (buyer, seller) or one past order, as a profile card.
 * @context  The Layer-2 profile card is the shape users recognise: role tag + country, the name, the
 *           public evidence, the verified/notice date. Buyers, sellers and past orders are all "a named
 *           organisation + the public record that proves it", so they share this card instead of three
 *           different row layouts.
 * @golden   Inform, never match. The card shows an ORGANISATION and links to the public notice. It never
 *           shows a contact person, an email or a phone number — TED publishes those and we do not.
 * @limits   Presentation. `locked` blurs the identifying fields for the free tier (plan §11) and blocks
 *           the click: a locked card must not open the detail modal, or the paywall is decorative.
 * @affects  Rendered by TenderList / SellerList / OrderList.
 */
export default function PartyCard({ tag, tagKind = "contract", country, name, meta, note, locked, t, onClick }) {
  if (locked) {
    return (
      <div className="company locked-card">
        <div className="company-head">
          <span className={`tender-kind ${tagKind}`}>{tag}</span>
          <span className="company-country muted">{country}</span>
        </div>
        <div className="company-name">{name}</div>
        <div className="company-src">{meta}</div>
        {note && <div className="company-verified muted">{note}</div>}
        <a className="lockmask" href="/pricing">🔒 {t.upgrade}</a>
      </div>
    );
  }
  return (
    <button type="button" className="company company-btn" onClick={onClick}>
      <div className="company-head">
        <span className={`tender-kind ${tagKind}`}>{tag}</span>
        <span className="company-country muted">{country}</span>
      </div>
      <div className="company-name">{name}</div>
      <div className="company-src">{meta}</div>
      {note && <div className="company-verified muted">{note}</div>}
    </button>
  );
}
