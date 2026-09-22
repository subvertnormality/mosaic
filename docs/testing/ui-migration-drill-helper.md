# Validating the channel-page drift drill

This helper supports [UI abstraction plan §7 step 4](ui-abstraction-plan.md).
It does not run the emulator, modify Mosaic or the map, or establish completion
from a planned run. The final drill remains outstanding until actual artifacts
have passed validation.

First commit the settled migration and its evidence. Derive the selection from
that exact revision, using the two channel-editor page keys to be swapped:

```sh
python3 tests/behaviour/ui_migration_drill.py \
  --baseline FINAL_MIGRATION_SHA --pages masks memory --list
```

The list is derived from every committed `controlled/after/results.json`,
including nested driver sessions. Each confirmation for either page contributes
its case once; the output also identifies the confirming session, entry and file
hash. All controlled after sessions must have parseable root/nested
recipe/results pairs. Unknown case IDs, malformed confirmation fields,
duplicate source IDs/JSON keys, missing pairs and an empty selection fail closed.
Real-time-only evidence does not enter this drill. `--list` only prints a plan;
it cannot write the final drill result.

On a scratch branch from that revision, swap just the two `CHANNEL_PAGES`
entries in `tests/behaviour/ui_map.py` and commit the change. Run every selected
case through `run.py --clock-mode controlled-experimental`, using its normal
profile and installation/dependency arguments. Preserve every resulting
`manifest.json` and its run directory. A nonzero exit is expected, but only an
actual first error of type `UiMapError` is acceptable.

Run `repeat.py` separately for the listed `repeat_case`, retaining its complete
output directory and the child run directory. `--repeat-case CASE` may select
another base-midi or midi-modulation member, but use the same choice during
validation. The default is the first eligible case in sorted order.

```sh
python3 tests/behaviour/ui_migration_drill.py \
  --baseline FINAL_MIGRATION_SHA --scratch SWAP_COMMIT_SHA \
  --pages masks memory \
  --run /absolute/path/to/first-run/manifest.json \
  --run /absolute/path/to/next-run/manifest.json \
  --repeat /absolute/path/to/repeat-output/manifest.json
```

Supply one `--run` for every selected case. The validator rejects missing,
extra or duplicate runs, passing cases, wrong errors, wrong lanes/profiles and
source identity mismatches. It verifies that the scratch commit changes only
the map and that its Python syntax differs solely by the requested page-order
swap. Every run's recorded behaviour-source hashes must equal that scratch
revision, and its recipe/results artifact hashes must match the manifest.

`repeat.py` stops at its first unsuccessful child process and reports an
`AssertionError` wrapper. The helper verifies the wrapper against
`process-0.json`, follows the child manifest, and requires that child's first
error to be `UiMapError`. A passed first child, other failure, missing process,
inconsistent normalized evidence or reuse of a standalone run as the repeat
child is rejected. No change to `repeat.py` is needed.

Only a fully validated actual drill writes
`docs/testing/ui-migration-drill.json`; an existing result is never
overwritten. `--output` can preserve a new result elsewhere. The report records
case, failed status, first error, evidence hashes, both committed revisions and
the separate repeat outcome. Its `passed: true` means the expected drift
failures were verified; `complete_regression_run` remains false. Commit this
report on the final migration branch, preserving the scratch revision and raw
artifacts. Do not merge the intentional map swap.

The helper is an offline evidence validator, not an authentication system:
retain the original run directories and run on a clean scratch checkout.
No emulator run or completed drill is claimed by the helper's unit fixtures.

## Helper verification

The tests are characterisations outside the user manual, tied to the plan's
evidence contract. The initial test module failed on source revision
`3bc0e950f39c0f8e490fe393a8fa557f4e29766f` with
`ModuleNotFoundError: No module named 'ui_migration_drill'`. Focused tests cover
set derivation, nested sessions, malformed/missing/duplicate evidence, repeat
selection, exact swaps, source identity, wrong first errors and report creation.

```sh
cd tests/behaviour
python3 -m unittest test_ui_migration_drill test_ui_baseline_import \
  test_ui test_ui_layer test_collection test_suite
```
