/**
 * TenderList.js — FORWARD demand: public buyers with an open tender for this product (plan §9.2).
 * @context  The signal feed says where demand moved (past). This says who is buying NOW — buyer
 *           organisation, country, deadline, and a link to the official EU TED notice.
 * @golden   Inform, never match: public buying ORGANISATION + the official notice link ONLY. No
 *           contact person, no introduction, no brokering. The user acts on the public notice.
 * @limits   Presentation only; the ETL already filtered to still-open notices.
 * @affects  Rendered in the right panel of HeroClient when the "Đấu thầu" tab is active.
 */
import { fmtDeadline } from "../lib/format.js";

export default function TenderList({ tenders, lang, t, tools }) {
  const list = tenders || [];
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
            return (
              <li key={x.id} className="feed-item">
                <div className="feed-row1">
                  <a className="feed-link" href={x.url} target="_blank" rel="noopener noreferrer">
                    {x.buyer || x.title}
                  </a>
                  <span className={`tender-due ${due.soon ? "soon" : ""}`}>{due.label}</span>
                </div>
                <div className="feed-row2">
                  <span className="flowtag import">{x.buyer_country}</span>
                  <span className="tender-title muted">{x.title}</span>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
