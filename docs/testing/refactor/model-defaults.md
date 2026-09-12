# R04 model construction and migration extraction

Base `f4d9a7d`. `lib/models/model_defaults.lua` now owns construction of the
program, song-pattern, channel, pattern and 64-value defaults, plus legacy and
NRPN migration. `lib/models/program.lua` remains the owner of the live store and
retains its public API through small wrappers. No persisted field, default value,
collection size, aliasing rule or migration rule changed.

Existing model tests cover the complete initial program shape, independent song,
channel, pattern and scale tables, fresh pattern and 64-value tables, selected-page
defaults, legacy top-level and nested `sequencer_patterns`, NRPN migration, memory
deserialization and save preparation. The broad unit/integration suite exercises
all public callers through the facade.

Validation on the changed source:

- Lua syntax and `git diff --check` passed.
- Six inventory, unique-name and Lua syntax guards passed in the preceding R03
  source state; no behaviour inventory or test-name file changed in this slice.
- Full Lua suite collected 1514 twice. Both runs passed 1513 functional tests and
  failed only `test_live_slide_admission_all_channel_parameter_slots` at 2.246 ms
  (while native suites ran concurrently) and 2.159 ms (shared host), against its
  2 ms wall-clock threshold. The same test passed alone: 1/1 in 0.026 seconds.
  The failures remain evidence and are not relabelled as green.
- Current complex persisted fixture passed in controlled time:
  `/home/andy/projects/mosaic-behaviour-runs/6fbd46b87bbc4daf987d18173f352ccb/manifest.json`.
- The same current fixture passed in real time:
  `/home/andy/projects/mosaic-behaviour-runs/ce33981224244201aaab86e72d624f29/manifest.json`.
- Legacy saved-range migration and two autosave generations passed in controlled
  time: `/home/andy/projects/mosaic-behaviour-runs/20af2befec124726b16a9d9841c62dd5/manifest.json`.

An attempted LuaUnit substring filter was rejected before collection; it is not
counted as validation. This slice establishes constructor ownership only. Explicit
live-store target identity and writer migration remain subsequent R04 work.
