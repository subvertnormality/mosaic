# R05 history ring extraction

Base `84e523f`. `lib/history_ring.lua` now owns bounded ring storage and its
serialization adapter. `lib/memory.lua` still owns project-bound history state,
event validation/application, undo/redo, original and prior states, recorder-facing
operations, and the outer saved shape.

The extraction preserves logical-to-physical index calculation after wrap,
append-after-truncate, `total_size` as the redo boundary, unused physical slots,
and the exact shallow wire fields `{buffer,start,size,max_size,total_size}`.
Deserialization retains the prior compatibility behavior: missing history creates
an empty default-sized ring, missing fields use the same defaults, and restored
`total_size` follows saved `size`. No history index or event-command abstraction
was added.

Validation on the changed source:

- Lua syntax and `git diff --check` passed.
- Six focused tests passed for wrapped branch order, wrapped serialization, retained
  undo floor, legacy events without `prior_state`, serialized redo position/tail,
  and project round-trip memory undo.
- Full Lua suite: 1515/1515 passed.
- Six inventory, unique-name and Lua syntax guards passed.
- Native controlled M-MEMORY-004 passed: wrapped history, undo, branch truncation,
  grid feedback and resulting MIDI:
  `/home/andy/projects/mosaic-behaviour-runs/038f35a379344a3a8294afdcf5e349c1/manifest.json`.

The immediately preceding project-binding slice already passed M-MEMORY-006 in
both controlled and real time. This pure storage move has no clock-mode-specific
path, so the targeted native case used controlled time as allowed by the plan's
development cadence. Full real-time qualification remains at the frozen phase.
