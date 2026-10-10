# Astra review closure checklist

**Created:** 3 October 2026  
**Worktree:** `/home/andy/mosaic-manual-1.4.0`  
**Baseline review:** [ADVERSARIAL_REVIEW.md](ADVERSARIAL_REVIEW.md)  
**Purpose:** actionable acceptance for every substantive review finding, alongside the authorized vertical-list UI conversion.

## Closure rules

A finding closes only when its relevant authoring, application behaviour, generated publication and served presentation agree. A prose edit, attached test ID, passing model test or newly generated screenshot alone is insufficient.

Use these states:

- **Open:** the defect remains in the delivered candidate or evidence is missing.
- **Authored:** an inspected source change addresses part of the finding, but delivered/behaviour acceptance is pending.
- **Candidate:** built changes and their evidence are available for independent review.
- **Closed:** the exact served candidate passed the acceptance below, with receipt paths and source identity recorded.
- **Blocked:** identify the unmet external dependency; do not call the finding closed.

A finding may have authored subitems while its overall state remains Open. Every checkbox below is initially unchecked. Do not infer acceptance from this checklist's existence.

For each closure, record: candidate Git revision plus working-tree/source-manifest hash; generated-book and served-byte hashes; feature/scene routes; applicable native run IDs and real/controlled lane reports; browser report and captures; limitations; independent review verdict. Preserve the original review and baseline failures. Append a dated closure record; do not rewrite the historical finding to match the new candidate.

**This pass launched no native application and modified no implementation, prose source, tests or evidence.** It only inspected the current source/served data and created this checklist. Native and browser acceptance remain assigned to their owners.

## Ownership

| Short name | Accountable task | Scope |
|---|---|---|
| Root | `/root` | Integration, publication identity, complete campaign/aggregate, final delivery and unresolved ownership |
| Navigation | `/root/manual_narrative_navigation` | Website IA, routes, active hierarchy, search, quick reference, responsive navigation |
| Teaching | `/root/manual_musical_teaching` | Musical course, scene pedagogy, prerequisites, project continuity, recipe/audio alignment |
| UI | `/root/vertical_list_implementation` | Actual Mosaic list UI, control semantics, renderer/spec/adapters |
| Behaviour | `/root/vertical_list_behaviour` | Red/green native acceptance, timing lanes, visible/MIDI/persistence oracles |
| Reference | `/root/vertical_list_manual` | README, cheat sheet, reference prose and UI illustrations |
| Astra | `/root/astra_manual_review` | Independent served-candidate rereview and closure verdict; no native launches in this assignment |

Teaching owns the reader-facing replay contract; Navigation coordinates shared edits to `manual/manual.js`, `book.js` and CSS. Root resolves file ownership before concurrent edits. Behaviour owns application evidence, not the decision that a lesson is comprehensible.

## Initial independent inspection — 14:50:51 UTC

Observed HEAD remains `69df623e06efd6721e1cc53e961a1dd845d2a48c`; substantial working-tree changes exist.

| Artifact | SHA-256 at inspection |
|---|---|
| Original adversarial review | `8b75da934867f6abfb803a143fd7c1c62287d5c90620e8433561dbb52a2cd155` |
| Local and HTTP-served `manual/generated/book.json` | `43f5bef85ed07658f1b917ea1a5c0b65fbcbb3ca8c6c238ecf464529e63ee902` |
| `manual/book.js` | `954bbf094184ca55fcb038e07148ac78d873c4105e59229479eecd73594b1aa2` |
| `manual/manual.js` | `f80348fbaccfb8a03db8c2bc4c8117c5786a115f2e556f5b8a02b55221097a4d` |
| `manual/manual.css` | `12ea8127391d7ec74422da49f7083e8fa416f2d889d4ab03c1c66f90e7f215f3` |
| `manual/features/tutorials.yaml` | `62d80cb05fcea36540c1ca9c017cd3e172ea9b1bff44d8dc4f376694713f549b` |
| `manual/features/cookbook.yaml` | `fc8b652943820feeaaa03d97750e46756938904562c6ee8bb30db68c474713ab` |
| `manual/features/masks.yaml` | `4ee9691bf731f934bba71c86f62c91ec0eab1526f3991449641de0cff70b9a0d` |

