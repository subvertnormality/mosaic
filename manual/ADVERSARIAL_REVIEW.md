# Adversarial review of the Mosaic 1.4.0 interactive manual

**Date:** 3 October 2026  
**Audience:** the human author and the implementation/review agent  
**Decision:** substantial teaching and navigation redesign required before calling this a complete interactive learning manual.

## Overall judgment

The current manual is a promising reference and an impressive collection of inspectable captures, but it is not yet a coherent course in making music with Mosaic. Its strongest asset is that concrete controls can be tied to actual instrument output. Its central weakness is that the reader is too often asked to infer the lesson from those checkpoints.

I broadly agree with the user's criticism, with two qualifications. First, binding examples to behaviour evidence is not itself the problem. Removing that binding would make the manual less trustworthy without making it more teachable. The problem is allowing verification grouping, fixture setup and boundary-test progression to determine the reader's sequence. Second, the manual does contain musical applications and a usable first-loop procedure. The failure is not “there are no musical examples”; it is that those applications, procedures, replays and recordings frequently describe different states or are not connected into an achievable journey.

**Newcomer journey: 3/10. Expert reference experience: 5/10. Overall readiness as an interactive manual: 4/10.** These are editorial judgments against the observable design, not measured user-study results or an arithmetic average.

A newcomer can reasonably get a first loop from the dedicated first-sound page. They cannot yet rely on the manual to carry that same project through rhythm, harmony, melody and arrangement without supplying missing operations, resolving state conflicts and finding subsidiary pages themselves. An expert who already knows the vocabulary can extract useful controls, but the flat contents, incomplete search scope and absent active chapter state create unnecessary work.

## Scope and source identity

This concerns the **current working-tree site**, not merely the committed repository or a future fully rebuilt edition.

- Worktree: `/home/andy/mosaic-manual-1.4.0`.
- Branch supplied for the task: `manual/1.4.0-interactive`.
- Observed HEAD: `69df623e06efd6721e1cc53e961a1dd845d2a48c`.
- Frozen baseline supplied for the work: `54d7b871358fcc68b7166847603cc9fb1461d0b6`.
- Working tree contained substantial modified and untracked manual material.
- Examined published book: **133 feature pages and 75 scenes**. These counts do not imply complete verification.
- Local browser: `http://127.0.0.1:8765/manual/`.
- Rendering checks: desktop 1440 × 1000 and mobile 390 × 844; screenshots inspected in light theme.

I read the navigation/player implementation, stylesheet, book manifest, STYLE.md and RESEARCH.md; sampled authoring sources including Masks, tutorials, cookbook, learning and workflow material; and examined published text and scene metadata across setup, first sound, rhythm, harmony, melody, Masks, merge modes, song, modulation, options and quick reference. I compared selected relevant passages with the frozen original README.

Browser inspection confirmed rendered Start here, Workflows, Masks, First sound and Quick reference; one Masks interaction was exercised. Browser work was deliberately small while native evidence work continued. No native behaviour campaign, new MIDI/audio verification, hardware test, exhaustive accessibility audit or user study was run. I did not listen to every recording or read all 133 pages exhaustively.

**SHA-256 values captured at 2026-10-03 14:11:45 UTC:**

