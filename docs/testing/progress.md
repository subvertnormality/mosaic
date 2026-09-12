# Campaign progress

2026-09-07: requested Paranoia plan critique plus focused follow-up returned and
were triaged. User confirms browser manual derives from repository docs; README
and cheat sheet hashes bind the inventory. No independent browser-source gate.

The Mosaic-owned runner boots this actual worktree through the generic emulator
Session API, drives real grid/keys/encoders, and records native screen/grid/MIDI
and cleanup evidence. Two initial cases are implemented. Pattern editing passed
on the baseline. The length collision case failed at approximately0.665 seconds
against an independent2-step expectation of0.333 seconds at90BPM, despite the grid
showing the shorter duration. The isolated pattern merge correction makes the
unchanged case pass; the unchanged editing case still passes. All474 upstream
units pass on baseline and corrected isolated copies with pinned runtime Lua and
a failing curl guard. Exact artifact paths and digests are in bugs.json.

The correction computes effective source-pattern lengths at the next source trig
without destroying the stored editing length; merge modes consume those lengths.
Tests for wrap/restoration/merge/mask interactions still need implementation.

Coverage remains incomplete:113 README headings plus the cheat sheet are indexed,
but only two requirements have partial-domain executable coverage. --require-all
fails explicitly. Controlled time has an inspected adapter design, no admitted
runtime implementation yet. T00/T01/T02 remain unfinished; no refactor starts.

## Continuation: length boundaries and repeated-pitch releases

Codex is the only permitted engine for future Paranoia reviews. No new review
checkpoint has been claimed in this continuation.

M-LEN-002 now verifies collision deletion/restoration/reinsertion with exact LEDs
and MIDI durations. M-LEN-003 verifies truncation across step64 using distinct
pitches over three complete64-step loops. The original same-pitch version failed
the stop/drain oracle and is retained as M-MIDI-001. Raw native emissions show
7 Note Ons but only4 Note Offs on the failing baseline; the minimal m_midi.lua
correction emits a release for each note lifetime and produces7/7. Both wrapped
duration cases, restoration and ordinary editing pass with both fixes applied.
All474 existing units pass on baseline and combined corrected isolated copies.
Exact manifests, digests and event counts are in bugs.json.

Five named Mosaic-owned cases now exist (M-LEN-001 is also executed inside the
restoration case). This remains partial coverage, not an exhaustive suite. The
emulator's isolated C scheduler seam passes original-versus-candidate boundary
checks, but controlled-time runtime integration and Codex P5 remain unfinished.
Next: coherent native time/internal clock/metro/event draining, complete atomic
manual reconciliation, runner fault probes and remaining workflow families.


## Experimental controlled-time diagnostics

The public Session candidate now runs the actual Mosaic worktree with controlled
time. This is explicitly unadmitted diagnostic evidence, pending C16/P5. Native
trace verification includes advances and logical-timestamp MIDI packets; normal
real-time mode remains the default. The four-note editing workflow passes in D.
The length case fails on its first note:328611113ns observed versus one third of
a second expected. Later notes agree within1ns. Both affected real-time cases
still pass, so the existing10ms jitter allowance hid this opening-interval issue.
All four source-bound manifests and digests are recorded under transport-start-phase
in bugs.json. No new Mosaic production-code fix has been applied.

A separate generic emulator probe (b7c813e19b8742bfa169161a0bd26dce) confirms
absolute clock.sync phase behaviour from independent120BPM calculations: notes
started at1ms/504ms end at250000001ns/750000001ns after48 native96PPQN syncs.
Mosaic's auto_pulse emits immediately then syncs to the absolute grid. This
supports a startup-phase diagnosis, not complete transport correctness or D
admission. Next: phase-swept transport start/restart, tempo/reset/external clock
contracts, mod/time-source audit and bounded Codex P5. Keep the failing duration
oracle; do not capture this shortened first note as a musical golden.


## Autosave restoration and optional modulation profile

Six named behaviour cases now exist. M-SAVE-001 creates its four-note pattern
through grid/encoders, checks no autosave at59 seconds idle, observes saved project
and PSET after61 seconds, closes the first process, and launches a fresh process
with those actual saved files as its isolated data seed. Restored grid LEDs and
three complete MIDI phrases are asserted without recreating or assigning notes.
The initial failing recipe8374d65c toggled off the restored pattern assignment;
removing that unintended edit made the unchanged output oracle pass (fd193c8a).
This was a harness correction, not a new Mosaic production bug or fix.

The final real-time case passes (f8fdcd07). Three fresh controlled runs also pass
and agree exactly in each segment's input recipe, full logical MIDI, grid, screen
hash and final clock/outstanding-note state (repeat-4ac65dde). Their wall times
are22.528/22.172/22.402s for64.93s of advanced time across both native processes,
versus88.536s end-to-end real time: about3.95x faster, including startup/cleanup.
No blanket speedup is claimed for shorter interactions or every feature.

The runner also supports an explicit midi-modulation profile with external
matrix/toolkit checkouts bound by mods.lock.json. It verifies exact clean source
revisions, uses actual native mod activation, records profile/revisions, rejects
missing mods and caught mod hook errors, and checks loaded/enabled counts.
M-PAT-001 passes real time (6104e51a) and three controlled fresh runs with exact
normalized output agreement (repeat-1833b336). The latter include startup with
matrix deferred bangs and the running toolkit lattice. This establishes loading
and coexistence; routing LFOs/rhythms/macros into Mosaic's emitted MIDI still needs
user-input workflow tests. No source/model mutations substitute for those tests.

Exact manifest paths and SHA digests are in state.json's
latest_profile_and_save_evidence. repeat.py retains child process output, source
bound case manifests and normalized comparison data outside the checkout.
Controlled time remains diagnostic-only pending C16/P5. The opening-note timing
failure remains open, and explicit save/load dialogs, corrupted/migrated files,
playing autosave exclusion, all remaining manual domains and T01 remain incomplete.


## Actual modulation output and a dependency defect

Eight named cases now exist. M-MOD-001 uses native System/Mods/Matrix and Params
menus to route toolkit macro1 at depth1.00 into Mosaic Fixed Note. It verifies
three complete phrases at MIDI note127, clears the route, checks the visible
cleared-depth marker, then requires the original60/62/64/65 pitches. The original
pinned matrix fails that final MIDI oracle in both controlled and real time:
its routing entry disappears but the target's cached modulation remains active.

The two-line matrix-clear-depth candidate clears the cache and defers reapplying
the non-trigger parameter. It passes the unchanged regression in both modes.
The original clean mod checkout and Mosaic production code are untouched.
--mod-patches applies the SHA-bound patch only to an owned per-run copy; manifests
record base mod revisions and complete patch identities. The normal unpatched
test remains a failing baseline, not an xfail or claimed release pass.

M-MOD-002 configures an actual clocked4-beat50%-width pulse LFO through the menus.
Across two complete modulation cycles it requires8 high-phase note127 events
then8 original-pitch events per cycle, preserving velocities. Every onset after
the separately tracked opening-phase issue is timed against90BPM. Real-time
maximum steady onset error is0.551ms; three fresh D runs agree exactly in logical
MIDI/input trace and final grid/frame/clock and pass the2ns timing bound.
Manifest paths and SHA digests are in state.json and bugs.json.

Menu assertions render literal expected labels/values with pinned font primitives,
without calling Mosaic or matrix drawing code. The value crop excludes the
separate source activity bar, which extends to x105; an initial wider crop caused
a harness-only false failure and was corrected without weakening the MIDI oracle.

Inspection also found a possible held-source binding problem in matrix's nilmul
call. That remains a source suspicion until reproduced with physical inputs;
it is not fixed or covered by clearing an existing route. Other LFO shapes,
depth signs, targets, source combinations, recording and manual domains remain
required. C16/P5 admission and full campaign completion are still open.


## Held macro routing and stable screen oracles

M-MOD-003 clears and restores a route, then binds depth 1.00 again while macro 1
remains at 1. The original held-source calculation fails in both clock modes:
the visible route exists but MIDI remains 60/62/64/65 instead of 127. These
baselines include the prior clear-cache fix, isolating the second Matrix defect.
The combined matrix-routing.patch supplies the missing depth argument to nilmul
and retains the clear-cache fix. It is applied only to an owned per-run copy.
No Mosaic production code or original pinned dependency checkout changed.

The unchanged held-source and pulse-LFO MIDI oracles pass real time and three
fresh controlled processes each, with exact normalized event/end-state agreement.
State latest_held_modulation_evidence records verified manifests and SHA digests;
all child manifest and artifact hashes were checked before recording these results.

A separate screen-oracle false failure was reproduced by repeated text drawing:
Cairo retained a scaled font after its FreeType face had been freed. The oracle
now retains one font/library pair for its process lifetime. oracle_contract.py
performs 1200 repeated draws; native modulation workflows pass after this fix.
This corrects a test harness defect, not Mosaic rendering or its expected pixels.

Reproduce with MONOME_EMULATOR pointing at the external emulator, run.py with
--profile midi-modulation --mod-code-root <pinned-code-root> --mod-patches and
--case M-MOD-003 or M-MOD-002. For controlled repeats, use repeat.py with those
arguments and --experimental-install <controlled-candidate-installation.json>.
Run python3 tests/behaviour/oracle_contract.py for the focused renderer check.

Nine named cases still cover only part of the manual. Controlled time remains
diagnostic-only until M5/P5; transport-start phase and all remaining feature,
failure-mode, timing and full release obligations remain open.

## Transport starting phase candidate

Current baseline reproduces the first-note4.722ms shortening. The isolated
0003 patch keeps the immediate lattice pulse and anchors subsequent syncs to
its phase, using the equivalent negative offset to avoid boundary skipping.
M-LEN-001 now meets the unchanged2ns bound; M-LEN-002 passes delete/reinsert
and repeated playback starts. Full474 baseline and candidate units pass after
adding the missing beat-time API to the unit-only native clock mock.

The real-time candidate is **failed**, not accepted: one later note has585ms
excess duration and the raw trace has a726ms gap across all native event types.
No timeout or tolerance was widened. Retain and diagnose this event stall before
a new real-time attempt. Source transitions, boundary starts and three repeats
remain required; controlled time is still diagnostic-only. Hash-bound run links
are recorded under transport-start-phase in bugs.json and state.json.

