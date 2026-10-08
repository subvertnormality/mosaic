# Candidate07 adversarial reader recheck — 8 October 2026

**Conditional failure.** The original R1–R5 findings and the smaller corrections are closed in this installed candidate. One remaining prerequisite defect in the separate Decay endpoint exercise keeps flow and interactive-example usefulness below 8. This report preserves that result; a later correction must receive its own scoped receipt.

## Identity and scope

Actual reader: http://localhost:8785/manual/. Authoritative source: `/home/andy/mosaic-manual-1.4.0`; the stale Windows checkout was not used as reader authority.

Independently fetched served SHA-256 values:

| Asset | SHA-256 |
|---|---|
| reader-index.json | 73dc1ddb8952ca590cb9d670ee3a145ee460a68ec27f3259c1a08e28283323ca |
| book.js | a80f66aee6f4b5cc3c98fb38b0ff39e027be8d178dba8c29e10f5c92661bbeb1 |
| manual.js | 49a88a9be93f58571b43fdb30e445bffb0bac4340941726a5488577ea21b21e4 |
| manual.css | 123afe7d35beb8e827089b16518f03ccdfdcc000c33916e64b8f0002eb2caa4a |
| index.html | c4386498a8f224507ff0316958078932e58865640ed91931afb9945599839b87 |
| cheat_sheet.html | 6c169304bd791673876479649ceb720e161b7a6bee2a570d074e0f082d251695 |

Inspected root installation receipt identifies compiled book `38beead5d88faa3a5aa1a5a0fc27c25796308c4d84bd831060035fe5085ef89f` and authoring `9d5e81b8776366aae0f9460d59bfe3d5f0d02e337d3188e965a143491d88e053`. Original receipt `/home/andy/mosaic-manual-build-operators/combined-teaching-install-20261008-04/POSTINSTALL-READER-PINS.json` has root-reported SHA `c8b434bcada1bcb2a2b302503ac80c3aa70b7c62d91b15ca5ca1f314cba7ed2f`; the local text copy is not claimed byte-identical. The served index still matched at review end.

The review read the bounded public prose inventory of 133 features, the affected recipes and expanded details in whole-page context, and all ten course openings. Browser coverage comprises 116 route/viewport pairs at 1440 and 390 pixels, plus actual interactive journeys. Evidence is in `collection.json`, `browser-observations.json`, `workflow-observations.json`, `interaction-observations.json`, `parity.json`, and the corresponding screenshots. Prior failed whole-manual review is preserved unchanged in `../final-whole-manual-astra-review-20261008-01/`.

## Seven independent scores

| Criterion | Score | Reason |
|---|---:|---|
| Readability | 8 | The revised prose speaks to the player; expanded reference panels no longer expose the identified audit and build commentary. Text wraps cleanly at both widths. |
| Comprehensibility | 8 | Pattern assignment, the four visible grid rows, merge preparation and relevant device prerequisites now precede the actions that need them. |
| Flow | 7 | The endpoint exercise overwrites the Decay parameter assignment immediately before instructing the reader to edit Decay. |
| Understandability | 8 | Pattern inheritance, musical comparisons, Harmony starting points and independent examples are explained with meaningful visible results. |
| User-friendliness | 8 | Search, keyboard activation, result focus, navigation, persistent hardware layout and enlarged-grid scrolling work in the observed journeys. |
| Usefulness of interactive examples | 7 | Captured walkthroughs and musical comparisons remain useful, but following the endpoint recipe literally cannot reach its named parameter without an unstated repair. |
| Cohesion | 8 | Course continuity, separate-project recipes and the relationship to recordings are now consistently identified. |

## Open finding C07-1 — restore Decay assignment after copying the plain slot

**Blocking; exact field:** `features[id=locks].recipes[4].text`, paragraph beginning “Separate endpoint practice”. Route `#locks`, fifth musical recipe. Screenshots `decay-blocker-1440.png` and `decay-blocker-390.png` show the actual rendered paragraph.

It says: “Copy slot 1 to slot 2 and set its length to 32. Tap slot 2 before editing its locks. In slot 2, hold step 1 and turn E3 anticlockwise until the displayed Decay reaches its 0.1 s minimum…”

The preceding relative-turn exercise assigned Decay only in Song slot 2. This endpoint exercise copies the plain slot 1 over slot 2. Song-slot copy replaces the channel's parameter assignments as well as its locks, so the instruction loses the assignment it requires. Selecting slot 2 does not restore it. This is a teaching prerequisite defect, not a demand for new native evidence or a browser instrument.

Root independently confirmed the bounded implementation facts: `lib/models/program.lua:84–100` deep-copies the source Song pattern including channels; comments at 91–94 explicitly describe replacing every channel's locks and assignments. `get_selected_channel` at 154–165 selects the current Song slot's channel, and `param_lock_assignments.lua` updates that channel's `trig_lock_params[index]`. These are root-confirmed semantics, not a newly executed native test in this review.

