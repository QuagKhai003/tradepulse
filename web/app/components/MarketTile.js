/**
 * MarketTile.js — one destination market card: value + YoY band + VN share (plan §7.1 tiles).
 * @context  The value/volume tile. Never shows order counts (plan §4.2). Honest period label.
 * @limits   Presentation only.
 * @affects  Rendered in the markets grid on page.js.
 */
import Link from "next/link";
import { bandArrow, bandColor, bandLabel, fmtPct, fmtUSD } from "../lib/format.js";

export default function MarketTile({ m, lang, t }) {
  const name = lang === "en" ? m.name_en : m.name_vi;
  const hasSignal = m.band && m.band !== "none";
  const color = bandColor(m.band, m.direction);
  const href = `/market/${m.slug}${lang === "en" ? "?lang=en" : ""}`;

  return (
    <Link className="tile" href={href}>
      <div className="tile-head">
        <span className="tile-name">{name}</span>
        <span className="tile-badge" style={{ background: color }}>
          {bandArrow(m.band, m.direction)} {bandLabel(m.band, lang)}
        </span>
      </div>
      <div className="tile-value">{fmtUSD(m.value_usd)}</div>
      <div className="tile-meta">
        {hasSignal ? (
          <span className="tile-yoy" style={{ color: m.direction === "down" ? "#b91c1c" : "#15803d" }}>
            {fmtPct(m.yoy_delta)} <span className="muted">{t.yoy}</span>
          </span>
        ) : (
          <span className="muted">{t.noSignal}</span>
        )}
      </div>
      {m.vn_share != null && (
        <div className="tile-share">
          {t.vnShare}: <strong>{(m.vn_share * 100).toFixed(0)}%</strong>
        </div>
      )}
      <div className="tile-period muted">{m.period}{m.published_date ? ` · ${t.published} ${m.published_date}` : ""}</div>
      <div className="tile-cta">{t.viewDetail}</div>
    </Link>
  );
}
