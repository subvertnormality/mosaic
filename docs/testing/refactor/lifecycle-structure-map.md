# R03 structural starting point

Inspected Mosaic `915d937`, 2026-09-12. This is a source map, not a completion
claim or a new acceptance prerequisite.

`mosaic.lua` currently owns five distinct responsibilities:

| Responsibility | Current entrypoints/state | Extraction constraint |
|---|---|---|
| Native startup and controls | init, enc, key, redraw, transport callbacks | Keep include order and native signatures |
| Project operations | load_project, save_project, load_new_project, checked_table_save | Preserve rejection before Stop, serializer format, IO restoration and history rebinding |
| Autosave | two metros, inhibition flag, prime/do/reset callbacks | Preserve deadlines, queued-callback inhibition and manual-save recovery |
| Parameter registration | init's MOSAIC group and action callbacks | Preserve registration order, IDs, defaults and callback identity |
| Recurring display/scheduler work | four clock loops and recursive blink | Preserve rates and startup ordering; cleanup changes are separate behaviour changes |

Next structural slice: separate parameter registration from application startup.
Move the registration block mechanically into an application-owned module. Supply
the three project action callbacks from the entrypoint; keep project state and
autosave closures in place. This reduces init without inventing a framework or
changing model, scheduling, persistence, UI gestures or parameter contracts.

Then extract project/autosave ownership together, with explicit operations replacing
private closure discovery in `lib/tests/lib/project_load_integration_tests.lua`.
That file currently finds load/new from init, prime from autosave_reset, do_autosave
from prime, and save from do_autosave. Its assertion bodies and failure inputs must
remain intact when lookup plumbing changes. Do not merely move the private lookup
problem to another facade.

Existing native anchors include M-SAVE-001 (cold restore), M-SAVE-002 (idle/playing
autosave), M-RANGE-SAVED-002/003 (rejected load and recovery), and
M-PERSIST-FIXTURE-CURRENT (saved complex phrase). Select affected cases for each
actual change; no new lifecycle matrix is needed for mechanical registration moves.

The already-running PERF-003 measurement is exploratory under shared-host CPU load.
It does not determine the structural work order and is not a start prerequisite.
