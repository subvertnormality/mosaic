# R10 playback ownership

## Existing pending-action inventory

| Action | Owner and identity | Time domain | Cancellation and terminal cleanup |
|---|---|---|---|
| Delayed strum onset | step closure captures note container, chord data and channel; scalar delayed-action ID belongs to channel clock | Channel-relative delayed action | Lattice reset discards future onsets; callback resolves live scale using the existing captured channel |
| Ordinary voice release | Note container retains player, MIDI channel/device; callback retains note and velocity | Channel-relative gate; nonpositive gates release immediately | must_execute IDs flushed on Stop; Note Off remains owed after Note On |
| Arp voice release | Same captured container, release ID additionally belongs to arp release_ids | Parent-channel phase plus off-phase offset; before-onset priority | execute_at_note_end plus arp finish flush; cancelling future arp onsets leaves owed releases intact |
| Arp next onset | Per-channel arp_sprockets and closure-local arp reference, interval and stop state | Lattice sprocket, channel division and shuffle projection | cancel_arp_onsets destroys future sprockets; finish also flushes owned release IDs |
| Slide sample/endpoint | Bounded ring slot, channel/parameter owner index, end occurrence | Absolute lattice transport plus projected channel onset occurrence | Replace silently; explicit finish may emit endpoint; retire ownership before callbacks; division/shuffle changes rebase without immediate output |
| MIDI transport pulse | midi_output_transport subscription, active flag, generation and epoch | Native outgoing F8 boundary plus intermediate scheduler deadlines | Cancel subscription and intermediate clock on Stop/reset; no generation guard is used to suppress owed voice releases |

This is the current ownership contract, not a claim every R10 extraction is done.
The MIDI adapter retains its existing note-count handling for overlapping pitches.
No universal generation system, new queue, heap or lattice rewrite is introduced.

## Voice emission/release boundary

`lib/clock/voice_lifetime.lua` now owns the existing On-then-schedule-Off helper
and ordinary/arp gate wrappers. It is constructed once with m_clock; step keeps
musical resolution, live-scale timing, dashboards and future onset decisions.
The callback still reads the captured note container, retaining existing behavior.
No new per-voice allocation, return convention or route remapping is introduced.
The unused selected-song/channel lookup was removed from that helper.

The existing arp release contract uses the explicit module instead of recursively
searching private step functions. All 54 combinations of parent period and arp
division pass. Reentrant Stop drains owned releases once; the boundary contract
still places release before onset. Full Lua suite: 1545 passed (27.608 seconds).
Six inventory/name/syntax guards passed. Existing step tests cover parent-route
retention during delayed live-scale edits and immediate nonpositive gate release.

Next: extract slide storage/interpolation/retiming behind the existing m_clock API,
then arp lifetimes and transport transitions one at a time. Preserve ring traversal
and reentrant callback behavior. Full R10 timing/profile acceptance remains owed.

## Native extraction regressions

| Case | Mode | Passing run |
|---|---|---|
| M-ARP-002 | controlled-experimental | 98a5a2f666f344f18a601200eaeca810 |
| M-LEN-004 | controlled-experimental | dfe7e87a914e4177bfa4748aa098fe04 |
| M-MIDI-001 | controlled-experimental | 2c31d93153c841c2bafa689d34a97f10 |
| M-ARP-002 | real-time | dcebda568973451aa0e4c6d5d468cbe3 |
| M-LEN-004 | real-time | c332bce9dbc842a087a9ecf6617f6c66 |
| M-MIDI-001 | real-time | 6df424ca88644e9aa449dd9508f0a5df |

Sol reviewed emission order, capture, scheduling flags, return behavior and allocation shape; no concrete correctness issue found. These results cover the extraction, not full R10 acceptance.

## Owned slide storage, interpolation and retiming

Base 6ace2ce. lib/clock/slide_lifetime.lua owns the 1024-slot ring, channel/slot
ownership index, compaction, sampling, cancellation, destination handoff, retiming
and reset realignment. m_clock retains its existing public methods, channel/lattice
construction, schedule projection and order-5 sampling sprocket. The module factory
receives the existing clock/program objects and a live lattice getter. Callback-time
lattice replacement therefore preserves the previous global lookup behavior.

The extraction preserves capacity/full policy, slot-reference ownership through
compaction, retirement before callbacks, fixed-end cancellation/handoff traversal,
last-value handling, fractional quantisation and projected endpoint occurrence.
It changes no clock algorithm, dispatch priority, overflow policy or musical timing.

Six composed contracts now capture the actual module instance through their include
stub instead of finding private m_clock.init upvalues. Only setup changed; stimuli
and assertions remain. All passed: cancellation 18/18, reset, live retime, retime
phases 14, endpoint phases 864/864 and timing type. Six guards pass. Sol's review
found no concrete semantic/binding issue in the extraction.

The first full Lua run had one failure in
`test_chord_strum_param_lock_with_four_extra_notes_division`: expected 62, actual64
at param_tests.lua:1404 (1544/1545 passed, 25.352s). It passed alone (0.007s), then
the entire 1545-test suite passed (24.679s) with no further production changes.
Cause is not established; this is not labelled a baseline defect or erased by the
rerun. Native slide validation below remains scoped to the extraction, and full
R10/final acceptance remains outstanding.

