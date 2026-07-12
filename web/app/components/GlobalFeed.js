/**
 * GlobalFeed.js — worldwide signal feed, both flows, filtered by the export/import toggle (plan §7.1).
 * @context  Each row: country + signed, colour-coded YoY % (the signal), then flow · value · magnitude
 *           · period. Direction = sign + colour + arrow, so a decline never reads as a rise. The flow
 *           toggle lives in the header (the only filter). No colour legend.
 * @limits   Presentation only; snapshot.feed is pre-sorted by severity then value.
 * @affects  Rendered on page.js from snapshot.feed + the active flow.
 */
import Link from "next/link";
import { bandArrow, bandLabel, fmtPct, fmtPeriod, fmtUSD, isFeedSignal, sigColor, slotFor } from "../lib/format.js";

export default function GlobalFeed({ countries, flow, freq = "A", lang, t, hs, sort = "value-desc", tools }) {
  const nm = (x) => (lang === "en" ? x.name_en : x.name_vi) || "";
  const loc = lang === "en" ? "en" : "vi";
  const metric = flow === "export" ? "exp" : "imp";
  // Derive the feed from the countries at the chosen grain, so the M/Q/A toggle switches it too.
  const items = [];
  for (const c of countries) {
    const slot = slotFor(c[metric], freq);
    if (!slot || !isFeedSignal(slot.band)) continue;
    items.push({ code: c.code, name_en: c.name_en, name_vi: c.name_vi, flow,
                 value_usd: slot.value_usd, yoy_delta: slot.yoy_delta, band: slot.band,
                 direction: slot.direction, period: slot.period });
  }
  if (sort === "name-asc") items.sort((a, b) => nm(a).localeCompare(nm(b), loc));
  else if (sort === "name-desc") items.sort((a, b) => nm(b).localeCompare(nm(a), loc));
  else if (sort === "change-desc") items.sort((a, b) => (b.yoy_delta || 0) - (a.yoy_delta || 0));
  else if (sort === "change-asc") items.sort((a, b) => (a.yoy_delta || 0) - (b.yoy_delta || 0));
  else if (sort === "value-asc") items.sort((a, b) => (a.value_usd || 0) - (b.value_usd || 0));
  else items.sort((a, b) => (b.value_usd || 0) - (a.value_usd || 0)); // value-desc (default)
  return (
    <div className="col-fill">
      <div className="panel-h">
        <h2><b className="panel-n num">{items.length}</b> {t.feedTitle}</h2>
        {tools && <div className="panel-h-tools">{tools}</div>}
      </div>
      <ul className="feed-list scrollx">
        {items.map((m, i) => {
          const name = lang === "en" ? m.name_en : m.name_vi;
          const color = sigColor(m.band, m.direction, true);
          const flowLabel = m.flow === "export" ? t.exportsLabel : t.importsLabel;
          return (
            <li key={`${m.code}-${m.flow}-${i}`} className="feed-item">
              <div className="feed-row1">
                <Link className="feed-link" href={`/country/${m.code}?hs=${hs}${lang === "en" ? "&lang=en" : ""}`}>{name}</Link>
                <span className="feed-pct" style={{ color }}>{bandArrow(m.band, m.direction)} {fmtPct(m.yoy_delta)}</span>
              </div>
              <div className="feed-row2">
                <span className={`flowtag ${m.flow}`}>{flowLabel}</span>
                <span className="feed-val">{fmtUSD(m.value_usd)}</span>
                <span className="feed-band" style={{ color }}>{bandLabel(m.band, lang)}</span>
                <span className="muted">{fmtPeriod(m.period, lang)}</span>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
