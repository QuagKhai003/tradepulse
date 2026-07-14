# ADR-0005 — Sellers are derived from won contracts, not from listings

- **Status:** Accepted — 2026-07-14 (owner's insight)
- **Context:** the app had a "Companies" tab fed by a hand-curated file that existed for exactly one
  product (wood pellets). Asked where the seller list was for everything else, the honest answer was
  "there isn't one" — and the reason mattered.

## The problem the owner named
> *"sellers usually do the business on their own way — not everybody goes outside and tells 'I am
> selling this'. They find buyers, contact them, and keep doing the job."*

There is **no public feed of sellers offering goods.** Sellers do not advertise; supply relationships
are private. Any "seller directory" we scraped would be either (a) a marketing list, or (b) invented.
So a seller list cannot be *collected* — it has to be **derived from an event that is public**.

## Decision
A seller is **an organisation that has WON a public contract for this product.** Nothing else.

EU TED publishes award ("result") notices naming `winner-name`, `winner-country`,
`winner-decision-date` and the contract value. That is a public, dated, citable record that a company
*sells* this product. So:

- **Past orders** = the award notices themselves (buyer and seller both named, value where TED gives
  one unambiguous figure, link to the notice).
- **Sellers** = those awards aggregated by winner: contracts won, last win, who they sold to.
- **Buyers** = open tenders (a buyer with a live deadline) — unchanged.

Three tabs, three different questions, one product: **Buyers · Sellers · Past orders** (alongside
Signals, which stays the aggregate trade view).

## Why this holds the Golden Rule
Both parties are named **only because the award notice is a public record**, and all we hand over is
that record. TED also exposes `winner-email`, `winner-person`, `winner-tel` — we never store or
display them. The user reads a published fact and acts on it themselves; we introduce no one.

## Consequences
- **Coverage is EU public procurement.** A seller who has never won an EU public contract does not
  appear. That is a *coverage limit, not a judgement* — and the UI must say so, or absence reads as a
  verdict on the company.
- **Value is often absent.** A multi-lot notice reports per-lot figures that cannot be attributed to
  one winner, so we show no number rather than a wrong one. `build_sellers` likewise refuses to sum
  across currencies.
- Curated profiles (`content/companies/`) still exist and are merged in, badged as verified — a seller
  can be evidenced either way.
- **Next sources to widen it:** US SAM.gov awards, UK Contracts Finder, World Bank / UN contract
  awards. Same shape (winner named on a public award), so the same pipeline absorbs them.
