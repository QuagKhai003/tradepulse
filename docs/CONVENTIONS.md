# CONVENTIONS — how we keep this repo production-grade

Assume **many people work here** and that **wrong data has real cost** (a bad requirement
rejects a container). Optimise for a stranger finding their way. These rules are mandatory.

## 1. Folder & file structure
- **Split by responsibility into folders.** A folder = one job (`etl/`, `web/`, `content/`).
- **Keep files small.** Soft cap **~200 lines**. Past that, or doing two jobs → split it.
- One concept per file; name the file after the concept.
- No "utils" dumping ground. If something needs a home, give its category a folder.
- Layer-3 requirement pages: **one markdown file per product × market** under `content/`.

## 2. Every source file starts with a header brief
```
<Title> — one line.
@context  What this file is and why it exists.
@done     What is implemented here.
@todo     What's left (or "—").
@limits   Hard constraints (e.g. PURE: no network/IO; DETERMINISTIC: no LLM in the number path).
@affects  What it depends on / is depended on by.
```
Use the comment syntax of the language. Update the header when behaviour changes.

## 3. Two always-current "what's happening" files
- **`docs/STATUS.md`** — the truth for *right now* (active task, next, blockers). Update at
  the start and end of every session.
- **`docs/progress/`** — the history (changelog), one file per month (`YYYY-MM.md`), newest on top.
  Log **all** progress here — features, minor fixes, bugs, data notes, decisions. Nothing too small.

## 4. Keep the model current
- **`docs/DATA_MODEL.md`** — entities/types/tables + relationships. Update whenever you add
  or change a class, type, or table.

## 5. Decisions & issues are logged, not remembered
- Non-obvious choice → an ADR under `docs/decisions/` (one file per decision), linked from
  `docs/decisions/README.md`.
- Bug/limitation → log in `docs/BUGS.md` immediately.

## 6. Data & signal discipline (project-specific, non-negotiable)
- **Deterministic signals only.** Signal math is a pure function of stored data (plan §6). Ships
  a deterministic offline test. No LLM in the number path.
- **Cite every requirement.** No Layer-3 item without an official source link + verified date.
- **Honest timestamps.** Every figure labeled with its publication period + date. Never imply real-time.
- **One mirror side per view.** Default importer-reported; state it (plan §6.4).
- **Raw before transform.** Store raw pulls before transformation; computation reproducible from them.

## 7. Tests
- Core/logic changes ship a deterministic offline test (signal bands, HS mapping, page diffs).
- Network/integration tests (live API pulls, scrapers) are marked separately and never gate the fast loop.

## 8. Definition of "done"
1. Code + header brief updated. 2. Tests green. 3. `STATUS.md` + `progress/` (+ `DATA_MODEL.md`
   if types changed) updated. 4. ADR batch ticked; new decision/limitation logged if any.

## 9. Git (overrides the kit's "merge when green")
- **Always branch.** Never commit straight to `main`. One logical unit per branch.
- **Naming:** `feature/<slug>`, `fix/<slug>`, `phase/<n>-<slug>`, `docs/<slug>`.
- **Conventional commits:** `feat(scope): …`, `fix: …`, `refactor: …`, `docs: …`, `chore: …`.
  Body explains the *why* when not obvious. **No AI/co-author attribution trailers.**
- **Never merge without the owner's explicit approval.** Never push without approval.
- Don't skip hooks or bypass signing unless asked.
- **Gitignore dev/product-build/testing artifacts + secrets + re-pullable data** (see `.gitignore`).

## 10. The build loop (one batch per cycle)
1. **Orient** — read `STATUS.md` (active task) → the ADR's first unchecked batch → `git log`
   + current branch → this file → `CLAUDE.md` (the Golden Rule).
2. **Branch** — `git checkout main && git checkout -b <type>/<n>-<slug>` (one batch per branch).
3. **Implement** — follow the ADR + these conventions. Reuse existing patterns. Header brief on new files.
4. **Verify** — tests green (offline); for UI, build + lint clean. Deterministic test for any core/logic change.
5. **Docs in the SAME batch** — `STATUS.md` (active + next), `progress/YYYY-MM.md` (newest on
   top), `DATA_MODEL.md` if types changed; tick the batch `[ ]` → `[x]` in the ADR.
6. **Commit** (conventional, no AI attribution). **Do NOT merge — await owner approval.**
7. Roomy context + more batches → next. Context large → stop after commit; disk resumes cleanly.

## 11. The seam pattern (external dependencies)
Put every external dependency (Comtrade, national stats, scrapers, DB, email, payments) **behind
an interface** with a real *local* impl now + a *documented* production swap later. Ship value
today without heavy infra; swap impls with no caller changes. Raw-before-transform still holds.
