# Explicit reviewed refresh after the complete manual build

The prepared tool does not run native sessions, change runtime code or activate acceptance. Root must first verify the actual build started from the preserved source snapshot and wait for the complete fresh build manifest. If sources move before build start, preserve this historical snapshot and create a newly reviewed snapshot; do not change its hashes.

Run this separate root-authorized step only after the full builder succeeds:

```sh
python3 docs/ui-reimplementation/tools/reconcile_manual_build.py \
  --build-evidence /absolute/path/to/completed-build \
  --manifest-sha256 EXACT_INDEPENDENTLY_CHECKED_COMPLETED_MANIFEST_SHA256 \
  --prebuild-snapshot docs/testing/manual-post-build-ledger/prebuild-20261003 \
  --evidence /absolute/path/to/new-ledger-review-evidence
python3 docs/ui-reimplementation/tools/refresh_source_inventory.py \
  --review docs/ui-reimplementation/current-source-review.json --check
python3 docs/ui-reimplementation/tools/validate.py
```

The manifest pin must come from the completed immutable build, not from a failed or partial run. The tool checks the current full ordered build plan, every individual stage record/log hash, Doctor role proofs, exact current source inventories, independently audited publications, same-build Doctor collection, reproduced scene YAML, feature/course before-and-after receipts, unchanged authored claims, exact generated root quick reference and preserved obsolete scene files. It archives all old ledger bytes and rolls back ledger writes if strict validation fails. The 125 historical manual slices and 64 callbacks/164 branches must remain exact. Generated source membership may legitimately move from 78 to 81 files; old generated paths are archived explicitly rather than retained as stale current sources.

Publication additionally requires the user's final every-example quality review: all five criteria at least 8 for every fresh example, with revisions and re-review as needed. This utility does not establish that review, exhaustive behaviour coverage, physical norns timing or final manual acceptance.
