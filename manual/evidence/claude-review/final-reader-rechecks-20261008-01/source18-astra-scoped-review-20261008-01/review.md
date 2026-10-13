# Source18 picker milestone recheck

8 October 2026 · http://localhost:8928/manual/

**PASS.** The actual keyboard-example picker now preserves the authored milestone groups. All seven cumulative reader scores remain **8/10**; no blocking finding arose in this narrow follow-up.

At both 1440×900 and 390×844, freshly opened `#midi-controller-options` without a scene suffix. Selected “Start from the chosen scale degree” through the visible scene picker, then used Next through all 11 frames. Every counter matched the authored 5-frame “Map white keys and compare C major with natural minor” group and 6-frame “Set degree II and verify only that option applies” group. The hash updated to `#midi-controller-options/keyboard-honour-degree`.

In the same page, selected “Rotate the keyboard voicing” through the picker and stepped through all 3 frames. The counters correctly followed the 2-frame starting-state group and 1-frame “Enable rotation and compare the keyboard notes” group. The hash updated to the rotation scene. These checks exercise the picker path that the earlier direct-route review did not cover.

Also freshly opened `#first-sound/create-your-first-loop` at each width and advanced through all 6 frames. Its own authored 2+3+1 groups remained unchanged: output/attacks, range/sound, then playback/result. No generic-counter fallback, browser error or document overflow occurred. Mobile picker screenshot inspected. Evidence contains eight observation records, including all 40 inspected frame counters across both widths. Chrome closed in `finally`.

Independently hashed the served index and assets. Reader index is byte-identical to source17; manual.js, CSS, HTML and quick reference are unchanged. Only book.js has the supplied new identity. Source16's whole-reader/quick-reference conclusions and source17's additional Panic lesson-outcome checks therefore retain their bounded scope. Original F01–F11 reader conclusions remain unchanged, with fresh support for F03/F07 from this picker check. Prior reports are preserved.

Scores: readability 8; comprehensibility 8; flow 8; understandability 8; user-friendliness 8; usefulness of interactive examples 8; cohesion 8. This is cumulative reader approval with a scoped renderer follow-up, not a repeated 133-feature/425-unit campaign or blanket native, PCM, runtime, CI or exhaustive-accessibility closure. No production edits, native/audio runs, listening, rebuilds or service restarts occurred.

Pins: book owner-supplied unchanged `db95208ebe2c3bd251819501ed6863af7c045cc3e8616870ab8fb19429f6a79e`; independently hashed index `300ddfae16cf5ee485e1f90da797715dceba0bd74a208477a5f63f6011954c52`; book.js `11f6a0c42082d6f0f79da17d49f88ffee0813247f7e5d9fea878518127a830a4`; manual.js `474512b2f321cd47f8601714f8f9c8df5aadfac1830745427c31a58c7700f436`; CSS `1afdc10e38a816dd58bd8b3a714ce38864271384b23a1897edc33ade6196e309`; HTML `2e97c18328141a080c7d24d7ce81c1d51a7c69523d3243a63e7aa0d59acaa482`; quick reference `6c169304bd791673876479649ceb720e161b7a6bee2a570d074e0f082d251695`.

Evidence: `observations.json`, `picker-degree-1440.png`, `picker-degree-390.png`.
