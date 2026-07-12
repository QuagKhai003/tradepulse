/**
 * format.js — display helpers + signal-band presentation (single source of truth for colours).
 * @context  Keeps money/percent formatting and band colour/label in ONE place so the map, tiles,
 *           and feed always agree. Bilingual band labels (plan §7.2 VN-first).
 * @limits   PURE presentation. No data fetching.
 * @affects  Used by WorldMap, MarketTile, SignalFeed.
 */

export function fmtUSD(v) {
  if (v == null) return "—";
  const abs = Math.abs(v);
  if (abs >= 1e9) return `$${(v / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `$${(v / 1e6).toFixed(0)}M`;
  if (abs >= 1e3) return `$${(v / 1e3).toFixed(0)}K`;
  return `$${v.toFixed(0)}`;
}

export function fmtPct(x) {
  if (x == null) return "—";
  const s = (x * 100).toFixed(1);
  return `${x >= 0 ? "+" : ""}${s}%`;
}

// Freshness stamp: turn a period into a plain "in 2024" / "năm 2024" (no source name).
// Annual 'YYYY', quarterly 'YYYY-Qn', monthly 'YYYYMM'.
const _MON = { vi: ["Th1","Th2","Th3","Th4","Th5","Th6","Th7","Th8","Th9","Th10","Th11","Th12"],
               en: ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"] };
export function fmtPeriod(period, lang = "vi") {
  if (!period) return "";
  const p = String(period);
  const inw = lang === "en" ? "in" : "năm";
  if (p.includes("-Q")) { const [y, q] = p.split("-"); return `${q} ${y}`; }
  if (p.length === 6 && /^\d+$/.test(p)) {
    const y = p.slice(0, 4), m = parseInt(p.slice(4), 10) - 1;
    return `${(_MON[lang === "en" ? "en" : "vi"][m] || "")} ${y}`;
  }
  return `${inw} ${p}`;
}

// Pick a country slot's sub-slot for the chosen grain (A/Q/M); fall back to the default slot when the
// product has no data at that grain (quarterly is bounded to core products).
export function slotFor(slot, freq) {
  if (!slot) return slot;
  return (slot.by_freq && slot.by_freq[freq]) || slot;
}

// Bands that qualify for the signal feed (moderate+); 'minor'/'none' are suppressed by design.
const FEED_BANDS = new Set(["surge", "collapse", "significant", "moderate", "new"]);
export function isFeedSignal(band) { return FEED_BANDS.has(band); }

export function fmtTons(kg) {
  if (kg == null) return null;
  const t = kg / 1000;
  if (t >= 1e6) return `${(t / 1e6).toFixed(2)}M t`;
  if (t >= 1e3) return `${(t / 1e3).toFixed(0)}K t`;
  return `${t.toFixed(0)} t`;
}

// Band metadata: bilingual MAGNITUDE label (no direction word — direction is carried by the
// arrow, colour, and signed %). Keeps "significant" a decline from reading as a rise.
export const BANDS = {
  surge:       { vi: "Bùng nổ",         en: "Surge" },
  significant: { vi: "Đáng kể",         en: "Significant" },
  moderate:    { vi: "Vừa",             en: "Moderate" },
  collapse:    { vi: "Sụp đổ",          en: "Collapse" },
  new:         { vi: "Tuyến mới",       en: "New lane" },
  minor:       { vi: "Nhẹ",             en: "Minor" },
  none:        { vi: "Chưa đủ dữ liệu", en: "No signal" },
};

export function bandLabel(band, lang) {
  const b = BANDS[band] || BANDS.none;
  return lang === "en" ? b.en : b.vi;
}

// Arrow reflects direction for magnitude bands; fixed glyph for surge/collapse/new.
export function bandArrow(band, direction) {
  if (band === "surge") return "▲▲";
  if (band === "collapse") return "▼▼";
  if (band === "new") return "★";
  if (band === "significant" || band === "moderate") return direction === "down" ? "▼" : "▲";
  return "";
}

// Colour by band + direction. Greens = growing demand, reds = shrinking.
export function bandColor(band, direction) {
  switch (band) {
    case "surge": return "#15803d";
    case "collapse": return "#b91c1c";
    case "significant": return direction === "down" ? "#ef4444" : "#22c55e";
    case "moderate": return direction === "down" ? "#fca5a5" : "#86efac";
    case "new": return "#8b5cf6";
    case "minor": return "#cbd5e1";
    default: return "#e2e8f0";
  }
}

export const MAP_NEUTRAL = "#eef2f7"; // countries with no covered data

// Strong, readable colour for signal TEXT. Direction carries meaning: green = rising, red = falling.
// `dark` returns brighter tints that clear 4.5:1 on the dark glass panels (the deep #15803d/#b91c1c
// and #64748b all fail on ~#0d142a); the light values stay readable on white.
export function sigColor(band, direction, dark = false) {
  if (band === "new") return dark ? "#a78bfa" : "#7c3aed";
  if (band === "minor" || band === "none") return dark ? "#9fb0d0" : "#64748b";
  if (direction === "down") return dark ? "#fb7185" : "#b91c1c";
  return dark ? "#4ade80" : "#15803d";
}
