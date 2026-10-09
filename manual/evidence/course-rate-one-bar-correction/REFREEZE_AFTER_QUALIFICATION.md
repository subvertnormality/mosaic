# Prepared authored refreeze — not applied

The root-approved correction contains exactly six literal replacements across four authored files: Rate /4 becomes /1 to match the unchanged intended one-bar/four-quarter-beat, 16-step lesson. This is an explicit correction to authored intent, not an exception to metadata-only post-build reconciliation. The three UI-ledger members change; scene-plans-course.yaml remains separately hash-bound authoring. No new ledger path is silently added.

`source-review.proposed.json` pins the three changed current source hashes and preserves all other reviewed files and historical manual source identity. `source-review-preparation.json` proves exact before/after reproduction and dry strict validation: 78 paths, 125 exact historical manual sections, 64 callbacks, 164 branches. The generated root cheat still exactly reproduces current controls and is unchanged. These dry checks do not establish native qualification.

Before root authorizes applying the proposal:

1. Preserve the helper regression failure for the expected Rate issue and the fixed relevant unit/integration evidence.
2. Require both complete continuous-course native lanes to pass all ten scenes/48 checkpoints using the corrected exact plan/helper/current application; verify exact MIDI period, stage IDs, independent assertions and cleanup. Retain original immutable reports, source snapshots and final command paths/hashes. A failed earlier scene or partial stage cannot close this gate.
3. Finalize the qualification closure receipt with the original real/controlled report paths and SHA, exact case-helper source SHA, explicit applicable clock modes and preserved baseline evidence. Reference it in the reviewed proposal instead of its currently pending closure statement; verify every authoring hash still matches the four-file authored receipt. Root reviews the final proposal before applying it.
4. Preserve current live source-review, inventory and generated review receipt content-addressed, in addition to the already immutable original `docs/testing/manual-post-build-ledger/prebuild-20261003` snapshot. Copy the exact reviewed proposal to `docs/ui-reimplementation/current-source-review.json`, then execute:

```sh
python3 docs/ui-reimplementation/tools/refresh_source_inventory.py \
  --review docs/ui-reimplementation/current-source-review.json
python3 docs/ui-reimplementation/tools/refresh_source_inventory.py \
  --review docs/ui-reimplementation/current-source-review.json --check
python3 docs/ui-reimplementation/tools/validate.py
```

5. Create a NEW versioned prebuild snapshot after these source/helper/prose qualification gates and final source writes settle. Include all current 78 reviewed bytes and the new ledger/review/receipt (81 snapshot files), retain the four exact reviewed authoring files/qualification closure receipt, and recheck every hash at final build launch. Keep `prebuild-20261003` and every earlier prepared-tool receipt unchanged as historical evidence. The final explicit reconciliation command must use this NEW snapshot, not the historical snapshot whose three authored hashes now legitimately differ.

Do not activate authority, promote bindings, relabel historical captures, rerun the whole manual build or publish from this prepared proposal. The full fresh build, post-build reviewed metadata reconciliation and all-example quality review remain separate later gates.
