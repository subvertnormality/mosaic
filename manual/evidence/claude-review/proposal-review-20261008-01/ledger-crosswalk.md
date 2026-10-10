# Review-unit to current 425-ledger crosswalk

Decision HOLD; 52 reviewed units; 10 initially below threshold.

Current ledger source19-final425-course-crossref-refresh-v01 SHA-256 fe378689a917dd0eedc2f77e13588bd9b6faba11b66dfc3d6e948dc78c1255f2. Review-time pin 4ceb17deba072d7c5a4b4ee75da6c8a5ae87f362a09c8a4b612541645c650917 differs from current bytes. Mapping uses current 425 IDs and transfers no scores.

## Mapping rules

- Recipe text maps by feature ID and exact authored recipe index to the matching current recipe ordinal.
- Recording relationship/build-step rows map to the recording row; related recipe, lesson, or course-stage IDs are separate dependencies.
- Feature prose/details, projected outcomes and captions have no standalone row in the 425 inventory. Dependencies are listed without transferring scores.
- HOLD remains HOLD; Locks v04 is a separate HOLD.

## Standalone/projected units not in the 425 ledger

- `recipe-text-overlay:small-hours:prose` -> `recipe:small-hours:1-percussion-channel`, `recipe:small-hours:2-bass-channel`, `recipe:small-hours:3-chord-channel`, `recording:three-voice-conversation`
- `doc-language-cleanup:feature:midi-panic:details[0]` -> `lesson:midi-panic:panic-from-song-channel`, `lesson:midi-panic:panic-from-song-pattern`, `lesson:midi-panic:play-panic-stops-sounding-note-note-sounding`, `recipe:midi-panic:1-silence-connected-midi-notes-from-song-view-with`, `recipe:midi-panic:2-silence-connected-midi-notes-from-song-view-with`, `scene:panic-stops-sounding-note`
- `doc-language-cleanup:feature:lock-lead-time:prose` -> `lesson:lock-lead-time:play-lock-lead-menu-values-play-0`, `scene:lock-lead-menu-values`
- `doc-language-cleanup:feature:locks:details[0]` -> `lesson:locks:clear-transpose-lock-to-global`, `lesson:locks:device-cc1-lock-and-play`, `lesson:locks:mask-default-exceptions-and-clear`, `lesson:locks:octave-step-2-local-minus-one`, `lesson:locks:play-global-parameter-slide-play`, `lesson:locks:play-parameter-slot-endpoints-clamped-slots`, `lesson:locks:play-trig-parameter-locks-default`, `recipe:locks:1-make-one-step-override-a-channel-note-default-th`, `recipe:locks:2-compare-a-stored-device-value-with-one-step-loca`, `recipe:locks:3-use-a-channel-octave-for-a-bass-line-and-a-local`, `recipe:locks:4-distinguish-an-explicit-zero-transpose-lock-from`, `recipe:locks:5-practice-longer-and-shorter-decay-envelopes`, `scene:trig-parameter-locks`
- `doc-language-cleanup:feature:save-and-load:detail-demo` -> `lesson:save-and-load:save-named-arrangement`, `scene:course-save-dialog`, `scene:named-project-roundtrip`
- `doc-language-cleanup:feature:save-and-load:binding-outcome` -> `lesson:save-and-load:save-named-arrangement`, `scene:course-save-dialog`, `scene:named-project-roundtrip`
- `doc-language-cleanup:feature:midi-controller-options:details[0]` -> `lesson:midi-controller-options:field-keyboard-honour-degree-pick-natural-minor`, `lesson:midi-controller-options:keyboard-honour-all`, `lesson:midi-controller-options:keyboard-honour-degree-rotation`, `lesson:midi-controller-options:play-mapping-child-selected-and-fixed-raw`, `recipe:midi-controller-options:1-map-an-external-keyboard-through-the-scale-s-rot`, `recipe:midi-controller-options:2-apply-scale-rotation-and-global-transpose-to-eve`, `scene:keyboard-honour-all`, `scene:keyboard-honour-degree-rotation`, `scene:mapping-child-selected-and-fixed`
- `doc-language-cleanup:feature:honor-scale-rotations:details[1]` -> `lesson:honor-scale-rotations:keyboard-honour-degree-rotation`, `recipe:honor-scale-rotations:1-map-an-external-keyboard-through-the-scale-s-rot`, `scene:keyboard-honour-degree-rotation`
- `doc-language-cleanup:feature:honour-scale-transpose:details[1]` -> `lesson:honour-scale-transpose:keyboard-honour-all`, `recipe:honour-scale-transpose:1-apply-scale-rotation-and-global-transpose-to-eve`, `scene:keyboard-honour-all`
- `doc-language-cleanup:feature:performance-management:details[0]` -> no unambiguous dependent ID
- `doc-language-cleanup:caption:chord-strum-a-timed-chord:assign-strum` -> `scene:chord-strum-a-timed-chord`, `lesson:chord-strum:play-chord-strum-a-timed-chord-forward`

