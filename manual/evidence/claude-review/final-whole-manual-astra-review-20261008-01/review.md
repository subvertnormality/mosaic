# Final whole-manual reader review — 8 October 2026

**Verdict: changes required. The current reader does not meet all seven 8/10 thresholds.** The continuing course and responsive player are substantially clearer. A fresh pass through the musical recipes exposed missing setup actions, wrong grid navigation and misleading listening expectations. Reference and recording pages also retain review/production language. Earlier scoped approvals are preserved; they do not supersede these newly observed whole-reader findings.

| Criterion | Score | Reason |
|---|---:|---|
| Readability | 7 | Typography and spacing are good; audit language and some dense reference prose still interrupt the player-facing voice. |
| Comprehensibility | 7 | Course concepts are explained well; several independent recipes contradict their stated starting state or the grid map. |
| Flow | 7 | Ten-course continuity works; the Average/Higher recipe copies its source before preparing it, and two recipes omit pattern assignment. |
| Understandability | 8 | Pattern/channel/slot, default/exception, Apply and independent example scope are now explained consistently in the main course. |
| User-friendliness | 8 | Search, readable mobile layout, keyboard access, persistent hardware choice and useful grid enlargement all work. |
| Interactive-example usefulness | 7 | Recorded controls, screen/grid states and MIDI feedback are useful, but a player following several recording recipes cannot reliably reproduce the stated result. |
| Cohesion | 7 | The course and reference are well connected; recipe mismatches and production-review voice prevent a consistent whole manual. |

## Identity and scope

Reviewed the actual `http://localhost:8785/manual/` reader in owned Chrome at 1440 × 900 and 390 × 900. The authoritative WSL root was read only. No source edits, builds, captures, emulator runs, service changes or publishing were performed. Audio was loaded and played **muted only** to check controls and cleanup; this is not a listening review.

Independently observed identities:

- Served reader index: `39eab0635e6bfcabefc61d44faec4ec368a0f86435da9ca48b3c72a7d042f0cf`.
- Current served and authoritative `book.js`: `a80f66aee6f4b5cc3c98fb38b0ff39e027be8d178dba8c29e10f5c92661bbeb1`. The earlier collection captured `ff595809…`; the only announced intervening change removed the injected tagline. Fresh browser evidence uses a80f.
- Served `manual.js`: `49a88a9be93f58571b43fdb30e445bffb0bac4340941726a5488577ea21b21e4`.
- Served CSS: `123afe7d35beb8e827089b16518f03ccdfdcc000c33916e64b8f0002eb2caa4a`.
- Served and authoritative index HTML: `c4386498a8f224507ff0316958078932e58865640ed91931afb9945599839b87`.
- Authoritative compiled book, independently hashed: `54a7433e87b61dba58865cd0a857aea642ddd7b96604e12cec56e6165c9d79c5`.
- Author identity supplied by root: `80cc81d39ab276c32da0561588cafad4ac3f4123b065043573a78b1483312d46`.
- Served quick reference: `6c169304bd791673876479649ceb720e161b7a6bee2a570d074e0f082d251695`.

The current 133-feature prose/detail inventory and public recipe text were read in bounded extracts. Three developer-held features were inspected as inventory only; their direct routes render the public guard. All ten current course openings were read as rendered, with selected full workflows, reference, recording, recipes, search and hardware controls exercised. Sixty-six route/viewport entrances plus the independent interaction/workflow passes are saved. All 146 served scene chunks were fetched for a bounded caption-text scan; this was not a new native assertion or audio-content audit. The inherited 425-unit threshold ledger remains external prior evidence, not a fresh rescore of every lesson in this review.

## Required corrections

### R1 — Two empty-project recipes omit Pattern 1 assignment (high)

- `#pocket-rhythm/recipe/1`, `features[pocket-rhythm].recipes[0].text`: starting point is an empty project. Step 1 assigns Oilcan, step 4 edits Pattern 1, step 5 sets masks and says all sixteen hits now play, and step 7 asks for playback. Nothing assigns Pattern 1 to Channel 1.
- `#tilting-harmony/recipe/1`, `features[tilting-harmony].recipes[0].text`: starts empty; steps 3–5 create the upper phrase and ask for playback without assigning its pattern. Step 6 does explicitly assign Pattern 2 to Channel 2, making the omission particularly clear.

The manual's own channel/No Sound explanation says unassigned source patterns do not play. Add an explicit Channel (3,8), channel 1, pattern slot (1,2) assignment before audition. These are instruction defects inferred from the documented setup, not claims of a new native test.

### R2 — Four-bar recipes instruct nonexistent Channel step pages (high)

