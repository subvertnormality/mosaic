# Source18 keyboard scene recheck

Reviewed the two assigned scenes in the actual Source18 reader on 2026-10-08. I entered each through the MIDI Controller Options interaction picker, then advanced every captured frame with **Next captured step**. Both intended routes rendered, and the final MIDI-note claims matched their visible result text. All ten criteria scored at least 8 for both scenes.

The degree scene advanced through 11 frames. Its final frame says C now begins on degree II and lists `62, 63, 65, 67, 68, 70, 72, 74`; it explicitly says rotation and transpose remain unapplied. The rotation scene advanced through 3 frames. Its final frame lists `62, 63, 65, 67, 68, 58, 60, 74` and says the first five keys do not change. These are reader-captured MIDI examples; I did not run a native instrument or listen to audio.

| Unit | Coherence | Usefulness | Understandability | Representation | Granularity | Flow | Integration | Vocabulary | Naming | Canonical home | Overall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `scene:keyboard-honour-degree` | 9 | 9 | 9 | 9 | 8 | 9 | 9 | 8 | 9 | 9 | 9 |
| `scene:keyboard-honour-degree-rotation` | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 8 | 9 | 9 | 9 |

The first scene is longer because it establishes mapping, scale, degree, rotation, and transpose before isolating the degree switch; its separate checkpoints keep that setup legible. The second is a focused three-frame comparison with clear note-by-note results. The picker labels and final step names accurately identify both outcomes, and the feature chapter is the appropriate home for these MIDI mapping tasks.

The served pins were reader index `300ddfae16cf5ee485e1f90da797715dceba0bd74a208477a5f63f6011954c52`, book JS `11f6a0c42082d6f0f79da17d49f88ffee0813247f7e5d9fea878518127a830a4`, manual JS `474512b2f321cd47f8601714f8f9c8df5aadfac1830745427c31a58c7700f436`, and CSS `1afdc10e38a816dd58bd8b3a714ce38864271384b23a1897edc33ade6196e309`. The reviewed scene chunks and all ten criterion rationales are recorded in [the JSON report](source18-keyboard-scene-recheck.json). Bounded rendered captures are in [the evidence log](../evidence/source18-keyboard-captures.json), with final screenshots for [degree](../evidence/keyboard-honour-degree-final.png) and [rotation](../evidence/keyboard-honour-degree-rotation-final.png).
