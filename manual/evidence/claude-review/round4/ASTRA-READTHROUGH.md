# Round 4 Phase 1 — whole-manual adversarial read-through

Date: 2026-10-07. Scope: initial first-time-reader experience review requested by section 4 Phase 1 of `HANDOFF-CHATGPT.md`. **This is not F01–F11 closure, a publication approval, or the Phase 2 per-lesson score campaign.**

## Verdict

The manual has the ingredients of a good teacher, but does not yet behave like one. The course gives me a sensible musical destination and several excellent explanations. Then it asks me to assemble the lesson myself from a prose procedure, two competing links, a distant demonstration, a second sequence of action buttons, and still more distant audio. When I seek reassurance, I sometimes get a different musical example, an error page, or an incomplete instruction. The result feels assembled from evidence rather than composed for someone making music.

Do structural remediation before polishing more individual paragraphs. Preserve the useful concrete explanations and authentic screen/grid evidence. Build one dependable home for each lesson and make its demonstration and listening comparison serve that lesson.

## What I actually read and tried

I used the live built manual at `http://localhost:8765/manual/` in a background Codex in-app browser. I followed actual links, read rendered visible text through the browser, and inspected screenshots at the chapter entrance, first-note action controls, result checkpoint, and audio player. My screenshot viewport was approximately 1265 × 712; this was not an exhaustive responsive or accessibility audit.

I read the home page; all ten course chapters in order; all eight guides offered by Workflows; the complete rendered quick-controls page; the complete rendered cookbook; and three full reference features: Masks, Channel Length, and Chord Strum. I inspected the reference index and navigation. I followed chapter 1's first practice link and independently reproduced its error. In chapter 3 I clicked all six action cues from opening Pattern through adding the fourth note, then clicked View the captured result and observed the transition from 01/10 to 02/10. I followed Listen, started the actual HTML audio player, verified it was playing, and paused it at about eight seconds. The audio had loaded successfully. **I did not assess the sound by ear**, so this report judges audio placement, selection, explanations, and interaction rather than sonic quality or timing fidelity.

The visible evidence entry points are `Capture evidence ↗`, `Sources & captured evidence`, and footer links to `INVENTORY.md`, `DISCREPANCIES.md`, and `BUILD.md`. I did not find a reader-facing About landing page in the visible main navigation. Capture evidence targets `BUILD.md`; clicking it did not produce readable content in my current tab. I therefore read `manual/BUILD.md` from disk as an explicitly source-based supplement. Its opening is “Manual generation and the exhaustive behaviour campaign are separate jobs,” followed by build, qualification and publication procedures. That is useful developer documentation, not a newcomer orientation.

I read the checkout's actual `AGENTS.md` and the handoff. Read-only source identity check: branch `manual/1.4.0-interactive`, HEAD `1867886ca2f39e3aff99cea19133e83b9c0cdd44`. Working-tree content is authoritative; HEAD alone does not identify its generated outputs. The parent independently verified the passing baseline `full-controlled-local-20261006-23/64c23dd9bab4498092f9a0bddd43dfbe` with 48 successful stages, `passed: true`, and `manual_generation_complete: true`. I did not rerun that audit or any build. Read-time SHA-256: `manual/course.yaml` = `910fe7678632e994e700ae25723eb34ce96e9ac036b19dd505fce87d83b4f5c4`; `manual/book.js` = `0fb6b16b9c037faa044b441114e78aeb406be6ef9a929037dea46235da00cd05`; untouched `manual/ADVERSARIAL_REVIEW.md` = `8b75da934867f6abfb803a143fd7c1c62287d5c90620e8433561dbb52a2cd155`.

Limits: I did not replay every interaction, inspect every reference feature, operate a physical norns, execute the course against a live instrument, audit test provenance, or establish why the visible defects occur. Exact observations below are browser evidence unless marked source-based. Proposed implementation layers are triage, not an assertion that root causes have been proved. Screenshots were observed in the tool transcript; this report does not add image files. No builds, native captures, recordings, service changes, or manual production edits were performed.

## Scores for the experience as a whole

These are reviewer judgments, not averages of unit scores. 8 means a newcomer can follow confidently with only small friction; 5 means useful content requires repeated reconstruction; 2 means the chosen path can block the task.

