# UI acceptance coverage (spec.json#/acceptance_matrix A01..A19)

Status of each acceptance item against the behaviour cases that exist on
`codex/ui-accept-sweep` (tests/behaviour/cases.py and its modules), plus the Lua
integration tests where they are the only evidence. "Covered" means a
registered behaviour case drives the live app through public input and checks
the visible and musical result the item names. Everything the item names that
no case checks is listed under "Uncovered", honestly, including the parts a
passing case only reaches halfway.

The live-UI acceptance cases for A01, A02, A03, A10, A11 and A19 are being
written in parallel as `M-UIACC-A01-001` and siblings in
`tests/behaviour/contract/live_ui_acceptance.py` on another branch. They are
named below as planned, not as evidence: until they land and pass in both
lanes, those items remain uncovered by a live-UI acceptance case.

Legend: RT = real-time lane, CT = controlled-experimental lane.

## Summary

| Item | Subject | Status |
|---|---|---|
| A01 | E1 family navigation C01/C02/N01 | partial (M-LIVEUI-TASKS-001); acceptance case pending |
| A02 | held steps + K1+K2 clear, release order | partial (mask/memory cases); acceptance case pending |
| A03 | assignment picker, K2 cancel, K3 apply, slides | partial (param/patch cases); acceptance case pending |
| A04 | Merge Shape field domains, Apply stopped/running, drafts | partial (musical only) |
| A05 | Harmony groups 16/17, validation, delete confirm | mostly uncovered |
| A06 | Tone map binding, reset draft | uncovered |
| A07 | event inspection H05/H06/H15/H16/H18 | partial (M-HARMONY-ENSEMBLE/FAILURE) |
| A08 | Rhythm Doctor lifecycle R01..R16 | uncovered by registered cases |
| A09 | Rhythm Doctor lanes, browse, paint | uncovered by registered cases |
| A10 | Norns follows channel/pattern/mute/merge gestures | partial; acceptance case pending |
| A11 | pattern pages, generators, viewer channel | partial (musical); acceptance case pending |
| A12 | Scale S01..S05 | partial (musical); S04/S05 unreachable |
| A13 | Song A01..A03 | musical semantics covered; screen scopes partial |
| A14 | external transport, panic | musical/transport covered; screen side partial |
| A15 | lock lead time | covered (musical and native value) |
| A16 | native menus, persistence | largely covered |
| A17 | device, dynamic params, live lock recording | musical covered; screen identity partial |
| A18 | native screen sweep | M-UIACC-A18-001 (this branch), with known defects |
| A19 | C06 output inspection | partial; acceptance case pending |

## A01 — E1 moves Masks, Trig params and Channel tasks

Screens C01, C02, N01. MAN.015/016.

- Covered: `M-LIVEUI-TASKS-001` (E1 +/- across C01, C02, N01 including both
  clamps; exact live headers), `M-LIVEUI-FOLLOW-001` (the Channel button returns
  to the remembered family). `M-UIACC-A18-001` also checks C01, C02 and N01 frames
  and that N01 clamps on its last row.
- Uncovered: "E1 large positive twice" (one large delta per detent is not sent:
  the driver only sends +/-2 per event), "C02 restored with remembered field",
  and the musical clause "no output/state/RNG mutation" (no MIDI/RNG assertion
  accompanies the navigation). Planned: `M-UIACC-A01-001`.

## A02 — held steps 1 and 64, K1+K2, release in either order

- Covered musically: mask and memory clearing cases (`M-MASK-*`, `M-MEMORY-*`,
  `M-TRANS-003`) clear held-step locks and keep channel defaults;
  `M-LIVEUI-FOLLOW-001` checks the held scope (ST05) and restore on release.
- Uncovered: the exact pair 1 and 64 held together with K1+K2, both release
  orders with the restored family checked on screen, and "unheld locks
  unchanged" asserted in the same case. Planned: `M-UIACC-A02-001`.

## A03 — assignment picker (C07)

- Covered musically: `M-PARAM-*`, `M-PATCH-*` (CC/NRPN encodings, Off policy,
  order), `M-REC-PARAM-011/012/020` (assignment change vs pending recording,
  confirmed same assignment, unconfirmed cancel), `M-SLIDE-STEP-001`.
  `M-UIACC-A18-001` opens C07 from C02 with K2, browses with E3 and assigns
  "Quantised Fixed Note" with K3.
- Uncovered: "same target slot" after browsing then K2 cancel on screen,
  "discarded candidate" frame check, repeat K3 apply, and hold-step K3 slide
  marker on the live screen. Planned: `M-UIACC-A03-001`.

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
  `M-UIACC-A18-001` opens H11 and H19 and cancels.
- Uncovered: selecting a different source binding, editing the map, Reset
  cancel/confirm effect on the draft, "reset remains draft until owner Apply",
  and the "other binding maps unchanged" musical clause. H19 currently paints
  LAYOUT OVERFLOW (defect D3 below).

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
  disconnect, leave/re-enter algorithm 5. Also: K3 on Pattern tasks >
  Rhythm Doctor does not open R01 (defect D5).

## A09 — Rhythm Doctor lanes, browse and paint

- Evidence: the standalone scripts above (phrase navigation) and Lua doctor
  adapter tests.
- Uncovered by registered cases: lane select for three-lane and ten-lane banks
  including (7,2) and (3,3), inert cells, browse tap/hold at both boundaries,
  paint toggle/add/replace, cancel an armed preview, arm-start-commit, stale
  preview after E3 or slot change, paint undo/redo API.