Verified source improvements: Build-a-phrase explicitly clears channel Note/Vel/Len to X and removes original attacks 2–4; its native-gap wording explicitly admits that the continuous handoff still awaits capture. Small-hours now specifies unique Oilcan/Polyperc/Doubledecker assignments and concrete percussion/bass/chord parts.

Neither improvement is in the HTTP-served book inspected here. Thus F01 and one part of F06 are **Authored**, not closed. Build-a-phrase still leaves second-channel setup, variation and song construction at outline level. Current replay still matches any constituent input; current search still omits detail/recipe fields; quick reference and active-hierarchy code remain as reviewed. The changed sidebar wording is present in source and does not close any substantive finding.

## Finding register

| ID | Original finding | Priority | Owner | Initial state |
|---|---|---|---|---|
| F01 | First-loop → phrase state conflict | Critical | Teaching + Behaviour | Open; authored correction inspected |
| F02 | Contents hide the learning narrative | High | Navigation + Teaching | Open |
| F03 | Replay teaches the wrong gesture granularity | High | Teaching + Navigation | Open |
| F04 | Finished-song instruction is an outline | High | Teaching + Behaviour | Open |
| F05 | Scene/fixture changes are implicit | High | Teaching + Navigation | Open |
| F06 | Recipes, scenes and recordings disagree | High | Teaching + Root | Open; Small-hours source improved |
| F07 | Weak persistent orientation/hierarchy | High | Navigation | Open |
| F08 | Essential prerequisites follow the player | Medium-high | Teaching + Reference | Open |
| F09 | Search and quick reference do not find answers efficiently | Medium | Navigation | Open |
| F10 | Mobile layout and recipe rendering obstruct use | Medium | Navigation | Open |
| F11 | Verification wording substitutes for musical result | Medium | Teaching + Reference | Open |

## Objective closure by finding

### F01 — Continue the actual first-loop project

**Targets:** `manual/features/tutorials.yaml`; new/updated lesson scene authoring; `tests/behaviour/composition_workflow.py` or a dedicated public-input lesson case; generated book. Routes: `#first-sound`, `#build-a-phrase`.

- [ ] The served continuation names the retained channel defaults and the exact operations needed to restore pattern inheritance. It distinguishes clearing defaults from K1+K2 clearing step masks.
- [ ] A continuous native case starts with the project produced by the first-loop instructions, performs the continuation through public input and proves the intended rhythm and distinct relative pitches audibly/perceptibly through exact MIDI. No replacement fixture or hidden state repair may bridge the lessons.
- [ ] Screen/grid assertions confirm the relevant scope and X/default state; the phrase has the specified attack positions and no leftover attacks 2–4.
- [ ] Applicable real-time and controlled-time evidence retain exact source identities, note releases and clean session exit. Existing regression failures remain preserved.
- [ ] The served instructions and attached scene describe the same resulting phrase and vertical UI route.

**Reject closure if:** only the new clearing sentence or an unrelated independently seeded composition test passes.

### F02 — Put the course at the front door

**Targets:** `manual/book.yaml`, `manual/book.js home()`, course metadata/source and browser tests. Routes: `#home`, `#learn`, `#getting-started`, `#workflow`.

- [ ] Start here exposes First Loop, No Sound and a visibly ordered route through phrase, parts, harmony, movement, arrangement and save/reload.
- [ ] Setup offers complete internal-sound and MIDI paths without requiring a custom mapping for basic MIDI output.
- [ ] Workflows opens actionable musical tasks; Reference retains feature lookup. Labels distinguish overview, lesson and reference.
- [ ] Every course page declares prerequisite/incoming state, lesson position, next/previous destination and outgoing state.
- [ ] Browser route checks traverse the intended links from the landing page and back, including direct links and reload. A reader need not guess a hidden hash or search for the course.

**Reject closure if:** new tiles exist but lead to disconnected reference pages or an incomplete narrative.

### F03 — Make replay actions truthful

