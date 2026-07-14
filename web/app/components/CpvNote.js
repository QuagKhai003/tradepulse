/**
 * CpvNote.js — states which CPV category a product's tender/award feed was matched to.
 * @context  TED classifies by CPV, not HS, and there is no official crosswalk. For the pilot products
 *           the map is hand-checked (exact). For the other ~650 it is a text match that was verified
 *           live against TED — right domain, but not always the identical good ("Vegetables, dried"
 *           lands on CPV "Frozen vegetables"). Printing the matched category is what keeps a broad
 *           feed honest: the user can see, per product, exactly what they are looking at.
 * @limits   Presentation only.
 * @affects  Rendered under the Buyers / Sellers / Past orders lists.
 */
export default function CpvNote({ match, t }) {
  if (!match) return null;
  if (match.exact) return <p className="muted tender-note">{t.cpvExact} <span className="num">{match.cpv}</span></p>;
  return (
    <p className="muted tender-note">
      {t.cpvApprox} <b>{match.label}</b> <span className="num">({match.cpv})</span> — {t.cpvApproxWhy}
    </p>
  );
}