## Twenty-phrase timing regression

M-TIM-001 adds literal90BPM onset and duration expectations across20 complete
phrases after a physical-input edit and playback restart. Controlled execution
passes all61 onsets and60 durations. Real-time execution failed the initial
phrase check, so it did not complete the longer stage. Both results are retained
in state.json and bugs.json. MAN-030/MAN-050 mapping remains partial; this does
not certify other tempos, swing/shuffle, external clocks or source transitions.

Thread profiling found a main-matron CPU burst near the late onset, with
insufficient sampling precision to identify the responsible callback. The next
profile uses matron-only selection and per-thread timestamps. No timing tolerance
was changed; neither real-time correctness nor M5 admission is claimed.

## Restart clock phase edges

M-TIM-002 checks full note durations at five offsets around a future96PPQN
boundary. Controlled execution places starts within1ns of requested offsets;
both controlled and real-time executions pass all five restarts. Real-time phase
placement remains approximate and keeps the10ms musical timing oracle. Evidence
is linked in state.json and bugs.json. Three-repeat admission and actual
clock-source transitions remain required; manual coverage is still partial.

## Native MIDI source and transport

M-TIM-003 passes in controlled and real time. It selects MIDI through the native
CLOCK menu; checks clock-only silence and Start on the next pulse; asserts
100BPM note bytes, spacing and durations; drains after Stop; switches back to
internal and explicitly edits90BPM, checking output timing again. MIDI inputs
are now included in the driver's native trace comparison.

Initial test navigation selected SYSTEM instead of PARAMETERS. A later test
assumption expected automatic90BPM restoration; pinned norns clock.lua instead
adopts external tempo. The corrected test asserts100BPM before explicitly editing
90BPM. These were test errors, not Mosaic bugs, and no production workaround was
added. Passing manifests are linked in state.json. Live source changes with
pending notes and the final13-comparison M5 matrix remain required.

## Live clock handoff

M-TIM-004 verifies the release of a pending two-step note after internal90BPM
to MIDI100BPM source selection. The controlled oracle uses remaining native
ticks and the source phase; controlled execution passes without reset or lost
notes. The real-time variant preserves one continuous25ms pulse schedule and
fails before source selection when UI/observation work consumes the next target.

This is an emulator scheduling gap, not a Mosaic defect. The next dependency is
a bounded native MIDI schedule that runs independently of control acknowledgements,
with actual delivery evidence and cancellation/cleanup tests. Do not retime the
clock around UI calls. Both run references are in state.json and bugs.json;
reverse live handoff and full admission remain required.

## Independent MIDI scheduling prerequisite

The emulator now has an opt-in controlled-04 native candidate with a bounded
real-time input queue independent of Lua/control acknowledgements. Its generic
probe passes13 checks including40 exact MIDI echoes, arrivals during a150ms
Lua control callback, cancellation and clean shutdown. This is emulator
prerequisite evidence, not a passing Mosaic M-TIM-004 run. Next connect the
Mosaic recipe and native evidence verifier to scheduled events, retain the
continuous intended timeline, execute the handoff, and add controlled-domain
scheduling/reverse handoff as needed. No Mosaic production code changed here;
M5/P5/full manual coverage and later stages remain incomplete.

## Queued bidirectional live clock handoff

M-TIM-004 now submits one native queue per direction, using explicit logical
deadlines in D and monotonic deadlines in E. The driver and emulator admission
reader verify actual native delivery records; an accepted schedule alone cannot
pass. Both-direction runs00527347 (controlled) and34898ce (real-time) passed
against candidate05, including pending-note releases and an ignored MIDI Stop
after internal clock selection. The reverse phase test establishes internal
100BPM while stopped first; internal24PPQN tempo-publication transients remain
a named pending edge, not waived coverage. The inventory wording was expanded
after these runs; no production Mosaic code changed.

Generic queue checks also pass in both modes. M5 still needs required queued
input checks/repeats, an accepted real-time baseline with this adapter, fresh
source-bound differential evidence, and Codex P5 follow-up. Batch refill for
long continuous MIDI-clock endurance and full manual reconciliation remain open.

## Applied-time handoff oracle and default queue

The emulator now includes the real-time queue in its default pinned runtime;
controlled-06 is rebuilt on that baseline. Mandatory queue checks pass for
default RT, candidate RT and three fresh D sessions; seven rehashed evidence
faults are rejected. Full M5 matrix and Codex follow-up remain pending.

Run d0d30294 exposed an oracle error: the pre-grid snapshot was26.907ms before
the audible onset. The predicted release was12.435ms early. The RT handoff now
uses emitted MIDI onset and actual native applied-control time, retaining the
10ms tolerance. Corrected prototype23479022, actual-default c579bae2 and
controlled b5007ebc pass both source directions. No Mosaic production change
was needed. The failed evidence remains in bugs.json; all manual coverage and
remaining timing-edge obligations are unchanged.


## Scale, merge, slot and held-combination continuation

The emulator M5 checkpoint passed on its recorded runtime/application source;
the default runtime remains real-time. This does not complete the full campaign.
The inventory now contains 141 requirements, 54 cheat-sheet mappings and 33 image
references awaiting specification audit. There are 19 executable cases. Six new
cases have focused real-time and controlled-time passes, recorded in state.json;
their remaining input domains and three fresh D repeats are still required.
Evidence binds each retained source tree, not subsequent documentation edits.

New cases cover scale editing/application and lock lifetime, all 16 pattern slots,
All/Skip/Only trig merge sets, stopped scale feedback and long-held combinations.
Two isolated production candidates have baseline failures and unchanged passing
regressions: restoring the stopped applied-scale LED without hiding a held lock,
and clearing combination bookkeeping after the last long-held key is released.
The latter previously swallowed the next ordinary press, including Play, in both
clock modes. Both candidate files document exact production patches and evidence.
All 474 existing unit tests pass on the combined candidate in an isolated snapshot
named mosaic, required by the legacy harness's relative include paths.

SEM-002 is resolved by the user: standalone channel-step long presses remain
inactive to protect combinations; independently selecting a one-step channel
range is unsupported. README states this. M-RANGE-001 verifies inactivity,
delayed range selection, the next Play press, exact notes and loop spacing.
No standalone long-press action was added. SEM-001 remains pending.


## Channel range sweep and mute gestures

M-RANGE-002 passes controlled and real-time checks for all 63 adjacent start/end
pairs, including row boundaries and step64, and the full 1..64 range. Every range
checks all64 LEDs, two complete MIDI phrases plus a closing onset, exact pitches
and velocities, stop/drain and one-sixteenth-note spacing at90BPM. This is not
all2016 ascending endpoint combinations; live edits and channel/global isolation
remain required. Later-step default pitches also leave independent pitch-address
coverage to the note-editor cases.

M-MUTE-001 passes the below-threshold hold, long hold and K1+press gestures,
stopped/live silence, audible unmute and pending-note cleanup. All16 channels,
exact threshold boundaries and per-sequence isolation remain required. Both
M-MUTE-001 and M-RANGE-001 have three fresh controlled-process repeats with exact
recipe, logical MIDI, grid and final-frame agreement. The broad range sweep
still needs its three-repeat gate. Exact manifest references are in state.json.

The range sweep took309.63seconds controlled and121.74seconds real-time. This
is broader validation, not a fast smoke test. Controlled time is not claimed to
be faster; polling/capture cost remains an emulator feedback task. No production
Mosaic changes were needed in this continuation. There are21 executable cases;
the141-requirement campaign remains incomplete.


## All-channel routing and mute isolation

M-CHANNEL-001 configures every channel through native grid/encoders/keys, checks
its rendered Device Config title, assigns the shared authored four-note pattern,
and routes16 distinct MIDI channels over two virtual ports. Real-time and
controlled runs verify exact pitches/velocities/routes and phrase spacing while
cumulatively muting every channel and restoring them in reverse order. Every
phase checks active-channel membership; equal-rate first onsets align and stop
drains all notes. No production change was needed. The first diagnostic failed
in the test's channel1-only header lookup; explicit tab5 rendering fixes that
oracle limitation without changing the intended screen expectation.

This raises executable case count to22. It does not complete CH-SELECT/DEVICE/
ASSIGN/MUTE: arbitrary pattern combinations, other device types, every port and
route-remap failure, song-sequence isolation and live route changes remain.
Three fresh controlled repeats of this new case are also still required.


## Native memory navigation and branching

M-MEMORY-001 enters two distinct held-step MIDI notes, then verifies E3 undo/redo,
K2/K3 jumps, empty and end-of-history bounds, and a new edit after undo replacing
the old redo path. Each stage asserts exact pitches/velocities and independently
rendered current/total memory counters. Real-time, controlled and three fresh
controlled repeats pass. The existing M-PAT-001 real-time header regression also
passes after the renderer gained explicit font-size/antialias parameters.

The first diagnostic failed at the initial counter because the test renderer used
antialiased10px text; pinned norns script.lua sets screen.aa(0). Correcting the
oracle to that native contract retains exact pixels and required no production
Mosaic change. No observed output was accepted as a golden.

There are23 cases. This covers held-step note/velocity memory only: all other mask
and lock types, recording histories, large histories, channel/song isolation and
live editing remain required. Shifted forget-history behavior awaits SEM-007;
full memory coverage and the complete campaign remain unfinished.


## Channel history isolation

M-MEMORY-002 passes real-time and three identical fresh controlled runs. Two
channels share the same source pattern but receive different held-step MIDI
edits. Alternating E3/K2/K3 undo/redo changes only the selected channel's exact
emitted phrase and history counter. Separate output ports/MIDI channels identify
both voices. Navigating an untouched third channel preserves its0-of-0 display
and both audible channels, and returning restores each channel's own counter.
Stop drains all notes after each phrase. No production changes were needed.

The suite now has24 cases. This is note/velocity history isolation on a small
channel set, not all history types or every channel/song transition. Remaining
domains and the complete campaign stay open; SEM-001/007 await user decisions.


## User-reported live keyboard placement

