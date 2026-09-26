# UI acceptance coverage (spec.json#/acceptance_matrix A01..A19)

Status of each acceptance item against the behaviour cases that exist on
`codex/ui-reimplementation` (tests/behaviour/cases.py and its modules), plus the Lua
integration tests where they are the only evidence. "Covered" means a
registered behaviour case drives the live app through public input and checks
the visible and musical result the item names. Everything the item names that
no case checks is listed under "Uncovered", honestly, including the parts a
passing case only reaches halfway.

The live-UI acceptance cases `M-UIACC-A01-001`, `-A02-`, `-A03-`, `-A10-`,
`-A11-` and `-A19-001` (`tests/behaviour/contract/live_ui_acceptance.py`) are
committed and, per their author, pass in both lanes. `M-UIACC-A18-001` passes in
both lanes on this branch.

Legend: RT = real-time lane, CT = controlled-experimental lane.

## Summary

| Item | Subject | Status |
|---|---|---|
| A01 | E1 family navigation C01/C02/N01 | covered (M-UIACC-A01-001) |
| A02 | held steps + K1+K2 clear, release order | covered (M-UIACC-A02-001) |
| A03 | assignment picker, K2 cancel, K3 apply, slides | covered (M-UIACC-A03-001) |
| A04 | Merge Shape field domains, Apply stopped/running, drafts | partial (musical; screens by A18) |
| A05 | Harmony groups 16/17, validation, delete confirm | mostly uncovered |
| A06 | Tone map binding, reset draft | mostly uncovered (screens by A18) |
| A07 | event inspection H05/H06/H15/H16/H18 | partial (M-HARMONY-ENSEMBLE/FAILURE) |
| A08 | Rhythm Doctor lifecycle R01..R16 | uncovered by registered cases |
| A09 | Rhythm Doctor lanes, browse, paint | uncovered by registered cases |
| A10 | Norns follows channel/pattern/mute/merge gestures | covered (M-UIACC-A10-001) |
| A11 | pattern pages, generators, viewer channel | mostly covered (M-UIACC-A11-001 + musical cases) |
| A12 | Scale S01..S05 | partial (musical); S04/S05 unreachable |
| A13 | Song A01..A03 | musical semantics covered; screen scopes partial |
| A14 | external transport, panic | musical/transport covered; screen side partial |
| A15 | lock lead time | covered (musical and native value) |
| A16 | native menus, persistence | largely covered |
| A17 | device, dynamic params, live lock recording | musical covered; screen identity partial |
| A18 | native screen sweep | covered for reachable screens (M-UIACC-A18-001) |
| A19 | C06 output inspection | covered (M-UIACC-A19-001) |

## A01 — E1 moves Masks, Trig params and Channel tasks

Screens C01, C02, N01. MAN.015/016.

- Covered: `M-UIACC-A01-001` (E1 at Masks clamps for one detent and one large
  event; a large positive event moves one family at a time; negative E1 at
  Channel tasks restores Trig params with its remembered slot; no MIDI, mask or
  LED change and the phrase replays exactly). Also `M-LIVEUI-TASKS-001`,
  `M-LIVEUI-FOLLOW-001` and the A18 sweep.
- Uncovered: RNG state is not observed directly (only through the exact phrase
  replay).

## A02 — held steps 1 and 64, K1+K2, release in either order

- Covered: `M-UIACC-A02-001` (steps 1 and 64 held, K1+K2 clears only the held
  steps on Masks and on Trig params; channel defaults and unheld locks stay on
  screen and in MIDI; both release orders restore the family at channel scope).
  Musical clearing cases `M-MASK-*`, `M-MEMORY-*`, `M-TRANS-003`.
- Uncovered: nothing named by the item beyond these.

## A03 — assignment picker (C07)

- Covered: `M-UIACC-A03-001` (the picker opened from slot 2 keeps its target
  slot; K2 discards an unapplied browse; K3 applies and repeats idempotently;
  Off sends no CC; held step + K3 slides CC1 between locks in order). Musical:
  `M-PARAM-*`, `M-PATCH-*` (CC/NRPN encodings, wrap), `M-REC-PARAM-011/012/020`.
- Uncovered: NRPN and wrap policy are proven by the musical cases, not inside
  the picker case.

## A04 — Merge Shape screens M02/M03/M04/M06/M07/M12/M13/M14

- Covered musically: `M-MERGE-FOUNDATION-001` (Foundation with P01 anchor,
  accented additions), `M-MERGE-PHRASE-001` (two-cycle Build phrase).
  `M-UIACC-A18-001` reaches M02, M03, M06, M07, M12, M13, M14 through their action
  rows and checks field values, including Add amount max 100, Anchor gap max 8
  and Seed min 0.
