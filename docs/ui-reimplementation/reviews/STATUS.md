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

## Round 2

Pending. `../tools/run_paranoia_fable.py` is set to round 2 of the same lineage.
Run it from a clean committed checkout with the paranoia-local virtualenv Python.

`LOCAL-PREFLIGHT.md` is an independent, explicitly non-Fable audit.
