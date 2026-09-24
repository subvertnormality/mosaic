# Targeted UI-migration gates on CI

The `Full behaviour suite` workflow has a manual `ui_migration_targeted` mode for
base-MIDI migration work when a local emulator slot is unavailable. This is a
partial check, not a replacement for the exhaustive workflow or its coverage
aggregation.

Dispatch `behaviour.yml` on the migration branch with `ui_migration_targeted`
enabled, two distinct full 40-character commit SHAs (`ui_migration_before_sha`
and `ui_migration_after_sha`), and comma-separated exact IDs in
`ui_migration_case_ids` (for example `M-GRID-001,M-SCALE-LOCK-003`).
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
controlled time against the pinned emulator. Both lanes use its qualified
runtime (`--experimental-install`), as the full campaign's `suite.py` does: the
emulator's default runtime lacks its JACK, screen-worker and SDL teardown fixes,
and native matron could exit with SIGSEGV (-11) after a passing real-time run.
A nonzero native exit remains a hard failure. Reports record
`runtime: {"real-time": "qualified", "controlled-experimental": "qualified"}`;
the importer requires every run in such a report to carry the qualified
(`diagnostic_only: true`) marker, and treats reports without the field as
earlier default-runtime real-time evidence. Both runs must pass and their
manifest source identities and artifact digests must validate. The existing
strict migration gate then checks every root and nested recipe/results session:
normalized recipes must be identical, controlled results may add only
`ui-confirm` entries, and real-time result-kind sequences must remain the same.
Symlinked manifests and evidence paths are rejected before reading or hashing.
After those gates pass, CI runs `repeat.py` once for a selected candidate case
from each distinct registered owner module. Each invocation starts three fresh
controlled-time processes and compares their normalized recipes and logical
outputs. The step checks all three run manifests against the candidate commit;
a failed, missing or mismatched repeat fails the targeted job. Inline cases
are grouped under `cases.py`. The separate `targeted-ui-repeatability.json`
records module selection and repeat verdicts; it is not a full-coverage report.
The uploaded `targeted-ui-migration-<run>` artifact contains the partial report,
repeatability report, repeat manifests and normalized traces, run manifests,
recipes, results and process logs, excluding copied code/data.
Its `complete_regression_run` field is always `false`. The targeted path skips
all exhaustive shards, special profiles and the full-coverage aggregate; an
ordinary manual dispatch with the toggle off retains the full campaign.

This satisfies the plan's controlled repeatability check only for the selected
base-MIDI modules, not for unselected modules or real-time-only profiles. It
does not authorize weaker assertions or acceptance of a failed source baseline.