## Full 52-unit mapping

| Review unit | Direct ID(s) | Dependent ID(s) | Below 8? |
|---|---|---|---|
| `recipe-text-overlay:pocket-rhythm:recipes[0]` | `recipe:pocket-rhythm:1-make-the-recorded-ghost-note-comparison` | - | yes |
| `recipe-text-overlay:pocket-rhythm:recipes[1]` | `recipe:pocket-rhythm:2-optional-probability-variation` | - | no |
| `recipe-text-overlay:small-hours:prose` | - | `recipe:small-hours:1-percussion-channel`, `recipe:small-hours:2-bass-channel`, `recipe:small-hours:3-chord-channel`, `recording:three-voice-conversation` | yes |
| `recipe-text-overlay:small-hours:recipes[0]` | `recipe:small-hours:1-percussion-channel` | - | yes |
| `recipe-text-overlay:small-hours:recipes[1]` | `recipe:small-hours:2-bass-channel` | - | yes |
| `recipe-text-overlay:small-hours:recipes[2]` | `recipe:small-hours:3-chord-channel` | - | yes |
| `recipe-text-overlay:tilting-harmony:recipes[0]` | `recipe:tilting-harmony:1-make-the-relative-note-scale-comparison` | - | yes |
| `recipe-text-overlay:loops-that-meet:recipes[0]` | `recipe:loops-that-meet:1-comparing-the-loop-alignment` | - | no |
| `recipe-text-overlay:masks:recipes[4]` | `recipe:masks:5-build-the-recording-small-hours-four-bars-in-c-m` | - | yes |
| `recipe-text-overlay:note-merge-modes:recipes[0]` | `recipe:note-merge-modes:1-build-the-recording-average-then-higher` | - | yes |
| `practical-small:scale-editor:recipes[0]` | `recipe:scale-editor:1-prepare-and-apply-a-second-scale` | - | no |
| `practical-small:song-editor:recipes[0]` | `recipe:song-editor:1-create-a-two-slot-group` | - | no |
| `practical-small:interacting-with-slots:recipes[2]` | `recipe:interacting-with-slots:3-build-the-recording-intro-verse-and-outro` | - | no |
| `practical-small:lock-random-to-pentatonic:recipes[0]` | `recipe:lock-random-to-pentatonic:1-compare-random-notes-with-and-without-the-filter` | - | no |
| `practical-small:lock-all-to-pentatonic:recipes[0]` | `recipe:lock-all-to-pentatonic:1-hear-every-note-restricted` | - | no |
| `doc-language-cleanup:feature:midi-panic:details[0]` | - | `lesson:midi-panic:panic-from-song-channel`, `lesson:midi-panic:panic-from-song-pattern`, `lesson:midi-panic:play-panic-stops-sounding-note-note-sounding`, `recipe:midi-panic:1-silence-connected-midi-notes-from-song-view-with`, `recipe:midi-panic:2-silence-connected-midi-notes-from-song-view-with`, `scene:panic-stops-sounding-note` | no |
| `doc-language-cleanup:feature:lock-lead-time:prose` | - | `lesson:lock-lead-time:play-lock-lead-menu-values-play-0`, `scene:lock-lead-menu-values` | no |
| `doc-language-cleanup:feature:locks:details[0]` | - | `lesson:locks:clear-transpose-lock-to-global`, `lesson:locks:device-cc1-lock-and-play`, `lesson:locks:mask-default-exceptions-and-clear`, `lesson:locks:octave-step-2-local-minus-one`, `lesson:locks:play-global-parameter-slide-play`, `lesson:locks:play-parameter-slot-endpoints-clamped-slots`, `lesson:locks:play-trig-parameter-locks-default`, `recipe:locks:1-make-one-step-override-a-channel-note-default-th`, `recipe:locks:2-compare-a-stored-device-value-with-one-step-loca`, `recipe:locks:3-use-a-channel-octave-for-a-bass-line-and-a-local`, `recipe:locks:4-distinguish-an-explicit-zero-transpose-lock-from`, `recipe:locks:5-practice-longer-and-shorter-decay-envelopes`, `scene:trig-parameter-locks` | no |
| `doc-language-cleanup:feature:locks:recipes[4]` | `recipe:locks:5-practice-longer-and-shorter-decay-envelopes` | - | yes |
| `doc-language-cleanup:feature:save-and-load:detail-demo` | - | `lesson:save-and-load:save-named-arrangement`, `scene:course-save-dialog`, `scene:named-project-roundtrip` | no |
| `doc-language-cleanup:feature:save-and-load:binding-outcome` | - | `lesson:save-and-load:save-named-arrangement`, `scene:course-save-dialog`, `scene:named-project-roundtrip` | no |
| `doc-language-cleanup:feature:midi-controller-options:details[0]` | - | `lesson:midi-controller-options:field-keyboard-honour-degree-pick-natural-minor`, `lesson:midi-controller-options:keyboard-honour-all`, `lesson:midi-controller-options:keyboard-honour-degree-rotation`, `lesson:midi-controller-options:play-mapping-child-selected-and-fixed-raw`, `recipe:midi-controller-options:1-map-an-external-keyboard-through-the-scale-s-rot`, `recipe:midi-controller-options:2-apply-scale-rotation-and-global-transpose-to-eve`, `scene:keyboard-honour-all`, `scene:keyboard-honour-degree-rotation`, `scene:mapping-child-selected-and-fixed` | no |
| `doc-language-cleanup:feature:honor-scale-rotations:details[1]` | - | `lesson:honor-scale-rotations:keyboard-honour-degree-rotation`, `recipe:honor-scale-rotations:1-map-an-external-keyboard-through-the-scale-s-rot`, `scene:keyboard-honour-degree-rotation` | no |
| `doc-language-cleanup:feature:honour-scale-transpose:details[1]` | - | `lesson:honour-scale-transpose:keyboard-honour-all`, `recipe:honour-scale-transpose:1-apply-scale-rotation-and-global-transpose-to-eve`, `scene:keyboard-honour-all` | no |
| `doc-language-cleanup:feature:performance-management:details[0]` | - | - | yes |
| `doc-language-cleanup:feature:interacting-with-slots:recipes[1]` | `recipe:interacting-with-slots:2-copy-a-song-slot-then-raise-the-copy-by-one-octa` | - | no |
| `doc-language-cleanup:recording:oilcan-pocket:lesson_relations[0]` | `recording:oilcan-pocket` | `recipe:pocket-rhythm:3-separate-fixed-percussion-example` | no |
| `doc-language-cleanup:recording:bass-and-intervals:lesson_relations[0]` | `recording:bass-and-intervals` | `recipe:tilting-harmony:2-separate-fixed-bass-and-chord-example` | no |
| `doc-language-cleanup:recording:three-voice-conversation:lesson_relations[0]` | `recording:three-voice-conversation` | `recipe:small-hours:1-percussion-channel` | no |
| `doc-language-cleanup:recording:three-voice-conversation:lesson_relations[1]` | `recording:three-voice-conversation` | `recipe:small-hours:2-bass-channel` | no |
| `doc-language-cleanup:recording:three-voice-conversation:lesson_relations[2]` | `recording:three-voice-conversation` | `recipe:small-hours:3-chord-channel` | no |
| `doc-language-cleanup:recording:ghost-note-comparison:lesson_relations[0]` | `recording:ghost-note-comparison` | `recipe:pocket-rhythm:1-make-the-recorded-ghost-note-comparison` | no |
| `doc-language-cleanup:recording:scale-slot-comparison:lesson_relations[0]` | `recording:scale-slot-comparison` | `recipe:tilting-harmony:1-make-the-relative-note-scale-comparison` | no |
| `doc-language-cleanup:recording:polymeter:lesson_relations[0]` | `recording:polymeter` | `recipe:loops-that-meet:4-listening-extension-sixteen-steps-against-twelve` | no |
| `doc-language-cleanup:recording:swing-comparison:lesson_relations[0]` | `recording:swing-comparison` | `recipe:clocks-swing-and-shuffle:1-build-the-recording-straight-then-swung` | no |
| `doc-language-cleanup:recording:note-merge-modes:lesson_relations[0]` | `recording:note-merge-modes` | `recipe:note-merge-modes:1-build-the-recording-average-then-higher` | no |
| `doc-language-cleanup:recording:song-sections:lesson_relations[0]` | `recording:song-sections` | `recipe:interacting-with-slots:3-build-the-recording-intro-verse-and-outro` | no |
| `doc-language-cleanup:recording:harmony-strum-arp:lesson_relations[0]` | `recording:harmony-strum-arp` | `recipe:adding-chords:2-build-the-recording-block-chords-strummed-then-a` | no |
| `doc-language-cleanup:recording:voice-leading-revoice:lesson_relations[0]` | `recording:voice-leading-revoice` | `recipe:harmony:2-build-the-recording-block-chords-then-revoice` | no |
| `doc-language-cleanup:recording:masks-small-hours:lesson_relations[0]` | `recording:masks-small-hours` | `recipe:masks:5-build-the-recording-small-hours-four-bars-in-c-m` | no |
| `doc-language-cleanup:recording:course-first-sound-hear:lesson_relations[0]` | `recording:course-first-sound-hear` | `course:first-sound-hear` | no |
| `doc-language-cleanup:recording:course-build-a-phrase-compare:lesson_relations[0]` | `recording:course-build-a-phrase-compare` | `course:build-a-phrase-compare` | no |
| `doc-language-cleanup:recording:course-masks-listen:lesson_relations[0]` | `recording:course-masks-listen` | `course:masks-listen` | no |
| `doc-language-cleanup:recording:course-masks-keep:lesson_relations[0]` | `recording:course-masks-keep` | `course:masks-keep` | no |
| `doc-language-cleanup:recording:course-sequence-composition-both:lesson_relations[0]` | `recording:course-sequence-composition-both` | `course:sequence-composition-both` | no |
| `doc-language-cleanup:recording:course-harmony-design-apply:lesson_relations[0]` | `recording:course-harmony-design-apply` | `course:harmony-design-apply` | no |
| `doc-language-cleanup:recording:course-modulation-movement-and-interest-level:lesson_relations[0]` | `recording:course-modulation-movement-and-interest-level` | `course:modulation-movement-and-interest-level` | no |
| `doc-language-cleanup:recording:course-song-composition-transition:lesson_relations[0]` | `recording:course-song-composition-transition` | `course:song-composition-transition` | no |
| `doc-language-cleanup:recording:course-keep-your-work-perform:lesson_relations[0]` | `recording:course-keep-your-work-perform` | `course:keep-your-work-perform` | no |
| `doc-language-cleanup:recording:param-lock-comparison:lesson_relations[0]` | `recording:param-lock-comparison` | `recipe:locks:5-practice-longer-and-shorter-decay-envelopes` | no |
| `doc-language-cleanup:recording:param-lock-comparison:build_steps[4]` | `recording:param-lock-comparison` | `recipe:locks:5-practice-longer-and-shorter-decay-envelopes` | no |
| `doc-language-cleanup:caption:chord-strum-a-timed-chord:assign-strum` | - | `scene:chord-strum-a-timed-chord`, `lesson:chord-strum:play-chord-strum-a-timed-chord-forward` | no |
