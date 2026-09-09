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

## Coordinated output integration checkpoint

The optional candidate04 native boundary API now has a Mosaic consumer. It emits
Start before the chosen F8, owns coincident lattice pulses after F8, and schedules
intermediate96-PPQN pulses using exact deadlines capped before the next boundary.
Stop cancels the subscription/thread; pending/running local Start coalesces while
explicitly reinitialized disabled lattices can start. Stock norns still loads and
uses immediate playback, with an explicit master-phase limitation; the sync fix
is not claimed without the optional native capability.

All14 affected D/R runs,520 existing units and6 adapter scenarios pass. Source
and manifests: midi-boundary-integration-validation.json. Codex review
01a08785-156e-7a81-bc0b-03fed3a76d2e holds acceptance for shared-clock failure on a
subscriber error and stale queued scheduler state across reset. The latter is
reproduced natively: resetting to0 leaves the next deadline at100.5beats.
Resolve these native blockers before admission, then forwarding/multi-port,
rapid lifecycle, gate/wrap/tempo and the remaining external synchronization matrix.
The original defect baseline remains retained; this is a partial candidate.

## Candidate07 review fixes

Queued/running scheduler state is now distinguished. Reset/source changes rearm
waiting resumes and reject stale queued sync delivery; running coroutines rebase
their next sync. Cancellation and sleep independence have explicit C guards.
Original queued-reset failure is retained; native old04 fails and06passes in D/R.
Candidate07 retains the same scheduler source as06.

Faulting output subscriptions are disabled individually. get_output_error(id)
returns a copy of the retained phase/message diagnostic until cleanup; errors are
also printed. Optional on_error(message,phase,id) may clean up but cannot yield.
Its failures are isolated too. Formatting an arbitrary error value is protected
and has a fallback; subscriber and handler unprintable-error tests pass in Lua
and native D/R. Healthy subscribers and F8 continue. Logical output IDs are
snapshotted per dispatch; native vport device bindings remain resolved at send
time, so remapping needs its remaining acceptance tests.

Codex follow-up01a08799-74cf-7b20-8d9e-de45fb8953c9 confirmed queued-reset correction
and identified the formatter follow-up. That exact negative/positive regression
and native D/R checks now pass. Mosaic faults invoke cancellation and existing
Stop cleanup;520units and7adapter scenarios pass. The14-case D/R matrix passed
on06; four scoped Mosaic startup/restart runs pass on07 after cleanup wiring.
See emulator midi-boundary-fixes-validation.json and Mosaic midi-boundary-fault-cleanup-validation.json for source-bound evidence and limitations.

The builder now applies upstream scheduler patches before the verified existing
controlled-step extraction. Candidate05's failed build log is retained;06/07
build successfully. No stock/default installation or runtime lock was promoted.
Next: rapid transport lifecycle/direct init/reset, forwarding and multiple-output
routing/remapping, intermediate notes/gates/wrap/tempo matrices, then the other
documented emulator/manual/final hardening gates. This is not full acceptance.
