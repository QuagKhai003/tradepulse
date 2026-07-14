# ADR-0006 — Sellers are real exporters (approval registries), not contract winners

- **Status:** Accepted — 2026-07-14 (owner's correction). Refines ADR-0005.
- **Context:** ADR-0005 derived "Sellers" from contract awards (who WON a public tender). The owner
  spotted the flaw: *"the seller tab is actually selling, not won-contract — if the seller already won
  the contract it would appear in past orders."*

## The problem
Award-derived sellers and "Past orders" are the **same data** — the awards, shown twice (once as
individual contracts, once aggregated by winner). So "Sellers" wasn't answering "who sells this", it
was answering "who won a contract", which the Past-orders tab already does. Redundant, and misleading.

## Decision
The three market tabs answer three *distinct* questions, from three sources:
- **Buyers** = open EU tenders (a public buyer with a live deadline). — EU TED.
- **Past orders** = awarded contracts (both parties named, value). — EU TED awards.
- **Sellers** = companies **APPROVED to export** the product, from official approval registries —
  independent of any contract. A seller here is a real exporter, evidenced by an approval number.

Sellers no longer come from awards. `export.build_sellers_web` reads `registry_sellers`, not the
award table. `build_sellers` (award aggregation) stays only for its unit test; it no longer feeds the
web.

## Why registries
Sellers don't advertise, but **destination markets publish the foreign establishments they approve to
export to them** — naming the company, an approval number, activity and address. Public, citable,
free: exactly Layer-2 evidence, and it fits the Golden Rule (public org + approval + source +
verified date; never a contact person).

## Phasing (owner chose "everything, phased")
- **Phase 1 (done):** EU DG SANTE (TRACES NT), keyless JSON, licence 2011/833/EU. Animal-origin only,
  so it covers **seafood + honey** among our products. Live: **2,219 approved exporters across 20
  countries, incl. 137 Vietnamese** (100 fishery + honey). A DG SANTE *section* maps to the HS products
  it covers (`config.SELLER_SECTIONS`); the API caps at 100 establishments/section (page param ignored)
  — logged, not silently truncated.
- **Phase 2 (needs free keys):** USDA Organic INTEGRITY (coffee/tea/cashew/rice certified sellers,
  api.data.gov key), Korea MFDS (data.go.kr key). UK Defra approved-establishment XLSX (keyless) is a
  fast-follow. FSC/PEFC for wood pellets (non-governmental but citable).

## Consequences
- **Coverage is honest and uneven.** Seafood products show real exporters now; coffee/rice/cashew/tea/
  wood pellets show an empty state that says *why* ("no exporter registry for this product yet —
  seafood covered, more sources coming"), not a fake list.
- A registry seller carries approval number + activity + city + verified date + a source link, so every
  name is reproducible and cited.
- The old award-seller redundancy is gone: Sellers and Past orders are now genuinely different tabs.