## A10 — Norns follows channel, pattern, dual range, mute and merge gestures

- Covered: `M-LIVEUI-FOLLOW-001` (page buttons, channel select, held steps),
  `M-NAV-001` (all 36 page transitions, menu LEDs, unchanged MIDI),
  `M-MUTE-001`, `M-CHANNEL-001`, `M-RANGE-*`, `M-MERGE-TRIG-002` and the numeric
  merge cases (merge arithmetic unchanged), `M-GESTURE-ORDER-001`.
- Uncovered: the screen resolving to C09 after assign/remove pattern and merge
  taps, and dual range in both release orders checked on screen; M09 is not
  observable (defect D7). Planned: `M-UIACC-A10-001`.

## A11 — pattern pages and viewer channel

- Covered musically: `M-ALG-001..004` (Euclidean, tresillo, drum banks, numeric
  masks), `M-ALG-PAINT-RACE-001`, `M-EDIT-*` (note/velocity ranges, banks,
  fader extremes), `M-PAT-*`, `M-VIEW-001` (independent screen grid, 16 viewer
  selections, clamps, unchanged MIDI). `M-UIACC-A18-001` reaches P01..P08, P05 in
  Scale/Trig/Song, both algorithm variants on P06, Paint preview, Trig step edit.
- Uncovered: E3 on view_channel at 1 and 16 on P01/P03/P04/P05/S03 with the
  label and "never writes selected_channel/MIDI/RNG" asserted live; source select
  K1/long; duplicate source banks. E2 on Trig options moves the viewer channel
  (defect D4), contrary to "E2 moves field focus only". Planned: `M-UIACC-A11-001`.

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
  edit/applied/locked scope on screen. S01's footer names Pentatonic as a
  neighbour, but E2 never reaches it.

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
  focused-screen neighbour labels or a named tooltip, and the selected field's
  whole value on its full-value route. Includes a long parameter name
  ("Quantised Fixed Note": fitted "QUAN" cell, whole name on the value line and
  on C13; "Quantised Fixed~" in the picker), a long raw value
  (GLOBAL_EFFECTIVE), NONE/X/NO EVENT/0 sentinels, maximum values (MIDI channel
  CC16, Add amount 100, Anchor gap 8) and minimums (Seed 0).
- Screens reached: C01..C07, C09, C12, C13, M02, M03, M05, M06, M07, M12, M13,
  M14, H01..H05, H07..H11, H17, H19, S01..S03, P01..P08, A01..A03, N01..N05,
  R01, and the norns menu round trip.
- Not reachable through public input on this build (no router path sets
  them): C08, C10, C11, S04, S05, M04, M08, M09 (shown and hidden within one
  release), M10 (the Voice leading link lands on H01), M11, H06 (needs a voicing
  failure), H12..H16, H18, F01..F08, X01..X09 (native), R02..R16 (need capture
  or analysis).
- Uncovered: "empty descriptor list", art pose 1 (the blink is time-based and
  not selected), "decorative art never replaces status" beyond the frames seen,
  values at the art boundary (see defect D6), and Seed 65535.
- Known defects asserted strictly (the case fails if one stops reproducing): D1,
  D2, D3, D4, D5 below. D6 is an oracle discrepancy; NEAREST (H03) and PATTERN
  (H01) are checked by label only.

## A19 — C06 output inspection

- Covered: `M-DASHBOARD-001..008` (root pitch, velocity, length rendered after
  exact MIDI), `M-DASHBOARD-SELECT-001`, `M-DASHBOARD-CHORD-001`.
  `M-UIACC-A18-001` checks every C06 field with no event (NO EVENT for Step and
  every stage, X X X X chord, velocity 0).
- Uncovered: held step in rows 4..7 while on C06, provenance/planned/scheduled/
  emitted/bypass for a held step, "no provenance for NO EVENT step", E3/K3 on
  every field, and the no-solve/RNG/MIDI clause. With no event the Root reads
  C-2 (the dashboard's initial note) rather than NO EVENT. Planned:
  `M-UIACC-A19-001`.

## Defects found by the sweep

- D1: feature editor booleans that are false render NONE, not OFF
  (`channel_feature_editor.lua` field_value: `field.get and field.get() or
  field.value` drops `false`). Keep anchor, Strict leap, Strict direction,
  Non-chord pedal, Crossing, Exact unison, Group enabled. OFF and NONE collapse.
- D2: K2 on read-only feature children does not go back: Merge Result (M05),
  Merge Reason (M14) and Harmony Result (H05) stay on screen; only E1 leaves.
- D3: H19 RESET TONE MAP? paints LAYOUT OVERFLOW (the selected Reset map value is
  too wide for the detail row).
- D4: E2 on Trig options (P02) moves the Trig grid viewer's channel (legacy
  enc(2) on the Trig page), so P05 then shows another channel.
- D5: K3 on Pattern tasks > Rhythm Doctor does nothing ("task not enterable
  rhythm_doctor": the router's row filter never sees the algorithm).
- D6: frame_oracle's text width disagrees with native text_extents at the art
  boundary (NEAREST at 19 px: oracle 73 px, native fits 70).
- D7: M09 is never observable: the merge-mode short press shows it and the same
  release hides it.
- Also noted: N04 K3 shows "K1 > PARAMS > X01" (an internal screen id);
  C09 shows "E1 TASKS" although E1 is inert there; C07's hint is fitted to
  "E3 CHOOSE  K3 ASSIGN  K2 B~"; M05 says Decision LEGACY while M14 says
  ADMITTED for the same step; P06 leaves unselected algorithms blank.
