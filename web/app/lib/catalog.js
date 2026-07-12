/**
 * catalog.js — everyday-words → HS lookup, two levels (plan §7.2).
 * @context  Search surfaces both the CATEGORY (HS-4 group, tag "Loại"/"Category") and the specific
 *           PRODUCTS under it (HS-6, tag "Sản phẩm"/"Product"). So "trà" lists Trà (category) +
 *           Trà đen, Trà xanh — the user can see the whole-category signal OR a specific product.
 * @done     Curated list with level + diacritic-insensitive search(); categories rank above products.
 * @limits   Data + pure search. No I/O.
 * @affects  Used by SearchBox (client) + page.js (covered vs locked routing).
 */

// level: "category" (HS-4 group) | "product" (HS-6). All covered = a snapshot exists.
export const CATALOG = [
  { hs6: "TOTAL", level: "category", name_en: "All products", name_vi: "Tất cả sản phẩm",
    synonyms: ["all", "total", "tất cả", "tat ca", "everything", "tổng"] },

  // Coffee
  { hs6: "0901", level: "category", name_en: "Coffee", name_vi: "Cà phê",
    synonyms: ["coffee", "cà phê", "ca phe", "cafe"] },
  { hs6: "090111", level: "product", name_en: "Coffee, green", name_vi: "Cà phê nhân",
    synonyms: ["green coffee", "cà phê nhân", "cà phê", "robusta", "arabica", "raw coffee"] },
  { hs6: "090121", level: "product", name_en: "Coffee, roasted", name_vi: "Cà phê rang",
    synonyms: ["roasted coffee", "cà phê rang", "cà phê"] },

  // Tea
  { hs6: "0902", level: "category", name_en: "Tea", name_vi: "Chè (trà)",
    synonyms: ["tea", "trà", "tra", "chè", "che"] },
  { hs6: "090240", level: "product", name_en: "Black tea", name_vi: "Trà đen",
    synonyms: ["black tea", "trà đen", "tra den", "chè đen", "trà"] },
  { hs6: "090210", level: "product", name_en: "Green tea", name_vi: "Trà xanh",
    synonyms: ["green tea", "trà xanh", "tra xanh", "chè xanh", "trà"] },

  // Rice
  { hs6: "1006", level: "category", name_en: "Rice", name_vi: "Gạo",
    synonyms: ["rice", "gạo", "gao"] },
  { hs6: "100630", level: "product", name_en: "Milled rice", name_vi: "Gạo xát",
    synonyms: ["milled rice", "white rice", "gạo xát", "gạo trắng", "gạo"] },
  { hs6: "100640", level: "product", name_en: "Broken rice", name_vi: "Tấm (gạo tấm)",
    synonyms: ["broken rice", "tấm", "gạo tấm", "gao tam", "gạo"] },

  // Seafood / crustaceans
  { hs6: "0306", level: "category", name_en: "Crustaceans", name_vi: "Giáp xác (tôm, cua)",
    synonyms: ["shrimp", "prawn", "tôm", "tom", "crab", "cua", "seafood", "thủy sản", "giáp xác"] },
  { hs6: "030617", level: "product", name_en: "Frozen shrimp", name_vi: "Tôm đông lạnh",
    synonyms: ["frozen shrimp", "tôm đông lạnh", "tôm đông", "tôm"] },
  { hs6: "0304", level: "category", name_en: "Fish fillets", name_vi: "Phi lê cá",
    synonyms: ["fish", "cá", "ca", "fillet", "phi lê", "pangasius", "cá tra"] },

  // Nuts
  { hs6: "0801", level: "category", name_en: "Nuts (cashew/coconut)", name_vi: "Hạt (điều, dừa)",
    synonyms: ["nut", "hạt", "cashew", "điều", "dừa", "coconut"] },
  { hs6: "080131", level: "product", name_en: "Cashew (in shell)", name_vi: "Điều thô",
    synonyms: ["cashew in shell", "điều thô", "hạt điều", "điều"] },
  { hs6: "080132", level: "product", name_en: "Cashew (shelled)", name_vi: "Điều nhân",
    synonyms: ["cashew shelled", "điều nhân", "hạt điều nhân", "điều"] },

  // Wood
  { hs6: "4401", level: "category", name_en: "Wood fuel", name_vi: "Nhiên liệu gỗ",
    synonyms: ["wood fuel", "củi", "cui", "nhiên liệu gỗ", "biomass", "chất đốt"] },
  { hs6: "440131", level: "product", name_en: "Wood pellets", name_vi: "Viên nén gỗ",
    synonyms: ["wood pellet", "pellet", "viên nén", "vien nen", "viên nén gỗ", "biomass"] },
  { hs6: "4407", level: "category", name_en: "Sawn wood", name_vi: "Gỗ xẻ",
    synonyms: ["sawn wood", "timber", "lumber", "gỗ xẻ", "go xe", "wood", "gỗ"] },

  // Spices
  { hs6: "0904", level: "category", name_en: "Pepper", name_vi: "Hạt tiêu",
    synonyms: ["pepper", "tiêu", "tieu", "hạt tiêu", "hat tieu", "black pepper"] },

  // Other Vietnam exports + global majors (categories)
  { hs6: "8517", level: "category", name_en: "Phones & telecom", name_vi: "Điện thoại & viễn thông",
    synonyms: ["phone", "smartphone", "điện thoại", "dien thoai", "telecom", "mobile"] },
  { hs6: "8542", level: "category", name_en: "Integrated circuits", name_vi: "Vi mạch (IC)",
    synonyms: ["chip", "ic", "integrated circuit", "vi mạch", "vi mach", "semiconductor", "chất bán dẫn"] },
  { hs6: "6109", level: "category", name_en: "T-shirts", name_vi: "Áo thun",
    synonyms: ["t-shirt", "tshirt", "áo thun", "ao thun", "shirt", "dệt may", "garment"] },
  { hs6: "6110", level: "category", name_en: "Knitwear", name_vi: "Áo len dệt kim",
    synonyms: ["sweater", "knitwear", "áo len", "ao len", "pullover"] },
  { hs6: "6403", level: "category", name_en: "Leather footwear", name_vi: "Giày da",
    synonyms: ["footwear", "shoes", "giày", "giay", "giày da", "leather shoes"] },
  { hs6: "9403", level: "category", name_en: "Furniture", name_vi: "Đồ nội thất",
    synonyms: ["furniture", "đồ gỗ", "do go", "nội thất", "noi that"] },
  { hs6: "4001", level: "category", name_en: "Natural rubber", name_vi: "Cao su tự nhiên",
    synonyms: ["rubber", "cao su", "natural rubber", "latex"] },
  { hs6: "0803", level: "category", name_en: "Bananas", name_vi: "Chuối",
    synonyms: ["banana", "chuối", "chuoi", "fruit"] },
  { hs6: "2709", level: "category", name_en: "Crude oil", name_vi: "Dầu thô",
    synonyms: ["oil", "crude", "dầu thô", "dau tho", "petroleum", "dầu"] },
  { hs6: "8703", level: "category", name_en: "Cars", name_vi: "Ô tô",
    synonyms: ["car", "ô tô", "o to", "vehicle", "automobile", "xe hơi"] },
  { hs6: "1201", level: "category", name_en: "Soybeans", name_vi: "Đậu tương",
    synonyms: ["soybean", "soy", "đậu tương", "dau tuong", "đậu nành"] },
  { hs6: "1511", level: "category", name_en: "Palm oil", name_vi: "Dầu cọ",
    synonyms: ["palm oil", "dầu cọ", "dau co", "palm"] },
];

const BY_HS = Object.fromEntries(CATALOG.map((c) => [c.hs6, c]));

export function lookup(hs6) {
  return BY_HS[hs6] || null;
}

// Lowercase + strip Vietnamese diacritics for forgiving matching ("trà" == "tra", đ → d).
export function norm(s) {
  return (s || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/đ/g, "d");
}

export function search(query, limit = 8) {
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
    // categories rank above their products at the same relevance
    .sort((a, b) => a.score - b.score || (a.c.level === "category" ? 0 : 1) - (b.c.level === "category" ? 0 : 1))
    .slice(0, limit)
    .map((r) => r.c);
}
