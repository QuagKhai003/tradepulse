/**
 * GlobalFeed.js — worldwide signal feed, both flows, filtered by the export/import/all toggle.
 * @context  The side panel (plan §7.1): every country's moderate+ signal, export or import, ranked
 *           by severity then value. Each row tags its flow so the user knows which side moved.
 * @limits   Presentation only; snapshot.feed is pre-sorted.
 * @affects  Rendered on page.js from snapshot.feed + the active flow.
 */
import Link from "next/link";
import { bandArrow, bandColor, bandLabel, fmtPct, fmtUSD } from "../lib/format.js";

export default function GlobalFeed({ feed, flow, lang, t, hs }) {
  const items = flow === "all" ? feed : feed.filter((f) => f.flow === flow);
  return (
    <aside className="feed">
      <h2>{t.feedTitle}</h2>
      <p className="feed-note muted">{t.feedNote}</p>
      {items.length === 0 && <p className="muted">—</p>}
      <ul>
        {items.map((m, i) => {
          const name = lang === "en" ? m.name_en : m.name_vi;
          const color = bandColor(m.band, m.direction);
          const flowLabel = m.flow === "export" ? t.exportsLabel : t.importsLabel;
          return (
            <li key={`${m.code}-${m.flow}-${i}`} className="feed-item">
              <span className="dot" style={{ background: color }} />
              <div className="feed-body">
                <div className="feed-top">
                  <Link className="feed-link" href={`/country/${m.code}?hs=${hs}${lang === "en" ? "&lang=en" : ""}`}>{name}</Link>
                  <span className="feed-band" style={{ color }}>
                    {bandArrow(m.band, m.direction)} {bandLabel(m.band, lang)}
                  </span>
                </div>
                <div className="feed-sub muted">
                  <span className={`flowtag ${m.flow}`}>{flowLabel}</span>
                  {" "}{fmtUSD(m.value_usd)} · {fmtPct(m.yoy_delta)} · {m.period}
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
