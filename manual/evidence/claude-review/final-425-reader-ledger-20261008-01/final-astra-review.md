# Final installed reader recheck — 8 October 2026

**Reader review passes: all seven criteria are 8/10. No open blocking reader findings remain in the reviewed scope.** The installed correction closes C07-1; the two Small Hours clarifications close C07-N1. This result combines the prior whole-reader review with a fresh, source-bound check of the only three changed recipe passages. It does not relabel the failed candidate07 report or claim a new native/audio acceptance campaign.

## Exact installed candidate

Actual reader: http://localhost:8785/manual/.

| Identity | SHA-256 |
|---|---|
| Served reader index, independently fetched before and after browser checks | 254d19c38871b71973a6252fe859a02c4a9d6c8c464840d367de58baa8c4ff24 |
| Compiled book, identified by served index and root installation receipt | e0d23614c74ca9fdf47caaaa6c4ab758b530639530e20b8eadd140fcf5ef49fe |
| Authoring identity | e34e4faed23c5f5ae6593aba425596eba7ba25594c806a216737d266a37e6800 |
| Served book.js | a80f66aee6f4b5cc3c98fb38b0ff39e027be8d178dba8c29e10f5c92661bbeb1 |
| Served manual.js | 49a88a9be93f58571b43fdb30e445bffb0bac4340941726a5488577ea21b21e4 |
| Served manual.css | 123afe7d35beb8e827089b16518f03ccdfdcc000c33916e64b8f0002eb2caa4a |
| Served index.html | c4386498a8f224507ff0316958078932e58865640ed91931afb9945599839b87 |
| Served cheat_sheet.html | 6c169304bd791673876479649ceb720e161b7a6bee2a570d074e0f082d251695 |

Root installation receipt: `/home/andy/mosaic-manual-build-operators/locks-c07-1-followup-install-20261008-01/POSTINSTALL-READER-PINS.json`, root-reported SHA `221496a38940a5b0374923005afa393fb2410c5d9abfe5318741eb6a06547fe8`. Final source manifest is root-reported `5c88a4c57867ae78e4b4addbe1bed4fd8922f86778535c3697c52a3a506faf41`. The independently inspected proposal's two source-file hashes and patch are unchanged: locks `72525c531a4726ea38d60c8b1e3106d692fa0c3b3c1139de124ca3af9c1ba074`, cookbook `f2d9bcf4c5bf824f9e809c8a9ae83772a87455cdc97c1b1db7c7fd44d6469ba6`, patch `19214520c9662803b9aee51eccbff8c336f15442aa346b9eb77d5c0fb17efe84`.

## Scope and parity

The preserved candidate07 whole-reader evidence covered the bounded 133-feature prose inventory, all ten course openings, 116 route/viewport observations at 1440 and 390 pixels, and representative actual navigation, search, controls, recorded walkthroughs, hardware layout preferences, enlarged grid, quick reference and media cleanup. Its report remains `../combined-candidate07-astra-recheck-20261008-01/review.md`, SHA `066f06fb28362b9fe2c93787fddb4f77b5fdd92c31bca73d068c6327df641d5d`; its JSON remains SHA `70f8d342d727343f272c25e73a439b490e6e1fb4d3015a61134c5272f3ea7768`.

This follow-up independently compared the complete served index against that exact reviewed index. Only Locks recipe 5, Small Hours Bass and Small Hours Chord text changed, plus the two authoring-file identities and derived identity fields. All 146 scene references, all 21 audio references and the complete learning path are exact matches. Served JavaScript, CSS, HTML and quick reference are byte-identical. Root separately confirms all 167 chunk files byte-identical; this review checked their index references and does not mislabel that as independently rehashing all chunk bodies.

Fresh browser contexts loaded each affected route as a full document at both widths. Six checks produced no page errors or unintended horizontal page overflow. All six screenshots were visually inspected. `observations.json` retains the rendered passage and surrounding main content, source hashes, complete bounded index differences and layout results. This exact parity supports retaining the prior 116 observations without repeating them.

## Findings closed in the actual reader

