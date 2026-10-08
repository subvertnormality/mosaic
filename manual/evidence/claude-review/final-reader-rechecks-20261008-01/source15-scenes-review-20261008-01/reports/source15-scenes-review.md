# Source15 four-scene review

Fresh review of four rendered scene selections on the frozen reader at `http://localhost:8925/manual/`. Source SHA-256: `52d70cb543d38b1f155a0f5c4fa6fed510d0a44a161bed6ef0c8faffd518a9e3`; compiled book SHA-256: `d49d8551e5a18334d23537974d16b18116cfd1a79122edd7a169452e53060202`; reader-index SHA-256: `1d0cf924b6e0e28819636edf950e43544f278bd7af384242673c5a46a04a8654`. Actual served `book.js`, `manual.js`, and CSS hashes are recorded in the JSON report.

All four scenes display their selected interaction, distinct final captured result, and bounded step sequence. The panic scenes explicitly begin silent, so their captions correctly say no sound change is heard; they show Note Off sweep evidence and state that playback continues. The two keyboard scenes give the needed scale setup and MIDI result. I inspected captured states only and did not play or listen to audio.

## panic-from-song-channel — Panic by holding Channel while on Song

Route: `#midi-panic/panic-from-song-channel`; scene chunk SHA-256: `92b7daaaffdccff6a2e7bcaa492bb1604e92b7eb76f1612ba2ba6bb892c6394c`.

| Criterion | Score | Rationale |
|---|---:|---|
| coherence | 8 | The scene starts silent, keeps Song selected, and says panic leaves playback running; its target matches the visible result and the 6,144 Note Off sweep. The overview says hold for about a second while this capture says about two seconds, a small duration inconsistency within the same gesture. |
| usefulness | 9 | It gives a concrete Song starting point, identifies the inactive Channel button, states the hold and release gesture, and explains when the sweep matters. |
| understandability | 9 | The scene names the button coordinates, duration, silent starting condition, unchanged Song page, and playback behavior in plain action language. |
| representation | 9 | The selected interaction displays the Song screen, grid, final “Hold Channel for two seconds” result, and the captured sweep count; it explicitly explains that silence means no audible change. |
| granularity | 9 | Three steps isolate the starting project, opening Song, and the final hold-and-release action. |
| flow | 9 | The captured path moves from Device screen to Song, then to the panic gesture and a finished result. |
| integration | 9 | The feature page links the lesson and relates panic to playback controls and troubleshooting; the recipe distinguishes panic from stopping playback. |
| vocabulary | 8 | Note Off and panic are tied to the outcome, and coordinates are explicit. The approximate one-versus-two-second descriptions could be aligned. |
| naming | 9 | The title identifies the action, button, and page context. |
| canonical_home | 9 | Selecting this named interaction on MIDI Panic changes the fragment to the matching scene ID and renders the complete three-step sequence. |

## panic-from-song-pattern — Panic by holding Pattern while on Song

Route: `#midi-panic/panic-from-song-pattern`; scene chunk SHA-256: `4b9ac1897334b95d03d1aa30432d8335b0725bc0ccd07c32b8c9a10b29839a9b`.

| Criterion | Score | Rationale |
|---|---:|---|
| coherence | 8 | The scene starts silent, keeps Song selected, and says panic leaves playback running; its target matches the visible result and 6,144 Note Off sweep. The overview says hold for about a second while this capture says about two seconds, a small duration inconsistency for the same gesture. |
| usefulness | 9 | It provides the Song starting state, identifies Pattern as the inactive page button, and gives the hold/release action and expected unchanged page. |
| understandability | 9 | The button name and coordinate, approximate duration, silent start, and playback outcome are stated directly. |
| representation | 9 | The selected scene shows the Song screen and grid with its final “Hold Pattern for two seconds” outcome and the captured Note Off count; the silent start is explicit. |
| granularity | 9 | Three focused steps separate setup, navigation to Song, and the Pattern panic gesture. |
| flow | 9 | It advances from the Device starting view to Song, then applies the gesture and shows the completed sweep. |
| integration | 9 | The lesson is available from the MIDI Panic feature page alongside the Channel variant and related playback/stuck-note guidance. |
| vocabulary | 8 | Pattern and Note Off are paired with coordinates and outcome; the approximate hold duration differs from the overview wording. |
| naming | 9 | The title clearly distinguishes this Pattern-button variation from the Channel version. |
| canonical_home | 9 | The named selector changes to the matching panic-from-song-pattern fragment and displays all three captured steps. |

