/**
 * catalog.js — everyday-words → HS lookup (plan §7.2). Hand-mapped, NOT generic classification.
 * @context  Users search in plain Vietnamese/English; we map to HS behind the scenes and show the
 *           code as an educational badge. Covered products drill into data; uncovered ones show a
 *           locked "coming soon — request it" page whose clicks are demand telemetry (plan §7.6).
 * @done     A small curated list (pilot vertical covered; candidate verticals locked) + a
 *           diacritic-insensitive search() so "trà" and "tra" both match.
 * @todo     Grow toward the 30–50 codes across covered verticals as Stage-0/telemetry picks them.
 * @limits   Data + pure search. No I/O.
 * @affects  Used by SearchBox (client) + page.js (covered vs locked routing).
 */

// covered=true means Layer-1 data exists for it today (pilot vertical only).
export const CATALOG = [
  { hs6: "440131", covered: true,  name_en: "Wood pellets",   name_vi: "Viên nén gỗ",
    synonyms: ["wood pellet", "pellet", "viên nén", "vien nen", "biomass", "chất đốt sinh khối"] },
  { hs6: "440710", covered: true,  name_en: "Sawn wood",      name_vi: "Gỗ xẻ",
    synonyms: ["sawn wood", "timber", "lumber", "gỗ xẻ", "go xe", "wood"] },
  { hs6: "090240", covered: true,  name_en: "Black tea",      name_vi: "Chè (trà) đen",
    synonyms: ["tea", "black tea", "trà", "tra", "chè", "che"] },
  { hs6: "090111", covered: true,  name_en: "Coffee",         name_vi: "Cà phê",
    synonyms: ["coffee", "cà phê", "ca phe", "robusta", "arabica"] },
  { hs6: "030617", covered: true,  name_en: "Frozen shrimp",  name_vi: "Tôm đông lạnh",
    synonyms: ["shrimp", "prawn", "tôm", "tom", "seafood", "thủy sản", "thuy san"] },
  { hs6: "080131", covered: true,  name_en: "Cashew (in shell)", name_vi: "Hạt điều",
    synonyms: ["cashew", "hạt điều", "hat dieu", "điều", "dieu", "nut"] },
  { hs6: "100630", covered: true,  name_en: "Milled rice",    name_vi: "Gạo",
    synonyms: ["rice", "gạo", "gao"] },
];

const BY_HS = Object.fromEntries(CATALOG.map((c) => [c.hs6, c]));

export function lookup(hs6) {
  return BY_HS[hs6] || null;
}

// Lowercase + strip Vietnamese diacritics for forgiving matching ("trà" == "tra").
export function norm(s) {
  return (s || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/đ/g, "d"); // đ -> d
}

export function search(query, limit = 6) {
  const q = norm(query).trim();
  if (!q) return [];
  return CATALOG
    .map((c) => {
      const hay = [c.name_en, c.name_vi, ...c.synonyms].map(norm);
      const exact = hay.some((h) => h === q);
      const starts = hay.some((h) => h.startsWith(q));
      const has = hay.some((h) => h.includes(q));
      const score = exact ? 0 : starts ? 1 : has ? 2 : 99;
      return { c, score };
    })
    .filter((r) => r.score < 99)
    .sort((a, b) => a.score - b.score || (b.c.covered - a.c.covered))
    .slice(0, limit)
    .map((r) => r.c);
}
