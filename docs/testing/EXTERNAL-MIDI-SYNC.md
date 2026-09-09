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
