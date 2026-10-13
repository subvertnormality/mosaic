# Source17 MIDI Panic lesson review

Fresh review of the two explicit lesson units on the frozen reader at `http://localhost:8927/manual/`. Source SHA-256: `0cab463ee80edddcc049c6e5678b6dc685303f740665f8fabb2c53fb8ce8e369`; book SHA-256: `db95208ebe2c3bd251819501ed6863af7c045cc3e8616870ab8fb19429f6a79e`; reader-index SHA-256: `300ddfae16cf5ee485e1f90da797715dceba0bd74a208477a5f63f6011954c52`; served `manual.js` SHA-256: `474512b2f321cd47f8601714f8f9c8df5aadfac1830745427c31a58c7700f436`.

The practical captions now align with the previously reviewed scene captions: each starts from Song and directs the reader to hold its non-selected Channel or Pattern button for about two seconds, release it, and understand that Note Off goes to connected outputs while the silent capture shows no audible change and playback/page remain unchanged. The result panel uses the short summary “Panic sends Note Off messages to the connected MIDI outputs. This capture starts silent.”

## lesson:midi-panic:panic-from-song-channel

Route: `#midi-panic/lesson/panic-from-song-channel`; scene: `panic-from-song-channel`; scene chunk SHA-256: `92b7daaaffdccff6a2e7bcaa492bb1604e92b7eb76f1612ba2ba6bb892c6394c`.

| Criterion | Score | Rationale |
|---|---:|---|
| coherence | 9 | The starting state identifies Song with Channel inactive. The lesson action, scene caption, and result all agree: hold Channel, send Note Off to connected outputs, keep Song selected and playback running, and expect no audible change because this capture starts silent. |
| usefulness | 9 | It names the Song starting point and Channel coordinate, gives hold/release actions, and explains when panic is useful and what it does not stop. |
| understandability | 9 | The practical action prose now gives one direct cause and result: hold Channel for about two seconds, release, send Note Off to connected outputs, and expect no sound change in this silent capture. |
| representation | 9 | The final panel pairs the Song norns/grid state with a concise Note Off summary and silent-start note; the before panel states no recorded MIDI output. |
| granularity | 9 | The lesson separates the hold and release into two simple checkpoints, then shows the recorded result. |
| flow | 9 | It moves from Song setup to the specific hold/release action and then the captured outcome. |
| integration | 9 | The lesson is in MIDI Panic with the Pattern alternative, separate stuck-note comparison, and related stop/troubleshooting links. |
| vocabulary | 8 | Note Off and connected MIDI outputs are concise and accurate; the manual context supplies the panic concept. |
| naming | 9 | The title names the exact button and Song page context. |
| canonical_home | 9 | The canonical lesson route loads the expected heading and exposes the before/result control for the Channel scene. |

## lesson:midi-panic:panic-from-song-pattern

Route: `#midi-panic/lesson/panic-from-song-pattern`; scene: `panic-from-song-pattern`; scene chunk SHA-256: `4b9ac1897334b95d03d1aa30432d8335b0725bc0ccd07c32b8c9a10b29839a9b`.

| Criterion | Score | Rationale |
|---|---:|---|
| coherence | 9 | The starting state identifies Song with Pattern inactive. The practical caption and final panel agree that Pattern sends Note Off to connected outputs while leaving Song and playback as they are; the capture starts silent, so no audible change is expected. |
| usefulness | 9 | The lesson gives the exact page and Pattern coordinate, the hold/release action, and the expected page and playback behavior. |
| understandability | 9 | The lesson uses direct action language and describes the silent capture without an unnecessary technical message count. |
| representation | 9 | The final panel shows the Song screen/grid capture with the concise output description and silent-start note, alongside a no-output before state. |
| granularity | 9 | Two short action checkpoints isolate the Pattern hold and release; the final captured outcome remains a separate state. |
| flow | 9 | The page sets up Song, demonstrates the Pattern gesture, and shows what the recorded result means. |
| integration | 9 | The lesson is grouped with the Channel variant and linked stuck-note and playback guidance. |
| vocabulary | 8 | The concise Note Off and connected-output language is accurate and avoids overloading the main instruction. |
| naming | 9 | The title makes the Pattern variation and Song context explicit. |
| canonical_home | 9 | The canonical lesson route opens the matching Pattern heading and its before/result control. |

All ten criteria for both lessons meet the 8/10 threshold. The Source16 scene and lesson reports, including the earlier 7/10 understandability finding, remain unchanged; this fresh Source17 review covers only the two lesson IDs. Evidence is in `../evidence/source16-panic-capture.json` and the two screenshots. No audio listening, live MIDI validation, build, or native run was performed.
