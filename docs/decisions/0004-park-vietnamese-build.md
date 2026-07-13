# ADR-0004 — Park the Vietnamese build (English-only for now)

- **Status:** Accepted — 2026-07-14 (owner call)
- **Context:** plan §10.4 and ADR-0002 set *Vietnamese first, English second* — the wedge is that
  incumbents sell English databases to analysts while our reader is a Vietnamese factory owner.

## Decision
Ship **English-only** until the catalog is translated. `i18n.VI_ENABLED = false`; every page resolves
its language through `resolveLang()`, which returns `"en"` while the flag is off, and the VI/EN
switches do not render. The Vietnamese string table stays in `lib/i18n.js`, untouched.

## Why
The catalog grew from 32 to **1,240 products**, and only 32 have Vietnamese names — the other 1,208
carry their English HS heading. So the "Vietnamese" UI was already showing English product names on
most screens: chrome in Vietnamese wrapped around English content. That reads as unfinished, and it is.
Tenders make it worse: EU TED titles arrive in the buyer's own language, so an all-Vietnamese page was
never on the table anyway. One honest language now beats two half-languages.

## Consequences
- The VN wedge is **paused, not abandoned** — it comes back the moment product names are translated.
- Turning it back on is one line (`VI_ENABLED = true`); the strings and the `lang` plumbing all remain.
- **Blocker to un-park:** Vietnamese names for the 1,208 HS4 headings (source: Vietnam Customs'
  published HS nomenclature — official, citable, matches the Golden Rule's "every source cited").
- Until then, `t("vi")` is unreachable in the app; the vi table is only exercised by its own tests.