**Targets:** `manual/manual.js gesture()/render()`, `index.html`, lesson/scene schemas and browser interaction tests. Reference case: `#masks/mask-precedence/step-one`.

- [ ] The UI clearly chooses demonstration or practice. Demonstration is labelled replay and uses explicit advance controls; it does not falsely imply a compound native gesture was performed.
- [ ] If hardware practice remains, hold → edit → release is required in order. Clicking E3 alone must not complete a hold-step-plus-turn lesson. Wrong controls/directions and premature release have defined, tested feedback.
- [ ] Current instruction, highlighted target and shown before/after state agree about the action phase.
- [ ] Multi-operation routes expose the screens/actions a learner must perform; test setup batches are not silently presented as one simple gesture. No arbitrary input-count limit substitutes for this semantic check.
- [ ] Back, reset, scene changes, autoplay, keyboard input and audio interruption preserve coherent player state; no phantom held key persists.

**Reject closure if:** only the wording changes while any matching input still jumps the whole bundle, or if practice is removed without offering a clear useful demonstration.

### F04 — Deliver a reproducible finished arrangement

**Targets:** tutorials/workflow/cookbook sources, lesson manifest and native workflow coverage. Routes: `#build-a-phrase`, `#song-composition`, `#keep-your-work`.

- [ ] One required path specifies actual channels/outputs, rhythms/pitches, ranges/rates, scale, variation, slot-copy gesture, repeats and global length. Optional choices occur after a working result.
- [ ] The course creates at least the promised two-section arrangement with an intentional audible contrast and a specified transition point.
- [ ] A continuous native public-input case follows the authored course, observes emitted arrangement and visible slot/selection feedback, saves by name, reloads and reproduces the intended result.
- [ ] The exact arrangement has a matching target recording where the lesson promises audio; the reader can compare the part they are building.
- [ ] No required instruction remains merely “add a channel,” “make a motif,” “copy a slot” or “check settings” without the specific control route/values available at that point.

**Reject closure if:** “finished song” is satisfied by a general workflow overview or a separately seeded two-channel test.

### F05 — Declare resets and maintain continuity

**Targets:** scene/lesson start-state metadata, feature sources, `manual/manual.js`, `book.js`. Sample: Masks note → expression → chord → trig scenes; Getting Started scene ordering.

- [ ] Every independent example visibly declares that it starts fresh and identifies output, channel, range/rate, notes, defaults, scale, transport and existing exceptions relevant to its outcome.
- [ ] Course scenes preserve the same state or explicitly teach the transition. Switching scenes cannot silently change a four-step G-based phrase to a different C-based/eight-step fixture.
- [ ] The first visible beginner example matches the current lesson; masks/merge boundary checks do not precede first sound without an explicit purpose.
- [ ] Browser checks verify state summaries update on selection/deep link and cannot retain another scene's caption/audio.
- [ ] Evidence maps each learning stage to its actual setup and immutable capture without renaming an unrelated test fixture as the learner's project.

### F06 — Match the music to the lesson

**Targets:** `manual/features/cookbook.yaml`, workflow sources, `manual/audio-scenes.yaml`, `manual/audio/`, audio builder/validation and lesson scenes.

- [ ] Small-hours title, parts, unique n.b. players, note/velocity/gate/rhythm manifest, fourth-bar change and recording all agree. The new source must be rebuilt and checked.
- [ ] Pocket-rhythm provides the actual quiet step-12 → strong step-13 comparison or clearly labels unrelated audio as inspiration outside the lesson result. Probability variation has deterministic evidence/invariants and an explicit listening goal.
- [ ] Tilting-harmony shows and records the taught C/D scale-slot application, or supplies an equally coherent matched lesson; MIDI-root changes are not represented as proof of scale-slot operation.
- [ ] Modulation teaches a musically interpretable change with defined source/target/depth/rate before presenting MIDI127/full-depth boundaries as advanced reference.
- [ ] Recording manifests, exact sequencer inputs and machine-verifiable PCM/output evidence agree. UI A/B playback identifies which clip/state is playing and does not reuse an unrelated soundtrack as the answer.
- [ ] Suggested variations and physical-output limitations remain labelled; scope disclaimers do not excuse a mismatch in the required lesson.

