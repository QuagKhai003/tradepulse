/**
 * TopCountries.js — top-20 countries by total trade, with export + import volume + YoY% (plan §7.1).
 * @context  Ranked by (export + import) value. Each row shows both flows' value and the YoY change
 *           vs last year, colour-coded (green rising / red falling). Click to drill in.
 * @limits   Presentation only; value/volume only.
 * @affects  Rendered in the left panel on page.js.
 */
import Link from "next/link";
import { fmtPct, fmtUSD, sigColor } from "../lib/format.js";

function Cell({ label, slot }) {
  if (!slot) return <span className="tc-cell"><i>{label}</i> <span className="muted">—</span></span>;
  const c = sigColor(slot.band, slot.direction);
  const pct = slot.yoy_delta != null ? fmtPct(slot.yoy_delta) : "";
  return (
    <span className="tc-cell">
      <i>{label}</i> <b className="num">{fmtUSD(slot.value_usd)}</b>
      {pct && <em className="num" style={{ color: c }}>{pct}</em>}
    </span>
  );
}

export default function TopCountries({ countries, lang, t, hs }) {
  const rows = [...countries]
    .sort((a, b) => ((b.exp?.value_usd || 0) + (b.imp?.value_usd || 0)) - ((a.exp?.value_usd || 0) + (a.imp?.value_usd || 0)))
    .slice(0, 20);
  return (
    <div className="col-fill">
      <div className="panel-h"><h2>{t.topCountries}</h2><span className="feed-count">20</span></div>
      <ol className="tc-list scrollx">
        {rows.map((c, i) => (
          <li key={c.code} className="tc-row">
            <Link className="tc-link" href={`/country/${c.code}?hs=${hs}${lang === "en" ? "&lang=en" : ""}`}>
              <span className="tc-rank num">{i + 1}</span>
              <span className="tc-name">{lang === "en" ? c.name_en : c.name_vi}</span>
              <span className="tc-flows">
                <Cell label={t.exportsShort} slot={c.exp} />
                <Cell label={t.importsShort} slot={c.imp} />
              </span>
            </Link>
          </li>
        ))}
      </ol>
    </div>
  );
}
