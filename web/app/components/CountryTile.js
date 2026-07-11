/**
 * CountryTile.js — one country card showing BOTH flows (export + import) with signal bands.
 * @context  "Vietnam — exports $X ▲, imports $Y ▼". Value/volume only, never order counts (plan §4.2).
 *           Clicking drills into the country. The chosen flow is emphasised.
 * @limits   Presentation only.
 * @affects  Rendered in the top-countries grid on page.js.
 */
import Link from "next/link";
import { bandArrow, bandColor, fmtPct, fmtUSD } from "../lib/format.js";

function Flow({ label, slot }) {
  if (!slot) return <div className="cflow"><span className="clabel muted">{label}</span><span className="muted">—</span></div>;
  const color = bandColor(slot.band, slot.direction);
  const hasSig = slot.band && slot.band !== "none";
  return (
    <div className="cflow">
      <span className="clabel muted">{label}</span>
      <span className="cval">{fmtUSD(slot.value_usd)}</span>
      {hasSig && (
        <span className="cband" style={{ color }}>
          {bandArrow(slot.band, slot.direction)} {fmtPct(slot.yoy_delta)}
        </span>
      )}
    </div>
  );
}

export default function CountryTile({ c, lang, t, emphasis, hs }) {
  const name = lang === "en" ? c.name_en : c.name_vi;
  const href = `/country/${c.code}?hs=${hs}${lang === "en" ? "&lang=en" : ""}`;
  return (
    <Link className="ctile" href={href}>
      <div className="ctile-name">{name}</div>
      <div className={emphasis === "exp" ? "" : "dim"}><Flow label={t.exportsLabel} slot={c.exp} /></div>
      <div className={emphasis === "imp" ? "" : "dim"}><Flow label={t.importsLabel} slot={c.imp} /></div>
    </Link>
  );
}
