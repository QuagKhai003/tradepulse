/**
 * TopCountries.js — countries ranked by total trade: export + import volume + YoY% (plan §7.1).
 * @context  ALL countries, ranked by (export + import) value, scrollable. Aligned columns; XK (export) / NK (import) shown as
 *           colour tags (green = export, indigo = import) so the flow is unmistakable. YoY colour =
 *           green rising / red falling. Click to drill in.
 * @limits   Presentation only; value/volume only.
 * @affects  Rendered in the left overlay panel on page.js.
 */
import Link from "next/link";
import { fmtPct, fmtUSD, sigColor } from "../lib/format.js";

function Flow({ tag, cls, slot }) {
  if (!slot) return <span className="tcf"><i className={`tcf-tag ${cls}`}>{tag}</i><b className="tcf-val num">—</b><em /></span>;
  const c = sigColor(slot.band, slot.direction, true);
  return (
    <span className="tcf">
      <i className={`tcf-tag ${cls}`}>{tag}</i>
      <b className="tcf-val num">{fmtUSD(slot.value_usd)}</b>
      <em className="tcf-pct num" style={{ color: c }}>{slot.yoy_delta != null ? fmtPct(slot.yoy_delta) : ""}</em>
    </span>
  );
}

export default function TopCountries({ countries, lang, t, hs }) {
  const rows = [...countries]
    .sort((a, b) => ((b.exp?.value_usd || 0) + (b.imp?.value_usd || 0)) - ((a.exp?.value_usd || 0) + (a.imp?.value_usd || 0)));
  return (
    <div className="col-fill">
      <div className="panel-h"><h2>{t.topCountries}</h2></div>
      <ol className="tc-list scrollx">
        {rows.map((c, i) => (
          <li key={c.code} className="tc-row">
            <Link className="tc-link" href={`/country/${c.code}?hs=${hs}${lang === "en" ? "&lang=en" : ""}`}>
              <span className="tc-rank num">{i + 1}</span>
              <span className="tc-name">{lang === "en" ? c.name_en : c.name_vi}</span>
              <span className="tc-flows">
                <Flow tag={t.exportsShort} cls="export" slot={c.exp} />
                <Flow tag={t.importsShort} cls="import" slot={c.imp} />
              </span>
            </Link>
          </li>
        ))}
      </ol>
    </div>
  );
}