The targeted campaign in LIVE_RECORDING_PLACEMENT.md is now a priority. Native
scheduled MIDI clock and keyboard inputs remove client polling from the input
schedule. Mid-step and minus/plus2ms-boundary cases pass both lanes: recorded grid
locations and disarmed internal-clock replay agree with independent expectations.
The exact-pulse new-step hypothesis fails in both lanes and is retained as an
unresolved diagnostic (SEM-008), not marked passing or called a confirmed bug.
Controlled native evidence separates pulse-deadline input from strict sync step
processing by1ns. No production changes were made. There are28 executable cases,
including this failing diagnostic; the complete suite is not green or complete.


## Held keyboard note survives channel selection

M-REC-005 now schedules note-on and note-off exactly500ms apart,50ms into
step1 of a90BPM four-step loop. Selecting channel2 while the note is held must
leave its release on port1/MIDI channel1 and its recorded length on channel1.
Replay independently checks both channels' pitches, velocities and note lengths.
The revised unchanged test fails on original a932827 (run3a0d6e0f81704774858457ad1d6b919d):
note-off wrongly goes to port2/channel2. Candidate0008 retains the note-on owner
and output route. It passes real-time b5c37a7b28ea47c3bcd836e57e67826f and
controlled c260ebd73acb40d6b98e0261d1fe18a0. Neighboring memory-isolation and
mid-step recording real-time tests pass; all474 existing unit tests pass.

Earlier real-time d8a21d6a6a9f4768a84f354401a051cb used unscheduled client waits:
actual hold553.88409ms invalidated its intended500ms stimulus. Its approximately
527ms replay duration is retained for a separate fractional-length investigation;
it is not explained away or used to widen tolerances. The first isolated baseline
clone omitted n.b. and failed startup (1b55c37e7fcb40b5863e8f508a64d6de); after
copying the same pinned dependency the intended release assertion failed.

Three fresh controlled runs each pass the case, but repeat-cf0ac225403244fba1daa2b4498d5f1c fails exact trace equality: simultaneous note releases change order. No trace sorting or tolerance change was applied. Deterministic acceptance remains pending investigation of release ordering.

This confirms a held-note channel-switch defect, not the cause of the reported
frequent step misplacement. Current-step quantisation is unchanged. Song changes,
cross-channel overlapping chords, route edits, variable tempo/divisions, fractional
lengths and the remaining placement matrix remain required. There are29 cases;
the complete campaign remains incomplete, including the exact-pulse diagnostic.


## Stable simultaneous delayed-action order

M-REC-005's three fresh processes exposed varying MIDI release order at equal
logical deadlines. Mosaic's lattice traversed generated string IDs with pairs(),
whose order is not stable across Lua processes. Candidate0009 keeps insertion
order in a compact per-sprocket list and respects cancellation before dispatch.
No emitted trace is sorted by the test runner. Native recording and musical timing
regressions and fresh-process repeat evidence are recorded in the candidate manifest.

The first candidate sorted pending actions each pulse. Its native repeats passed,
but a concurrent unit run failed the2ms pulse-performance gate (473/474).
The refined candidate retains insertion order without per-pulse sorting; the
sequential unit run passed474/474, including that performance gate. The earlier
failure remains retained; concurrency and implementation changed together, so its
cause is not attributed solely to sorting. Full performance/endurance and advanced
arpeggio/cancellation matrices remain required. No full campaign completion claim.


## Fractional recorded-note duration

M-REC-006 supplies a native scheduled550ms keyboard hold at90BPM. The nearest
supported length is3.25 sixteenth steps, so replay must last13/24s (541.67ms).
Baseline9fd1e5a instead emits approximately527.78ms: controlled
31a3a1a043814df49fb359e7ebf66b12 and real-time481469ce22ee459eacb0df549b1d808d
both fail. This reproduces the fractional discrepancy suspected in the earlier
unscheduled recording test without relying on client timing.

Candidate0010 corrects fractional elapsed-pulse accounting: phase starts at1
and is incremented before the check, so elapsed pulses are phase-2. Fractions
rounding up to a full cycle fire on its next onset. The note length remains
quantised as before; no recording placement model or tolerance changes.
M-REC-007 independently supplies210ms, quantising to1.25 steps (208.33ms).
Both cases pass real-time and three fresh controlled repeats; all474 unit tests
pass. The supplementary lattice_duration_contract.lua independently checks23
fractional/integer durations and cleanup. It rejects the old scheduler at the
shortest note (expected1 pulse, actual0) and passes the candidate. These pulse
checks complement the user-input/MIDI tests and do not replace native acceptance.

There are31 native behaviour cases. This validates fixed-tempo, onset-scheduled
fractional releases only. Arbitrary-phase arpeggio callbacks, changing clocks,
swing/shuffle, recording wrap/arm/disarm, visible playhead agreement and the
remaining manual/campaign/release domains remain required.


## Live recording range positions and wrap

M-REC-008/009/010 cover channel ranges2..5,15..18 and61..64. Independently
scheduled notes on relative steps2/4 must appear at the correct absolute grid
cells. M-REC-011/012 record across4-to1 and64-to61 wrap: replay must reverse the
input note order and preserve the expected three-step/one-step gaps. All64 grid
cells are asserted, then recording is disarmed and fresh MIDI capture checks
pitch, velocity, order and spacing. All five cases pass real-time and three
identical fresh controlled processes. No production Mosaic/emulator changes
were needed. There are36 native cases; these results do not explain the user's
reported frequent misplacement. Unequal divisions, live playhead feedback,
recording lifecycle, tempo changes and song boundaries remain open.


## Recording follows the selected channel clock rate

M-REC-013 sets x2 through the Clocks page and records across range15..18;
M-REC-014 sets /2 and records in61..64. MIDI clock supplies the independent
100BPM schedule. Absolute recorded grid positions follow the channel's75ms/300ms
steps, with global clock phase intentionally different. After disarming, internal
90BPM replay retains the rate and exact independently expected MIDI spacing.
Both cases pass real-time and three identical fresh controlled processes. No
production changes were needed. There are38 cases. These sampled clock rates do
not close all divisions, live rate changes, playhead feedback or the full campaign.


## Live playhead latency

M-UI-001/002 compare actual MIDI onsets with the visible grid playhead across two
four-step loops at normal/twice channel rate. Notes/velocities must match the
independent phrase; the playhead cannot show a future/unrelated step, must catch
up within the50ms redraw period (plus the existing10ms real-time scheduler
allowance), and must disappear on stop. Real-time observation brackets retain
client timestamp uncertainty. Both cases pass real-time and three identical
fresh controlled processes. No production change was made.

Normal-rate observations saw the previous step still visible at33.33ms in
controlled time and at least38.98ms after a MIDI onset in real time. These are
sampled stale intervals, not exact refresh latency or hardware measurements.
This is a plausible contributor to misplaced-looking live input; it does not
prove the cause of the user's report or alter current-step recording semantics.
An isolated one-step-stale renderer failed the intended native latency assertion
(e68551ca4a31440c8dbc34a214772f92, still step4 while MIDI step1 at69.22ms).
The normal checkout was untouched by fault injection.

There are40 native cases. Keyboard event/playhead boundary correlation, faster
rates, all clock divisions, recording lifecycle and the complete manual/release
campaign remain open. Existing recording placement cases independently verify
stored grid and replay; this feedback test does not replace them.


## Velocity-zero keyboard release

M-REC-015 uses Note On with velocity0 to release a held input note after channel
selection changes. Pinned official norns midi.to_msg defines this as Note Off.
Mosaic previously treated it as a new note, sent it to the newly selected channel
and left the original output note outstanding. Both controlled baseline
1c254dcdcaf1473982c70e22d11a5a65 and real-time6ff91400fe924ce6b42c4195972d4d3f
fail the original-route release assertion. Candidate0011 normalises a copy of the
packet before looking up held-note ownership. The release and recorded duration
then pass real-time and three controlled repeats, with conventional Note Off
real-time regression and474 unit tests passing. No emulator workaround was added.

There are41 cases. Other MIDI input channels/ports and repeated-pitch collisions
remain open. A separate user clarification asks whether disarming during a held
note should preserve its full length, trim at disarm, or discard it. Current code
buffers the note but skips committing it if release arrives after disarm; no
policy change has been made pending that answer. Full campaign remains unfinished.


## Keyboard MIDI input channels

M-REC-016 reproduces ignored keyboard notes on MIDI input channel16: both
controlled3bbaba3df8ae4c09bbc113556435840f and real-timee1dbb6ee63644582a10c168c3915174b
fail with no preview/release output. The handler compared whole status bytes
against channel1 constants. Candidate0012 extracts note message type from the
status high nibble; selected Mosaic channel still owns the output route.
The manual describes keyboard notes targeting the selected Mosaic channel and
provides no input-channel restriction/filter; pinned norns midi.to_msg decodes
note type separately from input channel. Controller CC handling is unchanged.

M-MIDI-002 verifies all16 channels across two input ports and both release forms:
64 sequential notes produce the exact128 output messages and leave no outstanding
notes. That matrix and channel16 recording/length replay pass real-time and three
identical fresh controlled processes; all474 unit tests pass. There are43 cases.
Simultaneous same-pitch inputs across channels/ports remain a separate required
isolation test; this sequential matrix does not prove overlap correctness.
Full manual coverage and emulator release remain incomplete.


## Confirmed held-note disarm policy

User decision: keep notes that began while recording was armed and finish their
length on release. M-REC-017 reproduces the old lost-note behaviour in real-time
ab7279ed7f7e4df09b93e6b023481174. Candidate0013 latches recording ownership at
note-on, allowing note-off to commit the complete quantised length after disarm.
The strengthened test also plays a new post-disarm note; replay must preserve the
original channel's complete held note and leave the other channel unchanged.
Real-time, three identical controlled repeats and ordinary held-note real-time
regression pass. README Arm live record now states this policy; all113 section
hashes and README requirement quotes were reconciled and audited.

An initial unit run passed473 and failed the automation2ms maximum pulse gate.
A paired isolated baseline/candidate diagnostic, with thresholds unchanged, passed
all474 each; maxima were0.954ms baseline and0.824ms candidate. Both the initial
failure and paired results are retained, without claiming a proven cause for the
first timing miss. No unrelated clock/performance code was changed.

There are44 native cases. Chord release permutations, mixed armed/unarmed overlap,
recording tempo/song transitions and the remaining full campaign remain required.