- Uncovered: every field's domain boundary (Seed 65535 is not reachable in
  practice: E3 moves one per event, 65535 events), validation errors attached to
  a field, Apply while running (queued vs active revision; M04 is a snapshot
  variant that no public input shows), "make second draft", and cancel keeping
  an accepted queue (M09 variant). The deterministic seed invariant is only
  asserted by the musical Foundation case at one seed.

## A05 — Harmony groups (H01/H04/H07/H10/H17)

- Covered: `M-HARMONY-ENSEMBLE-001` (four-channel group workflow),
  `M-UIACC-A18-001` (create a group, apply it, open Members/Source/Policies/Entry
  and the Delete group question, K2 cancel).
- Uncovered: creating 16 groups and the refused 17th (INVALID GROUP LIMIT),
  duplicate member validation reason, disabling a group, delete confirm, stale
  delete token, dependent Merge repair (target reset to legacy) on delete.

## A06 — Tone map (H11/H19)

- Covered: `M-HARMONY-PATTERN-001` (pattern mode maps identities musically);
  `M-UIACC-A18-001` opens H11 and H19 (Reset map "PAT 1 / AVERAGE") and cancels.
- Uncovered: selecting a different source binding, editing the map, Reset
  cancel/confirm effect on the draft, "reset remains draft until owner Apply",
  and the "other binding maps unchanged" musical clause.

## A07 — event inspection (H05/H06/H15/H16/H18)

- Covered: `M-HARMONY-FAILURE-001` (NO VOICING visible, only the mapped tone
  silenced), `M-HARMONY-ENSEMBLE-001` (local scale/octave bypass with visible
  checks). `M-UIACC-A18-001` opens H05 and checks Step 1 / NO EVENT / NONE.
- Uncovered: inspecting steps 1 and 64 while playback advances, mute during
  inspection, delayed voices, "no solve/RNG/MIDI triggered by inspection". H15,
  H16 and H18 are visual variants no public input selects; H06 needs a failure.

## A08 — Rhythm Doctor lifecycle (R01..R16)

- Evidence today: standalone acceptance scripts `tests/behaviour/rhythm_doctor.py`
  (fifth algorithm, phrase navigation), `rhythm_doctor_surface.py` (stopped
  setup controls, owned input and transport gate) and
  `rhythm_doctor_correction.py` (refused correction visible). They run through
  their own `main()`, are not registered in `cases.py`, and their docstring says
  they are "intentionally red until RD-04". Lua: `lib/tests/lib/ui_adapters_doctor_tests.lua`
  and `ui_live_tests.lua` (R01 from doctor_routes; E2/E3/K2/K3 reach the page
  handlers once). `M-UIACC-A18-001` checks R01 (READY) only.
- Uncovered by any registered behaviour case: worker absent/failure/restart,
  capture finish by Record and K3, cancel_capture/cancel_correction questions
  (R03/R16) answered K2 and K3, correction reject/apply (R07), ALIGNMENT_REQUIRED
  and clear (R10/R12), stale question after completion/transport start,
  transport start in each state (R11), READY editing while playing (R05),
  setup draft keep/discard (R01/R14), server ten-lane bank and fallback,
  disconnect, leave/re-enter algorithm 5. (The sweep opens R01 from Pattern
  tasks and from the grid.)

## A09 — Rhythm Doctor lanes, browse and paint

- Evidence: the standalone scripts above (phrase navigation) and Lua doctor
  adapter tests.
- Uncovered by registered cases: lane select for three-lane and ten-lane banks
  including (7,2) and (3,3), inert cells, browse tap/hold at both boundaries,
  paint toggle/add/replace, cancel an armed preview, arm-start-commit, stale
  preview after E3 or slot change, paint undo/redo API.

## A10 — Norns follows channel, pattern, dual range, mute and merge gestures

- Covered: `M-UIACC-A10-001` (channel selection, pattern add/remove, trig and
  note merge gestures, mute by shift and long press, both dual-range release
  orders keep Masks with footer feedback; a held note merge + unassigned pattern
  shows Merge detail without assigning it; LEDs and merged MIDI follow the
  README arithmetic). Also `M-LIVEUI-FOLLOW-001`, `M-NAV-001`, `M-MUTE-001`,
  `M-MERGE-TRIG-002` and the numeric merge cases.
- Uncovered: M09 (the merge gesture screen inside Merge Shape) is shown and hidden
  within one short press, so no case observes it.

## A11 — pattern pages and viewer channel

