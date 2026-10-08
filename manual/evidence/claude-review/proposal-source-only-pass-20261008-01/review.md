# Proposal review — 2026-10-08

**Decision: HOLD.** The JSON records a separate ten-criterion score for every affected content unit. The review uses the current rubric: coherence, usefulness, understandability, representation, granularity, flow, integration, vocabulary, naming, canonical_home. All ten must be at least 8.

Reviewed 52 units; 10 contain at least one below-threshold criterion.

## Blocking items

- Empty-project Small Hours, Masks and Locks recipes do not assign patterns to channels. New channels initialize `selected_patterns = {}` (`lib/models/model_defaults.lua:65`); playback processes assigned patterns (`lib/pattern.lua:115,229`); Channel Editor adds assignments (`lib/pages/channel_edit_page/channel_edit_page.lua:317`).
- Small Hours and n.b.-voice recipes need install/enable prerequisites for Oilcan, Polyperc and Doubledecker; use the verified reader route `#norns-sound-sources-with-n-b`.
- Note Merge Modes edits slot 2 then says “play in order” without explicitly selecting slot 1.
- Locks recipe 4 still uses production/review phrasing (“replay the captured relative gestures”; “contextual contrast, not a reconstruction”) and omits Pattern 1 assignment and Polyperc prerequisite. Preserve the relative-turn and no-absolute-value caveats.
- Performance Management retains stale “testing on version 1.1.1” history; remove that framing but keep the practical physical-device variability warning.

## Verified

The 64-step map is correct, including step 44 at (12,6) and step 60 at (12,7). Relative Pattern Note degrees and Note mask X are consistent with the stated pitch examples. The corrected channel pattern assignment and Song Editor copy sequences are coherent.

Exact candidate and source pins plus unit-by-unit score vectors are in `review.json`.