**C07-1 — closed.** At `#locks/recipe/5`, after copying plain Song 1 to Song 2 and selecting Song 2, the endpoint paragraph now says: “Open Channel tasks → Trig params. Use E2 to select parameter slot 1, press K2, use E3 to highlight Decay, press K3 to assign it and K2 to return.” Only then does it ask the reader to hold step 1 and change Decay. This restores the prerequisite lost by the Song-slot copy. The relative-turn exercise, separate endpoint exercise, visible value checks and restore instruction remain distinct. Evidence: `decay-1440.png`, `decay-390.png`.

**C07-N1 — closed.** At `#small-hours/recipe/2`, the bass part is explicitly silent in bars 2–4 while the completed drums continue. At `#small-hours/recipe/3`, the chord part is explicitly silent while completed drums and bass continue. Both predictions now describe the intermediate mix accurately and still lead into completing the later bars. Evidence: `bass-1440.png`, `bass-390.png`, `chord-1440.png`, `chord-390.png`.

The prior R1–R5 and smaller closures remain valid by exact content parity: explicit empty-project assignments, correct full 64-step grids, merge preparation/copy/audition order, intermediate musical predictions, device prerequisites and player-facing language. Expanded reader details were part of that prior inspection; the closure does not depend on hiding technical noise behind collapsed panels.

## Final seven scores

| Criterion | Score | Rationale |
|---|---:|---|
| Readability | 8 | Player-facing prose and consistent typography remain readable at both widths. The Decay recipe is dense but legible, and the inserted navigation fits the existing style. |
| Comprehensibility | 8 | The final prerequisite is now stated exactly where the slot copy makes it necessary; the two musical predictions identify the intended parts. |
| Flow | 8 | The endpoint sequence now proceeds from copying to selecting, assigning and editing without an unstated recovery step. The previously checked course and independent-example transitions remain unchanged. |
| Understandability | 8 | Relative turns, absolute endpoints, intermediate playback and restoring the plain line are distinguishable. Broader setup and reference explanations retain their reviewed clarity. |
| User-friendliness | 8 | Responsive layout and the previously exercised search, focus, navigation, layout preferences and grid controls are unchanged; the six fresh pages have no overflow or errors. |
| Usefulness of interactive examples | 8 | The remaining recipe can now be followed through its named controls. The captured walkthroughs, musical comparison instructions and recording relationships retain their earlier reviewed usefulness. |
| Cohesion | 8 | The three corrections agree with the Song-slot model and the progressive arrangement; course, reference, recipes and recordings retain their established roles. |

These are reader-usability judgments, not an automatic uplift from independent lesson ratings. Flow and usefulness rise from 7 because the observed blocker is actually corrected. The other five remain 8 on exact source parity and fresh affected-page inspection.

## Original F01–F11 status

| Finding | Final reader status |
|---|---|
| F01 first-loop state | Closed; ordered controls and result focus retained unchanged. |
| F02 course front door | Closed; product introduction/tutorial separation and removed tagline retained. |
| F03 replay gesture granularity | Closed within the stated recorded-walkthrough scope. |
| F04 finished-song outline | Closed; all ten course openings and arrangement progression retained. |
| F05 implicit setup changes | Closed; independent-example setup/full-scene transitions retained. |
| F06 recipe/scene/recording match | Closed at reader level; C07-1's assignment repair now rendered correctly. |
| F07 orientation hierarchy | Closed; course/reference/recipe/recording hierarchy unchanged. |
| F08 prerequisites below player | Closed; reviewed device/server prerequisites unchanged. |
| F09 search/quick reference | Closed; previously exercised exact/partial search, keyboard activation and private-material guards unchanged. |
| F10 mobile/recipe rendering | Closed; prior responsive checks retained plus six fresh affected-page checks. |
| F11 verification voice | Closed for the reviewed public reader corpus; player-facing corrections retained. |

No open blocker or nonblocking finding remains from this review. The preserved historical failures remain part of the audit trail.

No audio was listened to in this follow-up; no native capture, audio generation, emulator, complete CI campaign or physical-hardware validation was performed or implied. The separately qualified native/audio evidence and 425-unit ledger remain separately attributed. No source files or services were changed, and the owned browser closed. This is a final reader review for the exact source above, not publication or a substitute for the root's remaining release gates.
