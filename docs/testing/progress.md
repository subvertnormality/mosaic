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
