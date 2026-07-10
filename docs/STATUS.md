# STATUS — what's happening right now

> Single source of truth for the CURRENT moment. Update at the start and end of every
> session. History goes in `docs/progress/`, not here.

**Last updated:** 2026-07-10 (workflow adopted + merged to main; kit folder removed)

## Phase
**Stage 0 — validation (NO code per plan).** Plan §12–13: build nothing until the go/kill
gate passes. `main` holds product plan + the file-driven workflow docs. No app code yet.

## Active task
**Stage 0 — ADR-0001 — batch 0.1 NOT STARTED.** Workflow adopted + merged to `main`
(owner-approved 2026-07-10); repo now runs the file-driven loop (`docs/CONVENTIONS.md` §10).
**NEXT decision (owner):** run Stage 0 validation first (plan gate) OR start Phase 1 MVP
scaffolding now at owner's risk (write ADR-0002 first). See "Path to MVP" below.

## Next action (whoever picks this up)
- **Owner decision:** Stage 0-first (recommended by plan §12) vs. build-now. Drives which ADR opens.
- If Stage 0-first → ADR-0001 batch 0.1: hand-build the Vietnamese validation report (no code).
- If build-now → write ADR-0002 (Phase 1 batch plan), then branch `phase/1-etl-comtrade`.
- Confirm Golden Rule wording ("Inform, never match" — CLAUDE.md).
- Decide pilot-vertical fallback if pellet exporters go silent (tea/seafood/cashew — plan §15 Q1).

## Path to MVP (Phase 1 — see docs/ROADMAP.md, gated on Stage 0 GO)
Dependency order: 1.1 ETL(Comtrade→trade_flows) → 1.2 signal compute(+test) → 1.3 map+feed →
1.4 category search → 1.5 country drill-down → 1.6 profiles → 1.7 requirement pages →
1.8 watch/alerts+telemetry → 1.9 payments. Firm up in ADR-0002 before coding.

## Watch / before launch
- **Gate:** no MVP code until Stage 0 GO (≥5 substantive replies AND ≥3 willing to pay). Plan §12.
- Pilot-vertical fallback undecided if pellet exporters don't respond (tea/seafood/cashew) — plan §15 Q1.
- Price point (200k vs 500k VND) tested in Stage 0 conversations — plan §15 Q2.
- Comtrade rate limits: cache raw pulls aggressively when Phase 1 starts.
