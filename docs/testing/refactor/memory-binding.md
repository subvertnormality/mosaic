# R04 explicit project-memory binding

Base `5e8c1ef`. `memory.bind_project(project_memory)` now makes the history module's
state owner explicit. `program.init()` binds a newly constructed store when memory
is loaded, and `program.set()` binds the replacement store before deserializing its
history. `memory.init()` clears and binds through the same operation. Existing public
editing, history and persistence APIs remain unchanged.

The focused contract `test_project_replacement_rebinds_memory_to_the_new_store`
loads serialized history into a distinct replacement project and verifies that
memory's channel, index and original-state tables are the replacement store's tables.
It failed on parent `5e8c1ef` at the identity assertion and passes with this change.
The temporary detached baseline worktree was removed after the comparison.

Validation on the changed source:

- Lua syntax and `git diff --check` passed.
- Four focused persistence, cross-song history, redo-tail and wrap-floor tests passed.
- Full Lua suite: 1515/1515 passed in one run.
- M-MEMORY-005 New-project history clearing passed controlled:
  `/home/andy/projects/mosaic-behaviour-runs/72410bc352d64ca4836bccd69e935f1b/manifest.json`.
- M-MEMORY-006 autosave, cold restart and restored undo/redo passed controlled and
  real time:
  `/home/andy/projects/mosaic-behaviour-runs/e174b58da0164e048c03cb375b81e4c0/manifest.json`
  and `/home/andy/projects/mosaic-behaviour-runs/7128c1174e734068b9bc6e5d4ec9894f/manifest.json`.

This closes the live-store/history binding needed before extracting the history ring.
It does not yet migrate model writer families or introduce revision counters.
