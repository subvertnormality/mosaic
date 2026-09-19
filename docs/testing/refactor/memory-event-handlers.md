# Memory event-handler boundary

This R05 slice moves the existing note-mask and trig-lock event interpreters to
`lib/memory/event_handlers.lua`. The module constructor receives only `program`
and `fn`; validation, capture, apply and restore behavior moved without changes.

History ownership, ring indexing, event construction, undo/redo, serialization,
the explicit target seam and all production callers remain in `memory.lua`.
Event names and saved shapes are unchanged.

Validation:

- all 111 focused memory tests passed;
- the full 1,517-test suite had 1,516 successes and only the known load-sensitive
  `test_live_slide_admission_all_channel_parameter_slots` threshold red at
  2.341 ms under suite load; it passed in isolation at 0.019 s total test time;
- Lua syntax and diff checks passed;
- Terra review confirmed the moved handler implementation, dependency order,
  nested include and serialized event shape are preserved.