## Simultaneous keyboard source ownership

M-MIDI-003 and004 hold the same pitch from two input ports, or from two input
channels on one port, while selecting different Mosaic output channels. The
first release previously used the second note's output route: real-time baselines
29b500ccec4b48f9be39ad681717c887 and041b7cef6db24ff79ea8c6e5ed11a5a5 fail exactly
that ownership assertion. Candidate0014 keys held-note storage by input device,
input channel and pitch. Both release orders now produce exact routed outputs
and drain all notes. Both cases pass real-time and three identical controlled
repeats. Held-note disarm and velocity-zero release real-time regressions pass;
all474 existing unit tests pass. No emulator special-case was added.

There are46 native cases. This is preview/release ownership, not complete
recording chord isolation. Cross-source recording chord state and repeated-pitch
overlap within one source remain separate required tests, as do remaining manual
behaviours and full emulator acceptance/release stages.


## Recorded chord release order

M-REC-018..023 cover all six release permutations for a simultaneous three-note
keyboard chord, disarmed while held. Replay checks exact pitches, velocities,
route and nine voice durations over three loops. Root-last baseline passes;
root-first fails in controlled time (acc6c3097292429bb85b852dfbc8d7b8) and
real time (6cd079cc712f42c88fbba64c455519cc): the shared length becomes about
292ms instead of500ms. Candidate0015 removes the premature active-count reset
when the root releases. The shared length commits on the last held voice release.
All six permutations pass controlled and real-time; the root-first regression
also passes three identical fresh controlled processes. All474 unit tests pass.

There are52 native cases. This establishes simultaneous-onset chord release
order, not staggered-onset length or cross-source recording ownership. Those,
mixed armed/unarmed overlap, repeated same-pitch input and the remaining manual
and emulator release campaign still require execution.


## Recording chord ownership across channels

M-REC-024/025 record overlapping same-pitch inputs from two ports or two MIDI
input channels onto different Mosaic channels at the same step. Source-time
queued releases are independently held500ms each. Both baselines fail in
controlled and real time: replay retains the original channel1 note instead of
the recording. Preview releases route correctly, so the earlier source ownership
fix alone was insufficient. Candidate0016 keys chord bookkeeping by Mosaic
channel as well as step. Exact replay pitches, velocities, routes and lengths
now pass for both channels in both clock modes. Both cases pass three identical
fresh controlled processes; chord-release/disarm neighbors and all474 units pass.

There are54 native cases. Same-channel source aggregation, song changes and
repeated pitch overlap remain required. User decision: staggered chords use
first press to final release for their shared recorded length. Implement and
document that next, with native baseline/candidate regressions. The complete
manual campaign and emulator acceptance/release remain incomplete.


## Staggered chord length: first press to final release

User approved first press to final release for the chord's shared length.
M-REC-026/027 stagger C/E/G onsets by0/40/80ms within one step, release in
root-first/root-last orders and verify replayed notes and nine voice durations.
Before candidate0017, root-first saves416.667ms instead of500ms in controlled
and real time (e38bb0bb06f84693a046c9b1faee039b and
44674f6eea3f4908a4215b40ac64b1ee); root-last already passes. The candidate stores
the first onset on chord creation and uses it at final release. Both cases and
simultaneous-chord/channel-isolation neighbors pass in both clock modes;
root-first passes three identical controlled processes. All474 unit tests pass.
README Arm live record now documents the shared length and quantisation rule;
manual source hashes and quotations are reconciled.

There are56 native cases. Adding a voice after releasing the root, same-channel
cross-source aggregation, mixed armed/unarmed and repeated-pitch overlap,
tempo/song transitions and the remaining manual/emulator campaign remain open.


## Post-disarm preview must not own an armed chord

M-REC-028/029 inject a new preview note after disarming a held recorded chord,
with preview release after/before the recorded voices. The late preview release
loses the chord on baseline in controlled time9a4c4949e9a4430ba31cd2a1ddbc304b
and real time74093c6f5152413aa1eb0f688b566d18; early preview release passes.
Candidate0018 separates chord bookkeeping by armed-at-onset ownership. Both
cases now assert ordinary preview MIDI onset/release as well as unchanged
recorded chord replay and500ms shared length. Both pass controlled and real time,
with staggered-chord and cross-channel recording neighbors. The late preview
case passes three identical fresh controlled processes; all474 units pass.

There are58 native cases. This does not establish rearming with held notes,
same-pitch overlap, manual-step/live interaction, adding voices after root
release, same-channel cross-source aggregation or tempo/song transitions.
Those and the full manual/emulator acceptance and release campaign remain open.


## Chord voices added after a release: confirmed baseline failures

M-REC-030/031 release the root/non-root40ms after C/E presses, then add G at80ms
while another voice remains held. Both fail controlled and real-time independent
replay: the original chord/root is lost, or G overwrites the released E voice.
The real-time harness waits for all three note-on deliveries before disarming,
rather than counting an interleaved note-off as the third press.

Automatic approval review rejected applying the proposed core chord bookkeeping
replacement because of possible unvalidated behavior regressions. A read-only
diff was prepared; the implementation remains unchanged. The exact candidate and
validation plan are in emulator docs/delivery/reviews/chord-voice-lifetime-approval.md.
Payload-specific approval was requested. Do not execute the candidate helper
without resolving that rejection. Baseline tests are intentionally failing;
they are not skipped, waived or treated as completed acceptance.

There are60 native cases. This candidate is pending, and the full manual and
emulator delivery remain incomplete. Unaffected delivery work may continue.


## Approved chord voice lifetime candidate: broad validation

User explicitly approved candidate0019 and requested unit, integration and
behavior regression testing. It retains the chord root/onset while any voice
remains held and separates recorded voice slots from held-key count. Both new
regressions pass controlled and real time, plus three identical fresh controlled
processes each. All474 existing unit tests pass. All65 emulator contracts and
1200 repeated framebuffer draws pass. The native chord-editing integration
package54bf1d368fab4e45af3077afdbd3c2c8 passes on the same MIDI source hash.
Native MIDI roundtrip/overflow and grid conformance/fault-detection groups pass
through the real norns runtime with probe scripts independent of Mosaic.

All61 implemented behavior cases ran in both clock modes:117pass and5fail.
M-TIM-003 failed during MIDI-clock warmup because its per-pulse client request
missed a25ms deadline. The stimulus now uses the admitted native queue for49
warmup pulses,start,60 playback pulses and stop, with unchanged musical timing
expectations and a source-time assertion against premature notes. Targeted
controlled and real-time reruns pass. The initial failed sweep remains evidence;
it is not relabelled as passing. No production change was needed for that failure.
M-MIDI-005 still omits note0; exact MIDI payload comparisons match its pre-fix
controlled baseline, including the real-time candidate output. M-REC-004 still
times out on exact-boundary placement; final step grids match prior respective
controlled/real-time baselines. These failures remain explicit, unwaived and
incompatible with a full release-pass claim. No other implemented case failed.
The initial integration setup failed before execution because n.b. was looked
up as a sibling app; corrected to Mosaic's pinned lib/nb submodule.

Coverage audit:61 cases bind to portions of34 of141 requirements;107 have no
Mosaic-owned case binding. Existing emulator fixture packages are separate
evidence and cannot silently count as complete Mosaic-owned coverage. Same-pitch
overlap, chord voice overflow and the remaining manual/emulator stages remain
required. No refactor or full-delivery completion is authorized by this slice.

## MIDI note zero: isolated guard correction

Candidate0020 corrects the note-table guard to use the same one-based index as
conversion. Both prior native baselines dropped the two pitch-zero note pairs
(508 events instead of512). M-MIDI-005 now emits all512 expected events over
all128 pitches at velocities1/127 with explicit and velocity-zero releases, in
controlled and real time, with no outstanding notes. M-MIDI-002 all16 input
channels and M-REC-031 overlapping chord voice recording also pass both modes.
All474 existing unit tests pass against an isolated snapshot of the same source.
The six native manifests and source hashes are in candidates/midi-note-zero.json
and state.json. No emulator runtime or expected MIDI payload changed.

The exact-boundary M-REC-004 failures remain unresolved; their initial new-step
hypothesis was never an accepted oracle. The user's current-active-step decision
needs explicit reconciliation with native pulse/step ordering, not a silent
expectation change. Full campaign and release acceptance remain incomplete.

## Current-step boundary hypothesis resolved

The user chose current-active-step recording. Independent synchronized-channel
MIDI evidence and Codex review establish that MIDI pulse arrival need not mean
the next Mosaic step has executed. The old steps2/4 expectation was never an
accepted oracle. M-REC-004 now checks active steps1/3 at the pulse deadline;
M-REC-032/033 check minus/plus2ms, with fixed steps1/3 and2/4 respectively.
All six strengthened native runs pass, including complete transport-anchored
witness phrases, actual input delivery timing/order, grid and disarmed replay.
README clarifies the behavior. Production/runtime source is unchanged.
Original failing evidence remains in state.json. Full campaign remains incomplete.

## All duration endpoints and full-loop release ordering

M-PAT-003 authors durations1..64 through grid gestures, checks all64 length LEDs,
and verifies each note-on/off duration and stop cleanup. The baseline passed
endpoints1..63 but emitted the new note-on before the preceding same-pitch
note-off at64. M-LEN-004 reproduces this on a short four-step loop in both modes.
Candidate0021 marks note releases explicitly for processing before a new onset.
Strum and other delayed actions retain their existing post-onset order. The first
broad candidate moved strum before scale updates and failed one existing unit
test; it was rejected. The refined candidate passes all474 units,46 tagged and
untagged duration contracts, and an ordering contract that rejects the baseline.

All10 native regressions pass: short full-loop retrigger, length truncation and
restoration, both fractional recording cases and the complete64-duration domain,
each controlled and real-time. Native identities match all three changed source
files. The full domain manifest contains all64 distinct endpoint assertions in
each mode, not merely a passing exit code. No emulator runtime changes were made.

