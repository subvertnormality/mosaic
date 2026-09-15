# Pitch and note-mask resolution boundary

This R06 slice moves ordinary-note and note-mask pitch selection into the
allocation-free `lib/musical_resolution/pitch_resolution.lua` resolver. The
resolver binds quantiser functions and lazy option readers once at module load;
each trig uses positional inputs and multiple returns, with no new per-trig
input, result or callback tables.

The extraction preserves mask-zero handling, full-mask inheritance for
`nil`/`-1`/`0`/`1`/`2`, raw/snap/full quantiser branches, callback order and the
relative-mask metadata used by delayed chord and arp voices. RNG generation,
pentatonic policy, velocity, quantised-fixed and fixed-note overrides, routing,
scheduling and MIDI/player emission remain in `step.lua`.

Validation:

- all three direct resolver tests passed;
- all 262 selected step tests passed;
- the existing full-mask precedence contract passed;
- the existing seeded random/pentatonic/mask/fixed-note integration matrix passed;
- the full 1,527-test Lua suite passed;
- behavior inventory and Lua syntax guards passed (6/6);
- controlled M-MASK-019 passed (`be16ff56493c4cdeb4ab7b4a9de42fe8`);
- real-time M-MASK-019 passed (`da738c07c3c442fa914acc1e69d6d4b0`);
- controlled M-MASK-021 passed (`8a80d98f2f1d4e429d470f7f1836b550`);
- controlled M-MASK-022 passed (`b9a1438eb0ec49fa8511d5bc650b2117`);
- Terra review found no semantic, allocation, metadata, ordering or scope issue.

One initial full-suite launch failed before Lua started because the Windows WSL
connection timed out. WSL connectivity immediately recovered and the isolated
rerun completed with all 1,527 tests passing.
