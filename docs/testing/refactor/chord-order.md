# Chord-order resolution boundary

This R06 slice moves the existing four-voice chord-order selector from
`lib/step.lua` to the pure `lib/musical_resolution/chord_order.lua` module.
Arpeggio construction and strummed-chord playback call the same formulas with
the same arguments. Scheduling, MIDI emission, root insertion, release order,
randomness, timing and dashboard updates remain in `step.lua`.

Validation:

- both focused chord-order unit tests passed, covering nil, patterns 1-4 and
  the existing unknown-pattern fallback;
- the full 1,520-test Lua suite passed;
- behavior inventory and Lua syntax guards passed (6/6);
- controlled-time M-CHORDSHAPE-256 passed for arpeggiated pattern 4
  (`d0f948afa0484b5291c917e64bb1c09b`);
- controlled-time M-CHORDSHAPE-257 passed for reverse strummed playback
  (`1fc72ad8c465439396137ba3370c6e4f`);
- Terra review found no semantic, integration, test-coverage or scope issues.