Test-harness correction: the initial new case reused M-PAT-002, silently selecting
the existing pattern-slot test. That run earns no duration credit. M-PAT-003 is
unique; the runner now rejects duplicate literal case IDs before selection, and
a permanent collection regression detects an isolated seeded duplicate. A slow
duration attempt was intentionally interrupted after32 endpoints with cleanup;
it earns no full-run credit. Reduced polling retains complete source-timestamped
MIDI capture and every duration/order assertion. Original failures, rejected
candidate output and interrupted evidence remain in ignored artifacts.

PAT-DURATION remains partial: all endpoints from start1 plus existing wrap and
collision cases do not exhaust origins, live edits, or overlapping retriggers.
Full manual coverage and emulator delivery remain incomplete.

## Pattern duration controls and live edits

M-PAT-004 validates extension, long-hold reset to one step, empty-source combo
and long-hold gestures, and re-extension. All64 grid cells and six replayed
phrases have explicit expected note lengths and MIDI notes. M-PAT-005 shortens
and extends the authored duration while a note is sounding. Edits are asserted
to finish inside the held-note window; pending releases retain their original
schedule, later onsets use the edited length, and loop spacing remains8 steps.
The complete live MIDI stream is exactly three ordered note-on/off pairs with
lengths4/2/4, followed by stopped-grid and disarmed replay checks. Both cases
pass controlled and real time; state.json records the four final manifests.
The initial live-edit runs also passed; their oracle was strengthened to reject
extra/wrong-channel/reordered note events and rerun in both modes. No production
change or new bug was needed. PAT-DURATION and the overall campaign remain
partial, including origins, interrupted gestures and other live-edit interactions.

## Euclidean preview, paint and movement

M-ALG-001 ports the prior emulator fixture into Mosaic ownership with independent
three-in-eight and dense-fill rhythm expectations. Both preview blink phases
are checked across all64 cells; overlapping and new trigs remain distinct.
Unpainted preview and cancellation preserve exact MIDI playback. Shifted paint
uses an independently constructed XOR set across64 steps; repaint restores the
original phrase, left/reset controls restore the expected preview, and fill
exceeding length exercises saturation. All seven workflow checkpoints pass in
controlled and real time. No production change or emulator-private test import.
Six manual requirements gain partial coverage; all algorithms/faders/banks,
offsets and playing-state combinations remain required. Full delivery incomplete.

## Tresillo multiplier and drum-boundary coverage

M-ALG-002 covers all eight multipliers using independent literal 3/3/2 segment
positions; M-ALG-003 checks the drum-bank 64-step boundary. Both cases pass in
controlled and real time. Each variant checks all 64 painted cells and repaint
erasure, two complete MIDI phrases plus the closing onset, and every inter-onset
gap including wraparound. The Norns options-page header is independently checked.
A test-porting API error in the first four attempts was retained and corrected.
Then M-ALG-003 reproduced the previously isolated tresillo-bounds Mosaic defect
in both modes: a 3m segment can exceed a 16-bit drum table and read nil. Candidate 0004
now wraps the index at the stored bit length. The baseline supplementary contract
fails; the candidate passes 409600 independently constructed bit-string checks
across all stored patterns/multipliers and unchanged drum output, plus all 474
existing units. Six native candidate runs pass, also covering all five drum banks
and four numeric masks at selected literal patterns, including empty-bank silence.
Polling is reduced only by waiting with capture active before checking the entire
MIDI sequence; early/extra notes remain observable and fail the same assertions.
Selected pattern/bank fixtures remain partial coverage of algorithm/fader
requirements; broader domains and all remaining delivery gates are still required.

## Note, velocity and step-page editor ranges

M-EDIT-001..003 pass controlled and real-time native runs. Note-range tests cover
fine up/down movement, long-held extrema, repeated bounds and center reset using
literal expected MIDI pitches. Velocity tests cover all 14 displayed values,
including zero, fine range movements and held limits. K1 note and velocity edits
are checked on all four step pages and each page is replayed with exact MIDI.
Four manual requirements now have partial case bindings. Threshold edges, all
columns, mixed existing values and live edits remain required. No production
change; these cases migrate the earlier emulator-owned editor fixture into the
Mosaic suite without importing private emulator tests. Full delivery incomplete.

## Note-editor pattern selection across all slots

M-EDIT-004 passes both clock modes. It creates16 patterns through normal inputs,
uses both K1+press and long-hold selection to change each pattern, and verifies
the result through assigned-channel MIDI. A final revisit of all16 patterns checks
that later selection/edit gestures did not corrupt earlier patterns. Each run
contains32 selector edits and16 retention checks, with96 complete MIDI phrases.
The note-selector requirement now has a partial binding. Exact gesture thresholds,
interrupted modifiers and playing-state changes remain required; no production
change or full-coverage claim.

## Hold boundaries and cancellation

M-EDIT-005 passes both modes. Note-up and velocity-down range controls distinguish
short presses at one second minus1ns from long presses at one second plus1ns in
controlled time. Real-time delivery intervals are bracketed around native input
acknowledgements and must stay entirely on the intended side of the threshold.
A second grid press cancels each pending long action; holding past its former
deadline and releasing leaves the range unchanged. Each result is checked via
grid selection and exact MIDI playback. No production change. Other directions,
exact equal-deadline ordering and live/overlap combinations remain required.

## Stale channel visualizer cells

M-VIEW-001 reproduced stale screen dots after shortening a channel range in both
clock modes. Each baseline first passed an independent wide-range frame oracle.
Candidate 0022 clears the shared viewer cache before drawing the selected channel;
it changes screen feedback only. The focused rendered-cell contract fails on the
baseline and passes 4288 checks on the candidate; all 474 existing units pass.
Both native runs pass 27 exact frames across all 16 channels and trigger/note/velocity
viewers, with channel clamps, independent page selections and unchanged grid/MIDI.
An initial test-rasterizer error was corrected against the official norns
screen.aa(0) default and preserved separately. No captured output became a golden.
Multi-pattern merge and running-playhead cases remain required; full delivery
remains incomplete. This screen defect is not claimed as the cause of the user's
earlier live-recording step-placement observation.

## Priority merge ordering and modifier isolation

Two independently reproduced bugs are fixed by separate patches. Candidate 0023
applies explicit note/velocity/length priorities after trig collection, so later
table entries cannot overwrite the selected source; masks retain precedence.
Candidate 0024 makes dual-press priority selection honor K1, as ordinary mode
presses already do. A velocity choice no longer changes note length, and a length
choice no longer changes velocity. The order-only native checkpoint fixed notes
while preserving the separate modifier failures, documenting their separation.

All 474 existing units and 829760 focused merged-cell checks pass, including every
distinct priority/rhythm slot pair, all trig modes, three fields, mask precedence
and false/nil mode callers. The initial candidate's 34 sentinel-mode unit errors
were retained, fixed and supplemented with explicit regressions. Seven native
cases now have passing controlled/real-time evidence. The original final batch
remains 13/14: one HTTP timeout occurred during setup before merge assertions.
Cleanup completed; a single fresh-process retry passed with no source, timeout
or tolerance change. Its unproven cause remains a C12 reliability follow-up.
Full domains and delivery remain incomplete; no Lower/Shorter semantics changed.

## All inactive positions and priority-source assignment isolation

M-PAT-006 exercises all64 inactive note positions: silence without trigs,
unassigned and assigned priority use, later activation and removal. Each positive
phase checks two full loops, note durations and wrap spacing; negative phases
check two silent loops. M-MERGE-008 checks every16 priority slot in both assignment
states with distinct two-note fingerprints and exact phrase/rest timing.

The initial all-slot test failed in both modes when returning to the channel page.
Merge processing aliased the channel assignment table and inserted an unassigned
priority source as false. The refresh then treated its presence as assigned,
misleading the grid and the next assignment press. Candidate0025 copies the set
before adding merge-only sources and renders only active assignments. The native
diagnostic checks the assignment before and after navigation. Its original
failures are retained. A new module regression rejects the original source.

All474 existing units and830480 focused merge checks pass. Four native cases pass
both modes, including affected velocity/length priority regressions. No tolerance
or musical expectation was changed. Existing persisted false-entry projects and
the remaining manual domains remain explicit obligations; delivery is incomplete.

## Octave controls and locks

Three native cases pass in both time modes. They cover all five global octave
positions, repeated center presses and navigation, every25 global/step octave
pair, explicit zero overriding nonzero global values, and K2/repeated-selector
clearing. The K2 gesture runs on the Trig Locks screen page. A64-step sequence
checks every held-step octave indicator, overrides at both global extremes and
channel-wide clearing. Exact MIDI phrases, durations and inter-onset spacing
include loop boundaries. No production change. Channel isolation, pitch bounds,
pending strummed voices, playing edits and mixed-lock interactions remain required.

## Clock continuity and reset validation in progress

Seven native timing cases cover all47 clock selector rates, actual reset menus,
copied song transitions, and inactive shuffle preferences. All seven pass in
controlled time. Real-time inactive feel/basis, transitions and repeat policy
pass. The final fractional run fails an x5.3 ratio window at10.276ms against the
unchanged10ms bound; it remains failed. The matrix stopped, leaving its two
integer-ratio real-time cases unrun. Earlier passes do not replace this record.

Three separate candidates fix unconditional realignment, reapplication of
unchanged fractional settings, and inactive shuffle edits disturbing Swing.
All474 units and143 scheduler decision/integration traces pass, along with15
capture/release-oracle checks. The collector now rejects retention gaps and the
fractional test accounts for every note release, including duplicate rejection.
Candidate JSON files retain exact combined native source identities and results.

Codex arbitration chooses preserving remaining musical time for pending work
under unchanged effective rates. Native reset traces expose a1.5s note extended
to1.667s; this remains a separate confirmed defect. Prototype work is unapplied.
Actual rate changes, strums, arps, overlapping pitches and stop need their scoped
regressions. Neither these candidates nor the whole delivery are declared done.

## Pending timing and arpeggio validation in progress

Candidate0029 preserves pending timing across reset, including callback-created
children and cancellation cleanup found by Codex review. Native fractional,
two-step and128-step releases, transition/repeat resets and strums pass in both
clock modes. The maximum-length fixture spans18 resets. Candidate0030 fixes a
native length-selector crash beyond the89-entry division table; both modes pass.
These are scoped results, not complete feature-domain acceptance.

