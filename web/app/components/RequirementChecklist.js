/**
 * RequirementChecklist.js — the §8 requirements table (the paid core's centrepiece).
 * @context  Each row cites an official source + verified date (guaranteed present by the loader).
 *           This is what an exporter checks off before shipping; wrong data has real cost (S-001).
 * @limits   Presentation only.
 * @affects  Rendered by app/requirements/[market]/page.js.
 */
const MANDATORY = {
  "yes":         { vi: "Bắt buộc",       en: "Mandatory",  cls: "req-yes" },
  "de-facto":    { vi: "Trên thực tế",   en: "De facto",   cls: "req-def" },
  "phasing-in":  { vi: "Đang áp dụng",   en: "Phasing in", cls: "req-phase" },
};

export default function RequirementChecklist({ items, lang, t }) {
  return (
    <table className="reqtable">
      <thead>
        <tr>
          <th>#</th>
          <th>{t.requirement}</th>
          <th>{t.type}</th>
          <th>{t.mandatory}</th>
          <th>{t.evidence}</th>
          <th>{t.source}</th>
          <th>{t.verified}</th>
        </tr>
      </thead>
      <tbody>
        {items.map((r) => {
          const m = MANDATORY[r.mandatory] || MANDATORY["de-facto"];
          return (
            <tr key={r.seq}>
              <td className="muted">{r.seq}</td>
              <td className="req-text">{lang === "en" ? r.text_en : r.text_vi}</td>
              <td className="muted">{r.type}</td>
              <td><span className={`req-badge ${m.cls}`}>{lang === "en" ? m.en : m.vi}</span></td>
              <td className="muted small">{lang === "en" ? r.evidence_en : r.evidence_vi}</td>
              <td><a href={r.source_url} target="_blank" rel="noopener noreferrer">{r.source}</a></td>
              <td className="muted num">{r.verified_date}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