- Covered: `M-UIACC-A11-001` (E3 on View channel on P01/P03/P04/P05/S03, clamped
  1..16 and kept per context; E2 and E3 off the field change nothing; no MIDI;
  the selected channel stays 1 and a later grid step edit plays on channel 1).
  Musical: `M-ALG-001..004`, `M-ALG-PAINT-RACE-001`, `M-EDIT-*`, `M-PAT-*`,
  `M-VIEW-001`. The A18 sweep reaches P01..P08 and checks that E2 on Trig options
  moves its own focus and leaves the viewer on channel 01.
- Uncovered: source select K1/long and duplicate source banks as live-screen
  checks; generator input roles/unused inputs on P06 (P06 lists algorithms only).

## A12 — Scale S01..S05

- Covered musically: `M-SCALE-001` (edit-only gestures, applying, global off,
  re-entry through screen/grid/MIDI), `M-SCALE-002` (channel hold, lock
  persistence), `M-SCALE-003`, `M-SCALE-004` (16 slots edit-only isolation,
  precedence), `M-SCALE-LOCK-003`, `M-SCALE-ORDER-001`, `M-TRANS-001..009`
  (step/scale/song transpose), `M-SCALE-DISPLAY-001`. `M-UIACC-A18-001` checks S01
  (Scale, Degree, Transpose, Rotation), S02, S03 and P05 in Scale.
- Uncovered: "clear current slot", "hold global steps then scale/transpose/
  octave" on the live scope text, all-song confirm/cancel (S05 is never shown:
  no router path sets it), S04 (never shown), and the explicit
  edit/applied/locked scope on screen.

## A13 — Song A01..A03

- Covered: `M-SONG-FLOW-001` (song mode, queues to boundary), `M-SONG-QUEUE-STOP-001`,
  `M-SONG-COPY-001` (copy source first pressed in either release order, erase),
  `M-SONG-LENGTH-001/002` (all 64 global lengths, clamps), `M-SONG-SETTINGS-001/002`
  (repetitions, tempo bounds), `M-SONG-TEMPO-001`, `M-TIME-005`.
  `M-UIACC-A18-001` checks A01, A02, A03 and N05 frames.
- Uncovered: the 96-slot boundary, and "edit/playing/queued separated" on A03
  while running (the sweep only sees it stopped).

## A14 — external transport and panic

- Covered: `M-SYNC-001..023` (external Start/Clock, lost clock freewheel, jitter,
  drift, stall), `M-SYNC-014` (Continue/SPP limitation), `M-OPT-STOP-001`
  (stop safety), `M-PANIC-001..014` (non-selected page long hold panics with no
  navigation, overlapping holds, hot-unplug), `M-KEYBOARD-STOP-001`,
  `M-REC-017..019` (live chord record first/final note release),
  `M-STARTUP-TRANSPORT-001`.
- Uncovered: "transport updates without focus theft" as a live-screen check
  (field focus before/after an external Start), and "panic does not navigate on
  release" asserted with the live header (the panic cases assert MIDI and
  "no navigation" through the grid menu LEDs, not the live header).

## A15 — lock lead time

- Covered: `M-SYNC-LEAD-001` (25 ms default, values early by a pulse or more,
  unshifted notes/clock, gates at 0/5/10/25 ms), `M-SYNC-LEAD-002..019` (0/25/50
  ms, x4/x16 clocks, swing/shuffle, a global slide, tempo change, resend off,
  channel ranges). The
  native value and units are checked by the driver's lead-time setup on every
  case (`Driver._set_midi_lead_time`: menu row "Lock lead time (ms)").
- Uncovered: "early sent lock edited" after it was sent, and "shared MIDI
  address" (two slots on one address) under lead, as named cases; the lead
  value is read back on the native menu, not on a live Mosaic screen.

## A16 — native menus and persistence

- Covered: `M-SAVE-NAMED-001` (text entry, cancel writes nothing, overwrite),
  `M-SAVE-FAIL-001` (save failure keeps autosave suspended), `M-SAVE-001/002`
  (idle autosave), `M-PROJECT-LIVE-001..004` (native new/cancel/accept dialogs
  while playing), `M-RANGE-SAVED-001..006` (rejected loads, legacy alias
  migration), `M-PATCH-051` (pre-policy NRPN project migrates to historical
  mode and keeps bytes), `M-PERSIST-*`, `M-TOOLTIP-002`, `M-LIFECYCLE-001`.
  `M-UIACC-A18-001` opens and closes the norns menu with short K1 and checks the
  live screen returns unchanged.
- Uncovered: "native exclusive key ownership" as a live-screen check,
  "return generation checked" (a stale question after a menu round trip), and
  X01..X09 as live-screen variants (norns draws its own menu).

## A17 — device, dynamic parameters, live lock recording