**Reject closure if:** only the recording title is renamed or existing scope warnings are expanded.

### F07 — Maintain orientation on every route

**Targets:** `manual/book.js`, `book.yaml`, parent/course metadata, CSS and browser navigation coverage.

- [ ] Feature pages visibly select their containing top-level section and current chapter.
- [ ] Breadcrumb parents are functional links; current page and route context are accessible to keyboard/screen-reader navigation.
- [ ] Reference preserves hierarchy and siblings rather than presenting parents and small options as an undifferentiated category dump.
- [ ] Course order is separate from reference ancestry. Options/modulation/hardware integration are not misleadingly nested under Save and Load.
- [ ] Direct links, legacy aliases, scene links, refresh and browser back preserve orientation at desktop and mobile widths.

### F08 — Teach prerequisites before use

**Targets:** learning/Mask/scale/reference sources, glossary/concept material and page section ordering.

- [ ] Before the first relevant action, show required starting state, current scope, X versus zero, defaults versus exceptions and exact controls.
- [ ] A concrete pattern → merge → mask → output example lets a reader predict an altered note without teaching all advanced options first.
- [ ] Relative scale degree versus absolute MIDI pitch, Masks octave labels and edit-versus-apply are introduced where used; necessary terms link to concise definitions.
- [ ] Optional constraints may be collapsed, but information needed to perform the visible task is not hidden below its player.
- [ ] Vertical-list terminology matches actual row/focus/scope feedback. Harmony includes the actual select/edit/apply route instead of an unexplained “edit root and scale.”

### F09 — Find an answer rather than a page title

**Targets:** `manual/book.js` search/quick route, generated subsection anchors and browser tests.

- [ ] Search indexes details, recipes and scene captions as well as title/prose/control rows. Use real queries whose sole occurrence is in each formerly excluded field.
- [ ] Results show the matching phrase and navigate to the actual subsection/scene; no-match and empty search work.
- [ ] Quick reference filters by editor/task/control and provides grouping/index plus visible density control where offered.
- [ ] Tests retrieve answers such as Masks inheritance/clearing and octave convention without requiring the reader to know the containing page name.
- [ ] Keyboard navigation, small-width layout and direct links work with filtered results.

### F10 — Make follow-along use practical on small screens

**Targets:** `manual/manual.css`, `book.js`, `manual.js`, `index.html`, representative browser captures.

- [ ] At 390 × 844 and representative tablet/desktop widths, a visible local navigation control reaches the lesson/current action and Controls directly; essential orientation remains recoverable without scrolling to page top.
- [ ] Numbered recipe operations render as semantic ordered lists, with each action separately scannable.
- [ ] Practice offers usable tap targets, enlarged grid or an accessible alternate action control; the user need not hit a 14.6px pad to progress.
- [ ] Current caption, control/action and result can be understood without chasing unrelated sections. Page-height reduction alone is not acceptance.
- [ ] Focus visibility, zoom/reflow, theme and reduced-motion checks retain controls/text without overlap or loss. Capture representative actual served pages.

### F11 — Explain results; keep evidence inspectable

**Targets:** player outcome renderer, scene captions, feature detail prose, STYLE compliance and caption audits.

- [ ] Every required lesson step says what visibly/audibly changed and why it matters, including no-change/default-restoration results.
- [ ] Generic “Verified captured interaction” does not substitute for the step's outcome.
- [ ] Case IDs/raw assertions belong in the expandable evidence panel, not ordinary musician instructions; inspect modulation and representative boundary scenes.
- [ ] Exact captures, semantic assertions, citations, immutable run/source IDs and limitations remain accessible.
- [ ] Caption/compiled-content checks run on the served candidate; a source-only wording audit is insufficient.

## Cross-cutting gates

### V — Vertical UI and documentation agree

**Owners:** UI + Behaviour + Reference, integrated by Root.

