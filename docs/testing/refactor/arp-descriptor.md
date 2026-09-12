# Arp sequence descriptor boundary

This R06 slice moves scheduling-time arp slot construction into the
allocation-neutral `lib/musical_resolution/arp_descriptor.lua` builder. The
builder binds chord ordering once at module load and returns the same sequence
array and per-voice records the previous `handle_arp` block created.

Four ordered chord positions, false rest slots, captured pitch inputs, root
placement, the root-only ratchet and the empty-muted result are preserved.
Quantisation, live callback-time scale reads, release ownership, clock
scheduling, velocity progression, cancellation, dashboards and note emission
remain in `step.lua`.

Validation:

- all three direct arp descriptor tests passed;
- five focused existing arp/random/rest/muted integration contracts passed;
- controlled M-ARP-006 passed (`ffc7d72722c5439c80c1269cbcdb1b66`);
- controlled M-ARP-010 passed (`5fe58d8bee43424198821228591e613e`);
- real-time M-ARP-010 passed (`d44ac8ecf08943a98d7692a6980f5f5e`);
- controlled M-ARP-013 passed (`8f2904f224c042559b9035a98801c83c`);
- behavior inventory and Lua syntax guards passed (6/6);
- the full suite completed with 1,529/1,530 tests; its only red was the known
  load-sensitive `test_massive_concurrent_automation_with_param_slides` 2 ms
  threshold, which passed immediately in isolation;
- Terra review found no semantic, allocation, scheduling, coverage or scope issue.
