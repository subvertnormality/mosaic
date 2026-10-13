# Compact-grid v2 review — 8 October 2026

**CG-1 is closed in the actual installed reader. Overall approval remains conditional on enlarged-grid coordinate alignment (CG-2).** The compact desktop layout preserves the user's requested side-by-side devices and now gives the original norns screen adequate space. A stronger enlarged-mode check exposed an additional issue that appears to predate this correction; it is not attributed to v2 without a baseline comparison.

Actual preview: http://localhost:8785/manual/. Independently fetched CSS SHA `7959bc1e9f40f4320f7516ee8125dff945153a0ab9d950d8904824a0fcf00a25`, unchanged at check end. Reader index `254d19c38871b71973a6252fe859a02c4a9d6c8c464840d367de58baa8c4ff24`, book.js `a80f66aee6f4b5cc3c98fb38b0ff39e027be8d178dba8c29e10f5c92661bbeb1`, manual.js `49a88a9be93f58571b43fdb30e445bffb0bac4340941726a5488577ea21b21e4`. The unchanged index identifies book `e0d23614c74ca9fdf47caaaa6c4ab758b530639530e20b8eadd140fcf5ef49fe`.

Fresh checks covered `#rhythm-doctor` and `#first-sound/course` at 1440, 1280, 1121, 768 and 390 pixels, with original and Shield compact/enlarged layouts: 40 states. No page errors or unintended page overflow occurred. For all 20 compact states, all 128 pads were checked against the viewport and each ancestor that clips or scrolls horizontal content; none were clipped. This explicitly covers the hidden-overflow failure that an ordinary page-width check could miss. Forty screenshots and `observations.json` preserve the results. Additional screenshots and `settled-diagnostic.json` cover enlarged keyboard focus and expanded course controls.

## CG-1 closed: readable screen with paired hardware

Original-norns course screens now measure **282 × 141px at both 1440 and 1280**, up from 160 × 80 and 132 × 66. Rhythm Doctor at 1121 also measures **282 × 141px**, up from 164 × 82. Actual menu text is visibly readable. At 1440, the instruction column is approximately 280px and remains beside the paired hardware; at 1280, the instructions occupy a full row before the paired hardware. Expanded control-guide buttons also fit. Compact grids retain all sixteen visible columns. Tablet and phone arrangements remain coherent.

Key visual evidence: `lesson-1440-original.png`, `lesson-1280-original.png`, `rhythm-1121-original.png`, `lesson-1440-shield.png`, `lesson-1280-shield.png`, `lesson-1440-guide.png`, `lesson-1280-guide.png`.

## CG-2 open: enlarged column labels drift from pads

**Blocking for a coordinate-based walkthrough.** At 1121px, open Rhythm Doctor, expand “Enlarge grid controls”, focus the first pad and press ArrowRight fifteen times. Column 16 becomes focused, but the visible number 16 is around x608 while that pad begins around x1007. Its right edge is 1073px, beyond the grid container's 1043px right edge. Keyboard scrolling stops at 401px even though the container permits approximately 445px. A 30-second visibility wait did not resolve it; a fresh check after 500ms confirmed the stable geometry in both original and Shield modes. The user sees misleading column coordinates, and the final focused pad is partly clipped.

Evidence: `rhythm-1121-original-settled-column16.png`, `rhythm-1121-shield-settled-column16.png`, `settled-diagnostic.json`. The first strict visibility probe timed out; the diagnostic records the actual bounds rather than converting that timeout into a pass.

CSS inspection explains the label discrepancy: `.grid-enlarged #grid` uses a responsive 44–80px column size, while `.grid-columns` retains its previous sizing. The same pad-sizing rule existed before v2. Earlier checking established focus arrival at column 16 but did not establish full visibility or label-to-pad alignment; this review makes that distinction explicit.

Minimum correction: give enlarged labels and pads the same column widths, gaps and inset, and make keyboard navigation reveal the entire focused pad within the scroll container. Retain compact all-column visibility and the newly readable norns layout. Recheck both a desktop enlarged view and phone enlarged scrolling; no new native or audio evidence is needed for this reader correction.

## Seven-score judgment

| Criterion | Score | Rationale |
|---|---:|---|
| Readability | 8 | Actual norns menu text and instructions are now readable together. |
| Comprehensibility | 8 | The reviewed teaching content is unchanged. |
| Flow | 8 | Instructions stay before or beside hardware; controls remain ordered. |
| Understandability | 8 | The previously corrected explanations remain intact. |
| User-friendliness | 7 | Enlarged coordinates and final keyboard focus are misleading/incomplete. |
| Usefulness of interactive examples | 7 | A reader following enlarged grid column labels can target the wrong pad. |
| Cohesion | 8 | The compact pairing and responsive lesson arrangement now meet the intended design. |

The prior text/teaching approval is retained by exact reader-index and JS identity. The c664 CSS failure remains preserved in `../compact-grid-astra-recheck-20261008-01/`. This report closes its CG-1 finding but cannot restore unconditional seven-at-threshold status while CG-2 remains.

No production files, services, native captures or audio were changed. No listening or native/CI acceptance claim is made. Owned browsers closed. This is a scoped reader-layout review with unchanged content carried from the prior complete review.
