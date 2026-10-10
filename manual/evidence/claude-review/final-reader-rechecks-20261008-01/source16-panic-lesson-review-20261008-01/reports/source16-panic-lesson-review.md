# Source16 MIDI Panic lesson review

This is a fresh review of the two lesson units (distinct from the previously reviewed scene IDs) at `http://localhost:8926/manual/`. Book SHA-256: `d49d8551e5a18334d23537974d16b18116cfd1a79122edd7a169452e53060202`; reader-index SHA-256: `1d0cf924b6e0e28819636edf950e43544f278bd7af384242673c5a46a04a8654`; served `manual.js` SHA-256: `474512b2f321cd47f8601714f8f9c8df5aadfac1830745427c31a58c7700f436`.

Both final result panels now read: “Panic sends Note Off messages to the connected MIDI outputs. This capture starts silent.” The before panels read “Recorded MIDI output: none.” I reached the final state with Show result; this is captured evidence, not live MIDI or audio.

## lesson:midi-panic:panic-from-song-channel

Route: `#midi-panic/lesson/panic-from-song-channel`; scene: `panic-from-song-channel`; scene chunk SHA-256: `92b7daaaffdccff6a2e7bcaa492bb1604e92b7eb76f1612ba2ba6bb892c6394c`.

| Criterion | Score | Rationale |
|---|---:|---|
| coherence | 8 | The lesson begins on Song with Channel inactive, then demonstrates the same hold while keeping the selected page and playback unchanged. The final result summary matches the silent captured state. The surrounding user-visible action caption also gives the connected-output behavior, but its technical count is redundant with the shorter final summary. |
| usefulness | 9 | It names the starting page and inactive button, gives hold/release instructions, and describes the output and playback behavior. |
| understandability | 7 | The final result sentence is now direct, but the visible `human_outcome` action caption still says “Mosaic sends Note Off for every one of the 128 notes on all 16 MIDI channels of each of the three connected ports, 6,144 messages.” This developer-level enumeration is unnecessary beside the simpler result summary and makes the lesson harder to scan. |
| representation | 8 | The rendered lesson pairs a Song screen/grid capture with the clear final sentence “Panic sends Note Off messages to the connected MIDI outputs. This capture starts silent.” The preceding caption repeats the explanation as a detailed 6,144-message count. |
| granularity | 9 | The lesson has focused hold/release actions, with separate starting and result states. |
| flow | 9 | It moves from the Song starting condition to the hold/release gesture and then the captured result. |
| integration | 9 | It sits on MIDI Panic beside the Pattern alternative and linked stuck-note/playback guidance. |
| vocabulary | 8 | Note Off and connected MIDI outputs are accurate terms and the summary explains the silent capture; the long count adds avoidable jargon. |
| naming | 9 | The title identifies the exact button and page context. |
| canonical_home | 9 | The canonical lesson route loads the expected title and interactive before/result states, with final state available through Show result. |

## lesson:midi-panic:panic-from-song-pattern

Route: `#midi-panic/lesson/panic-from-song-pattern`; scene: `panic-from-song-pattern`; scene chunk SHA-256: `4b9ac1897334b95d03d1aa30432d8335b0725bc0ccd07c32b8c9a10b29839a9b`.

| Criterion | Score | Rationale |
|---|---:|---|
| coherence | 8 | The lesson begins on Song with Pattern inactive, demonstrates its hold while keeping the page and playback unchanged, and shows a result consistent with the silent capture. The technical-count caption repeats information already stated more simply in the result summary. |
| usefulness | 9 | It explains how to select Song, hold the inactive Pattern button, release it, and interpret the captured output. |
| understandability | 7 | The final summary reads clearly, but the still-visible `human_outcome` caption says “Mosaic sends Note Off for every one of the 128 notes on all 16 MIDI channels of each of the three connected ports, 6,144 messages.” This technical count is redundant with the concise result panel and makes the instructions harder to scan. |
| representation | 8 | The captured Song screen/grid is paired with “Panic sends Note Off messages to the connected MIDI outputs. This capture starts silent.” The action caption above still adds the detailed count. |
| granularity | 9 | The focused hold and release actions are shown as a compact lesson with a distinct before/result state. |
| flow | 9 | The route supplies Song context, one gesture, and the result in order. |
| integration | 9 | It is presented as the Pattern alternative within MIDI Panic and links to the Channel version plus relevant troubleshooting. |
| vocabulary | 8 | The result sentence uses clear Note Off and connected-output language; the repeated technical count is unnecessary. |
| naming | 9 | The title clearly distinguishes Pattern from Channel and specifies Song context. |
| canonical_home | 9 | The canonical lesson route opens the expected title and exposes the final captured result through Show result. |

## Below-threshold finding

On both routes, the still-visible lesson action caption comes from the teaching binding `human_outcome` (mirrored in `presentation_metadata.human_outcome`). The exact text includes: “Mosaic sends Note Off for every one of the 128 notes on all 16 MIDI channels of each of the three connected ports, 6,144 messages.” That count remains in the user-facing teaching caption even though the final `#midi-text` is now concise. I scored understandability 7 for both lessons. Suggested bounded cleanup: replace the prose in both mirrored `human_outcome` fields with the direct connected-output/silent-capture wording, retaining the detailed count only in an expandable evidence detail if it is still useful.

The prior source15 four-scene report and source16 two-scene report remain untouched. Evidence is in `../../source16-panic-summary-review-20261008-01/evidence/source16-panic-capture.json` and the two final screenshots. No source edits, build, native run, or audio listening were performed.