- Covered: `M-SETUP-003` (config defaults on confirmation), `M-SETUP-001/002`,
  `M-SETUP-UNREADABLE-CONFIG-001`, `M-SETUP-DEVICE-NAMES-001`, `M-XA-007-NB-SWITCH-SLOTS`
  (device switch empties slots), `M-REC-PARAM-001..031` (live mapped lock
  recording: wrap, pause/resume, assignment/device change during record),
  `M-MAP-001..004`, `M-PARAM-*`. `M-UIACC-A18-001` checks C05 including the
  staged maximum MIDI channel (CC16) with its RESET/REBUILD consequences and
  K2 cancel.
- Uncovered: C10 and C11 are never shown (no router path), so "explicit
  destination and parameter id" on those screens and "removed field consumes
  pending delta" have no live-screen check.

## A18 — native screen sweep

- Covered by `M-UIACC-A18-001` (`tests/behaviour/contract/live_ui_sweep.py`), RT
  and CT. It opens 50 live screens through public input and, on each, checks
  the exact title and scope, that LAYOUT OVERFLOW is not painted on the layout's
  overflow line, that the footer (rows 56..63) is exactly the hints, the
  focused-screen neighbour labels E2 can reach, or a named tooltip, and the
  selected field's whole value on its full-value route. Includes a long
  parameter name ("Quantised Fixed Note": fitted "QUAN" cell, whole name on the
  value line and on C13; "Quantised Fixed~" in the picker), long raw values
  (GLOBAL_EFFECTIVE, "PAT 1 / AVERAGE" on the tone-map reset question), OFF,
  NONE, X, NO EVENT and 0 kept distinct, maximum values (MIDI channel CC16, Add
  amount 100, Anchor gap 8), minimum Seed 0, and values at the 70 px art
  boundary (NEAREST, PATTERN).
- Screens reached: C01..C07, C09, C12, C13, M02, M03, M05, M06, M07, M12, M13,
  M14, H01..H05, H07..H11, H17, H19, S01..S03, P01..P08, A01..A03, N01..N05,
  R01 (from the grid and from Pattern tasks), and the norns menu round trip.
- Not reachable through public input on this build (no router path sets
  them): C08, C10, C11, S04, S05, M04, M08, M09 (shown and hidden within one
  press), M10 (the Voice leading link lands on H01), M11, H06 (needs a voicing
  failure), H12..H16, H18, F01..F08, X01..X09 (native), R02..R16 (need capture
  or analysis).
- Uncovered: "empty descriptor list", art pose 1 (the blink is time-based),
  and Seed 65535 (E3 moves one per event).

## A19 — C06 output inspection

- Covered: `M-UIACC-A19-001` (Output shows the latest played event; a held step
  is inspected in place with provenance, planned, scheduled, emitted and bypass;
  a step with no event shows NO EVENT; release returns to the latest event; E3/K3
  on every field send no MIDI and change no LED, selection or music). Also
  `M-DASHBOARD-001..008` and the A18 sweep (every C06 field with no event).
- Uncovered: with no event yet, Root reads C-2 (the dashboard's initial note)
  rather than NO EVENT; no case pins either way.

## Defects found by the sweep

Fixed on `codex/ui-reimplementation` ("Fix the screen sweep's findings" and the
commits before it); the sweep now asserts the fixed behaviour exactly:

- False feature booleans rendered NONE; they now read OFF (asserted on Keep
  anchor, Strict leap, Strict direction, Non-chord pedal, Crossing, Exact unison,
  Group enabled).
- K2 did not leave read-only feature screens; M14 now returns to M05, M05 to
  M02 and H05 to H01.
- H19 painted LAYOUT OVERFLOW; its Reset map value now reads "PAT 1 / AVERAGE",
  whole.
- E2 on Trig options moved the Trig viewer channel; P02 focus now moves and P05
  still shows CH01.
- K3 on Pattern tasks > Rhythm Doctor did nothing; it now opens R01.
- frame_oracle measured text above 8 px antialiased; NEAREST and PATTERN are now
  checked by value.
- Also fixed: N04's native hint no longer names an internal screen id; C08/C09/
  S04 footers say K2 BACK; the picker hint is "E3 PICK  K3 SET  K2 BACK";
  focused footers on owner-selection screens name only neighbours E2 reaches.

Still open:

- After K3 then K2 on the Reset map question (H19) and K2 back to Voice leading,
  the first E1 stays on the clean root (a stale return frame) and a second E1 is
  needed to reach Channel tasks. The sweep turns E1 twice there.
- M05 says Decision LEGACY while M14 says ADMITTED for the same step; P06 leaves
  unselected algorithms blank; P07's fields all read NONE (paint state is not
  exposed to the adapter).
