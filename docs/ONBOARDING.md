# ONBOARDING

Welcome. This routes you to the right files by role. Read `CONVENTIONS.md` either way — it's
the contract everyone follows.

## Everyone, first 10 minutes
1. `CLAUDE.md` (repo root) — what this is + the **Golden Rule** ("Inform, never match" — never violate).
2. `docs/STATUS.md` — what's happening right now + what's next.
3. `docs/ROADMAP.md` — the phases and where we are.
4. `trade-signal-terminal-plan.md` — the full product vision (scope source of truth).

## Where we are right now
**Stage 0 — validation, NO code.** Nothing is built. The first real work is a hand-made
report (ADR-0001), not engineering. Read that ADR before assuming there's a codebase.

## By role (once Phase 1 starts)
- **Data / ETL dev** → `etl/`; external deps (Comtrade, national stats, scrapers) go behind a
  seam (`CONVENTIONS.md` §11). Raw-before-transform. Cache aggressively (Comtrade rate limits).
- **Core / signal dev** → signal math is PURE + DETERMINISTIC (plan §6). Every change ships an
  offline test. No LLM in the number path — the Golden Rule's engineering half.
- **Backend / API dev** → `docs/DATA_MODEL.md` for the schema + contracts.
- **Frontend dev** → `web/`; Next.js SSR for SEO; MapLibre/D3 choropleth. VN-first i18n from day one.
- **Content / curation (Layer 3)** → `content/`; one markdown page per product × market.
  No item without an official source link + verified date. This is a curation business.

## Your first task
Pick the first unchecked batch in the active ADR (`docs/decisions/`), branch from `main`, and
follow the build loop in `docs/CONVENTIONS.md` §10. Finish per the "done" definition
(§8). **Do not merge without the owner's approval.**