## keyboard-honour-degree — Start from the chosen scale degree

Route: `#midi-controller-options/keyboard-honour-degree`; scene chunk SHA-256: `da67d2e4d9e3c511f36f62cecbe3f7eb5fc03122d65060553b84429fa0eb7f5d`.

| Criterion | Score | Rationale |
|---|---:|---|
| coherence | 9 | The 11-step path first enables white-key mapping, selects natural minor, degree II, rotation 2 and transpose +2, then turns on only Honour scale degree. The final caption states rotation and transpose remain unapplied and the MIDI output lists the expected degree-shifted white-key phrase. |
| usefulness | 9 | It takes a player from defaults through the required mapping and scale setup to a clearly checked degree-II result. |
| understandability | 8 | Each step gives a concrete control or grid action and describes the resulting row or notes. The 11-step prerequisite sequence is substantial, but its checkpoints make the sequence traceable. |
| representation | 9 | The final captured frame shows the norns/grid context and MIDI output for the new phrase; the caption supplies note names and separates degree from rotation/transpose. |
| granularity | 8 | The long sequence covers several prerequisites before the degree switch, but these are needed to isolate what Honour scale degree changes. |
| flow | 9 | The example progresses from unmapped input through white-key mapping and scale setup to a before/after comparison and a usable phrase. |
| integration | 9 | The page places the scene under MIDI Controller Options, links the relevant scale controls, and keeps the other Honour transformations off for an isolated comparison. |
| vocabulary | 8 | Degree II and white-key mapping are contextualized by the resulting notes; musical/control terms such as Scale Editor and Honour switches are used consistently. |
| naming | 9 | “Start from the chosen scale degree” states the musical outcome rather than a technical flag name. |
| canonical_home | 9 | The “Start from the chosen scale degree” selector updates the feature fragment to `keyboard-honour-degree` and renders the full 11-step scene. |

## keyboard-honour-degree-rotation — Rotate the keyboard voicing

Route: `#midi-controller-options/keyboard-honour-degree-rotation`; scene chunk SHA-256: `e8db3ed73e909eb4a3c08784021b02bed4498007af783c794cc4fc6594b018e4`.

| Criterion | Score | Rationale |
|---|---:|---|
| coherence | 9 | The starting caption establishes white-key mapping, natural minor, degree II, rotation 2, transpose +2, and degree honored; the rotation switch is then the only changed setting. The final caption and MIDI output show the last two white-key positions lowered while the first five stay fixed. |
| usefulness | 9 | A three-step before/action/after comparison tells the player what to set, which switch to change, and how to use the resulting voicing. |
| understandability | 9 | The scene lists the setup state, names the exact menu control, then describes the changed A/B positions with MIDI note values. It explicitly distinguishes the white-key subset from intervening black keys in the practice prompt. |
| representation | 9 | The captured final frame includes norns/grid and MIDI output, and its caption explains the octave drop and unchanged first five keys. |
| granularity | 9 | Three steps are enough to isolate the toggle and compare its output; deeper setup remains available in the linked complete lesson. |
| flow | 9 | The progression is a focused baseline, one toggle, and a musical before/after result. |
| integration | 9 | The scene is linked from both MIDI Controller Options and the Honor Scale Rotations feature context, and the feature recipe gives the broader chromatic comparison. |
| vocabulary | 8 | Rotation, degree, transpose and white-key subset are used consistently; the starting-state caption names their exact values. |
| naming | 9 | “Rotate the keyboard voicing” communicates both the change and its musical use. |
| canonical_home | 9 | The named selector changes the canonical feature fragment to the matching scene ID; the Honor Scale Rotations feature also exposes a link to this full lesson. |

One small consistency issue: the MIDI Panic overview says to hold for about a second, while both captured scene captions say about two seconds. The gesture is otherwise consistent; I rated coherence and vocabulary 8 for those scenes. During the first panic-feature load, an unrelated Masks recipe audio URL (`/manual/audio/masks-small-hours.ogg`) returned 404/aborted; it did not affect the four scene captures.

Evidence: `../evidence/source15-scenes-capture.json` and four scene screenshots under `../evidence/`. These captures do not establish live MIDI hardware behavior. No source edits, compilation, native run, or audio listening were performed.