| Dimension | /10 | Reason |
|---|---:|---|
| Readability | 6 | Clear type and many plain instructions; long repeated paragraphs, dense MIDI detail, and truncated cookbook values interrupt reading. |
| Comprehensibility | 6 | Patterns/channels/slots and mask precedence are explained well locally. Competing starting states make the whole difficult to understand. |
| Flow | 4 | The course's musical arc works, but text, demonstration, audio, detours and reference compete instead of forming one progression. |
| Understandability of the next action | 5 | Physical gestures are often explicit. Two links per stage, cue-only progression, missing values and a failed practice route leave uncertainty. |
| Friendliness | 5 | Helpful recovery notes coexist with source-receipt errors, test language and repeated statements about unavailable practice. |
| Interactive examples' usefulness | 4 | Authentic results are valuable, but intermediate cue clicks do not show intermediate results; controls and feedback are spatially separated. |
| Cohesion | 3 | The same concept is independently presented under course, workflow, recipe, reference and audio identities, sometimes with different music. |

## Journey as it is

The front page's “Start with four notes. Turn them into a phrase, add another part and arrange two sections” is the right promise. Chapters 1–4 teach objects and controls, routing, a four-note stutter, and then beats across a bar. Chapters 5–8 add a D ending, soften it, add a bass, migrate pitch from masks into relative notes, compare scales, restore C, and add a quiet pickup. Chapters 9–10 copy a section, mute one part, alternate the sections, save, deliberately change, reload and verify. This is a credible musical course.

The strong moments should survive: “You hear C, C, C, D”; the comparison with “G, G, G, D”; the definition of a ghost note; the audible bass-only/full-section contrast; and saving, making an unsaved change, then reloading. Before/after/recovery information is useful. The reference's explicit distinction between an unset X and zero is valuable. Draft/apply explanations help avoid a real confusion.

The course is also an obstacle course through representations. Each chapter starts with broad feature metadata, then detailed preparation and outcomes, then all text stages with two links apiece. The next-chapter link appears before its demonstrations and audio. Below that are a scene selector, two grid presentations, a current state, upcoming outcome, action cues, MIDI, another next action, checkpoint navigation, and audio. Chapter 5 has ten prose stages and twenty captured checkpoints. These counts are not naturally the same lesson progress.

Workflows looks like the next level, but much of it repeats the course in compressed form, while its demonstration changes to an older C–D–E–F example. The cookbook expands recipes in a very long collection that mixes musical ideas, recovery gestures, regression checks and developer tests. Quick controls is useful as a searchable reference, but opens with 293 controls and Lock lead time rather than the likely first lookup. Reference pages contain genuine depth, but start with outcome fragments before the concepts they describe.

## Prioritized findings and recommended changes

Layer key: **R** reader (`manual/book.js`, `manual/manual.js`, `manual/manual.css`); **A** authoring (`manual/course.yaml`, `manual/features/*.yaml`, captions and `manual/scene-starting-states.yaml`); **M** audio metadata/selection; **N** native capture, only when an actual changed or missing checkpoint requires it. Every recommendation below is assigned a layer. No recommendation authorizes a rebuild or recording.

### R4-01 — P0: the first invitation to practice fails

Route: `#getting-started/course` → first “Practice the recorded walkthrough” → `#getting-started/lesson/getting-started-objects`.

Exact result: “Manual content could not be loaded: The requested recorded course walkthrough is unavailable or its source receipt is stale.” I independently reproduced this through the visible link. A newcomer has done nothing wrong, yet the first exercise tells them the manual is invalid. It also removes the lesson body instead of leaving a useful fallback.

**Recommendation [R, A]:** make the chapter stage itself the working demonstration home. Resolve old practice URLs to that stage and its valid checkpoint. Verify every generated course-stage link by actually following it. Fail closed for evidence, but preserve readable lesson text and a truthful explanation if an asset cannot load. Diagnose route/receipt selection before considering recapture; no evidence here establishes a need for N.

### R4-02 — P0: cookbook instructions lose necessary numbers

Route: `#cookbook`, “Add a ghost note before an accent”. Exact text: “Starting point: the four-step loop from Make your first loop, with channel default Vel”; “Hold step 3 (grid (3,4)) and turn E3 right until the screen reads”. The corresponding recipe at `#masks` says “Vel 80” and “reads 100.” I checked the cookbook paragraph's DOM textContent: the missing number is not merely a line wrap in extracted text.

