# Source16 panic summary review

Fresh review of the two canonical hold-and-release lessons at `http://localhost:8926/manual/`. Reader book SHA-256: `d49d8551e5a18334d23537974d16b18116cfd1a79122edd7a169452e53060202`; reader-index SHA-256: `1d0cf924b6e0e28819636edf950e43544f278bd7af384242673c5a46a04a8654`; served `manual.js` SHA-256: `474512b2f321cd47f8601714f8f9c8df5aadfac1830745427c31a58c7700f436`.

Both final result panels now say: “Panic sends Note Off messages to the connected MIDI outputs. This capture starts silent.” The before-state says “Recorded MIDI output: none.” I reached the final panel through the visible Show result control. These are captured results; I did not play or listen to audio and make no live MIDI claim.

## panic-from-song-channel — Panic by holding Channel while on Song

Route: `#midi-panic/lesson/panic-from-song-channel`; scene chunk SHA-256: `92b7daaaffdccff6a2e7bcaa492bb1604e92b7eb76f1612ba2ba6bb892c6394c`.

| Criterion | Score | Rationale |
|---|---:|---|
| coherence | 9 | The lesson starts on Song with Channel inactive, then demonstrates the Channel hold while preserving the selected page and playback. Its final captured summary now says plainly that Note Off messages go to connected outputs and the capture starts silent; the surrounding step explains why there is no audible change. The overview’s “about a second” versus the scene’s “about two seconds” remains a minor accepted approximation difference. |
| usefulness | 9 | The starting state, inactive button, hold and release, expected page/playback behavior, and separate use of Stop are stated where needed. |
| understandability | 9 | Two short lesson actions introduce the hold and release, and the result sentence explains the captured silence without requiring the reader to interpret a message count. |
| representation | 9 | The final view pairs the Song norns/grid capture with the concise Note Off summary and silent-start note. It presents a captured result, not live output or sound. |
| granularity | 9 | The two action checkpoints isolate holding Channel and releasing it; the full page adds setup and result details without splitting the gesture into excessive steps. |
| flow | 9 | It starts from Song, identifies the available Channel control, gives the hold/release action, and displays the outcome. |
| integration | 9 | The lesson is placed on MIDI Panic with related stuck-note and playback guidance and the alternate Pattern example. |
| vocabulary | 8 | Note Off and connected MIDI outputs are named accurately; “capture starts silent” distinguishes the recorded example from a live instrument result. |
| naming | 9 | The title says exactly which control to hold and the page context. |
| canonical_home | 9 | The direct lesson fragment opens the expected titled Channel scene, and its final state is reachable with the visible Show result control. |

## panic-from-song-pattern — Panic by holding Pattern while on Song

Route: `#midi-panic/lesson/panic-from-song-pattern`; scene chunk SHA-256: `4b9ac1897334b95d03d1aa30432d8335b0725bc0ccd07c32b8c9a10b29839a9b`.

| Criterion | Score | Rationale |
|---|---:|---|
| coherence | 9 | The lesson begins on Song with Pattern inactive, then shows the same panic action while keeping Song and playback as they are. The final captured summary plainly says Note Off messages go to connected outputs and that this capture starts silent; the detailed step explains the silent result. The overview’s “about a second” versus the scene’s “about two seconds” remains a minor accepted approximation difference. |
| usefulness | 9 | It tells the player which page to open, which inactive button to hold, how to release it, and what will happen to playback and the selected page. |
| understandability | 9 | The two action checkpoints name Pattern and release, while the final result summary explains the captured silence in everyday terms. |
| representation | 9 | The final view includes the Song screen/grid capture and the concise Note Off plus silent-start summary, clearly bounded as a capture. |
| granularity | 9 | The hold and release are separated as two checkpoints; the surrounding caption provides one focused explanation of the outcome. |
| flow | 9 | The lesson starts from the Song page, gives one hold/release gesture, then shows the completed capture. |
| integration | 9 | The scene appears alongside the Channel variant and links to separate stuck-note and playback guidance. |
| vocabulary | 8 | Pattern, Note Off and connected outputs are used consistently, and the summary clarifies why a silent-start capture has no audible change. |
| naming | 9 | The title distinguishes the Pattern control and Song context from the Channel version. |
| canonical_home | 9 | The canonical lesson fragment renders the titled Pattern scene, and the final captured state is available through its Show result control. |

All ten criteria for each scene meet 8/10. The overview still says “about a second” while the two scenes say “about two seconds”; this remains a minor accepted difference. A Masks audio request was aborted during navigation; the parent verified the resource itself returns HTTP 200.

Evidence: `../evidence/source16-panic-capture.json` and both screenshots. The Source15 four-scene report is preserved unchanged. No audio listening, production edit, build, or native run was performed.
