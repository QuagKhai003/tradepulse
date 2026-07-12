"use client";
/**
 * BrowseCountries.js — pill button that opens a searchable country list to drill into (plan §7.3).
 * @context  Alongside the product search: pick a country directly. Filterable; click → country page.
 * @limits   Client island; navigates on select.
 * @affects  Placed next to the search in HeroClient.
 */
import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

export default function BrowseCountries({ countries, lang, hs, label }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");

  const list = useMemo(() => {
    const nq = q.trim().toLowerCase();
    const sorted = [...countries].sort((a, b) =>
      (lang === "en" ? a.name_en : a.name_vi).localeCompare(lang === "en" ? b.name_en : b.name_vi));
    return (nq ? sorted.filter((c) => `${c.name_en} ${c.name_vi}`.toLowerCase().includes(nq)) : sorted).slice(0, 80);
  }, [countries, q, lang]);

  function pick(code) {
    setOpen(false);
    router.push(`/country/${code}?hs=${hs}${lang === "en" ? "&lang=en" : ""}`);
  }

  return (
    <div className="browse">
      <button type="button" className="browse-btn" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        <svg className="browse-globe" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" aria-hidden>
          <circle cx="12" cy="12" r="9" />
          <path d="M3 12h18" />
          <path d="M12 3a14 14 0 0 1 0 18a14 14 0 0 1 0-18" />
        </svg>
        {label}
      </button>
      {open && (
        <div className="browse-menu">
          <input className="browse-input" autoFocus value={q} onChange={(e) => setQ(e.target.value)}
                 onBlur={() => setTimeout(() => setOpen(false), 160)} placeholder="…" />
          <ul className="scrollx">
            {list.map((c) => (
              <li key={c.code}>
                <button type="button" className="browse-opt" onMouseDown={() => pick(c.code)}>{lang === "en" ? c.name_en : c.name_vi}</button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