Other examples on `#cookbook`: “The draft is saved to slot”; “Outcome: The step lock sends 99 on step 1 while the device default remains”; “Select High with E2 and turn E3 five times left. High reads”. Missing targets make the procedures impossible to follow exactly.

**Recommendation [R, A]:** investigate cookbook extraction/rendering as a class, retain full authored instruction values, and verify representative numerical endings against their canonical lesson. Do not repair this by guessing numbers or individually padding sentences until a parser happens to preserve them. Rendering/content regressions need a check that the number and its action are visible together. No M or N needed.

### R4-03 — P1: a lesson has several competing places

Routes: all ten `/<course>` pages, most visibly `#masks/course`. Every prose stage ends “Practice the recorded walkthrough” and “View the captured result.” Later come “Interactive examples,” “NEXT ACTION,” and “05 / AUDIO EXAMPLES.” The next chapter is offered before those sections. I am repeatedly choosing whether to continue reading, leave for practice, inspect a result, or scroll to a player; none is clearly the lesson's main track.

**Recommendation [R, A]:** one chapter page with one active stage workspace: short purpose → action → actual screen/grid checkpoint → expected change → relevant listening comparison → continue. Stage links focus this workspace, not a second page. Keep full instructions available for reading/printing. Offer reference as an optional concise link after the local explanation. Remove the two-button fork. Existing captures can support this without N unless a new gesture/result is promised.

### R4-04 — P1: cue clicks feel like performing actions but only advance text

Route: `#first-sound/course`, first interactive stage. I clicked “Open the Pattern page,” “Choose pattern 1,” and all four “Add the … note” buttons. The workspace stayed “01 / 10,” “PREPARED STARTING POINT,” “Starting point,” while its status changed to the next cue. Only “View the captured result” changed it to “02 / 10” / “Enter four trigs.” Before that result, the page already said “Four bright buttons light at (1,4) to (4,4).”

This is not evidence of a broken emulator: it is a misleading teaching progression. I cannot tell whether I have done something or merely acknowledged an instruction. A screenshot at the cue buttons showed neither the norns screen nor the grid in the viewport.

**Recommendation [R, A]:** clearly present grouped instructions followed by one honest “Show result” when only a group checkpoint exists; do not dress text advancement as individually simulated instrument actions. Keep action, checkpoint and changed-value explanation adjacent. Where a fine interaction is essential, mark the missing checkpoint and request **N only for that checkpoint**. Do not draw invented intermediate states. Separate “Before” from “After”; never state a future result as current feedback.

### R4-05 — P1: audio is detached both spatially and musically

Routes: `#first-sound/course`, `#masks/course`, `#harmony-design`, `#loops-that-meet`. The audio says “The devices above follow the captured playhead while audio plays.” At chapter 3's visible audio player, none of those devices was visible. Listen did eventually land correctly, and playback worked; the problem is placement, not a broken audio link.

On `#masks/course`, the goal ends with velocity 50, but the first clip is “Raising the last note,” explicitly “all at velocity 80”; “Quieter last note” is a separate choice below. On `#loops-that-meet`, the title teaches four against three, while the audio is “Sixteen steps against twelve.” Each can be valid, but the reader must do the matching work.

**Recommendation [R, A, M]:** place each clip at the stage it demonstrates, with one sentence naming the change to hear. Bind selection deliberately to that stage rather than first matching feature entry. Put the synchronized device view alongside or immediately above the player, with a compact mobile arrangement. A different musical example deserves its own named extension, not the principal lesson's default soundtrack. Prefer selecting/repositioning existing recordings; no new recording is justified by this review.

### R4-06 — P1: workflows contradict the user's working example

Route: `#harmony-design`. Main text: “C–C–C–D returns through relative notes.” Interactive starting point: “four trigs on steps 1 to 4 with the notes C, D, E, F … at velocities 127, 117, 107 and 97.” Course chapter 7 is the sixteen-step phrase and bass; workflow audio also swaps its internal voice assignments from the course and compares two bars per key. Route `#sequence-composition` similarly begins with the course phrase but selects “Add a second pattern in D major.” Route `#song-composition` teaches a sixteen-step sparse/full arrangement while the first demonstration starts with four-step channels and changes global length to four.

