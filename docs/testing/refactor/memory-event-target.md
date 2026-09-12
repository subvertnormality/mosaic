# Explicit memory event target

This R04 seam separates history ingress from ambient song selection.
`memory.record_event_for_target(song_pattern, channel_number, event_type, data)`
contains the existing capture, keying, apply and result-state logic. The public
`memory.record_event` API remains a compatibility wrapper: it preserves the old
invalid-event validation order, resolves `data.song_pattern` or current selection,
then delegates.

The serialized event shape is unchanged. History remains indexed by channel, and
its state key still includes song, step and parameter where applicable. Undo and
redo continue to use the song stored on the event.

Existing recorder callers remain on the wrapper. Migrating pending parameter-lock
recording to a captured song target can change behavior if selection moves between
queue and commit, so that migration requires the campaign's two-lane behavioral
baseline before it is treated as a correction.

Validation:

- focused explicit-target contract: 1 passed;
- full Lua unit/integration suite before the validation-order correction: 1,517
  passed, 0 failed;
- all 17 memory mutation-killer tests after the correction: passed;
- controlled native `M-MEMORY-004`: passed, manifest
  `a0159542c56c466597cb01075932ef41`;
- Terra review confirmed event shape, undo/redo targeting and state-key behavior;
  its validation-order finding was corrected before commit.
