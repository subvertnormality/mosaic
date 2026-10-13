# CI artifact path audit

Harness characterisation outside the player manual, based on checkpoint
`84cae84f`. The new `ci.test_artifact_paths` test failed on that workflow in all
three upload-block subtests: root and nested `code/mosaic` symlink targets and
`data` files appeared alongside actual run evidence. After adding exclusions,
all 29 importer, shard-selection, aggregation and artifact-path tests passed:

```sh
cd tests/behaviour
python3 -m unittest -v test_ui_baseline_import ci.test_select_shard ci.test_verify_full ci.test_artifact_paths
```

The [upload-artifact v4 search implementation](https://github.com/actions/upload-artifact/blob/v4/src/shared/search.ts)
sets `followSymbolicLinks: true`. `Driver` creates `code/mosaic` as a symlink to
the checkout. A previously downloaded CI artifact at
`/tmp/mosaic-ci-34775032792/behaviour-base-0/runs/real-time/029348bb4015450894d2201d477a5c12/code/mosaic/tests/behaviour/mod-patches/manifest.json`
also demonstrated this traversal. Since the checkout contains baseline
recipe/results files, the new upload globs would include those as unlisted
evidence and the baseline importer would correctly refuse the run.

The exclusions mirror the manifest's code/data evidence boundary, retain root
and nested session evidence, and cover serial-rerun manifests too. The importer
remains strict. Its original-runs UUID directory layout and source revision,
dirty-patch hash, untracked list and source-stability checks match `suite.py`
and `run.py`.

The workflow retains 16 base-MIDI shards and an aggregate requirement of 18
suite reports. Partition tests verify 826 disjoint base cases and aggregation
verifies the 837-case inventory with 1,659 applicable case/lane runs. No emulator
or live CI execution was performed for this infrastructure-only change; this
audit does not establish a completed CI pass or scheduling benefit from raising
the shard count further.