**Recommendation [A, R, M]:** choose one canonical lesson for each musical task. Link workflow cards to the existing course lesson when they teach the same task; offer a compact “Start from your own project” prerequisite beside it. Keep genuinely independent C–D–E–F examples under their own named lessons. Reuse the course's already matching captures and clips before requesting N. Rewording “independent example” is insufficient when the page still presents it as the main worked result.

### R4-07 — P1: displayed output appears to include history from earlier chapters

Routes: `#masks/course`, `#sequence-composition/course`, `#keep-your-work/course`, initial checkpoint. While the current caption says playback is stopped, the strip labelled “MIDI sent in this step” lists old C3 notes starting `@39820 ms`, later notes, hundreds of controller/program messages, and note-offs. In chapter 10 it still begins with the early-course stutter. I cannot use this to check the action I just performed.

**Recommendation [R; A if selection is authored]:** show current action or playback-window output with a meaningful local time origin. Collapse raw MIDI history under optional output details, preserving original evidence. A stopped setup should explain historical output as history, not imply it happened in this step. Diagnose interval selection against existing reports; use N only if the required interval genuinely was not captured.

### R4-08 — P1: cookbook is an extraction dump, not a set of musical recipes

Route: `#cookbook` and home “Musical examples”. It starts with “Return from a held-step edit to the page you were using,” followed by two nearly identical panic checks. The mask-inheritance recipe recurs repeatedly. Later recipes include “Check a change before a pull request” and “Read a harness example,” with Lua code. “Comparing the Loop Alignment” says “the six steps above are done” although those setup steps are not its immediate recipe context.

**Recommendation [R, A]:** make cookbook a curated index of musical outcomes (a ghost note, an answering bass, changing harmony, interlocking rhythms), not full flattened recipe bodies. Each card links to one complete lesson, with its prerequisites and matching audio. De-duplicate by lesson identity. Put emergency controls in troubleshooting/quick controls, and contributor tests under About/Evidence → For contributors. Preserve specialist recipes without putting them before the first useful musical choice. No N required merely to organize existing material.

### R4-09 — P1: build and test prose addresses the wrong reader

Routes: home and `#cookbook`: “Confirm the source case records the full all-notes-off stream”; “Keep the held-step readout as the lock proof; do not infer exact MIDI output from the truncated intermediate stream”; “the earlier startup output is truncated and is not used as the target.” Across course/reference: “CAPTURED INTERACTIONS,” “Recorded walkthrough. No authored practice is available for this transition,” and the footer “133 guide sections · 145 captured interactions.”

**Recommendation [R, A]:** replace player instructions with observable musical/screen actions, remove implementation-status badges, and move source limitations, receipt kinds and test assertions behind a consistently named Evidence disclosure. Preserve the limits there; do not replace precise qualification with unsupported claims. Introduce a short About page explaining that browser demonstrations replay authentic examples and do not control the user's instrument. No need to repeat this on every step.

### R4-10 — P2: the course spends momentum on undoing itself

Routes: `#masks/course`, `#sequence-composition/course`, `#harmony-design/course`. Chapter 5 says “Chapter 7 removes the channel Note mask again”; then creates, compares, restores, clears and rebuilds the ending. Chapter 6's optional Skip/Only/All detour occupies four of its eight stages. Chapter 7 must clear both Note and Vel and restore Vel to make the scale lesson possible. These explanations are accurate-looking locally but make a first piece feel like preparing test fixtures.

**Recommendation [A, R]:** keep the existing captured core path for this edition where possible: make the ending and soften it; add the bass; explicitly teach one intentional change from fixed pitches to scale-relative notes; arrange and save. Move mask clearing/default comparisons and merge experiments into optional extensions reached after a completed musical result. Show the precise current musical state once at chapter boundaries. A larger reorder or different pitch-entry path would touch **N** and must be justified separately; it is not a necessary first remedy.

### R4-11 — P2: names and navigation imply several different books

Routes: `#masks/course` has title “5. Give the phrase an ending,” breadcrumb “Masks,” and eyebrow “MOSAIC / CHANNEL.” Chapter 8's title is “8. Add a pickup,” breadcrumb “Adding Parameter Variation,” and eyebrow “MOSAIC / WORKFLOW.” Navigation says “Start here,” breadcrumb “Make a piece”; Workflows opens “Make a change”; Musical cookbook opens “Musical examples” twice. Legacy references still say “Make your first loop” or “Build a phrase.”