**Targets:** `lib/ui_render.lua`, live router/adapters, `docs/ui-reimplementation/spec.json` and its generator; README/cheat sheet/reference sources; durable `images/`; affected behaviour/manual scene publications. [NORNS-UI-ALIGNMENT.md](NORNS-UI-ALIGNMENT.md) is the scope inventory, not evidence of implementation.

- [ ] Selection/editing screens in agreed inventory use stable readable vertical rows, visible selection, scroll position and scope; musical diagrams/read-only dashboards retain their purpose.
- [ ] Exact values, long labels, negative/fractional values, X/zero/None/Mixed, sparse/empty domains and multiple held steps remain understandable at 128×64, with motion on/off.
- [ ] E/K and grid scope, live edits versus drafts, Apply/Cancel, masks clearing, assignment, slides and undo/redo retain their explicit contracts. Do not silently universalize K2 Back or K3 Apply.
- [ ] Source-generated runtime/spec artifacts are regenerated from the authority, not hand-patched. Meaningful new presentation regressions fail on preserved old UI and pass on candidate.
- [ ] Relevant unit/integration, emulator public-input real/controlled acceptance and existing full Lua suite pass at settled candidate. Record inapplicable-lane reasons; do not claim hardware accuracy.
- [ ] Every changed manual image/scene is recaptured against the candidate UI; old tile/carousel captures are not presented as current. README and cheat sheet controls stay consistent. Preserve historical assets/identities.

### P — Freeze and publish the actual candidate

**Owner:** Root, with evidence/publication support.

- [ ] Freeze one identifiable candidate for final review: application sources, authoring, generated data, JS/CSS, audio and schema manifests.
- [ ] Verify HTTP-served bytes match that build and embedded authoring/source hashes match actual sources. Resolve the currently observed stale-book condition.
- [ ] Inventory every required page/scene/control; incomplete native gaps remain explicit and block completion where within the authorized scope. Do not let aggregate counts stand for coverage.
- [ ] Preserve baseline failures and source identity; never overwrite/relabel them with a passing candidate.
- [ ] Required behaviour campaign reports identify selected cases and keep shard `complete_regression_run` false; only a valid aggregate covering the required inventory can establish full campaign coverage.
- [ ] Native runs leave no sessions, held keys, active notes or modified user projects. Root reports remaining failures accurately rather than replacing oracles.
- [ ] Confirm the authoritative README/manual migration and cheat-sheet relationship; current manual claims cannot conflict with the repository's declared source of truth.

### R — Independent served-candidate rereview

**Owner:** Astra, after Root provides frozen candidate and receipt bundle.

- [ ] Re-run the original newcomer and expert journeys against exact served pages; sample setup, Masks, merge, rhythm, harmony, melody, song, modulation, cookbook, options and quick reference.
- [ ] Review the continuous musical lesson with its true prerequisites, actions, display states and matching audio manifest; do not infer pedagogy from the presence of passing tests.
- [ ] Revisit all eleven findings, recording Closed/Open with concrete routes, excerpts/actions and receipt links.
- [ ] Score the same seven dimensions using the original definitions/anchors and explain any changes. A requested score is not a test target.
- [ ] Preserve limitations: no unsupported claim of exhaustive page coverage, human study or physical-norns equivalence. Manual clicking/listening is not required acceptance.

## Closure record template

For each finding/gate append:

- ID and date:
- Owner:
- Candidate revision + working-tree manifest:
- Served book/JS/CSS/audio identity:
- Changed source targets:
- Exact reviewed routes and incoming/outgoing project state:
- Native/browser/audio receipts and applicable timing lanes:
- Observable musical/visible result:
- Remaining limitation:
- Independent verdict and reason:

## Sequencing and handoff

First resolve F01 and the course contract, then stabilize the vertical UI and one complete Masks lesson. Build/verify that lesson before multiplying it. Finish arrangement and exact audio matching, then navigation/lookup/mobile refinements. Rebuild/reconcile the whole publication and supply the frozen candidate for rereview.

Some work can proceed concurrently, but final scene capture depends on stable native UI, and closure depends on the actual served build. More scenes, nicer vertical menus or better prose in isolation do not close the teaching findings.
