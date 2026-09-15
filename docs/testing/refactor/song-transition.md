# Song-transition extraction (R06 item 4)

From `6b57944`, moved nine song selection/queue/boundary/Elektron functions and
four pending-state cells from `step.lua` to `song_transition.new(program, m_clock, step)`.
Public step entry points remain direct facades. Program/clock and iterator/table
bindings retain their lifetime; UI, parameters and runtime globals retain call-time
lookup. Stop clears the same three pending cells before UI refresh and blink cancel.
No queue/copy/repeat/Stop policy changes.

All nine extracted bodies compare byte-for-byte with their original bodies after
normalizing only the declaration owner (`step` to `transition`). The existing
64-case conditional realignment matrix passes with all assertions unchanged.
Its loader adds only module include plumbing for musical_resolution and song_transition;
there are no private song-function upvalue lookups to migrate. Sol static review
found no correctness issue in state lifetime, facade overrides or reset order.

Native validation (17 passes):

| Case | Lane | Run |
|---|---|---|
| M-SONG-FLOW-001 | controlled-experimental | `fd009c09cb444be6846ea77eb6214d68` |
| M-SONG-QUEUE-STOP-001 | controlled-experimental | `44c9d36060e240f3879e233c1670b299` |
| M-SONG-TEMPO-001 | controlled-experimental | `b4ef0f28e57749348ff1ff541f0ff3d5` |
| M-SONG-COPY-001 | controlled-experimental | `cb6b7c2ede4d42e0b55ba9c20102d822` |
| M-TRIPLE-005 | controlled-experimental | `7ea595c5bfc043939bf261837ce81796` |
| M-SYNC-001 | controlled-experimental | `b338c32af3dc4b1fae58152f8b058ece` |
| M-SONG-FLOW-001 | real-time | `7f6952785596489faf712ef14cb35202` |
| M-SONG-QUEUE-STOP-001 | real-time | `f097393ddffb4ec5b01a0de22d981386` |
| M-SONG-TEMPO-001 | real-time | `cf3b1afd4bd24fa3935c06193d741a75` |
| M-SONG-COPY-001 | real-time | `f9fbda4e94314660ae82d8671511f75d` |
| M-TRIPLE-005 | real-time | `0f9c38bc65f84a43b51f397a287ec0f2` |
| M-SYNC-001 | real-time | `c8cfa505b693469183e1fbda0b623ee0` |
| M-TIME-014 | controlled-experimental | `901a51afb44544b7bfef805e2ce9d974` |
| M-OPT-ELEK-002 | controlled-experimental | `6b1b216bf6064280be7430493f47ac9d` |
| M-PAT-BOUNDARY-001 | controlled-experimental | `e8349767d94541dbb71145132b372c06` |
| M-TIME-014 | real-time | `8765985828cb406694bfd6025084fdb1` |
| M-OPT-ELEK-002 | real-time | `9871f398109f495aa71f0de1ed3d5359` |

All 1536 Lua tests pass on the final tree (27.409 seconds, zero failures); all six
inventory/name/syntax guards and the 64-case standalone contract pass. Native input recipes and oracles are unchanged. Boundary-edit evidence
here is controlled only; no real-time boundary-edit claim is made against the older
runtime lacking native_input_schedule. Other listed cases retain both timing lanes.

Next: R07 pattern rebuild optimization, beginning with measured effective-length
resolution. Respect the R04 writer/invalidation map before introducing reuse/caches.
This receipt closes this extraction, not the complete refactor or emulator release.