**Recommendation [R, A]:** course breadcrumbs and browser titles use the chapter's musical title; reference uses the instrument feature name; links explicitly distinguish “Masks controls” from “Give the phrase an ending.” Use one navigation name per destination. Keep chapter progress (“5 of 10” is helpful, not banned vocabulary), but remove duplicate numbering in ordered lists such as “1. 1. Meet Mosaic.” Old routes remain aliases to a canonical page/stage, with no independently maintained duplicate lesson.

### R4-12 — P2: dense precision and loose fragments obscure useful explanation

Routes: `#setup/course` explains a beat as “2/3 s”; `#first-sound/course` repeats 1/6 s, 2/3 s and “about 167 ms”; later chapters repeat 2.7/5.3/10.7 seconds. Reference pages prepend “Recorded walkthroughs” followed by note-number summaries before definitions. `#chord-strum` opens with “consume spacing and acceleration ordinals, including trailing empty slots.” `#sequence-composition/course` apologizes for “The extra pad at (13,6) is not one of yours”.

**Recommendation [A, R]:** lead with what to do and hear: one note per beat, last beat higher, bass joins on beats one and three. Keep exact MIDI/time details in optional output inspection, and advanced strum edge cases after a simple demonstrated strum. Investigate the unexplained extra pad against the existing capture instead of normalizing unexplained state with prose; **N only if a truthful matching checkpoint cannot be selected**. Keep concrete feedback names and required values visible; simplification must not remove the information needed to act.

### R4-13 — P2: quick lookup starts as a catalogue rather than a shortcut

Route: `#quick`. Opening: “293 matching controls in 101 feature groups”, starting with “Lock lead time” and including Development's `./test.sh`. The core gesture tables themselves are useful and often concise.

**Recommendation [R, A]:** preserve searchable complete controls, but start with Play/stop, choose page/channel, edit/clear a step, save/load and panic. Group the rest by the visible instrument page or task; exclude contributor commands from the musician default. Search results should point directly to the relevant canonical control or lesson, not force a choice among course and reference aliases. No M or N needed.

## Target structure and canonical homes

**Primary reader intents [R, A]:** “Make your first piece” (continuing course), “Try an idea” (independent musical lessons, replacing overlapping workflow/cookbook bodies), “Find a control” (feature and gesture reference), “Solve a problem” (no sound, wrong context, clearing, recovery), and “About & evidence” (what these examples are and how they were checked). The home page gives these choices briefly, with one obvious start action. Do not lead the home page with regression recipes.

**One home per lesson [R, A]:** retain stable feature IDs and deep links internally. Existing `#masks/course` can remain the canonical chapter page with stable stage anchors; `/lesson/...` and `/course/.../<checkpoint>` routes should resolve into it with the correct focus. `#masks` remains the controls/concept reference and links to the chapter or a distinct independent lesson. A cookbook card, workflow listing, search result and audio card all link to that same lesson identity. A second example with different notes is a second lesson, not an invisible substitution within the first.

**Naming rules [A, R]:** lesson titles are verbs plus musical results (“Soften the pickup”); reference titles match actual instrument names (“Masks”, “Trig params”); exercise controls say what the browser will do (“Show result”, “Hear the softer ending”). Use one consistent term each for pattern, channel, song slot, step, trig, mask, default and override. Explain technical instrument terms rather than banning them. Build terminology belongs only in evidence. Stage numbering tracks the learner's progression; capture numbering does not compete with it.

**Reusable lesson composition [R, A, M]:**

1. A short musical promise and, when available, an immediately playable preview of that exact example.
2. “Start here”: prior course state or a complete independent setup, chosen deliberately rather than both intermixed.
3. One action or honest grouped action with its necessary controls, authentic before/after checkpoint, and a short explanation of the perceptible difference.
4. Matching audio at the listening stage, with device feedback in view and a compact “what to listen for.” Explicit before/after choices for comparisons.
5. A small recovery option, then Continue. Optional variations and full controls come after success.
6. A collapsed Evidence link preserves source identities, timing qualifications, raw output and provenance without making them the teaching material.

For chapter 5, this means “Raise the last beat” uses the existing raised-note clip and D3 result; “Soften it” uses the quieter-last-note clip and Vel 50 result. Clearing and changing defaults become optional lessons. The same workspace and ordering should then be applied to other chapters; do not build a special Masks-only reader.