`small-hours.prose`, `small-hours.recipes[0]` step 6, `small-hours.recipes[2]` opening, `pocket-rhythm.recipes[0]` opening, `pocket-rhythm.recipes[1]` probability steps and `masks.recipes[4]` control map tell a player to move to sixteen-step pages while using Channel Masks or Trig params. On those pages the documented map is all 64 steps on rows 4–7: 1–16 row 4, 17–32 row 5, 33–48 row 6, 49–64 row 7. The Masks four-bar recipe even supplies this correct map and then contradicts it with “move to the page.” Pattern Trig also shows all 64 steps. Only Pattern Note and Velocity use the sixteen-step pages described elsewhere.

Replace these paging instructions with the appropriate row/column map and explicit examples, such as step 44 = (12,6), step 60 = (12,7). Preserve paging instructions where the player is actually on Pattern Note/Velocity.

### R3 — Average/Higher comparison starts editing the wrong Song slot (high)

`#note-merge-modes/recipe/1`, `recipes[0].text`, paragraph “Prepare the two-slot comparison” copies slot 1 to slot 2 and selects slot 2 before numbered steps 1–3 build the patterns. Step 4 later says set slot 1 length, and step 5 copies slot 1 onto slot 2 again. The source/variation sequence is internally inconsistent and can overwrite the prepared comparison.

Keep slot 1 selected while preparing both patterns, masks and Average. Copy it once after preparation, select the copy, then change only its note mode to Higher.

### R4 — Two listening instructions misdescribe the written setup (medium)

- `#small-hours/recipe/1`, step 5: after setting range 1–64 and entering only steps in bar 1, “hear bar 1 loop” promises continuous one-bar playback. The written setup has three empty bars until step 6 fills them. State that the first bar is followed by three silent bars, or explicitly shorten then restore the range. The bass/chord intermediate auditions likewise should identify that only their first bar has been entered so far.
- `#loops-that-meet/recipe/1`, step 2: says MIDI 60 and MIDI 79 do not coincide again on steps 2–12. The supplied phrases are 60/62/64/65 and 79/81/79. At step 9, CH1 is 60 and CH2 is its third note, also 79. Their **first steps** next align after twelve steps; the pitch pair can coincide sooner. Explain phrase-start alignment rather than uniqueness of that pitch pair.

### R5 — Player-facing prose still contains review and production material (medium, F11 reopened)

Fresh browser expansion confirms these five “Evidence” panels, not merely hidden metadata:

| Feature / field | Actual reader wording to revise |
|---|---|
| `midi-panic.details[0]` | “Evidence: release coverage”; examples “verify the full all-notes-off message stream”; “These captures do not establish physical-device timing…” |
| `locks.details[0]` | “Evidence: transpose output scope”; “intermediate MIDI stream is truncated and is not evidence of a complete phrase”; “final clear checkpoint…” |
| `midi-controller-options.details[0]` | “Evidence: keyboard output scope”; startup output “is not the acceptance target” |
| `honor-scale-rotations.details[1]` | Same keyboard evidence paragraph |
| `honour-scale-transpose.details[1]` | Same keyboard evidence paragraph |

Additional player-facing fields found in the complete prose/recipe sweep:

- `lock-lead-time.prose`: “Mosaic restores its output hooks on cleanup”. Keep the useful stopping/held-note behavior, remove implementation hooks.
- `performance-management.details[0]`: “Host and emulator timing do not establish physical norns scheduling accuracy.” Keep practical workload advice and historical date qualification; put verification scope in the external audit.
- `save-and-load.details[0]` and its lesson `human_outcome` projections: “complete decoded arrangement”. Use the saved arrangement and visible Load result.
- `interacting-with-slots.recipes[1]`: “The captured checkpoint proves slot state; it does not claim audible playback…” State what can be inspected while stopped.
- `locks.recipes[4]`: “replay the retained recording's…”, “The retained capture records these encoder gestures…”, and especially “the reader did not listen to a captured sound example.” The latter is review residue. Preserve the distinction between the recorded relative moves and the separate endpoint exercise in practical player language; do not invent absolute values for the recording.
- `recordings_context.recordings['param-lock-comparison'].build_steps`: “The retained input trace does not preserve displayed Decay values…” Preserve a plain limitation on relative moves and the separate endpoint exercise.
- Recording `lesson_relations[].explanation` fields: nine course entries say “retained recording… verified outgoing project”; six independent entries say “retained authored recording setup”; seven recipe links use “authored notes”. Explain how the recording relates to the lesson without discussing publication verification.
- Minor caption polish: `chord-strum-a-timed-chord / assign-strum / caption`, “From the verified half-step Strum slot…” can simply say “From the half-step Strum slot…”. It is a low-impact word, not a request to rerun the capture.

Do not delete necessary installation instructions, mathematical behavior, explicit recorded-versus-live scope, or random-example limitations simply because they are technical. Rhythm Doctor's compiler/server requirements and model download checks serve real setup decisions. Developer metadata behind the guard was not graded as visible reader copy.