| Case | Mode | Passing run |
|---|---|---|
| M-PATCH-064 | controlled-experimental | c5690c91a95746c58c1b79a39e7fbf5a |
| M-SLIDE-RESET-001 | controlled-experimental | 8783ee6b1cbb44f39d211542295af3ff |
| M-PATCH-064 | real-time | b29a56bcc5d64aadbc366de9fcccb2ba |
| M-SLIDE-RESET-001 | real-time | b121ad16cfa94b1a9a2e52c583f130f2 |

Next structural slice: arp onset lifetime and release-list ownership, retaining separate cancellation of future onsets and cleanup of releases already owed.

## Arp onset and terminating-release ownership

Base acecaa7. arp_lifetime owns per-channel sprockets, first/following-gap state,
stop-onsets and finish callbacks, and the release list supplied by the voice path.
m_clock retains channel construction and public cancel/new-arp aliases. Init still
destroys old arps before resetting channels 1..16; channel0 behavior is unchanged.
Finishing clears each release ID and pending action before invoking callbacks;
merely cancelling future onsets retains releases already owed.

The initial extraction incorrectly captured the global m_clock table. Full units
reported 29 errors and one load-sensitive dense-slide failure (5.077ms vs5ms),
with 1515/1545 passing. Isolated
`test_rests_apply_when_in_last_chord_slots_multiple_slots` reproduced a nil parent
clock at arp_lifetime.lua:86. A live clock getter preserves the original dynamic
global accesses and fixes that extraction regression. Inspection identified and
corrected the same capture difference in the preceding slide realignment slice;
its quantizer remains captured once as in the original implementation.

The scoped review initially missed this binding difference; unit evidence exposed
it. Re-review confirmed the scope. This is a refactor correction, not a new Mosaic
behavior change. A dedicated slide clock-replacement test now verifies that the
new parent is projected without emitting an extra sample.

After correction: all 1545 then-existing Lua tests passed (24.592s). The added
clock-replacement test passed separately; six guards pass. All54 arp/parent release
combinations and the reentrant Stop contract pass. All six slide contracts pass,
including864 endpoint phases,14 live retiming cases and18 cancellation cases.
Native receipts below cover the extraction; R10 aggregate acceptance remains owed.

| Case | Mode | Passing run |
|---|---|---|
| M-ARP-002 | controlled-experimental | 36157e8974fe4543b941733d02af483e |
| M-ARP-012 | controlled-experimental | b720b93b8ab44e1788c206cec73f283b |
| M-SLIDE-RESET-001 | controlled-experimental | 1267e3e8690c44e8b00818c3a4b35c52 |
| M-ARP-002 | real-time | b5d22786ebc3443fb860f75cadbd5fdf |
| M-SLIDE-RESET-001 | real-time | dff0a151847a46f1840d75fd1b6b1687 |

M-ARP-012 real-time attempt7252a898ad8d4970b5e025487b4ffbfd was rejected
by its explicit controlled-only precondition before behavior assertions. It is
not a real-time pass or a Mosaic regression; absolute live-edit deadline mapping
is not admitted in that lane.

## Next transport slice

Incoming Start/Continue/SPP decoding belongs to norns; Mosaic's native transport
callbacks enter m_clock start/stop. Do not invent a second input state machine.
Extract only the existing playing state, output subscription cancellation and
start/stop/reset orchestration. Keep first_run, delayed release lists and channel
construction with their existing owners. Preserve live global clock/lattice
lookup and Stop release draining. midi_output_transport already owns the native
F8 boundary, epoch and intermediate deadlines and should remain unchanged.

Final suite including the new clock-replacement regression: 1546/1546 passed (25.730s), after native runs finished.

## Transport lifecycle extraction (0b6a63f)

Base2e60f7d. transport_lifecycle owns playing/subscription/warning state and existing
start/stop/reset orchestration. m_clock retains first_run and release lists via
callbacks. Dynamic clock/lattice lookups, method self and local dependency captures
preserve the original bindings. Native F8 adapter and norns input decoding remain
unchanged. Sol review found no concrete difference. Full1546 Lua tests passed
25.728s; six guards, reentrant Stop and8 native-output adapter scenarios pass.

Controlled006/010/014 passed respectively80350c6e1d8140cea94e831019115b3e,
429e86cbe8a34ac9b15ffa8f1a138060,992548fd3c3945fd9a527a873fb06912.
Real-time comparison against detached baseline2e60f7d shows default runtime failures
in all three on both revisions. Explicit midi-schedule-capacity-12 installation
passes010/014 on both and fails006 on both. Bounds and recipes unchanged.
M-SYNC-006 phase accuracy remains unresolved; this is preservation evidence, not
full timing acceptance. R10 aggregate quick and affected performance/profile
validation remain outstanding.