| File | SHA-256 |
|---|---|
| `manual/generated/book.json` | `43f5bef85ed07658f1b917ea1a5c0b65fbcbb3ca8c6c238ecf464529e63ee902` |
| `manual/index.html` | `717bc0a1aaf1d2f808821250307faacf076cc346b3d712fcc747361ef0b8e025` |
| `manual/book.js` | `93e8a743f7a08168b2101cc93ef7ec301ed580e6664e628d913f2d1a6f9cce4b` |
| `manual/manual.js` | `f80348fbaccfb8a03db8c2bc4c8117c5786a115f2e556f5b8a02b55221097a4d` |
| `manual/manual.css` | `12ea8127391d7ec74422da49f7083e8fa416f2d889d4ab03c1c66f90e7f215f3` |
| `manual/book.yaml` | `039369c8aa066d90a3c794e59a39373ff28f3adf505daa0821dee9fbf58aaf5b` |
| `manual/features/masks.yaml` | `4ee9691bf731f934bba71c86f62c91ec0eab1526f3991449641de0cff70b9a0d` |
| `manual/features/tutorials.yaml` | `6c52e1c9ab52cc16bad507c2dd04ea79b2c8b2bb333d111106bf3125bd047eb8` |
| `manual/features/cookbook.yaml` | `6863d014ff5640b0fd1b74c7742170c2413125839a4ac0c5a26277fffeacd552` |
| `manual/STYLE.md` | `fb60343e0694ca6764161c286e6d970c682adc0a0c73f23a0467793fced2c0c1` |
| `manual/RESEARCH.md` | `a6691d65ef72cd1d3c38eb66e8e4935cdfe289c1604aa631335c2ecabd1aafe0` |
| `manual/legacy/README-1.4.0.md` | `532f08b5fff1d2b90022f02ba418dcbef3b77017e8a1a5c6e057d04a9e41b51c` |

The published book reported authoring identity `0c91983e271f0c75fe83122ecea20ee3c92deb439f11c2507d507fd747eb0eb2` and source SHA `423b9fa7eb675c4559efb1e13140b261a93bd73ae6f31878823f750dfd6be4ab`. Its embedded manifest's hashes for book.yaml and cookbook.yaml already differed from the current files. Newer authored content should not be assumed visible in this reviewed build. This is a publication-state limitation, not proof of semantic failure in newer sources.

Links below use the approved preview for convenience. The hashes above, rather than a changing URL, identify the reviewed content.

## Scores and definitions

**Anchors:** 1–2 = fails the intended reader's job; 3–4 = substantial gaps requiring outside knowledge or reconstruction; 5–6 = usable with friction and prior knowledge; 7–8 = clear and dependable in most cases; 9–10 = exemplary, coherent and low-friction. A 10 would require stronger direct usability evidence than this review supplies.

The overlapping terms are separated by the question each answers:

| Dimension | Definition | Score | Basis |
|---|---|---:|---|
| Readability | Can the reader scan and parse words and layout? | **7/10** | Restrained presentation, literal titles and tables. Oversized openings, flattened recipe steps and long unindexed pages reduce efficiency. |
| Comprehensibility | Can the reader understand the current explanation? | **5/10** | Channel defaults and step exceptions are locally clear. Terms and implied operations accumulate faster than they are taught. |
| Flow | Does the next instruction follow from the previous resulting state? | **3/10** | Beginner routes are not primary navigation; fixture changes and missing transitions break continuity. |
| Understandability | Can the reader build a mental model and predict a new result independently? | **4/10** | The pattern/channel/scale/song distinction helps, but most scenes reward advancing rather than predicting or comparing. |
| User-friendliness | How much effort is needed to navigate, operate and recover? | **4/10** | Search, keyboard support and named controls help. Missing active section, static breadcrumbs, tiny mobile pads and hidden prerequisites hinder use. |
| Usefulness of interactive examples | Do interactions teach transferable musical decisions? | **3/10** | Some Masks captions teach scope. Larger scenes are compressed test histories; recordings often do not match the taught operation. |
| Cohesion | Do navigation, prose, scene state, recipes and sound tell one consistent story? | **3/10** | Reused scenes and audio are grouped by feature relevance rather than a shared musical project. |

These scores do not grade the sequencer or the test engineering.

## Prioritized findings

### 1. Critical: the beginner continuation contradicts its inherited musical state

