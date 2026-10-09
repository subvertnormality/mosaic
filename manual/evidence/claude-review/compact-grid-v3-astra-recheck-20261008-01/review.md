# Final compact/enlarged grid review — 8 October 2026

**Pass: all seven reader criteria are 8/10. CG-1 and CG-2 are closed in the actual installed reader. No open reader-layout finding remains from this review.** This is a scoped final layout recheck, combined with the retained whole-reader/content assessment; it does not claim another complete prose read or native/audio campaign.

## Exact served identity

Preview: http://localhost:8785/manual/.

| Asset | Independently fetched SHA-256 |
|---|---|
| manual.css | 9612881156f6229ede39deb3da0bef94fc31d541c79d27986b4d87fb6972ea8a |
| manual.js | 2bd5d3b995cc357f68a09a61f5d1522e780c66d6e4404bbcd3037418bb95b9f2 |
| book.js | a80f66aee6f4b5cc3c98fb38b0ff39e027be8d178dba8c29e10f5c92661bbeb1 |
| reader-index.json | 254d19c38871b71973a6252fe859a02c4a9d6c8c464840d367de58baa8c4ff24 |

CSS and manual.js matched again at check end. The unchanged index identifies book `e0d23614c74ca9fdf47caaaa6c4ab758b530639530e20b8eadd140fcf5ef49fe` and authoring `e34e4faed23c5f5ae6593aba425596eba7ba25594c806a216737d266a37e6800`. Independent manual.js comparison with v2 shows only the focused grid pad's nearest-edge scroll call was added; no reader text or scene data changed.

## Fresh evidence

Forty actual browser states: Rhythm Doctor reference and first-sound course, at **1440, 1280, 1121, 768 and 390px**, each in original/Shield compact and original/Shield enlarged mode. `observations.json` and forty screenshots preserve this run. Representative screenshots across these widths, both hardware layouts, compact and enlarged modes were visually inspected.

- All twenty compact states show all 128 pads inside the viewport and every horizontal clipping/scrolling ancestor. No hidden final columns and no unintended page overflow.
- All forty states retain sixteen column labels and 128 accessible pad labels. Label centers are within **1px** of their corresponding pad centers.
- In all twenty enlarged states, fifteen ArrowRight presses reach column 16 and reveal its entire pad, with **9.5–10.3px** right margin. Document scroll displacement during those key presses is **0px**.
- No browser page errors occurred. Grid-label/brightness descriptions remained unchanged during keyboard movement.

## Closure and practical result

**CG-1 remains closed.** The original-norns screen is 282 × 141px in the 1440/1280 lesson views and the 1121 Rhythm Doctor view. Actual screen text is readable while the compact grid stays beside norns. At 1440, instructions remain beside the hardware; at 1280, instructions come first in a full-width row and the paired hardware follows. The earlier expanded-guide check is retained because the layout has not changed in this fix. Tablet and phone layouts remain coherent.

**CG-2 is closed.** Enlarged grid numbers now track the actual pads, including at the previously failing 1121px width in both Original and Shield layouts. Column 16 is completely visible after keyboard navigation. Phone enlarged scrolling also retains aligned numbers and a visible focused pad. The fix restores useful coordinates without sacrificing the compact overview.

Key screenshots: `rhythm-1121-original-enlarged.png`, `rhythm-1121-shield-enlarged.png`, `lesson-1440-original.png`, `lesson-1280-original.png`, `lesson-390-shield-enlarged.png`.

## Seven overall reader scores

| Criterion | Score | Rationale |
|---|---:|---|
| Readability | 8 | Original-norns menu text and lesson prose remain readable together. |
| Comprehensibility | 8 | Corrected teaching content is unchanged; grid labels now match the controls they identify. |
| Flow | 8 | Starting context and instructions stay before or beside hardware, and keyboard movement does not displace the page. |
| Understandability | 8 | The established content explanations remain intact, with reliable coordinate feedback. |
| User-friendliness | 8 | Compact overview, enlargement, layout choice and keyboard focus work at all five checked widths. |
| Usefulness of interactive examples | 8 | Readers can inspect screen feedback and accurately locate the named grid columns in either mode. |
| Cohesion | 8 | Paired hardware, lesson instructions and responsive arrangements retain a consistent relationship. |

The two scores previously held at 7 rise because CG-2 is now observed fixed, not because an independent test or lesson ledger declared a pass. The prior R1–R5, smaller teaching findings and original F01–F11 reader closures remain valid through the unchanged content identity and this repaired responsive interaction layer. Native, audio, CI and hardware qualification remain separately attributed.

## Preserved audit trail and limits

The preceding failed layout reports are unchanged: `../compact-grid-astra-recheck-20261008-01/review.md` (SHA `7ac8f0389d25ecc761e7f76eba01c29a5add5deb23df43d24a2a62a6f6205a37`) and `../compact-grid-v2-astra-recheck-20261008-01/review.md` (SHA `e46bb13bbf9dfb3d6ce63560d8b56d1d06ce29bcafe060f9d188f3c283078938`). The content approval remains `../locks-c07-1-astra-final-recheck-20261008-01/review.md` (SHA `c704b486fc630f6826a4ccc0de39a8dcf47578e3ea850f2d892a7493a0ad1909`), backed by the earlier whole-reader observations.

No production source was edited, no installation or commit performed, and no service restarted. No native capture, audio generation, listening or full-build claim is made. Owned browsers closed. This final reader approval applies to the exact assets above and does not itself publish or replace other release gates.