Codex decision01a07f14-57cb-7cb1-9f93-07c02f229e92 rejects the new test's guessed
nearest-rounding convention. Its replacement checks3840 exact reset invariants,
960 independently bounded gates and253 full rational windows, including every
denominator phase and length18/128. No Mosaic rounding policy was changed.
The separate real-time metric amendment is approved in principle but remains
unimplemented until independently expected deadlines and transport origin are
established. Historical timing failures are retained; C12 remains required.

Native arpeggio tests reproduced an early first interval, nearly immediate
off-beat release and old-generation termination cutting replacement notes.
Candidates0031/0032/0033 isolate those corrections. Basic, fractional final-gate
and replacement cases pass controlled and real time, and strum real-time still
passes. All474 existing units pass. A96-case actual scheduler cadence matrix
passes; a broader48-case release probe exposes three one-pulse5/6 rounding
errors, which are still open. Focused Codex review and reset/tail edges remain.

WSL native sessions now use a detached emulator worktree on the Linux filesystem,
at the same446672f revision, avoiding Windows-mounted hot journals. This resolves
the diagnosed setup path for the pending-note test; it neither establishes the
cause of earlier jitter nor counts as native-Linux portability acceptance.

## Arp boundary findings resolved; broader campaign continues

The final ten-case controlled package passes: five arp cases plus reset,
transition, fractional/two-step/128-step releases and strum. Latest-source
real-time reset overlap and strum also pass. All474 units pass. Thirteen focused
contract packages pass and two counterfactual source snapshots fail as intended;
24 additional exact positive/negative swing cadence cases pass.

Codex follow-up01a07f42-e03d-7ab3-b2cb-d9425be14605 confirms the wrapped-origin,
floating residue and reentrant Stop fixes, with no new blocker reproduced in
that scope. The earlier48-case probe's three5/6 misses are resolved by the
expanded54-case actual-step-helper integration test; old failure evidence stays.
Native one-pulse1/24 arps emit289 expected notes with exact release/order checks.
Its first fixture run omitted the nanosecond-rounded final pulse; the input
horizon now explicitly includes it by1us while retaining the2ns musical oracle.

README explains the zero-spread arp interval, gate clipping, preserved tails,
replacement and Stop, and all manual evidence anchors are reconciled. Full arp
domains, nonzero spread/acceleration, live channel-rate changes and remaining
manual/emulator release gates still require work. No refactor or full release
acceptance is authorized by this partial campaign result.

## Division parameter bounds

Three native baselines show Strum, Arp and Spread can move beyond the89-entry
musical division table, leaving their displayed value blank. Candidate0036
derives their maximum from the label table excluding Off. All three native
screen-boundary cases pass in controlled and real time;474 units pass.

Codex decision01a07f50-06ce-76f2-86f5-76414bd23074 settles a new spread/acceleration
contract. Its manual amendment, native old-behavior baselines and implementation
are pending. No nonzero-spread musical code changed in this bounds correction.

## Spread, minimum swung interval and bounded arp rests

Candidates0037/0039/0038 implement the documented spacing recurrence, preserve
a one-pulse minimum after swing, and traverse all arp slots without an unbounded
search. The empty-muted native baseline hung; the corrected runtime stays silent
and responsive. No-mask ratcheting, timed trailing/internal rests, muted reverse
shapes, velocity ordinals, live scale editing (ordinary and fully quantised mask),
replacement tails and Stop have native regressions.

Eleven historical unit expectations were amended explicitly for the new
spacing/rest contract; their literal per-pulse assertions reject extra notes.
All474 units pass. Earlier dense arp boundary fixtures now use no-mask ratcheting;
the fractional-gate fixture populates its final sounding slot, preserving the
regression each was designed to catch. Native results are individually source
bound in spacing-rest-validation.json. Historical failures remain unchanged.

Codex found a zero-rounded swung interval and its focused follow-up verified
the isolated fix. The rest review requested three native interactions, now
implemented and reviewed. These are scoped validations, not full campaign or
D20 absolute real-time acceptance. The full refactor prerequisite remains unmet.

## Chord shape, sparse slots and velocity boundaries

Candidates0040/0041/0042 correct muted reverse roots, preserve all four mapped
strum slots and clamp the final root velocity to MIDI bounds. Native baselines
retained extra/missing/wrongly timed notes and malformed velocity bytes. All478
unit/integration tests pass, including four new literal pulse/velocity tests.
The finite256 mask/shape/root/articulation cases have196 source-bound passes;
startup/response failures interrupted the campaign, and197..256 remain unverified.
Boundary257 (nonpositive next gap),258 (disabled articulation) and259 (Stop before
the final root) have passing native evidence. Full real-time shape coverage and
the pre-existing root-last dashboard issue remain pending.

Codex cleared the production changes and found a release-channel blind spot in
the zero-velocity oracle. The one-line correction rejects30 injected bad releases
and both affected cases pass fresh native runs. See chord-shape-validation.json
for exact identities and limitations. Historical failures are not reclassified;
this checkpoint does not complete the manual campaign or permit the refactor.


## Native MIDI hot-plug panic validation

M-PANIC-011..014 add four removal/reconnection intervals, with eight canonical
D/R passes. Complete exported MIDI proves unaffected ports, connected portions
of interrupted sweeps, no replay, restored keyboard input, a fresh full panic,
page LEDs and melody recovery. Seven oracle groups include the one/16-message
omission regressions requested by Codex; its focused follow-up closed that gap.
Fresh affected native cases pass the stricter bound. Existing live-note Stop and
pending-arpeggio panic cases also pass D/R against the new runtime (four runs).
All result/artifact hashes are verified in `hotplug-validation.json`.

Only tests, driver recipe accounting, inventory mappings and delivery records
changed; Mosaic production Lua and its manual are unchanged. The emulator is the
published `codex/midi-hotplug` branch, using locked patch0013. Automatic approval
review rejected emulator main merge/runtime activation; neither ran, and these
tests use the authorised feature branch directly. Full manual coverage and
controlled-time admission remain incomplete; this is a scoped checkpoint.

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

### Candidate09 received-zero forwarding checkpoint
+Candidate09 serializes source selection with Start eligibility and admits only an
+actually received beat-zero boundary to tagged MIDI-output waiters. Generic D/R,
+M-SYNC001..013 D/R (26/26),526 Lua tests, complete-tail mutations and the focused
+Codex follow-up pass. Exact evidence is in midi-forwarding-candidate09-validation.json.
+The broader synchronization/manual/release campaign remains incomplete.


## Degraded external MIDI clock and explicit recovery

M-SYNC015-020 drive Mosaic through the native CLOCK menu and scheduled physical
MIDI input. The matrix covers alternating +/-5ms jitter, one missing pulse, one
extra half-interval pulse, an abrupt100-to150BPM step, gradual drift over42
intervals, and a500ms clock gap followed by Start. Every case asserts received
24PPQN ordinal phase, the authored four-note phrase, velocity, complete note
ownership and release timing in controlled and wall-clock lanes. Selecting MIDI
clock input1 through the menu proves transport on port2 cannot start Mosaic.

Pinned norns freewheels during an unaccompanied clock gap. In the explicit
recovery case, Mosaic produces the bounded holdover phrase, then Start followed by the next Clock
releases the sounding note and reanchors step1 with no stale task output. The
README now states the all-input default, pulse-fault consequences and holdover
semantics. This does not decide ambiguous recovery without Start or cover burst
loss, stochastic jitter, simultaneous source edits or every feature interaction.


## Full-range transpose-lock defect

M-TRANS-001 now walks every -12..+12 value advertised by the scale-page fader through held-step grid input. The stock `061fc8c` baseline fails immediately: selecting -12 emits MIDI53 because the model clamps it to -7 instead of emitting MIDI48. The isolated candidate aligns the storage clamp to the public range; controlled and real-time native runs then pass exact pitches, gates, phase, explicit-zero bounding and K2 restoration. The fresh snapshot also passes527 Lua tests and21 focused integration/oracle tests. Codex review and its explicit-zero follow-up accepted the scoped fix. Wrap, scale/octave, live-clear, merge and lifecycle interactions remain.


## Transpose composition and live-clear interactions

M-TRANS-002 composes -12/zero/+12 step locks with scale transpose+3, overridden song transpose+4 and channel octave+1 across repeated wrap; exact native output is63/77/91/92 in both clocks. M-TRANS-003 clears step1 during playback while step2 sounds, proving the current release remains owned and one step long, the next wrap inherits global+4, and step2 remains explicitly zero. Both lanes pass. A fresh immutable snapshot first hit the existing2ms param-slide performance threshold with526 functional successes, then passed527/527 on immediate rerun; both logs are retained. Twenty-one focused oracles pass. Codex interaction review and focused follow-up accepted the scoped cases with all findings closed.


## Transpose locks with scale merging

M-TRANS-004 uses two physical pattern sources and Average note merging, then composes a four-step global scale track with a step3 D-minor/root-D/+3 scale lock and -12/zero/+12 transpose locks. The independently derived 50/65/85/82 phrase passes three scale-track loops in controlled and real-time lanes. The strengthened oracle accounts for all 94 MIDI events from script start through physical Stop: exact data for 13 onsets and 13 matching releases, the boundary release caused by Stop, deterministic program changes and three-port transport. Timing is measured as accumulated phase from the first onset. This case claims scale-track reset and the step3 transpose's persistence into unlocked step4; M-TRANS-003 owns the separate unlocked transpose-wrap reset claim. Fresh M-MERGE-009 and M-SCALE-002 adjacent regressions also pass both lanes. The first test recipe incorrectly selected pattern-priority notes and left the global scale track at 64 steps; its retained failure demonstrated those independent semantics before the recipe was corrected. Codex follow-up review conceded all three findings. A fresh Mosaic-named source snapshot passes all 527 Lua tests and all 21 focused integration/oracle tests; the retained initial unit launch failed only because the worktree basename did not satisfy the legacy include path.


## MIDI pitch boundary after composed transposition

