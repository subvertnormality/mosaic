# Importing migration BEFORE evidence from CI

`tests/behaviour/ui_baseline_import.py` copies original, passing case/lane pairs
from downloaded `behaviour.yml` artifacts into the BEFORE layout required by
[the migration plan, section 6](ui-abstraction-plan.md#6-migration-gate-fail-closed).
It does not run the emulator, change the comparator, or declare any migration or
regression campaign complete.

Download the artifacts for one exact GitHub Actions run into a new directory,
preserving each artifact's own directory. The importer finds `suite.json` under
each artifact and expects the uploaded `runs/<clock-mode>/<session>/` structure.
It is independent of shard count and accepts the base-MIDI, modulation, audio and
Crow profiles recorded by the reports. Keep the downloaded directory quiescent
during import; do not combine artifacts from different runs or revisions.

```sh
python3 tests/behaviour/ui_baseline_import.py /tmp/behaviour-download \
  --revision FULL_40_CHARACTER_SOURCE_COMMIT_SHA \
  --source-run https://github.com/OWNER/REPO/actions/runs/RUN_ID \
  --case M-EXAMPLE-001 --case M-EXAMPLE-002 --dry-run
```

Review the JSON plan, then repeat without `--dry-run`. `--case` is repeatable;
omitting it selects every original report row. `--output DIRECTORY` overrides
the default `docs/testing/ui-migration-baselines` destination. Use explicit case
selection when other cases already have baselines: an existing `before/`, even
an empty one, is an error and is never replaced or merged.

Every report must identify the exact supplied source commit, a clean source tree
and stable sources across the run. Each imported row must pass with return code
zero. Its manifest must match the report's manifest SHA-256, revision, case,
lane and profile, and must independently record a pass with no failure. Every
root or nested recipe/results pair must be present, parseable, correctly shaped,
and match its manifest's SHA-256 and byte length. Unlisted evidence, unmatched
pairs, duplicate case/lane rows, unsafe paths and symlinks are rejected.
`controlled-experimental` maps to the migration directory name `controlled`;
`real-time` retains its name.

The importer validates all selected pairs before writing any. Dry run performs
the same validation without creating a destination. On a later filesystem I/O
failure, any newly created partial baseline is left for inspection and a retry
refuses to overwrite it. The importer assumes no concurrent modifications to
input or output directories; it is not a sandbox for a hostile local process.

Each imported `before/` retains the evidence bytes and nested session paths,
plus `source-manifest.json`, `source-suite.json` and `provenance.json`. These
preserve the complete original identities, report row, requirements, diagnostic
qualification, original file hashes, source artifact paths, supplied run URL and
the report/manifest hashes. The run URL is caller-supplied attribution: this
offline importer verifies internal consistency, not GitHub authenticity. Obtain
the artifacts from the intended authenticated Actions run. Neither a diagnostic
controlled run nor a partial shard is relabelled as a complete regression run.

Failed original rows are reported as skipped, even if `suite-effective.json`
contains a passing serial retry. Original reports and failures are never
rewritten. Serial retries are intentionally not imported; their classification
and failure lineage require separate review. The expanded workflow uploads
recipe/results for `runs/`, but currently only manifests for `serial-rerun/`.
A requested case absent from all original report rows is an error. A missing
lane cannot be invented: this tool imports available passing lanes and does not
prove that all lanes required by section 6 have been supplied. The existing
before/after gates and module repeatability requirements still apply.

## Validation

The tests are harness characterisations outside the player manual and are
registered with the suite's Python test layer. On source commit `485ea9a6`, the
new acceptance test initially failed with `ModuleNotFoundError` for the missing
`ui_baseline_import` module, before implementation. Run the focused coverage with:

```sh
python3 -m unittest discover -s tests/behaviour -p test_ui_baseline_import.py -v
```
