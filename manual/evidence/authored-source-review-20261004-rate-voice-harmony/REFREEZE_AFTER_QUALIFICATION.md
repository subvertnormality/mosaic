# Combined explicit authored source review — prepared only

This versioned proposal combines the root-reviewed rate, voice and baseline-first harmony corrections. Earlier rate-only proposals, authored receipts, native failure reports and the original prebuild snapshot remain unchanged. The exact current/proposed review patch is `source-review.proposed.patch`; the complete hash/archive chain and dry validation proof are in `review-preparation.json`.

Five of the existing 78 ledger paths change: course, tutorials, workflow, voice introduction and Scale explanation. The course scene plan and VOICES.md are separately reviewed and hash-bound, without silently changing UI-ledger membership. Dry strict source validation preserves all 125 historical MAN slices, 64 callbacks and 164 branches exactly. The original 48 scene assertion maps, 38 teaching stage IDs and complete harmony-design-apply procedure remain exact. Generated root quick-reference controls remain identical to the current authoritative model.

Applying or freezing this proposal remains gated on the whole continuous course passing in both native lanes, the independent raw audit and final root review. Preserve the helper's expected regression failure and focused fixed tests; retain both complete original reports, exact current corrected source/plan/helper identities and session cleanup proof. Partial or failed runs do not close this gate. Fill the proposal's currently pending qualification closure with those exact reviewed receipts before final root approval.

After final authorization, preserve the old current-review/inventory/generated-receipt bytes content-addressed; apply only the exact approved proposal. Then run the existing refresher, check and strict validator with no fingerprint skip:

```sh
python3 docs/ui-reimplementation/tools/refresh_source_inventory.py --review docs/ui-reimplementation/current-source-review.json
python3 docs/ui-reimplementation/tools/refresh_source_inventory.py --review docs/ui-reimplementation/current-source-review.json --check
python3 docs/ui-reimplementation/tools/validate.py
```

Create a NEW versioned prebuild snapshot only after the helper/prose/native qualification and root review settle. Include all current 78 reviewed bytes plus the new ledger/review/generated receipt; bind the two nonmember files and qualification closure explicitly. Recheck those exact bytes at final build launch. Keep `docs/testing/manual-post-build-ledger/prebuild-20261003` immutable as historical evidence and use the new snapshot for later explicit post-build reconciliation.

This preparation does not apply the review, create a new snapshot, promote feature/course bindings, activate acceptance, launch the full build or publish the manual.