M-TRANS-005 combines the already validated extreme Higher/Lower merge arithmetic with channel octave +/-2, saved scale transpose +/-12, an explicit global scale lock and step transpose +/-12. The finalized unclamped baseline corrupts the MIDI stream with `Status interrupted an incomplete message`. The candidate clamps only at `m_midi` output and emits the independently derived 127/127/96/96 and 0/0/0/0 phrases. Both clock lanes account for every onset, release, program change and transport event through physical Stop, with accumulated phase. M-TRANS-002, M-TRANS-004 and M-MERGE-016 pass fresh adjacent runs in both lanes. The final cleanup-corrected snapshot passes all 530 Lua tests and 21 focused Python oracles. Codex review found and closed endpoint-collision cleanup, exact program-output and source-binding gaps, then accepted the scoped fix.


## Global transpose full value domain

M-TRANS-006 selects every displayed global transpose value from -12 through +12 using the scale-page fader and verifies the independent base+semitone four-note phrase in controlled and real time. Every stage pairs all onsets/releases through physical Stop, checks one-step gates, ordered program channels, three-port transport, complete dynamic event count and accumulated phase. A retained first strict real-time run correctly exposed that the observation loop can receive a tenth valid onset before Stop; the bounded oracle accepts nine or ten and accounts for either without dropping data. No production change. Codex accepted the scoped checkpoint with high confidence; tooltip text is not independently asserted by this case, while exact MIDI and complete grid-driven behavior are.


## Global transpose copied-song lifecycle

M-TRANS-007 copies song slot1 at global transpose+5, visibly selects slot2 and
plays its inherited +5 phrase before editing only the copy to-7. Song mode then
crosses two full1,536-pulse boundaries while the 24-pulse note lane produces
the exact 64-onset source, 64-onset copy and wrapped source sequence. Controlled
and real-time lanes validate every note, release, gate, exact per-onset program
group (including transposition69/57/69), three-port transport, slot LEDs, event
count and accumulated phase. M-TRANS-008 crosses the actual60-second autosave
deadline and loads a fresh native process, where both slots retain their exact
MIDI phrases and selection feedback. Initial shorter-boundary, strict adjacency,
exact wall-clock timestamp and narrow observation assumptions are retained as
oracle corrections. The final source-bound snapshot passes530 Lua tests and21
focused Python timing oracles. Codex review requested stronger copy-inheritance,
program-payload and provenance checks; its focused follow-up conceded all three
findings. Global-transpose live-edit timing remains pending.


## Global transpose live-edit timing

M-TRANS-009 performs 0 to +1 and +1 to -12 global transpose edits through the
scale-page grid while notes are sounding. Each edit is bracketed from first
press through final release. The sounding note retains its original pitch and
full gate; the first onset after the completed gesture uses the new transpose.
Both clock lanes validate literal pitch/velocity sequences, exact harmonic-sync
program groups with transpose64/65/52, complete onset/release ownership,
three-port transport, Stop cleanup, event-count identity and accumulated phase.
Controlled and real-time runs each capture11 balanced onsets. Codex accepted the
timing and ownership oracle with high confidence. No production code changed.


## Recording eligibility under Trigless Locks

M-REC-PARAM-003 and M-REC-PARAM-028 compare the same removed step with
Trigless Locks enabled and disabled. Enabled recording writes the empty rest;
disabled recording skips it and preserves the old value96, which a later
re-enabled replay exposes against the distinct channel default65.
M-REC-PARAM-029 proves an authored probability-zero trigger remains eligible
for recording even though probability suppresses its note. M-REC-PARAM-030
changes the option Off/On/Off through the native parameter menu during a /48
recording pass and distinguishes the resulting rest/rest/active boundaries.
M-REC-PARAM-031 records zero across all ten CC slots on one rest while exact
replay proves adjacent step values1/3/4 remain unchanged.

The oracles separate live encoder emissions from step dispatch, require exact
controlled and bounded real-time deadlines, order every applicable CC before
its note, pair every onset and release, and measure every naturally completed
gate. Codex review found shared-helper regressions for the existing recorded
zero and Off paths; their path-specific timing/silence assertions were fixed,
and M-REC-PARAM-005/006 pass both clocks. Fourteen final native manifests and
210 artifact hashes are recorded in recording-trigless-validation.json. The
source-bound snapshot passes530/530 Lua tests and100/100 applicable Python
unit/oracle tests with hashed logs. Codex follow-up
01a08a51-15cb-7780-aab2-46622b7d49c6 accepted the scoped slice. Broader
recording-lifetime combinations remain under REC-PARAM-AUTOMATION, so the
manual inventory stays conservatively partial.


## Held-step parameter lock creation and overwrite

M-PARAM-043 creates locks through native held-grid/E3 input on every physical
step1..64, distributed round-robin across ten independently assigned CC slots.
It overwrites the first, middle and last rows, makes step33 explicitly Off,
observes both phases of every lock LED, and validates the exact first-cycle plus
wrap CC stream, step ordinals, CC-before-note order, pitches, completed gates
and paired releases in controlled and real time. M-PARAM-044 changes future
step2 from48 to49 while step1 is sounding at /24; step1 retains its full
four-second gate, step2 receives49 before its note, and a fresh transport pass
proves the overwrite was committed rather than consumed once.

A production-model unit test stores, reads, isolates from song2, overwrites and
rereads all640 step/slot cells. The final source snapshot passes531/531 Lua and
100/100 applicable Python tests. Codex initially found stale controlled evidence,
a missing persistent replay and an unsupported display phrase; all were fixed
and the four final manifests bind one source. Follow-up
01a08a73-f1f9-7082-99e2-73e91f6ec64b accepted the scoped held-step contract.
Clearing, slides, recording lifetimes and parameter-type semantics remain under
their own inventory requirements.


## Trig-parameter slots and K1 fine adjustment

M-PARAM-045 uses native K1/K3 and E3 input on a wide NRPN parameter. The same
encoder detent advances Off to0 with K1, while neither modifier and K3 each use
the coarse129 increment. Playback requires exact standard NRPN bytes for258 as
both patch recall and step1 default before its note. Source and history show the
cheat sheet's K3 wording was stale; it now agrees with the README and production
K1 behavior, while K3 keeps its established parameter-slide action.

M-PARAM-046 assigns all ten slots, drives the selector twenty inputs past each
endpoint, and proves through held-step edits and exact MIDI that it remains at
slot10/CC10 and slot1/CC1. Both cases pass fresh controlled and real-time runs
after the documentation correction. The final source snapshot passes531/531 Lua
and100/100 applicable Python tests. Codex review
01a08a85-ce64-7a01-9624-71c0b506c667 accepted the scoped cases and K1 manual
resolution; final source/evidence audit 01a08a94-e05a-77e2-8cfc-4e5b6fba6356
verified all source, manifest, artifact and snapshot bindings. PARAM-SLOTS and NAV-FINE-K1 remain in progress for their declared
additional classes, boundaries and gesture orders.


## Concurrent local CC and global NRPN slides

M-PATCH-064 configures two slots through native menus on one MIDI channel. A
+held-step K3 gesture makes CC1 step1 slide locally from24 to96, while unheld K3
+enables a standard-NRPN global slide from126 to253. Across two cycles and both
+clock lanes, the case classifies every MIDI event, requires exact program and
+transport traffic, complete note/release ownership, literal status176/port1 CC
+traffic, contiguous NRPN packets, and independent six-sample trajectories at
+1/18-second intervals with both endpoints before their notes and both sources
+restarted at the next cycle.
+
Fresh M-PATCH-033/034/046/053 regressions retain local/global toggle behavior,
+all ten concurrent CC slots and slow NRPN rollover in both lanes. Final4 passes
+531/531 Lua and100/100 Python checks. An earlier snapshot's existing2ms
+performance assertion failed once and remains recorded; the focused immutable
+recheck passed, and a subsequent unmodified full snapshot passed. Codex session
+01a08aa9-c9ea-76c3-b2a2-02c4366b0590 required complete MIDI accounting, literal
+curves, closed timing windows and exact channel status, then conceded and
+accepted the corrected slice. Broader modulation, live lifecycle, wrap and song
+domains remain pending.
+

## Norns-class performance scope — 2026-09-10

Performance is now a required pre-refactor campaign, not incidental timing in
individual cases. The emulator plan owns calibrated resource control and generic
probes; Mosaic owns dense-channel/lock/trig/scale/clock/render/recording/persistence
stress cases and musical output oracles. Toolkit/Matrix is deprioritized. Future
Paranoia reviews use Opus only. Implementation and qualification remain pending.


## External-clock burst and long-run phase — 2026-09-10

M-SYNC-021 adds a three-pulse2ms burst with an exactly compensating gap and an
onset inside the burst. M-SYNC-022 runs16 bars from1536 external24PPQN clocks,
checks256 exact note lifetimes, accumulated phase and post-Stop silence. Both pass
controlled and real time on capacity candidate12. The emulator now admits2048
events atomically; its73 contract tests and13 focused capacity tests pass. The
completed Codex review found and then closed a combined event/payload transport
bound. Future reviews use Opus only. Evidence is in
`external-clock-capacity-validation.json`. Larger stochastic corruption and
clock-loss-without-explicit-transport behavior remain open.

## Coverage session — 2026-09-10

User direction: coverage and a full regression suite first; isolated bug fixes
only; no performance fixes or refactor. `tests/behaviour/suite.py` now runs every
Lua contract, Python oracle module, the isolated Lua units and every registered
case in both lanes, fail-closed, with serial rerun and baseline comparison. Its
first collection found three contracts that no longer loaded current production
modules; they were repaired. New cases, each passing both lanes and three fresh
controlled repeats with a demonstrated fault detection: lock-all-to-pentatonic
across all ten scales; keyboard white-key/degree/rotation/transpose options;
Shift press to stop (baseline defect: K3 instead of K1, fixed); chord velocity
boundaries; memory truncation; Elektron program changes (length 4 passes; lengths
2 and 1 fail, open as SEM-013); idle autosave lifecycle; named save/load; channel
active scale slot display; tooltips. Concurrent native startup failed 15 of 18
simultaneous sessions (emulator R22); the emulator line now serialises startup,
and the suite spaces launches because the current campaign emulator checkout
predates that fix.

## Stress triples, persistence and traceability — 2026-09-10