**Minimum correction:** after copying and selecting slot 2, reopen Channel tasks → Trig params and assign Decay to parameter slot 1 before holding step 1. Include the existing E2/K2/E3/K3/K2 navigation, or an equally explicit established instruction. Preserve the distinction between the relative-turn recording and this separate absolute-endpoint practice.

## Nonblocking wording observation C07-N1

Small Hours Bass and Chord intermediate predictions say bars 2–4 remain silent. The previous parts have already been completed, so this could mean the whole mix rather than the newly added part. Name the bass or chord part and say the preceding parts continue. This does not independently lower a score, but is a useful bounded clarification.

## Original correction closure

| Finding | Current evidence and status |
|---|---|
| R1 — missing pattern assignments in empty projects | Closed. Pocket Rhythm and Tilting Harmony explicitly assign the intended pattern to the intended channel before the pattern is played; the related slots and Masks preparations also name both assignments. |
| R2 — incorrect 64-step grid/paging | Closed. Small Hours, Pocket Rhythm and Masks describe rows 4–7 and correct coordinates. Trig steps 44 and 60 are (12,6) and (12,7); Note/Velocity editing remains distinguished from the full Trig grid. |
| R3 — merge comparison preparation/copy order | Closed. Both source patterns and Average are prepared in Song 1 before copying once to Song 2 and choosing Higher; the comparison returns to slot 1 before playback. |
| R4 — intermediate listening predictions | Closed as a blocker. Percussion predicts the first populated bar and the remaining silence before filling later bars; loops alignment acknowledges the earlier pitch coincidence and the later phase alignment. Bass/Chord wording has C07-N1 above. |
| R5 — provenance/build/test voice in reader | Closed for the identified corpus. Locks, Panic, keyboard options, rotation, transpose, performance and save details now give player-facing explanations. Recording relationships distinguish the course, the matching recipe and the separate endpoint exercise. The Strum caption gives the action without verification language. Expanded panels were inspected, not ignored because collapsed. |

Smaller findings are also corrected: Small Hours uses “Turn E1”; scale-editor and Song-editor recipes describe their actual starting pitches and setup; slots explicitly assign patterns; random playback no longer promises both outcomes in a short run; the lock-all scale change names the controls and apply action. Device-mod prerequisites and Rhythm Doctor's separate-server setup are visible before use.

## Original F01–F11 reader closure

| ID | Status in this candidate |
|---|---|
| F01 first-loop state | Closed: six ordered control actions reach the visible result; result focus lands on “Enter four trigs”. |
| F02 course front door | Closed: product introduction and guided tutorial are separate; no removed tagline reappears. |
| F03 replay gesture granularity | Closed within the declared recorded-walkthrough scope; no live browser-instrument claim. |
| F04 finished-song outline | Closed: ten course openings establish the progression to an arrangement and saving. |
| F05 implicit setup changes | Closed for the course/independent-scene transition: the next Harmony example identifies its own setup and offers the full scene. |
| F06 recipe/scene/recording match | Conditional/open through C07-1: the remaining endpoint prerequisite must be repaired. |
| F07 orientation hierarchy | Closed: course, reference, recipes and recordings remain distinguishable. |
| F08 prerequisites below player | Closed for inspected affected device and server workflows. |
| F09 search/quick reference | Closed: exact and partial search, keyboard result activation, retained query and result collapse work; private material is guarded and excluded. |
| F10 mobile/recipe rendering | Closed: no page overflow in the 116 route/viewport observations; dense recipes remain readable; enlarged grid intentionally scrolls within its container. |
| F11 verification voice | Closed for the identified visible reader material, including expanded result/reference panels; public player explanations remain. |

## Interaction and visual evidence

The observed routes had no browser errors or unintended page overflow. First-loop actions, keyboard Degree picker through all eleven steps, the independent Harmony transition, advanced LFO, save result and the rewritten recipe/reference panels were checked at both widths. Search activation focuses the destination heading and preserves the query. Developer routes are guarded; developer search terms return no result.

Fresh context uses original norns layout; Shield selection persists. Standard mode fits all sixteen columns. Enlarged mode makes pads materially larger and scrolls to the final column inside the grid container. The quick reference retains its logo, search, theme and navigation. A muted recording loaded and started; navigation to the Recordings page stopped playback once that destination actually rendered. This is media-control evidence, not listening or musical verification.

Index comparison retained 146 scene references and 21 audio references. Only the approved Strum scene reference changed; its revised caption was inspected. All audio references and the learning-path structure were unchanged. Root's broader native/chunk parity receipt remains separate evidence; this review does not independently certify 425 lesson scores, all native contracts, real-time scheduling, physical hardware or CI.

No source files, captures, audio or services were changed. Owned browser sessions were closed. A scoped follow-up on the exact installed Decay correction (and optional two Small Hours phrases), with source parity, can resolve the remaining conditional result without repeating the unchanged 116 observations.
