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