The remaining plan stress triples now run in both lanes with three fresh controlled
repeats and a demonstrated fault detection each. M-TRIPLE-002/003 record live notes
under MIDI clock across a song transition; M-TRIPLE-003 found that a note held
across the transition was stored in the next slot, fixed by capturing the slot at
first press (`record-slot-at-first-press`). M-TRIPLE-004 follows a trigless
silent-destination slide through an external 100 -> 150 BPM step; the ramp is
linear in received clock ordinals. M-TRIPLE-005 records a CC edit while armed and
shows recording clears at the song transition. M-PERSIST-COMBINED-001 restores
that combined state after idle autosave and cold restart; tempo is norns system
state. Per-sequence tempo means per-slot clock divisions of the global tempo
(SEM-014, user decision), covered by M-SONG-TEMPO-001.

Two harness defects were repaired. Commit 0d6387e had redirected the release
lookups in `recorded_note_channel_switch` and `recorded_input_sources` to the
scheduled-input list, so M-REC-005/006/007/015/016/017/024/025 failed with
`KeyError: 'index'` in both lanes since 2026-09-08; they read the snapshot
again, as ff8c27f had already done for the other two sites. The inventory was
missing 90 case-to-requirement back-links and two cases omitted a requirement
the inventory listed them under; `test_inventory` (in the suite) now
fails on either direction of drift.

## Refactor and performance-sweep gap scan — 2026-09-10 (night)

User direction: finish the behaviour and unit/integration suites, then find and
fill the tests a broad refactor or performance sweep could regress
(`refactor-gap-scan.md`). Every scanned claim was checked in code before use; two
were wrong and corrected (the README states 96 song slots, not 90; the D4 step
argument is masked, not observable).

Seven defects were found by the new tests, each with a Lua unit regression, a real-input
behaviour regression that fails on the baseline, an isolated fix and a candidate
record: memory history after wrapping (M-MEMORY-004), the quantiser cache raising
after about 100 scale saves (M-SCALE-CACHE-001), nb/norns parameter step locks
raising at Play (M-XA-005-NB-LOCK, nb-audio runtime), fractional length masks shown
as X after reload (M-SAVE-LENGTH-001), slides dropped once 1024 replaced slides sat
behind a long one (M-SLIDE-CAPACITY-001), + New keeping the previous project's
memory (M-MEMORY-005), and Elektron program changes sent only to channel 1's port
(M-OPT-ELEK-004).

Refactor guards: seven shadowed Lua unit tests revived (`test_lua_test_names`
prevents repeats); every production Lua file must compile (`test_lua_syntax`; the
units never load the pages); division table alignment; a real tabutil save/load
round trip; the Sinfonion global-lock path; 14-bit CC splitting; processing order of
the global scale track (M-SCALE-ORDER-001); failed saves and autosave suspension
(M-SAVE-FAIL-001); and frozen saved projects from the current version and release
1.2.12 (M-PERSIST-FIXTURE-*). Restart-style cases now close their second session on
failure; leaked sessions had exhausted JACK's server slots.

Second pass (UI state machines, MIDI input, algorithms, hot loops, shared state): three
more defects fixed with real-input regressions — the "Autosaved" tooltip never expired
because tooltips freed metro slot 1 instead of their own id (M-TOOLTIP-002); song
commands queued during playback survived Stop invisibly (M-SONG-QUEUE-STOP-001,
arbitrated SEM-015 discard-on-stop); releasing the copy source first erased it
(M-SONG-COPY-001, arbitrated SEM-016 press order for slot copy only). The real
scheduler is pinned by Lua units; a cancelled-mid-sweep slice and a `lengths_mask`
typo are recorded as latent; a claimed transpose side effect of incoming MIDI was not
reproduced. Mapped mask, trig-param and memory controls now have an equivalence case
(M-MAP-003). The root disk filled at midnight: the 5e0501a baseline suite was
truncated and is invalid; large observations were gzipped in place (evidence kept)
and the full suite was restarted at 8bd70b5 with a compressor alongside.

Full suite at 8bd70b5 (real-time lane from the original run, controlled lane from a
parallel run at the same tree; combined in `suite-8bd70b5-combined`, serial rerun in
`suite-effective.json`): 1504 case runs, 18 still failing and 3 load-sensitive
(real-time M-PARAM-040, M-SYNC-020, M-TIME-007 pass serially). The 18 are all known:
four M-OPT-ELEK-002/003 runs (SEM-013 pending), eight M-PANIC-007..010 runs on an
oracle that predates `b1afcc5` (arbitrated SEM-018: a fresh project sends no startup
Stop; oracle corrected, green in both lanes), and six controlled-only fixtures that
assert on the clock mode in the real-time lane (now declared `controlled_only` and
recorded as not applicable there).

Third pass: M-STARTUP-TRANSPORT-001 pins both boots from the native export (fresh:
no transport; autosave: one Stop per port). M-MAP-004 found that a fixed-channel mask
map wrote another channel's held-step masks from the selected channel's value
(fixed, SEM-017). M-TIME-013, M-MEMORY-007 and M-GESTURE-ORDER-001 pass in both
lanes. M-PAT-BOUNDARY-001 is red at a 1 ms margin (controlled) and green at 10-80 ms:
an edit that close to a song boundary is heard one pass late; the fix changes
boundary scheduling, so it is deferred to the refactor. A full suite at 96d465d runs
with the concurrent scheduler.


## Independent handover audit and canonical dense performance — 2026-09-12

The Opus handover was checked against clean ab3e705. All 51 hashes referenced by state.json resolve and match. Fresh validation passed the six inventory/name/syntax guards, 1471 Lua units, all 24 applicable reruns of the stale 8bd70b5 suite failures, all 40 base-MIDI runs for the post-reference fix regressions across real-time and controlled lanes, and M-XA-006 in its n.b. real-time profile. The historical combined suite remains stale rather than reclassified as green.

Canonical constrained measurements are bound in perf-dense-canonical.json. PERF-002 passed 12/12 at 1, 4, 8 and 16 channels. PERF-003 produced exact notes, balanced releases and complete ordered CC slide curves in all 12 runs, but its event-timing gate failed in 16-channel repeats 2 and 3: p99 10.063 ms and 10.562 ms (10 ms gate), maximum 11.993 ms and 12.483 ms. Repeat 1 passed at 8.268 ms p99. Peak RSS stayed below 422 MB, queue high-water was zero, and workload-window CFS throttling was zero. This is refactor evidence for the norns-class x86 proxy, not physical-norns equivalence; thresholds are unchanged and no performance fix was made.


## Unit/integration hardening matrix — 2026-09-12

The mandatory final hardening pass is active. unit-integration-hardening-matrix.json assigns all 141 manual requirements, 67 production Lua modules and 55 existing unit/integration files to 15 domains, with finite-axis cardinalities, interaction strategies and explicit residual gaps. test_hardening_matrix.py fails if the manual or inventory changes without reconciliation, if any requirement/module/test loses an owner, if a behavior reference goes stale, or if a finite-axis claim lacks a positive cardinality and coverage method. The matrix is a work queue and does not claim its residual gaps complete.


## Merge arithmetic hardening  2026-09-12

H05 now includes an independent, README-cited merge matrix. Six top-level Lua tests
sweep all 17 overlap counts (zero through all 16 sources), all three trig modes,
all 16 priority identities for note, velocity and length, signed and half-up
numeric partitions, fractional length outcomes, empty and singleton contributors,
source insertion orders, source/result immutability and channel/mask isolation.
The complete Lua unit/integration suite passes 1477/1477. The nine inventory,
matrix, test-name and Lua-syntax guards also pass. This slice changes no production
code. MIDI-bound effects and merged-scale cache invalidation remain explicit H05
gaps requiring native/composed coverage.


## Parameter-lock and trig-parameter hardening  2026-09-12

H04 now exhausts every probability value from 0 through 100 against the complete
099 draw domain through step.handle. It also exercises all ten parameter-lock and
slide slots at song slots 1/96, channels 1/16 and steps 1/64, checking clamp, Off,
replacement, full-step clear, and song/channel/step isolation. The complete Lua
unit/integration suite passes 1480/1480. No production code changed. Cross-family
assignment UI and probability interactions with random pitch, transitions and
persistence remain explicit composed/native obligations; the pending S34
single-lock slide-clear semantics were not altered.


## Scale, cache and pentatonic hardening  2026-09-12

H06 now distinguishes 16 editable scale slots from the ten production scale
types. All 16 slots are exercised through warmed-cache save changes; a copied song
slot is verified independent of later source edits; type names/numbers are bound;
and all eight all/merged/random pentatonic setting combinations run through
step.handle in merged-note and random-offset contexts with exact MIDI assertions.
The complete Lua unit/integration suite passes 1484/1484. No production code
changed. The characterised set-all scale alias and unsupported in-place mutations
remain explicit gaps pending native evidence or route-level coverage.


## Chord overlap and release hardening  2026-09-12

H07 now creates ten simultaneous owners from two consecutive five-voice chords,
including two owners for each repeated pitch, then verifies Stop emits exactly ten
matching releases. A separate probability-zero case proves the root and all four
delayed strum voices remain silent through subsequent pulses and Stop. The full
Lua unit/integration suite passes 1486/1486. No production code changed. The
snapshot-versus-live semantics for delayed voices across scale or device changes
remain explicit, because choosing that contract requires native observable
evidence rather than a unit-only assumption.


## Pattern algorithm application hardening - 2026-09-12

H01 now drives the real trigger-editor handlers for all four algorithms at their
maximum legal fader and bank boundaries. Independent arithmetic oracles check all
64 painted cells, selected-pattern isolation, inactive-song activation, XOR paint,
length storage, repaint erasure and cancel preservation. The underlying drum,
tresillo and numeric generators retain exhaustive input-domain coverage in
drum_ops_extra_tests.lua. The complete Lua unit/integration suite passes
1488/1488. No production code changed. Deterministic generated edit sequences
remain an explicit H01 gap.


## Memory history hardening - 2026-09-12

H11 now crosses both production memory event types through all four scalar mask
fields, all four chord voices, all ten trig-lock slots, song and step boundaries,
undo, redo-all, branch truncation and serialized redo tails. The complete Lua
unit/integration suite passes 1491/1491. No production code changed. S58 is
minimized with a capacity-three sequence: after edits 60,61,62,63 leave retained
events 61,62,63, undoing the retained log restores nil instead of the required
pre-retention floor 60. It remains unfixed pending the required native behavior
baseline; full project-file reload remains behavior-owned.