## Smaller corrections worth including in the same text pass

- All three `small-hours` recipes say “Press E1 to Channel tasks”; E1 is turned.
- `scale-editor.recipes[0]` calls C/D/E/F “pattern degrees 1 to 4”; the Pattern Note convention used throughout is 0/1/2/3. It also links Build a phrase, whose continuing four-beat lesson retains fixed C masks; link a matching relative-note setup or state it completely.
- `song-editor.recipes[0]` says a C/D/E/F motif is built as in Creating a First Loop; that first loop now contains four equal C notes. Link a matching relative-note example or add the pitch edits.
- `interacting-with-slots.recipes[2]`, the Intro/verse/outro recording, says “create pattern 1” and “create pattern 2” on channels but never spells out assignment; make both assignments explicit for its empty-project start.
- `lock-random-to-pentatonic.recipes[0]` promises an F or B “will turn up within a few passes”. Random playback does not guarantee this short-run result. Use “may appear; listen over several loops.”
- `lock-all-to-pentatonic.recipes[0]` step 4 changes scale with E3 without selecting the Scale row. Include E2 selection, as the standard Scale instructions do.

## What currently works

The fresh home has no tagline. It first defines Mosaic as a rhythm and harmony sequencer, then clearly labels “Make your first piece” as a guided tutorial. Served HTML and final served JS agree with the authoritative files. Ten course openings state their starting points and continue the same project through sound, four notes, a bar, a softer ending, bass, harmony, pickup, arrangement and save/reload. The first-loop guide's six ordered control actions and final result focus work at both widths.

The Harmony exact search is first, partial “poly” finds relevant n.b. topics with readable excerpts, and activation focuses the destination heading while retaining the query and collapsing results. Searching `luaunit` returns no public match; three contributor routes show only the guard. Independent Harmony continuation labels the different setup and opens its own complete example. The modest modulation example remains first and the advanced lfo 1 route opens correctly. Keyboard Degree selected through the actual scene picker retains its 5-step and 6-step milestone groups through all eleven frames.

Original norns controls and Shield controls are recognizable, accurately grouped and selectable. Shield preference persists across reload. Standard grid fits all sixteen columns at both widths. Pad widths change from about 59 to 80 px on desktop and 16.8 to 44 px on mobile when enlarged. Only the grid scrolls; ArrowRight reaches column 16 and brings it into view. All 66 initial route checks had no document overflow or JavaScript page errors; the complete workflow pass also had no errors or overflow. Rhythm Doctor's server instructions and Polyperc's install/restart/enable/restart sequence render legibly at 390 px.

The recording page gives its independent setup, musical comparison and restoration steps. Media loads with controls (sample duration 13.673 s). After waiting for the actual Recordings destination, muted playback is paused at both widths. An earlier measurement immediately after hash change still saw the old playing element; this was a harness timing error, not a reader failure. Likewise, the guide's final result is enabled by completing its preceding actions; the complete sequence correctly focuses the result heading. The quick reference remains within the page width and its Masks filter works. `polyperc` returns no quick-reference control card, while the manual search does find it; optional future search alias improvement, not a current blocker.

## Original F01–F11 closure, reader scope

| Original issue | Current status |
|---|---|
| F01 first-loop → phrase state | Closed in the continuing course; explicit masks and range transitions remain. |
| F02 course front door | Closed; product description and tutorial are distinct. |
| F03 gesture granularity | Closed within recorded-replay design; six first-loop control actions and outcome focus exercised. No live-instrument claim. |
| F04 finished-song outline | Closed; ten chapters reach bass-only/full arrangement and named save/reload. |
| F05 implicit setup changes | Closed in the reviewed course/independent transitions. |
| F06 recipe/scene/recording match | **Reopened** by R1–R4: independent recipe setup and listening expectations need correction. |
| F07 orientation/hierarchy | Closed; course, tasks, reference, recipes and recordings remain distinct. |
| F08 prerequisites below player | Closed in reviewed course and sound/server setup. |
| F09 search/quick reference | Closed at reader threshold; exact/partial search and useful mobile quick controls work. |
| F10 mobile/recipe rendering | Closed as layout; R2 is erroneous instruction content, not rendering. |
| F11 verification voice | **Reopened** by R5, confirmed in expanded normal-reader content. |

No blanket closure of native, real-time, hardware, acoustic or CI requirements is granted by this review. The next review can be scoped to these text corrections and their rendered destinations if all unaffected sources retain parity.

Evidence files in this package: `collection.json`, `reader-prose.json`, `browser-observations.json`, `interaction-observations.json`, `workflow-observations.json`, `audio-check.json`, `caption-candidates.json` and desktop/mobile screenshots. Earlier failed and passing reports remain unchanged in their original packages.
