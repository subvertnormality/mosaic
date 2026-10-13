# Source15 scoped review — conditional failure receipt

8 October 2026 · http://localhost:8925/manual/

**Final reader approval is withheld.** Source15 closes the LFO wording condition and passes the keyboard-milestone checks, but the Panic result panel still exposes development/audit prose below its newly simplified caption. Root confirmed this as actionable and is preparing a narrow renderer correction. The separate quick-reference style patch has not been reviewed here.

## Remaining blocker P15-1

At `#midi-panic/panic-from-song-channel/hold-and-release` and `#midi-panic/panic-from-song-pattern/hold-and-release`, the caption now explains the correct two-second hold, Note Off purpose, silent starting state, continuing playback and inactive same-page hold. Immediately below it, the ordinary visible MIDI/result panel still says:

> Captured panic sweep: 6144 note-offs across 3 ports, 16 channels and 128 pitches (MIDI0–127). Each port/channel/pitch combination occurs once. No note-ons were captured. The complete event history is retained with the development records.

This is retained renderer output, not a newly introduced source15 caption error. It remains contrary to the requested nontechnical reader presentation and defeats the intended removal of this detail from these pages. Keep a concise useful Note Off/result summary visible; retain numerical audit completeness and history in evidence/details. Do not alter or discard the underlying evidence. Implementation location identified read-only: source15 `manual.js`, `midiText`, branch for `retained-panic-original-full-window-v1` (line101 of the saved file).

Actual screenshots: `390-panic-from-song-channel.png` and `390-panic-from-song-pattern.png`, plus desktop equivalents. The issue is in the visible panel beneath the caption; caption-only checks would miss it.

## Passed affected checks

At1440×900 and390×844:

- The LFO overview now correctly says `lfo 1` at depth1.00 while retaining Macro1 for the modest example. The modest example remains first. The Advanced link works and Show result reaches “Clock the LFO to the tempo.” The prior source14 wording condition is closed.
- Both Panic captions are clear and retain the actual behavioral limitations. Their ordinary result-panel prose remains the blocker above.
- `#midi-controller-options/keyboard-honour-degree` shows the authored first milestone “Map white keys and compare C major with natural minor ·1/5.” Stepped through all11 frames: the counter changes to “Set degree II and verify only that option applies ·1/6” at the intended boundary. Instructions and note comparisons remain coherent.
- `#midi-controller-options/keyboard-honour-degree-rotation` shows “Start from degree II with rotation and transpose set ·1/2,” then the final “Enable rotation and compare the keyboard notes ·1/1.” All3 frames inspected.
- `#first-sound/create-your-first-loop` retains its own first milestone, “Choose the output and enter four attacks ·1/2.”

At390px, additionally confirmed the clean private guard, Harmony search destination focus/query retention, and the real Oilcan caption link leading to its Apply scene. No document overflow occurred in the measured target pages. Mobile Panic and keyboard-result screenshots inspected. There were21 bounded observations and no browser errors; all owned Chrome sessions closed.

## Seven criteria and original findings

The cumulative reader quality assessment remains8/10 for readability, comprehensibility, flow, understandability, user-friendliness, usefulness of interactive examples and cohesion, as scoped in source14. Those quality scores are **not final acceptance**: P15-1 is a specific unmet reader-presentation requirement, and the forthcoming quick-reference candidate is unreviewed. Final adoption and any final threshold claim must wait for the targeted source16 check.

| Original finding | Source15 status |
|---|---|
| F01 First-loop/phrase state | Prior bounded reader closure retained; no changed course data. Native final-source qualification remains separate. |
| F02 Course front door | Prior reader closure retained by unchanged course/learning-path data. |
| F03 Truthful replay | Prior recorded-replay closure retained; fresh canonical milestone progression works. No live-instrument claim. |
| F04 Reproducible arrangement | Prior reader closure retained; no changed arrangement/save data. Native timing/persistence gates separate. |
| F05 Setup changes | Prior reader closure retained; fresh Oilcan continuation works. |
| F06 Recipe/example/recording agreement | Prior bounded reader closure retained; LFO wording condition now resolved. No new listening/PCM audit. |
| F07 Orientation | Prior reader closure retained; private guard and canonical keyboard milestone counters freshly checked. |
| F08 Prerequisites | Prior reader closure retained; keyboard starting states specify mapping/Honour settings and note comparison. |
| F09 Lookup | Prior manual-reader closure retained; Harmony search freshly checked. Separate quick-reference patch pending and excluded. |
| F10 Responsive use | Prior manual-reader closure retained; targeted390px pages fit. Separate quick-reference responsive review pending. No exhaustive accessibility certification. |
| F11 Useful results, evidence kept separate | **Open for P15-1**: Panic sweep audit/development prose remains in ordinary reader output. |

## Parity and identity

Compared the full source15 reader index to source13 (which equals source14): only LFO prose and MIDI Panic teaching bindings differ among feature records. Exactly the two expected Panic step captions changed. Learning path and audio examples are identical. Fresh index hash matches root's pin. Saved `parity.json` records the comparison. `manual.js`, CSS and HTML retain source14 identities; book.js changes canonical milestone inheritance. This is a scoped cumulative review, not a repeated133-feature or425-unit campaign.

Book, root-supplied: `d49d8551e5a18334d23537974d16b18116cfd1a79122edd7a169452e53060202`.

Independently hashed index: `1d0cf924b6e0e28819636edf950e43544f278bd7af384242673c5a46a04a8654`; book.js: `914abab5bb05c25d4272a4fbbbb9b79cfe98767f861056dc05f9657ff869b825`; manual.js: `e2d1057bc5375691541620951cb8e0484c7395ba52d6e686bac8fbad780534d7`; CSS: `1afdc10e38a816dd58bd8b3a714ce38864271384b23a1897edc33ade6196e309`; HTML: `2e97c18328141a080c7d24d7ce81c1d51a7c69523d3243a63e7aa0d59acaa482`.

Prior reviews and the source12 erratum remain preserved. No production edit, native/audio run, listening or service restart occurred. This report grants no blanket native/runtime/CI or original-checklist closure.
