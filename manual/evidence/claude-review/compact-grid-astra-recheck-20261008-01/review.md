# Compact-grid layout review — 8 October 2026

**Conditional failure: retain the side-by-side design, but restore readable original-norns screen dimensions before publication.** One layout finding prevents carrying all seven prior 8/10 scores unchanged. The earlier text/teaching approval remains preserved and valid for its source; this is a separate CSS review.

Actual preview: http://localhost:8785/manual/.

Independently fetched CSS SHA-256: `c664709772996b542460a5c55a9c2eaf54e633170a29ce90685b78b10645cbcc`, matching again at the end of the initial matrix. Reader index remains `254d19c38871b71973a6252fe859a02c4a9d6c8c464840d367de58baa8c4ff24`; book.js remains `a80f66aee6f4b5cc3c98fb38b0ff39e027be8d178dba8c29e10f5c92661bbeb1`; manual.js remains `49a88a9be93f58571b43fdb30e445bffb0bac4340941726a5488577ea21b21e4`. The unchanged reader index identifies compiled book `e0d23614c74ca9fdf47caaaa6c4ab758b530639530e20b8eadd140fcf5ef49fe`.

Fresh browser coverage: `#rhythm-doctor` and `#first-sound/course`, widths 1440, 1280, 1121, 768 and 390, each in original/Shield compact and original/Shield enlarged modes: **40 states**. All states fit without unintended page overflow. The first 30-state run recorded no page errors. Enlarged original-mode keyboard navigation reached column 16, scrolling within the grid container, at all ten route/width combinations. Evidence: `observations.json`, `enlarged-original.json`, and 40 screenshots. Representative screenshots across all five widths, both routes and both hardware layouts were visually inspected.

## CG-1 — default original screen becomes too small

**Blocking.** Open the course chapter at `#first-sound/course` in a fresh context using the default original-norns layout. The screen is only **132 × 66 CSS pixels at 1280px**, and **160 × 80 at 1440px**. It contains a complete native 128 × 64 frame, so menu letters become approximately 5–7 CSS pixels high. The actual screen values are difficult to read comfortably even though the surrounding written instructions remain legible. Evidence: `lesson-1280-original.png`, `lesson-1440-original.png`.

The same compression affects `#rhythm-doctor` at 1121px: **164 × 82** screen pixels. At 1280 it improves to 229 × 115 and at 1440 to 295 × 147. Evidence: `rhythm-1121-original.png`, `rhythm-1280-original.png`, `rhythm-1440-original.png`.

The 1121px course layout makes the contrast clear: stacking its device and grid restores the screen to 266 × 133 and its menu is visibly clearer. Shield compact mode is also clearer because its controls do not consume the screen's right side: 236px screen width in the 1280px lesson and 264px at 1440. Enlarged original mode restores a 412 × 206 screen at 1280/1440. These alternatives demonstrate the problem but should not be required to read the default desktop lesson screen.

**Correction requirements:** preserve the requested desktop device/grid pairing. Allocate enough width for an original-norns screen around 224–256px minimum, preferably 256, while retaining an instruction column around 270px or more. At 1440, a wider player can fit a roughly 400px norns device, 280px-or-wider compact grid, gap and padding. At narrower desktop widths, place the whole hardware pair in a full-width row below the instructions if needed. Do not solve this by returning the 1440px hardware to disjoint vertical blocks or by requiring the reader to choose Shield. The 1121px reference layout also needs sufficient norns width. Keep compact all-16-column visibility and enlarged container scrolling.

## What works

The side-by-side reference composition at 1440 is balanced and shorter than the prior full-width grid. The original control arrangement remains K1/E1 above the screen with E2/E3 and K2/K3 to its right; Shield remains coherent. Both compact grids show all sixteen columns. The lesson text is narrower but still readable and retains its lists and result controls without overlap. Tablet and phone layouts stack naturally. Enlarged pads increase from roughly 15–39px compact to 44–80px depending on width and remain inside their scroll container. No changes to prose, scene content or navigation were observed in the source identity comparison.

## Seven-score adjudication

| Criterion | Score | Basis |
|---|---:|---|
| Readability | 7 | Default desktop lesson framebuffer text is too small; surrounding prose remains readable. |
| Comprehensibility | 8 | Unchanged reviewed teaching and clear written instructions. |
| Flow | 8 | Instructions, hardware and result controls remain ordered and usable. |
| Understandability | 8 | The corrected content remains unchanged. |
| User-friendliness | 7 | Reading the default screen requires an undisclosed workaround such as changing layout or enlargement. |
| Usefulness of interactive examples | 7 | Some desktop walkthrough screen feedback is too small to inspect comfortably. |
| Cohesion | 8 | The compact hardware pairing is coherent and matches the user's requested arrangement. |

Original content findings remain closed by exact index/JS identity. The responsive reader closure is now conditional on CG-1. This is not a new whole-manual content review, native/audio validation or listening claim. No production files, services, captures or audio were modified; owned browsers closed. Recheck the corrected CSS at the affected widths and retain this failed layout report.
