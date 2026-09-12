# Strum scheduling descriptor boundary

This R06 slice moves scalar strum scheduling decisions into the allocation-free
`lib/musical_resolution/strum_descriptor.lua` helpers. Chord ordering and timing
are bound once at module load. Per voice, the helpers return only chord number,
delay and velocity ordinal through Lua multiple returns.

Immediate and delayed root eligibility, unknown-pattern root omission, silent
mask slots, reverse ordinal zero, delay zero and nil suppression are preserved.
The existing clock closures still reread the captured chord table, quantise with
the live callback-time scale, emit through the captured route, schedule releases
and update dashboards in `step.lua`.

Validation:

- all three direct strum descriptor tests passed;
- reverse-root ordering/velocity, delayed live-scale/captured-route and
  nonpositive-release focused contracts passed;
- controlled M-CHORDSHAPE-001 passed (`fdda272e074345b193a4a1c0b52a2668`);
- controlled M-CHORDSHAPE-003 passed (`b9845b493c764cc096251145f51b0f32`);
- real-time M-CHORDSHAPE-003 passed (`04151b64f3a54b63906cfb0d7ea1aba0`);
- controlled M-SPREAD-005 passed (`7df310d4565c4aaba91fd871ee78b58f`);
- controlled M-DASHBOARD-CHORD-001 passed (`d6ad5bb0eeaa4c908f89d48cecbde6a3`);
- the full 1,533-test Lua suite passed;
- behavior inventory and Lua syntax guards passed (6/6);
- Terra review found no semantic, allocation, callback, coverage or scope issue.

The first direct-test run exposed a faulty nil-return idiom in the test fake.
Production behavior was already green; the fake was corrected and all three
direct tests then passed.