**Where:** [First Loop](https://karen-diy-clarity-status.trycloudflare.com/manual/#first-sound) → [Phrase and Arrangement](https://karen-diy-clarity-status.trycloudflare.com/manual/#build-a-phrase).

First sound sets a **channel-wide Note mask to MIDI 60**. Build a phrase begins, “Begin with a named copy of your first working loop,” then asks for “a simple root–third–fifth contour” in Pattern Note.

The documented Masks rule says the channel default overrides merged pattern notes. The continuation never unsets that Note default. Following the written continuation therefore preserves a value that can conceal the new pattern melody.

This is a **documentary state-continuity conflict inferred from the manual's own precedence rule**, not a newly reproduced application defect.

**Impact:** a beginner can edit correctly and hear the same pitch, then assume they misunderstood Pattern Note or harmony.

**Repair:** explicitly reconcile the incoming state. Change the applicable Note mask back to X before teaching relative pattern notes, or choose another coherent route. Demonstrate why. Do not silently load another fixture.

### 2. High: the primary contents do not expose the learning narrative

**Where:** [Start here](https://karen-diy-clarity-status.trycloudflare.com/manual/#learn), [Getting Started](https://karen-diy-clarity-status.trycloudflare.com/manual/#getting-started), [Workflows](https://karen-diy-clarity-status.trycloudflare.com/manual/#workflow); `book.js home()`.

Rendered Start here offers Installing Mosaic, Hardware Requirements, MIDI Device Configuration, Norns Sound Sources with n.b., Adding Trigs, and Save and Load. It omits Creating a First Loop, Creating a Phrase and Arrangement, and Troubleshooting No Sound.

The separate Getting Started page has a better ordered route: Setup → First sound → Build a phrase → Save. “Start here” does not lead directly to that page.

Workflows shows Pattern Editor, Merge Modes, Masks, Scale Editor, Channel Length and Song Editor: feature destinations rather than the already-authored sound → rhythm → harmony → melody → variation → song progression.

**Impact:** the data contains a curriculum but the front door presents a catalogue. MIDI configuration receives more prominence than the shortest route to sound.

**Repair:** make Start here the actual course and Workflows task-based. Keep the comprehensive catalogue in Reference.

### 3. High: replay interaction teaches the wrong granularity of action

**Where:** [Masks / step exception](https://karen-diy-clarity-status.trycloudflare.com/manual/#masks/mask-precedence/step-one); `manual.js gesture()` and `render()`.

The caption says, “Hold step 1 and turn E3 five detents to C4.” The browser accepts **one click on E3 alone**, advancing checkpoint 02 → 03 including the held-step state. This was directly observed. The code advances when any recorded input in the next checkpoint matches, rather than requiring its ordered combination.

The display already shows the **result** of the captioned action, while highlights indicate controls in the **next** checkpoint. The written instruction and invited action are temporally offset.

| Scene/checkpoint | Captioned operation | Recorded input entries |
|---|---|---:|
| `merge-overlap-and-union/patterns` | Assign patterns 01 and 02 | 270 |
| `pattern-note-range/initial-note-range` | Tap the fourth-column note fader | 226 |
| `pattern-velocity-range/velocity-0` | Hold range-down and choose the lowest value | 600 |
| `workflow-compose-two-channels/chained-song` | Copy, transpose and play two slots | 121 |

These are **raw input entries**, including navigation, presses/releases and other recorded actions, not distinct human gesture counts. They indicate undisclosed state transitions between teaching frames.

**Impact:** a reader advances without learning the gesture and may infer that touching E3 substitutes for holding a step.

**Repair:** distinguish demonstration from practice. A demonstration can show constituent operations with “Show the next action.” A practice mode must require the relevant ordered gesture and hold state. Both can use verified captures; neither should treat any input in a bundle as successful enactment.

### 4. High: first sound is promising, but finished-song instruction is an outline

**Where:** [First sound](https://karen-diy-clarity-status.trycloudflare.com/manual/#first-sound), [Build a phrase](https://karen-diy-clarity-status.trycloudflare.com/manual/#build-a-phrase), [Arranging Song Slots](https://karen-diy-clarity-status.trycloudflare.com/manual/#song-composition).

First sound names coordinates, channel, output application, range, values, stop behaviour and save. It approaches a self-contained lesson.

The continuation switches to “Add a second channel with a contrasting voice,” “make a short motif with three stable notes and one answer,” and “Copy the slot.” These are musical intentions, not executable beginner procedures. Song composition says “Check Song mode, slot repetitions and global sequence length” without assigning values for the promised arrangement.

The scene `workflow-compose-two-channels/chained-song` combines copying, octave editing and playing an arrangement into one checkpoint. A successful native outcome does not supply the missing learner operations.

**Impact:** the difficult part of making a song is delegated to the reader immediately after the tutorial.

**Repair:** build one bounded arrangement with exact routes/voices, steps, notes, lengths, repeats, copy gesture, mute variation and named save. Put creative choices after a working result. An outline should be called an overview.

### 5. High: fixture changes are not introduced as lesson-state changes

**Where:** [Masks](https://karen-diy-clarity-status.trycloudflare.com/manual/#masks), scenes `mask-precedence`, `mask-expression`, `mask-chords`, `mask-trigs`; Getting Started.

Precedence ends with a G3 channel default. Selecting velocity returns to an independent C–D–E–F fixture. Chords also starts from the original pattern; trig masks uses an eight-step rather than four-step loop.

These are legitimate independent tests. The player lacks a prominent “This example starts fresh” card specifying notes, range, defaults and output. The initial frame is already after navigation.

Getting Started's first attached scene is mask precedence, before its first-sound scene. Its interactive ordering contradicts its own numbered course.

**Impact:** readers assume changes persist and cannot explain why notes, length or defaults changed. Reused scenes feel repetitive rather than progressive.

**Repair:** independent examples need visible initial-state summaries. A course needs one continuing project, with explicit reset/branch points. Reuse evidence freely; author the reader's sequence around its purpose.


### 6. High: musical recipes, scenes and audio often demonstrate different things

**Where:** [Four-Bar Bass, Chord and Melody Example](https://karen-diy-clarity-status.trycloudflare.com/manual/#small-hours), [Adding a Ghost Note](https://karen-diy-clarity-status.trycloudflare.com/manual/#pocket-rhythm), [Changing Harmony with Scale Slots](https://karen-diy-clarity-status.trycloudflare.com/manual/#tilting-harmony).

- Small-hours promises bass, chords and a Polyperc melody. Its recording uses **percussion, bass and chords**, with different velocities and roots. The authoring source explicitly acknowledges this difference.
- Pocket-rhythm teaches velocity 35 on step 12 before velocity 90 on step 13. Its recorded-example text specifies velocity 48 and a three-timbre sequence. Attached scenes teach velocity boundaries and probability endpoints, not construction of that exact ghost-note pattern.
- Tilting-harmony teaches applying C-major and D-major scale slots. Its audio description teaches bass and chord masks with MIDI roots 60 and 62, rather than the named scale-slot comparison.
- Modulation's `matrix-macro-route-clear/value` drives all notes to MIDI **127**. This is a clear extreme-value test but a poor first example of musically controlled movement.

Scope disclosures are honest and should remain. They do not make the mismatch a good lesson.

**Impact:** audio cannot serve as a reliable answer key for the reader's work. The link between musical effect and control remains uncertain.

**Repair:** provide an exact target clip and the same material before/after the taught change. Put unrelated performances in a separate inspiration area. Start modulation with a modest audible range before offering extremes as reference experiments.

### 7. High: persistent navigation does not provide persistent orientation

**Where:** all feature routes; [Masks](https://karen-diy-clarity-status.trycloudflare.com/manual/#masks), [Reference](https://karen-diy-clarity-status.trycloudflare.com/manual/#reference); `book.js route()`.

On rendered Masks and First sound, **none of the six sidebar sections is selected**. Selection matches only top-level hashes. “MOSAIC / CHANNEL / MASKS” is plain text, not a clickable parent path; CHANNEL is not one of the six sidebar destinations.

Parent relationships exist in the data, but Reference flattens pages into category tiles. Large chapters and tiny options receive similar visual weight. “In this chapter” helps locally, but there is no persistent sibling map or previous/next course position.

Inherited relationships can also mislead: Options, Sinfonion Connect and LFOs and Modulation sit under Save and Load.

**Impact:** a user sees navigation without knowing where the current page belongs or what comes next.

**Repair:** persist active section/chapter; provide clickable parent breadcrumbs, a collapsible chapter tree and course previous/next controls. Keep tutorial order separate from legacy heading ancestry.

### 8. Medium-high: prerequisites appear after the interaction that needs them

**Where:** [Masks](https://karen-diy-clarity-status.trycloudflare.com/manual/#masks), [Controls and Navigation](https://karen-diy-clarity-status.trycloudflare.com/manual/#getting-around-mosaic), [Applying a Scale](https://karen-diy-clarity-status.trycloudflare.com/manual/#harmony-design).

Masks places an abstract definition, child tiles and the player before Controls. Core explanations — X means unset, precedence, polyphonic output, pitch-name conventions — are collapsed below the player. The original pilot's explicit starting-state card is hidden by the book renderer.

Notation is reasonably consistent once learned, but trigs, relative notes, masks, slots, applied scales and channel scope accumulate quickly. “Edit its root and scale type” in Harmony omits the actual selection/edit operation.

**Impact:** the reader must leave the confusing interaction to discover the prerequisite that would make it intelligible.

**Repair:** hide optional limits, not the current task's essential model. Show a concrete source pattern → merged channel → default/step exception → output example. Introduce relative and absolute pitch through a listening comparison.

### 9. Medium: quick reference and search find titles better than answers

**Where:** [Quick reference](https://karen-diy-clarity-status.trycloudflare.com/manual/#quick); `book.js` search handler.

Quick reference renders all feature control rows in one page: approximately **20,658 CSS pixels** high at 1440 × 1000, without a local index or filter.

Search indexes titles, summaries, prose and controls, but **not detail text, detail titles, recipes or scene captions**. Content in those fields can therefore be invisible unless a query occurs elsewhere. Results have no matching excerpt or local destination for the actual explanation. Dense view is on feature Controls sections, not an obvious quick-reference toolbar.

**Impact:** experts must know which page owns an answer or scan a very long page.

**Repair:** filter by editor/task/control, index details and recipes, and return the matching phrase and subsection link. Preserve compact control/result pairs.

### 10. Medium: presentation wastes limited space beside an instrument

**Where:** Masks at 390 × 844; `manual.css`; recipe renderer.

In the checked mobile state, interaction began around **1,405 px** down the document and Controls around **2,802 px**. Total page height was roughly **6,303 px**. Navigation is static and scrolls away. Grid pads measured approximately **14.6 CSS px** wide: useful as an image, demanding as practice targets.

The opening is clean, but large introductory text and child tiles defer action. Numbered recipes are rendered as a single paragraph: the browser displays “1. … 2. … 3. …” inline rather than separate steps.

**Impact:** following along on a phone requires repeated scrolling between meaning, action and result.

**Repair:** add a compact local outline and Try it/Controls links, use ordered lists and offer an enlarged grid or accessible alternate interaction. Do not depend on 128 simultaneously tiny tap targets.

### 11. Medium: verification wording sometimes substitutes for result wording

**Where:** player captions/results; [LFOs and Modulation](https://karen-diy-clarity-status.trycloudflare.com/manual/#lfos-and-modulation).

For object-valued assertions, the player often falls back to “Verified captured interaction · screen and grid shown together.” This reports that something was checked, not what the musician should notice.

A visible modulation detail says “M-MOD-004 checks positive, negative and cleared CC modulation with step locks.” STYLE.md says to keep case names out of ordinary player instructions. The standard is sensible; publication is inconsistent.

**Impact:** confidence language looks like explanation while leaving the reader unable to predict the result.

**Repair:** explain the musical change first. Put case IDs, raw MIDI, boundary details and capture identities in the evidence panel. Preserve them all there.

## What works and should be retained

1. **Restrained, literal language.** “Entering a Melody” and “Set channel and step note masks” are useful titles.
2. **Concrete first-loop instructions.** CH01, coordinates, range, Note/Vel/Len, playback and save are a strong starting pattern.
3. **A compact object model.** Getting Started's pattern/channel/scale/song explanation needs better placement and illustration, not a much longer theory chapter.
4. **Useful scope teaching in Masks.** `mask-precedence/release-one` distinguishes displayed channel G3 from retained C4. This observation transfers to real use.
5. **Sensible no-sound diagnosis.** Transport → channel/mute → range/merge → masks → output is a useful order.
6. **Real screen/grid captures and immutable evidence.** Preserve this foundation against attractive but false demonstrations.
7. **Stable routes, native buttons, focus styling, themes and reduced-motion handling.** Useful foundations, although this review does not establish full accessibility compliance.
8. **Honest recording-scope disclosures.** Keep them while fixing mismatches.

The site should not be discarded. Its teaching architecture needs to catch up with its evidence architecture.

## Proposed narrative information architecture

Give learning and lookup distinct entry points, linked to the same feature definitions and evidence.

### A. Start here: make one small piece

A numbered route visible from the homepage and every course page:

1. **Meet Mosaic:** pattern → channel → sound, coordinates and K/E notation.
2. **Choose your sound path:** internal norns or an existing MIDI instrument, one complete route at a time.
3. **Make four notes:** an empty-project loop, exact audible target, stop and save.
4. **Turn it into a phrase:** rhythm and relative notes; explicitly clear an inherited mask that would hide the edit.
5. **Give the phrase an ending:** the Masks lesson below.
6. **Add a second part:** bass/lead, explicit routing, register and musical role.
7. **Change harmony:** two scale slots; distinguish editing from applying.
8. **Add movement:** one accent/parameter lock, then an optional slide.
9. **Arrange two sections:** copy gesture, purposeful variation, length, repeats and transition.
10. **Save, reload and perform:** restore the arrangement; link stop/panic and no-sound recovery.

Every chapter states its goal, incoming state, changes, expected result, undo/recovery and next destination. Its final state is the next chapter's starting state.

### B. Make a change: task guides

Add a pickup; combine two rhythms; record a melody; thicken a chord; create a gradual change; combine loop lengths; prepare a verse/chorus transition. Each starts from explicit prerequisites and supports independent entry.

### C. Reference: the instrument's structure

An expandable hierarchy: Pattern; Channel (routing, assignment, merge, Masks, length/clock); Scale; Song; locks/modulation; projects/options; MIDI/n.b./hardware integration. Each feature starts with route/effect, then controls, defaults, interactions and recovery. Developer material belongs outside the beginner progression.

### D. Quick controls and troubleshooting

Filtered control index, editor/gesture lookup, glossary and diagnostic tasks. Experts can stay here; learners arrive through contextual recovery links.

### E. Musical examples

A small set of complete pieces with exact recordings, project/voice manifests, preparation paths and deliberate variations. Reuse a piece across lessons only where its state actually continues.

Persistent orientation should read **Learn → Make a piece → 5. Give the phrase an ending**, with chapter list and Previous/Next. An independently entered reference page should read **Reference → Channel → Masks**.

## Worked redesign: Masks as a musical lesson

### Give a repeating phrase an answering note

**Status:** proposed teaching design, not a claim that its new captures/audio already exist. Execute and verify the exact route through native input before publication. Reuse semantic evidence where applicable and add missing lesson-specific assertions. Never relabel an old run as proof of this new sequence.

**Goal:** start with four identical notes on the beat, raise the last note to lead into the next loop, give it lighter emphasis, compare and deliberately remove it. Learn defaults, exceptions and clearing through a musical decision.

**Visible prerequisites:**

- A saved first-loop project with a supported audible output on channel 1, Pattern 1 assigned, playback stopped and Record off.
- Show channel, rate, range, applied scale, Note/Vel/Len defaults and existing overrides.
- Explicitly extend the range to 16 steps and place attacks at 1, 5, 9 and 13. Set sixteenth-note rate and 90 BPM through documented controls. This preparation belongs to the lesson; it is not an invisible fixture.
- Use C major, channel Note MIDI 60 (Masks C3), velocity 80, half-step length, no step overrides or chords.
- Provide complete preparation operations or a verified resume project with an equally complete manual preparation route.

Before controls, play exact original/target clips: C–C–C–C versus C–C–C–D. A strip marks steps 1/5/9/13. Explain that the beats stay the same while the ending changes.

### Stage 1: establish the default

1. Press Channel at (3,8); show CH01.
2. Turn E1 to Channel tasks; pause with the task list visible.
3. Select Masks with E2, press K3; pause on Masks.
4. Select Note with E2, with no step held; show C3/MIDI 60.
5. Play two complete bars, then stop.

**Visible:** channel C3 and no held step.  
**Audible:** four equal C notes on four beats.  
**Meaning:** the default supplies each step unless the step has its own value.

Later lessons can abbreviate a learned Open Masks operation. Its first encounter should expose intermediate screens.

### Stage 2: make the last beat answer

1. Ask for a prediction: “We change only step 13. Which other notes should change?”
2. Hold step 13 at (13,4); pause with held-step header.
3. While holding, turn E3 until D3/MIDI 62.
4. Release; pause as the channel display returns to C3.
5. Play two bars and offer exact before/after comparison.

**Visible:** D3 while held, C3 after release.  
**Audible:** C–C–C–D.  
**Meaning:** the common pitch is still C; one step replaces it. Returning to C3 on screen does not undo D3.

Practice must require hold/edit/release in order. Demonstration should clearly say it is showing those actions.

### Stage 3: shape the answer's emphasis

1. Select Vel with no step held; show default 80.
2. Hold step 13, turn E3 to 50, release.
3. Play two bars.

**Result:** the last D is quieter; pitch and timing stay the same.  
**Meaning:** mask attributes can change independently.

Keep exact velocities beside the note strip. Probability is an optional later lesson, not a boundary test inserted here.

### Stage 4: predict a changed default

1. Without holding a step, select Note and set channel G3/MIDI 67.
2. Before playing, show expected G–G–G–D.
3. Play two bars and compare with C–C–C–D.
4. Return the channel default to C3 through the native control.

**Meaning:** the default changes unmasked steps; the ending retains its own pitch and velocity. State the exact resulting project before continuing.

### Stage 5: remove the exception intentionally

1. Hold step 13 and press K2; release.
2. Play two bars.

**Result:** C–C–C–C, all at velocity 80. Both exceptions are gone.  
**Meaning:** K2 clears **all mask attributes of the held step**, not merely the selected field.

This consequence matters because the reader has created two attributes. Show both note and velocity before/after.

### Stage 6: keep a musical choice

Re-enter D3 at velocity 50, or select E3/MIDI 64 as an explicit optional variation. Save a new named version. Identify exactly which variant is recorded and carried into the next lesson.

End by connecting the skill: changing one note without rewriting the rhythm. Continue to a second part, or open Masks reference for chords, trig masks and quantisation.

### Retained verification

Keep existing precedence, expression, chord, trig, clear-scope, boundary and failure evidence. Six teaching stages do not need to equal six behaviour cases.

For this new lesson retain assertions for exact two-cycle notes/velocities, positions 1/5/9/13, durations, output, held-step/channel displays, preserved rhythm, clearing both attributes, named save/load, clean stop and note release. Cite manual semantics and maintain required applicable timing lanes and source identities.

Several teaching microsteps may map to one retained checkpoint; one stage may map to multiple assertions. Capture missing intermediate screens instead of manufacturing them or implying a final frame proves the whole gesture.

The reader sees the musical consequence first, evidence second.

## Repair order

1. **Fix first-sound → phrase continuity and expose the actual course in Start here.**
2. **Build one complete musical Masks lesson.** Validate its exact project, recording and ordered physical operations before multiplying the pattern across 133 pages.
3. **Fix replay semantics/granularity.** Separate demonstration and practice; do not accept any constituent control as completion of a compound gesture.
4. **Finish one continuous loop-to-two-section arrangement**, preserving chapter states and save/reload continuity.
5. **Repair navigation/lookup:** active hierarchy, linked breadcrumbs, local outline, contextual search and filtered quick reference.
6. **Align cookbook recordings with the recipes they teach.** Put other performances in a labelled inspiration section.
7. **Apply the lesson pattern selectively.** An advanced option can use a precise table and short comparison; not every parameter needs a full course.
8. **Then expand interactive coverage.** More scenes in the current structure increase volume faster than teaching value.

## Acceptance criteria for the next design

These are concrete design and automated-verification criteria. Manual clicking or listening is not required acceptance and cannot replace native semantic evidence.

### Navigation

- Start here provides the ordered first-sound-to-saved-arrangement route; First Loop and No Sound are visible at its entry.
- Course pages declare prerequisites, position, previous/next destinations and outgoing state.
- Feature routes identify the active parent; breadcrumbs navigate to real parents.
- Quick reference filters by editor/task/control; search includes details/recipes with matching excerpts.
- Automated link checks cover intended course order, subsection destinations and browser back navigation.

### Teaching integrity

- One supplied project continues through the beginner course without silent fixture replacement.
- Every changing instruction has native inputs and an observable result. Critical compound gestures expose hold/edit/release.
- Each musical lesson includes a specific goal, exact state, small actions, immediate consequences, recovery and an extension.
- The first-loop Note default is explicitly reconciled before relative pattern notes.
- Target audio matches listed notes, rhythm, velocities, voices and arrangement. Suggested variations remain separately identified.
- Finished song means the promised arrangement is built, transitions, saves and reloads; an outline is insufficient.

### Interaction and presentation

- Practice advances on the taught ordered action with meaningful hold state; replay identifies itself as demonstration.
- Current instruction, display and highlighted target refer to the same action phase.
- Independent examples declare their fresh state before the first checkpoint.
- Recipes use real lists; essential prerequisites precede the player.
- Mobile users can reach controls/current step without traversing the full introduction; grid practice has usable targets or an accessible alternative.
- Outcomes explain the change; case IDs and raw proof stay in the evidence panel.

### Evidence preservation

- Keep raw captures, assertions, seeds, baseline failures, timing lanes and source hashes intact.
- New captures cite applicable README semantics or explicit characterisations and run through the actual application's public input.
- Verify chapter-to-chapter continuity, not just separately prepared chapter fixtures.
- Keep audio, controlled-time, real-time and hardware claims separately identified.
- Rebuild publication data and check its manifest against delivered sources. A passing candidate must not overwrite or relabel baseline evidence.

## Late status note

After the sampled review, the root agent reported additional edits: cosmetic sidebar wording/logo changes, an authoring correction to clear first-loop defaults and remove the original trigs before pattern editing, and an authoring alignment of Small-hours with its actual trio. I have **not independently recaptured or rechecked those corrections**. The root reported that the served generated book still retained the reviewed material at that point.

The findings above deliberately preserve the reviewed reader experience and its hashes. Corrected authoring should be credited once built and checked; it does not retroactively change what this snapshot showed. Cosmetic edits do not alter the substantive teaching assessment.

## Final recommendation

Treat the current site as a **reference-and-capture foundation awaiting a teaching pass**. The highest-value next work is one complete, musically motivated, state-consistent lesson and a visible course path that proves the approach, not another batch of test-derived scenes.

Preserve the hard-won evidence. Change what the reader is asked to do with it.
