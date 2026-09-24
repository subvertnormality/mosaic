# Fable plan review status

The user explicitly approved transferring Mosaic's private plan and source to
Anthropic Claude Fable for this Paranoia review.

## Round 1 (24 September 2026)

`critique_plan`, `engine=claude`, `model=claude-fable-5-1`, `effort=high`,
`propose_patch=true`, lineage `mosaic-ui-reimplementation-20260924`. It ran from a
clean clone of `codex/1.4.0` at `0b3b7148`. The result is
`fable-plan-round1.md`: 1 blocker, 12 major, 9 minor, and a plan-only patch
proposal.

Root cause of the blocker: the package had been inventoried against a Windows
working tree that held uncommitted stale copies of the Rhythm Doctor sources and
README (≈ `c74aaea0`). The package is now baselined on commit `56a9ba23`
(`source-inventory.json#/baseline = commit`).

The findings were verified against committed source and repaired directly in
`spec.json`, `source-inventory.json`, `fixtures.json`, `code/screen.lua`,
`tools/` and `tests/`, not deferred as plan obligations. Corrections to the review
recorded in the spec:

- Lane selection is never transport-gated.
- REANALYSING routes to R04, not R06/R07/R12.
- The scale-clock wrong-channel write is not live, because the Scale page forces
  channel 17.
- Merge/Harmony child screens do not observe holds in place; like every edit
  screen they show the family while held and return on release.
- C06 has no K3 detail route in source; the prose was removed rather than
  inventing one.

Intentional interaction changes, chosen for a consistent UX (E2 selects, E3
changes, K2 backs out, K3 confirms, a hold shows the edit family then returns),
are listed in
`spec.json#/test_migration/documented_interaction_changes`.

## Round 2 (24 September 2026)

Same lineage, `model=claude-opus-5-5`, `effort=high`, against `fe6dc8c9`. The
result is `plan-round2-claude-opus-5-5.md`. It raised no findings, and structural
debt is 0 open. Convergence is blocked only by:

- five external norns claims left unverified. Their quoted sources support them:
  monome docs, and `lua/core/menu.lua` `_norns.key` for K1;
- a required cold final regression pass.

No patch was proposed.

## Status: converged by owner decision (24 September 2026)

The owner accepted the plan as converged after round 2. The tool gate stays
open on two items:

- the five unverified external claims, whose quoted sources support them;
- the cold final regression pass.

Both are recorded here as knowingly waived. Paranoia's own lineage state was
not edited and still reports BLOCKED. Re-running the review in this lineage
would start from that state.

`LOCAL-PREFLIGHT.md` is an independent, explicitly non-Fable audit.
