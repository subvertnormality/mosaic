# Targeted UI-migration gates on CI

The `Full behaviour suite` workflow has a manual `ui_migration_targeted` mode for
base-MIDI migration work when a local emulator slot is unavailable. This is a
partial check, not a replacement for the exhaustive workflow or its coverage
aggregation.

Dispatch `behaviour.yml` on the migration branch with `ui_migration_targeted`
enabled, two distinct full 40-character commit SHAs (`ui_migration_before_sha`
and `ui_migration_after_sha`), and comma-separated exact IDs in
`ui_migration_case_ids` (for example `M-GRID-001,M-SCALE-LOCK-003`). The candidate
Both commits must contain the same targeted runner and comparison gate: capture
the before baseline only after this CI tooling lands. Both commits must contain the named
registered cases as base-MIDI cases. Use a source commit immediately before the
case edit and the commit containing that edit; do not substitute an unrelated
baseline or a changed production build.

Before starting an emulator, the runner compares Git object identities,
including file modes and submodule gitlinks. `mosaic.lua`, the complete `lib/`
tree, `.gitmodules`, `README.md` and `cheat_sheet.html` must be identical. Under
`tests/behaviour/`, only selected cases' registered owner modules and the fixed
UI source list in `targeted-ui-migration.py` may change. The gate and runner
themselves must have identical Git object identities. Shared driver,
suite, fixture or unrelated case changes reject the pair. If a migration
genuinely needs a shared change, establish a fresh passing before baseline at
the new revision; do not widen the comparison as a shortcut.

Each selected case runs independently at both commits in real time and
controlled time against the pinned emulator. Both runs must pass and their
manifest source identities and artifact digests must validate. The existing
strict migration gate then checks every root and nested recipe/results session:
normalized recipes must be identical, controlled results may add only
`ui-confirm` entries, and real-time result-kind sequences must remain the same.
Symlinked manifests and evidence paths are rejected before reading or hashing.
The uploaded `targeted-ui-migration-<run>` artifact contains the partial report,
run manifests, recipes, results and process logs, excluding copied code/data.
Its `complete_regression_run` field is always `false`. The targeted path skips
all exhaustive shards, special profiles and the full-coverage aggregate; an
ordinary manual dispatch with the toggle off retains the full campaign.

The plan's independent repeatability requirement still applies to migrated
modules. Targeted CI gates do not claim to satisfy it, nor do they authorize
weaker assertions or acceptance of a failed source baseline.
