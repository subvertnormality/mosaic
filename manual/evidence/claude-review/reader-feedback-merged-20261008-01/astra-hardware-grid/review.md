# Hardware and grid — scoped independent reader review

8 October 2026 · http://localhost:8785/manual/

**PASS.** The original/Shield hardware views and compact/enlarged grid controls are understandable and useful at both tested widths. No blocking reader defect was found. All seven cumulative reader scores remain **8/10**. This is a scoped UI follow-up, not a new whole-manual review. Pending Polyperc wording was not reviewed.

At 1440×900 and 390×844, the default original layout places K1/E1 above the screen on the left, with E2/E3 and K2/K3 on its right. The Shield view places K1/E1 above the screen at the right, and K2/K3/E2/E3 along the bottom. Labels remain readable and distinct. Actual device screenshots were inspected; the layout is visibly different while keeping the same captured screen and highlighted control.

The “norns Shield layout” toggle is discoverable directly above the device. It works with Enter and exposes its state through `aria-pressed`. The selected Shield layout persists after reloading Masks and opening the first-loop scene. Toggling again restores the original. The stable toggle label is appropriate for a pressed/unpressed choice.

The compact grid shows all 16 numbered columns without horizontal scrolling at both widths. The “Enlarge grid controls” action produces a substantially larger version of the same grid:

| Viewport | Compact pad | Enlarged pad | Result |
|---|---:|---:|---|
| 1440px desktop | 59.28px | 80px | About 35% wider; horizontal scrolling stays inside the grid. |
| 390px mobile | 16.81px | 44px | About 2.6× wider; practical larger targets while preserving the compact overview option. |

After enlargement, the control reads “Use the standard grid controls” and explains horizontal scrolling. ArrowRight from column1 through column16 moves focus and scrolls the grid to the rightmost column. Column numbers remain aligned and the focused pad is visibly outlined. The document itself remains 1440/390px wide; there is no page overflow. Collapsing restores the all-column compact view. The mobile enlarged-column16 screenshot was inspected.

Explicit replay advancement remains coherent after changing layout and grid size. Next moves the Masks milestone counter from1/6 to2/6 and displays the specific G3 channel-mask caption at both widths. A repeated generic step title was not used as an advancement oracle. The earlier immediate desktop size reading occurred before the details-toggle event settled; the settled enlarged measurement is80px, as confirmed with focused column16.

Readability, comprehensibility, flow, understandability, user-friendliness, usefulness of interactive examples and cohesion each remain8/10. Accurate hardware placement and a meaningful enlarged mode support those scores. The compact mobile pads are intentionally small for an overview; the clearly available44px alternative makes that tradeoff usable. This does not assert touchscreen device testing, physical-hardware equivalence or exhaustive accessibility compliance.

Evidence: two initial observations,20 layout/grid observations and two focused replay-advance observations. Inspected original/Shield device images, default mobile layout and enlarged keyboard focus. All owned Chrome sessions closed. No browser errors were reported. Prior whole-reader findings retain their original bounded scope; no production files, authoring, audio, native captures or services were changed.

## Identity

Independently hashed the actual served files at the start of this review:

| Artifact | SHA-256 |
|---|---|
| Reader index | 300ddfae16cf5ee485e1f90da797715dceba0bd74a208477a5f63f6011954c52 |
| book.js | 5079bd12045d8ad09b4501b0867f7e6bb527d734fde8d0441c68815d9fdf91cf |
| manual.js | 49a88a9be93f58571b43fdb30e445bffb0bac4340941726a5488577ea21b21e4 |
| CSS | 123afe7d35beb8e827089b16518f03ccdfdcc000c33916e64b8f0002eb2caa4a |
| HTML | 93f9acf8b83257999a88d6db8974b70bd2eee10891cdd869082929ba275a6254 |

Files: `initial-observations.json`, `interaction-observations.json`, `advance-observations.json`, `original-device-1440.png`, `original-device-390.png`, `shield-device-1440.png`, `shield-device-390.png`, `enlarged-column16-390.png`, and corresponding viewport captures. Native/audio/runtime/CI gates remain separate.
