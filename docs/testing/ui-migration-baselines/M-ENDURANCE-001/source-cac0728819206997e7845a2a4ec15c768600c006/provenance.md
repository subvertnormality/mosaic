# Source-qualified M-ENDURANCE-001 evidence

These captures were made from Mosaic source revision `cac0728819206997e7845a2a4ec15c768600c006`, after the deterministic M-SYNC-011 test-reporting fix and before extracting `endurance.py` into `contract/`. The run manifests beside each `recipe.json` and `results.json` record the case source hashes, emulator identity, and installation identity.

The first post-move real-time invocation was interrupted before a result manifest existed and is not evidence; its partial artifact root remains outside this source tree. The fresh rerun passed. The separate `controlled-repeat/manifest.json` records three fresh-process controlled repeats; it is deliberately outside the lane directories so strict gate discovery sees only the paired before/after captures.

The older canonical M-ENDURANCE-001 evidence remains unchanged; it was committed with `9f951611` and has no per-run manifest. Fresh captures are kept in this revision-qualified subtree so both before/after comparisons use traceable, same-source evidence. Migration gates for this attempt use the `controlled/` and `real-time/` directories below this source tag.