| Runtime | Revision | Case | Passed | Run ID | Failure |
|---|---|---|---|---|---|
| default | candidate | M-SYNC-006 | False | 82fe12120ae34b8c8e60255aecaa0232 | ('Onset phase', 4, 0.012853421999999948) |
| default | candidate | M-SYNC-010 | False | d4e4bfb9a6184b55b39feada620bbd72 | ('Receiver step/clock mismatch', 0, -1) |
| default | candidate | M-SYNC-014 | False | 0d98e063a4e642aab01f270e907bcccc | ('Onset phase', 0, 0.026652153) |
| default | baseline | M-SYNC-006 | False | f77fa8a592fa45cdb4b5f23fc10f3e72 | ('Onset phase', 4, 0.021844955000000055) |
| default | baseline | M-SYNC-010 | False | 4b5e53d4a2bd4ea088f0f30571053086 | ('Receiver step/clock mismatch', 0, -1) |
| default | baseline | M-SYNC-014 | False | b32262dce5a246cfb2bab6c182aabce2 | ('Onset phase', 0, 0.026745972) |
| explicit | candidate | M-SYNC-006 | False | fed3410772954474a28893fef7497599 | ('Onset phase', 4, 0.020835495000000037) |
| explicit | candidate | M-SYNC-010 | True | a6c0400411b04345b023d785b9618c44 |  |
| explicit | candidate | M-SYNC-014 | True | efb84d4c6e784b6aba7c1ace1220459c |  |
| explicit | baseline | M-SYNC-006 | False | ec95e97235fe463fba2d18f684549571 | ('Onset phase', 4, 0.010015409999999947) |
| explicit | baseline | M-SYNC-010 | True | 8c7774f104d64675849698be816f5f8d |  |
| explicit | baseline | M-SYNC-014 | True | b8fe7220987440ce9086f70755976e4a |  |

Baseline receipts are under /home/andy/projects/mosaic-behaviour-runs/mosaic-behaviour-runs; candidate receipts under /home/andy/projects/mosaic-behaviour-runs.


## Aggregate controlled regression, 2026-09-13

At 86c94c3, the base-MIDI controlled suite completed 791 native cases: 788
passed and three failed; source identity stayed stable. Original report:
`/home/andy/projects/mosaic-behaviour-runs/r10-quick-86c94c3-20260912/suite.json`.
This is not all-profile or real-time release acceptance. The original report
remains failed; no assertions or thresholds were relaxed.

M-CHORDSHAPE-201 failed during sclang startup and passed its isolated unchanged
rerun (`edf7b70e54684260ad2446a09a44719c`). M-MEMORY-008 reproduced velocity 50
instead of restored 117 after undo (`15fd65ba094342dfa53addc644e43d1f`).
M-PAT-006 reproduced a note-entry LED assertion failure before inactive-pattern
playback (`ba2652f41f7c4dfda249ded4155a6b2d`). Both latter failures also occur at
5ada934, before scheduler/playback extraction, with identical assertion sites
and, for undo, identical output. Baseline manifests are under
`/home/andy/projects/mosaic-behaviour-runs/mosaic-behaviour-runs/`:
`b39aaaa8e7b84dcdaca61815424be9b9` and `f09ac4d3856a47bdb6ade74744f5a463`.
They remain unresolved; this comparison excludes R09/R10 as their introduction,
not earlier refactor changes. Next: trace earlier provenance and compare real time.

Four fast-layer failures were test setup/metadata drift. Explicit include routes
now load extracted production modules in three standalone contracts, preserving
all assertions. Revalidation passed 64 reset decisions, 16 composed step/lattice
cases and 9 slide destination cases. The existing hardening inventory was
reconciled with extracted modules/tests; its unchanged four checks pass. Production
code is unchanged by these repairs, so the 791-case run is retained rather than
repeated for fixture-only edits. Full Lua units in the aggregate passed 1546/1546.


### Aggregate follow-ups resolved, 2026-09-13

Velocity undo is fixed in e89f02c, with baseline failures in both lanes, undo/redo
passes in both lanes, three controlled repeats, 1546 Lua tests and six guards.
Candidate: `tests/behaviour/candidates/held-velocity-undo-prior-state.json`.

M-PAT-006 expected a steady level 12 at every authored note. The selected-pattern
indicator in vertical_fader.draw intentionally offsets the row-1 selected note
to 11/13. The test now characterizes that one cell explicitly and retains exact
level 12 on other selected notes, plus all silence, pitch, duration and spacing
assertions. No production renderer change. Full controlled workflow passed:
`70fb7ba082e048eb86bce0894bd1a849`. First real-time attempt
`a01882a68f2d4c2398b607bb6a092c0d` passed LED checks but failed later durations:
two of 128 notes had +16.695/-17.325 ms error; others were within 1.173 ms.
The unchanged real-time rerun `78025c38bf874fc7a64fabf78da1fead` passed the full
workflow. Retain the first failure as an intermittent timing observation of
unestablished cause, not proof of a fixed timing defect. Bounds are unchanged.
The aggregate report remains the original failed report; these focused receipts
resolve its case follow-ups without falsely claiming all-profile qualification.
