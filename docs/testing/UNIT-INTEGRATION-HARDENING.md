# Final unit and integration hardening pass

Status: in progress; reconciled matrix and drift guard landed 2026-09-12. Test expansion and final validation remain open.

Run after the planned emulator delivery and Mosaic behaviour campaign and before
the broad Mosaic refactor. Existing unit/integration tests remain useful during
delivery; this final pass systematically closes gaps left by the native campaign.
Do not mark the full goal complete until this card and the existing gates pass.

## Scope and choice of test layer

Build a matrix from the manual/cheat-sheet requirements, production modules,
existing unit/integration tests, behaviour cases, and known defect regressions.
For each domain record legal values, boundaries, invalid inputs where supported,
state transitions, interacting features, cheapest faithful test layer, and evidence.

Exhaust finite, affordable domains: steps, pattern/channel/song slots, pitch and
velocity values, length choices, parameter sentinel/bounds, scale and chord
choices, and meaningful combinations. Calculate matrix cardinality before
execution. Use unit tests for pure transforms and invariants; use integration
tests when ownership, state, scheduling, persistence or multiple modules matter.
For large or unbounded products, record the residual domain and use boundary
partitions, justified pairwise/higher-order combinations, and deterministic
generated sequences with retained seeds. Do not call sampled coverage exhaustive.

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
Keep existing native tests as user-visible integration anchors. A cheap matrix
can extend their combinatorial depth but cannot substitute for an unimplemented
documented workflow or establish emulator timing fidelity by itself.

## Execution and completion

1. Produce `unit-integration-hardening-matrix.json` with owners, domains,
   cardinalities, selected test layers, existing evidence and unresolved gaps.
2. Give the matrix one proportionate Codex-only Paranoia pass focused on omitted
   combinations, circular oracles and mocked-away interactions. Use the local
   review budget; no per-matrix mutation campaign or dual-vendor review.
3. Add and run the matrices. Minimise discovered failures, establish a regression,
   make isolated candidate fixes, and run the affected native anchors when a fix
   changes observable behaviour. Preserve all previously authorised semantics.
4. Run the final unit/integration suite with pinned dependencies, nonzero
   collection, explicit skip handling and source-bound results. Run required
   native and release checks affected by these changes.
5. Publish `unit-integration-hardening-validation.json`, the matrix, tests and
   fixes on the authorised branch. Record full finite-domain coverage separately
   from partitioned/generated coverage, with every residual explicitly stated.

Done only when the matrix is reconciled, all required tests pass, discovered
defects are resolved, any material review findings are addressed, and the
original behaviour/emulator gates still pass. This card does not authorise the
subsequent refactor; it strengthens the prerequisites for that work.


## External-clock delayed callback responsiveness

Required follow-up from Codex review01a08750-93e8-7213-a7d0-c7607971ab6d.
The external lattice currently reconciles all elapsed pulse indices in one loop.
Inject a substantially delayed callback at the coroutine/unit boundary, measure
work before yielding, and verify that Stop can interrupt backlog processing.
If a work budget is needed, choose it from the responsiveness measurement and
yield between bounded batches without losing/duplicating pulse indices or
reversing release/onset order. Verify the native Stop path too. Cold acquisition
normally reconciles only four lattice pulses; it is not evidence for large
backlog responsiveness. This follow-up remains open before full goal closure.
