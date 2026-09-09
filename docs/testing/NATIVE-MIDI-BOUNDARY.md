# Native MIDI output boundary coordination

Status: required follow-up to the reproduced M-SYNC-009 master failure.
Owner: general-purpose emulator native dependency adapter, then Mosaic consumer.
Codex arbitration: `master-clock-candidate-review.json`. The independent-sync
candidate is retained under `candidates/` and rejected; production is restored.

## Contract and implementation order

1. Preserve official norns pin14bbeae8646c6717f6bb44c8cd60250bf94b6042 and current
   stock/candidate installations. Develop an explicit optional upstream patch;
   no default promotion and no Mosaic imports or conditionals. First inspect
   clock scheduler event publication and Lua resume argument handling. Add an
   exact scheduled beat/deadline and epoch identity without changing existing
   clock.sync return meanings. Observed callback time is not the deadline.
2. Add a generic cancellable subscription around native MIDI clock fanout.
   Dispatch snapshots participating outputs, executes before callbacks, sends
   F8, then executes after callbacks synchronously. Specify non-yielding callback
   enforcement, errors, registration/removal during dispatch, cleanup on script
   unload, and epoch/source changes. Existing clock output stays core-owned.
   Unsubscribed scripts retain existing behaviour. Verify arbitrary generic
   scripts with Mosaic absent before adding the application consumer.
3. Validate with a generic probe that delayed Lua delivery does not turn the
   callback's observed time into the musical origin. Exercise pending cancellation,
   repeated registration, multi-port fanout, callback failure, source/epoch change,
   and coincident versus intermediate subdivisions in controlled and real time.
   Keep a stock baseline that demonstrates the missing coordination capability.
4. Adapt Mosaic with explicit pending/running state and generation cancellation.
   Before a chosen boundary send Start; after F8 establish the supplied scheduled
   origin and pulse zero. Persistent after-boundary ownership must also order
   subsequent coincident notes after their F8. Intervening96-PPQN pulses use the
   native scheduler with exactly one owner per pulse; do not double-count on
   catch-up. Stop cancels pending/active subscriptions before releasing voices.
   Repeated pending local Start coalesces; local Start while running preserves
   existing playback. Incoming Start retains source epoch and repeated-start
   cleanup; forwarding must be explicitly tested. Source/output changes and
   unload must not leave callbacks referring to destroyed lattices.
5. Preserve no-output immediate local playback and ordinary Stop transport
   routing. Define behaviour on stock norns lacking the extension explicitly;
   do not silently claim fixed synchronization there or make Mosaic unable to
   load. Compare feasibility of upstream inclusion and a small capability-tested
   adapter before choosing this compatibility path. Never fork/copy clock.lua
   wholesale or replace core clocks with Mosaic logic.

## Acceptance and regression guards

- M-SYNC-009 unchanged receiver tick expectations0,6,12... and existing timing
  tolerances; all four phases in both modes, plus near-boundary queued delivery.
- Start/Stop before first boundary; Start/Stop/Start; duplicate pendingStart;
  no late notes, balanced releases, one Start per intended transport epoch.
- Multiple clock outputs and non-clock ports; routing follows explicit policy,
  all participating receivers agree without feedback or double clocking.
- Later notes, gates, phrase/bar wraps and tempo changes, not only startup.
- External acquisition/restart, source handoff, local Play against external
  clock, forwarding; rerun M-SYNC001..008 and affected TIM/recording guards.
- Unit/integration matrices for dispatch mutation, cancellation generations,
  exact subdivision ownership, delayed catch-up and Stop responsiveness.
  Restore the full520-test baseline with faithful mocks; no testing-only runtime
  bypasses. Seven independent receiver oracle tests must continue passing.
- One scoped Codex implementation review, generic native conformance, explicit
  source-bound evidence. No M5/default/release admission from this slice alone.

The core hook design is an arbitration recommendation pending implementation
proof, not a completed feature. If an existing official API can prove the same
ordering/deadline contract, prefer it and retain the failing/race baselines.