## Build-vocabulary policy for the musician-facing surface

This is an editorial policy, not a request to mechanically search-and-replace evidence. Terms in the first column are prohibited as teaching/navigation labels unless the reader explicitly opens evidence. Some are observed; others are preventive rules from the handoff. Product concepts such as parameter lock, fixed note, mask and random seed remain legitimate.

| Current/build term | Plain reader alternative or destination | Layer |
|---|---|---|
| CAPTURED INTERACTIONS / CAPTURED EXAMPLE | Omit badge; “Example” if needed | R |
| Practice the recorded walkthrough | “Try this step” only if genuine supported practice; otherwise “Show the steps” | R/A |
| View the captured result / Preview the captured result | “Show result” | R |
| Recorded walkthrough cue | Current action, or omit status if already visible | R/A |
| No authored practice is available | Do not offer practice; present available demonstration normally | R |
| Prepared starting point / captured native pre-input baseline | “Before you start” / “Before” | R/A |
| scene / scene step / step ID | “Example” / learner stage title; identifiers in Evidence | R/A |
| source case / target / checkpoint proof | Actual screen or musical result; proof details in Evidence | A |
| binding / contract / receipt / source identity | Evidence-only terminology | R/A |
| truncated intermediate stream / complete mapped phrase | Useful musical expectation; diagnostic limitation in Evidence | A/R |
| test device | “Example MIDI instrument,” or name the required route/device honestly | A |
| 133 guide sections · 145 captured interactions | Edition/version in footer; inventory counts in Evidence | R |
| Reproduce captures / reconciliation notes | About & evidence → For contributors | R/A |
| exact revisions / native / profile / controlled-time | Evidence metadata; short plain explanation of scope in About | R/A |
| deterministic (when only explaining a pickup) | “The pickup plays every time” | A |
| MIDI numbers and milliseconds | Keep required targets; optional detailed output for repeated diagnostic listings | R/A |

Do not ban “Chapter 5 of 10”: it orients the reader. Do not hide the fact that examples are recordings or imply a live emulator. State that plainly once in the demonstration introduction/About and describe each control honestly.

## What moves to About & evidence

**[R, A]** Add a short musician-facing About page explaining the edition, the real captured norns/grid demonstrations, browser-only playback, independent versus continuing lessons, and the limits of device/timing claims. Keep a consistently placed link from each example to its specific evidence. Put hashes, source cases, raw MIDI journals, generation status, inventory/reconciliation, pipeline instructions, qualification matrices and contributor harness recipes in the deeper evidence/contributor area. Keep operational warnings near actions when relevant: overwritten song slots have no undo; a particular sound needs polyphony. Those are user information, not build noise.

## Remediation order and next review sample

1. **[R, A]** Repair the broken practice route and cookbook number loss with focused visible regressions. Do not let a passing build hide these reader failures.
2. **[R, A, M]** Pilot one canonical workspace on first-sound and Masks using existing captures/audio; retain all evidence. Check a chapter entrance, stage link, completed grouped action, back/continue, and matching listening result at normal and narrow widths.
3. **[A, R, M]** Reconcile workflow/recipe homes and starting states, then apply the proven workspace to the remaining chapters. Move detours after the musical result.
4. **[R, A]** Curate the cookbook, quick controls and About navigation; sweep numerical completeness and build prose across all reader surfaces.
5. **[N only if demonstrated necessary]** Log genuinely missing native checkpoints separately. No native recapture should be inferred merely from poor placement, duplicate pages, or an unsuitable default audio choice.

Phase 2's small sample should include chapter 1's first link, chapter 3's grouped trig action plus listening, chapter 5's pitch/velocity pair, chapter 7 versus its workflow entry, the four-against-three lesson versus its audio, a cookbook ghost-note recipe, and one reference lesson such as Chord Strum. Score each as actually reached from its entry point, not as isolated YAML. Ask: Can I identify my starting state, know the next action, see its result without losing the controls, hear that same example, recover, and continue without choosing between duplicate homes? Keep the five required unit dimensions and these journey questions explicit. Do not award an 8 for locally good prose when the route fails or the demonstration teaches different music.

No full build, audio recording, evidence relabelling or F01–F11 closure is recommended by this report. Remediation must follow the handoff's impact-note, scratch-output, focused-check and immutable-baseline rules.
