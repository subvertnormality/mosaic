# Bidirectional MIDI clock and transport synchronisation

Status: mandatory, user-requested regression priority. Complete before the broad
Mosaic refactor and full goal closure. Existing M-TIM-003/004 and recording-clock
tests provide starting evidence, not completion of this requirement.

Reported symptom: starting an external instrument did not reliably start Mosaic
in musical alignment. Test both external-master/Mosaic-follower and
Mosaic-master/external-follower operation through native runtime MIDI paths.

## Independent musical reference

Use a scripted external instrument with an independently computed 24-PPQN clock
and transport timeline. Retain the exact submitted bytes, intended deadlines,
native receipt times, emitted MIDI and screen/grid feedback. For the reverse
direction, implement a small independent receiver that consumes Mosaic's actual
outgoing clock/transport bytes and compares its beat/bar position with Mosaic's
note output. Never call Mosaic's scheduler to compute expected results.

Assert absolute first-note/beat alignment to the external transport/clock
timeline, not just subsequent intervals or average BPM. Do not rebase the oracle
on Mosaic's first emitted note: that can conceal the reported startup offset.
Specify the Start/first-Clock phase convention from pinned upstream behaviour
and the chosen fixture timeline before execution. Exercise both immediate and
one-clock-period-delayed first clocks, and clocks already running before Start.
Document any supported latency separately from musical phase and drift. Keep
exact controlled expectations and the existing justified real-time bounds;
do not widen tolerances merely to pass. Physical hardware is not an acceptance
prerequisite, and software evidence is not a claim of hardware measurement.

## Required scenarios

1. Cold and warmed startup in both directions; Start at multiple sub-clock
   phases, first-clock gaps, and repeated Start trials to expose phase-dependent
   alignment. Check first note, first beat, first bar and subsequent phrase wraps.
2. Stop during notes/rests, silence while stopped, balanced note releases,
   Start resetting the intended position, and Continue retaining the intended
   position. Check the actual pinned upstream/Mosaic support for Song Position
   Pointer; test supported positioning or explicit unsupported behaviour rather
   than silently treating it as Start.
3. Incoming clock before/after transport, duplicated Start/Stop, source changes,
   disconnect/reconnect, clock loss and resumption, wrong input ports, and
   multiple connected devices. Ensure no clock feedback loop or double counting.
4. Stable low/normal/high tempos, live tempo changes, fractional pulse divisions,
   swing/shuffle, short and long song lengths, repeats, slot changes and multiple
   channel rates. Include held notes, slides and realtime keyboard recording
   around the first external beat and later clock boundaries.
5. Deterministic bounded jitter, delayed/bunched ticks, dropped ticks and recovery.
   Separate ideal-clock regressions from degraded-input behaviour; specify
   expected recovery without claiming impossible reconstruction of lost data.
6. Sustained phase/drift checks over many bars, with at least one long real-time
   run included in the existing performance campaign. In master mode assert
   clock count 24 per quarter, byte ordering, port routing, tempo and phase
   relative to note events and the independent receiver's beat/bar position.

## Evidence and completion

Map each scenario to case IDs, clock mode, initial state, independent phase
expectation and executable assertions. Use unit/integration matrices for cheap
phase/ordering domains and native behaviour anchors for real inputs and outputs.
Have one proportionate Codex Paranoia review challenge the startup phase oracle,
receiver independence, Stop/Continue semantics and omitted interactions.
Preserve/minimise failures, fix confirmed Mosaic or emulator defects at their
own layer, and run the affected timing regressions. Publish source-bound results
on the authorised branches. The Digitakt exception remains confined to NRPN;
it does not relax clock/transport correctness.

Done only after both directions and the interaction matrix have passing evidence,
startup phase is explicitly verified and any detected defects are resolved.

## Initial executable coverage

M-SYNC-001 exercises four warmed-source Start phases using native scheduled MIDI
input and absolute output-note deadlines. Controlled and real-time runs passed;
see `external-start-phase-validation.json` for retained manifest identities.
This does not close cold startup, master mode, or the remaining matrix above.

M-SYNC-002 preserves a failing cold-start baseline: first note is 25 ms late in
controlled time and 28.369 ms late in real time at 100 BPM. A separate C probe
compiles byte-identical pinned official norns MIDI clock code and reproduces
the one-tick transport delay without Mosaic or the emulator scheduler. See
`external-cold-start-validation.json`. The upstream-compatible correction and
full cold-start matrix remain pending; this is not an accepted limitation.

## Master clock ordering regression

M-SYNC-009 enables native MIDI clock output using norns keys/encoders and checks
an independent receiver driven only by captured Start/Clock/Stop bytes. Expected
note positions use that receiver's 24-PPQN timeline, never the first note as an
origin. Four local start phases are specified. The first phase currently fails
in both controlled and real time: Mosaic emits Note On before MIDI Start.
See `master-clock-baseline-validation.json`; later assertions remain unverified
because execution correctly stops on that first failure. This is an unresolved
regression, not an accepted limitation. The fix must also align the first clock
and note; merely reordering Start does not establish musical phase correctness.

The earlier cold-start baseline above is historical. Subsequent acquisition,
repeated Start, early Stop, and fractional subdivision results are recorded in
`midi-acquisition-validation.json`, `repeated-start-validation.json`, and
`acquisition-edge-validation.json`. The complete bidirectional matrix stays open.

## Master boundary arbitration

M-SYNC-009 exposes first-note-before-Start in both modes. An independent sync
candidate passed controlled four-phase checks but failed real time with the
first note after the second F8. Codex session01a0876c-f9b2-7c63-95b0-8afea1324d1f
rejected that approach; its patch and manifests are retained, production restored.
Seven independent receiver unit checks pass. Next execute NATIVE-MIDI-BOUNDARY.md:
prove a generic native output transaction/deadline contract before integrating
Mosaic. This remains an unresolved master synchronization defect.

## Direct lifecycle, multiple receivers, and forwarding baseline

M-SYNC010 cancels Start at0/1/25ms, proves continuing F8 with no late Start/notes
after Stop, balanced ownership, and aligned restart. M-SYNC011 enables two outputs
through native menus, compares independent receiver clock/phase, and checks no
F8 on disabled port3 or note leakage to port2. Both plus M-SYNC009 pass D/R.
Four new integration tests reproduce stale boundary subscriptions on direct
init/reset in pending/active states. Routing those replacements through existing
Stop cleanup fixes all four; the full524-test suite passes.

M-SYNC012/013 add cold/warmed incoming clock forwarding to port2, independently
checking notes against the original input timeline and the second receiver.
All4D/R baselines fail first-note/forwarded-F8 ordering. Cold output is25ms late
with bunched first ticks; warmed controlled output is1ns after the first note.
The existing absolute note/gate checks pass before the receiver assertion fails.
A separate generic native probe reproduces cold delay without Mosaic:25msD and
25.486193msR. These are open failures, not accepted limitations.

Codex arbitration01a087b2-c56f-7d50-8699-ea5b325ede1d recommends an optional native
received-zero output-boundary exception and atomic sourceStart publication,
then source-origin-aware Mosaic forwarding through the boundary adapter. Keep
ordinary clock.sync strict and forbid speculative pre-acquisition subdivisions.
Implementation card: emulator docs/delivery/MIDI-RECEIVED-ZERO.md. Evidence and
exact identities: midi-lifecycle-forwarding-validation.json. Full synchronization,
manual coverage, release and final hardening remain incomplete.
