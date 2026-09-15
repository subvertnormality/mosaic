# Final unit and integration hardening pass

Status: in progress; reconciled matrix and drift guard landed 2026-09-12. The
approved minimal final scope below supersedes further test expansion and review
work for this card.

Run after the planned emulator delivery and Mosaic behaviour campaign and before
the broad Mosaic refactor. Existing unit/integration tests remain useful during
delivery; this final pass systematically closes gaps left by the native campaign.
Do not mark the full goal complete until this card and the existing gates pass.

## Approved minimal final scope

H01 through H13 are frozen as completed evidence. Preserve their tests, stated
residuals and coverage claims, but do not add axes, samples, generated sequences,
pairwise arrays or Cartesian products to them. The completed matrices remain
refactor guards; they are not a standing request for more combinations.

The only remaining unit/integration work is:

1. align the Lua runner with the source revision under test and run the complete
   existing Lua suite with nonzero, source-bound collection;
2. run tests/behaviour/test_hardening_matrix.py; and
3. add one coroutine-level external-clock regression that issues Stop after the
   initial backlog yield and proves stale catch-up work does not continue.

No further reviewer, Paranoia, mutation, native, profile, performance or
combinatorial-expansion requirement applies to this final hardening card. Add a
new test only when a later refactor changes the seam it protects; that work belongs
to the affected refactor card, not to this baseline pass.

H14 is profile-dependent and deferred. Its retained software tests and behaviour
anchors remain evidence, but unavailable profile or hardware-oracle gaps do not
block this unit/integration card. H15 is owned by R01 and the performance ledger;
keep its existing fast regression test, but do not treat performance recipes,
measurements or real-time failures as unit/integration hardening work.

## Scope and choice of test layer

Build a matrix from the manual/cheat-sheet requirements, production modules,
existing unit/integration tests, behaviour cases, and known defect regressions.
For each domain record legal values, boundaries, invalid inputs where supported,
state transitions, interacting features, cheapest faithful test layer, and evidence.

The existing finite-domain, partitioned and generated evidence in the frozen rows
is retained as recorded. Do not extend it during this pass. Use unit tests for pure
transforms and integration tests when ownership, state, scheduling, persistence or
multiple modules matter only when the single remaining Stop/backlog regression
needs that composition.

Prioritise:

- Parameter locks, trig parameters and slides: sentinel inheritance, precedence,
  clearing, replacement, slot/channel/song isolation, interpolation rounding,
  wrap, probability/trigless controls, undo/redo and persistence.
- Scale merging and pitch arithmetic: every merge mode and legal discrete option,
  signed values, rounding, MIDI limits, scale/root/degree/rotation/transpose,
  pentatonic switches, masks, fixed notes and random/random-twos interactions.
- Musical timing: exact rational phase and release deadlines across clock rates,
  tempo changes, shuffle, queued transitions, repeat/reset policies, simultaneous
  events, repeated pitches, rests, nonpositive/fractional lengths and cancellation.
- State and persistence: undo branching/truncation, copy isolation, inactive and
  highest slots, legacy migrations, malformed range structures, failed IO at
  open/write/close boundaries, interrupted save/load, timer and callback cleanup.
- MIDI/configuration/mapping: finite codec and relative-control domains, bounds,
  accumulated deltas, routing, device reassignment and held-note ownership.
  Keep the Digitakt-specific exception confined to NRPN.

## Test quality and integration fidelity

Exercise actual production functions and composed production modules. Mock only
external boundaries necessary for isolation; do not replace the musical/state
logic under test with a parallel implementation. Reuse the pinned official Lua
libraries and actual scheduler/model components where the contract depends on
them. Check independent literal examples, algebraic invariants and event traces;
do not derive expected values by calling the function being tested.

Check both results and absence of unintended changes: wrong-channel writes,
mutation of copied data, leaked clocks/callbacks, missing or duplicate releases,
and stale state after a failed operation. Use fixed seeds and report failing
inputs so a generated counterexample can become a minimal permanent regression.
Keep existing native tests as user-visible integration anchors. They are not a
requirement to run native work for this final hardening card.

## Execution and completion

1. Confirm the runner uses the intended production revision; fail closed on a
   missing source module, hidden fetch, skip or zero collection.
2. Add the single external Stop/backlog coroutine regression, minimising any
   discovered failure before an isolated repair.
3. Run the complete existing Lua suite and tests/behaviour/test_hardening_matrix.py.
4. Publish source-bound results and the existing matrix; do not add review receipts,
   new coverage matrices or native/performance evidence to this card.

Done only when the source-bound existing suite, hardening guard and single
Stop/backlog regression pass. This card does not authorise the subsequent refactor;
it strengthens the prerequisites for that work.


## External-clock delayed callback responsiveness

The sole remaining regression is coroutine-level: inject a substantially delayed
external callback, issue Stop after the initial backlog yield, and verify stale
catch-up work does not continue. It must use the real lattice loop and retain
release/onset ordering. Cold acquisition normally reconciles only four lattice
pulses and is not evidence for this backlog path. Native Stop verification is
owned by the existing behaviour/performance gates, not this final hardening card.
