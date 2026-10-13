# README 1.4.0 discrepancies found during the Claude manual review

The legacy README (manual/legacy/README-1.4.0.md) is left unchanged. Each entry records where the README disagrees with the shipped behaviour, the evidence (Lua and behaviour cases), and which way the manual follows.

## channel-masks


1. README lines 844-903 (Merge Modes) / 1409-1458 (Merge Shape). README text: Trig Merge Modes are All/Skip/Only on a trig merge button; Merge Shape Mode Off/Foundation/Fragments with `SHAPE (ONLY)` and `FRAGMENTS (AVERAGE)` labels. Actual: one Strategy selector (grid (14,8) cycles Skip, Only, All, Foundation, Fragments; E3 on Merge modes clamps), Active/Pending/Boundary rows, NEEDS ANCHOR refusal, inactive modes shown as `AVERAGE SAVED`. Evidence: tests/behaviour/contract/merge_strategy_ui.py:38-201 (M-MERGE-STRATEGY-001, tests/behaviour/cases.py:2649), lib/musical_merge/strategy.lua:50, lib/ui_adapters/read_only.lua:278-302.
2. README line 828-832 (Adding Chords). README text: add up to four voices to the root, silent on direction. Actual: Chd1-Chd4 range -14..+14 scale steps, so voices can sit below the root. Evidence: lib/pages/channel_edit_page/channel_edit_page_ui.lua:71-76,212-219.
3. README line 812 (Adding Trig Masks) vs old manual text "A trig mask only switches a step on": code agrees with README (K1+tap on a pattern trig sets mask 0). Evidence: lib/models/program.lua:754-765.

## learn

- README line 185 (adding-custom-devices): "dust > mosaic > config" folder for custom device .json. README line 173 and the manual say data/mosaic/config. Actual: manual follows data/mosaic/config; README is internally inconsistent. Evidence: README-1.4.0.md:173 vs :185.
- README line 392 (midi-panic): no duration stated; actual hold is 1 second. Evidence: lib/m_grid.lua:443-444 (clock.sleep(1)).

## locks-options


1. README line 1312 (Parameter Slides Wrap): "trig locks will smoothly transition beyond step 64, wrapping back to the next trig lock earlier in the sequence." Actual: wrap follows the channel's active range and the song pattern's global length (wrap at step 4 in a 4-step range). Evidence: tests/behaviour/cases.py:2995 (M-PATCH-018), :2727 (M-SLIDE-STEP-001).
2. README 1322-1326 (Parameter Lock Options): lists only Trigless locks (plus lead time elsewhere). Actual: also "Resend unchanged locks" (Off/On, default On), sending a slot's value only when it changes when Off. Evidence: lib/application_parameters.lua:99-103; tests/behaviour/cases.py:2795-2796 (M-SYNC-LEAD-014/015).

## musical-developer


1. README line 1409. README: Merge modes shows trig mode as `SHAPE (ONLY)`; trig merge button tooltip says Merge Shape is in use; saved trig mode applies when Merge Shape is off. Actual: a five-way Strategy selector (Skip, Only, All, Foundation, Fragments) on the Merge modes screen and grid (14,8), with Active, Pending, Boundary and Request rows; the saved trig mode is retained and restored by choosing Skip/Only/All. Evidence: lib/ui_adapters/read_only.lua:293-302; lib/musical_merge/strategy.lua:14,50; tests/behaviour/contract/merge_strategy_ui.py:139-149.
2. README line 1456. README: Merge modes shows each saved mode as `FRAGMENTS (AVERAGE)`; a merge button tooltip says Fragments is in use. Actual: note, velocity and length rows read "<Mode> inactive" with value `AVERAGE SAVED`; trig is part of the Strategy row. Evidence: lib/ui_adapters/read_only.lua:284; tests/behaviour/contract/merge_strategy_ui.py:80-86.
3. README lines 1436-1440 (undo). README: one undo step restores a Merge Shape draft. No behaviour case asserts it for a full draft (only Structure group deletion: tests/behaviour/merge_extension_acceptance.py:967-983). Unresolved.
4. README Interlock (1474-1500) and Harmony (1625-1629) do not mention Strategy selector, NEEDS ANCHOR, Seed range 0-65535, Tone Map rows, Failure fallback, LEGACY RANGE, NO VOICING RANGE; code evidence: lib/musical_merge/config.lua:58; lib/pages/channel_edit_page/channel_feature_editor.lua:437; tests/behaviour/contract/harmony_workflows.py:274-299.

## pattern-scale


## README 555-559 (manual/legacy/README-1.4.0.md:555-559) - Rhythm Doctor setup options
- README text: "The current build presents these settings but does not pass manual BPM or the input selection to the capture or analysis backend, so they are not an audio-routing configuration."
- Actual behaviour: Manual BPM and the Stereo/L/R input selection are passed to capture and analysis. Stereo keeps left and right separate; L or R duplicates that input into both recorded channels. Manual starts the phrase at origin sample 0 at the chosen BPM; Auto estimates tempo and phrase start.
- Evidence: lib/rhythm_doctor/runtime.lua:36-46 (capture_configuration), :210-214 (manual alignment {bpm, origin_sample=0}); lib/rhythm_doctor/capture_controller.lua:98,110 (input_source sent in PREFLIGHT); lib/rhythm_doctor/ui_adapter.lua:611-613 (Record passes manual_bpm and input_source); behaviour contract tests/behaviour/contract/rhythm_doctor_capture_options.py (cases manual_stereo, auto_left, manual_right; docstring: "implements the formerly documented display-only BPM/Input settings"; asserts ADC channel duplication and analysis tempo_mode/origin_sample); commit f36a766f "honor capture options". The README paragraph is stale.

