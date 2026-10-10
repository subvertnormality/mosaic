# Current UI source inventory review

3 October 2026. This is source reference regeneration and a semantic review of existing source drift, not a new production UI or musical change.

## Why the original gate failed

The original source inventory described commit 56a9ba239526e7d01e757ea5e89f7ca5ad45e019 on 24 September, before the current live UI and subsequent 1.4.0 feature expansion. It recorded28 source files,64 grid callbacks,164 branches,284 controller anchors and119 manual headings. Running the full validator against the actual candidate returned 172 errors:123 stale branch locations,25 manual section digests,22 source digests, one missing manual section inventory and one callback registration inventory mismatch.

An isolated read of immutable HEAD file bytes, original inventory and original spec returned exactly the same 172 source errors. `baseline-source-inventory-failures.json` records every baseline source SHA and separates current-generated-artifact cross-snapshot checks. The issue therefore predates this vertical-list change. `full-validator-pre-refresh.log` preserves the candidate failure; the earlier `declarative-validation.log` remains distinct.

## Actual source meaning was reviewed

The prior changes are not all whitespace or line shifts. Stable descriptor metadata and owner accessors were added throughout the pages; `lib/ui.lua` now dispatches through the live adapter/router; grid outcomes and held-step notifications run after original handlers. Trigger algorithm entry/exit was extracted into one shared helper. Doctor READY Alignment accepts K3 through the same stopped-only helper as E3. Native UI motion, input-preserving splash, norns-input autosave reset and GC lifecycle were added.

The current feature editor additionally implements existing 1.4.0 Fragments, Interlock and Structure, actual Result/Reason reporting, structure-reference repairs, canonical v2 drafts and pattern/cycle commit feedback. Its false boolean formatter, full E2 delta, stable descriptor identity and paired planned/sent voice display differ from the old snapshot. These changes were already present at HEAD and are explicitly acknowledged; the refreshed source record does not claim they are draw-only or unchanged from September. Existing source/version/native evidence remains distinct. `current-source-review.json` records exact reviewed bytes and per-file meaning, including the newly converted renderer/live layer/runtime export.

## How regeneration avoids hash-only acceptance

The immutable original 386,355 byte inventory is preserved at `docs/ui-reimplementation/history/source-inventory-56a9ba239526e7d01e757ea5e89f7ca5ad45e019.json`. A new `refresh_source_inventory.py` requires an explicit review receipt pinning every current file and explaining its meaning. It verifies historical source hashes through git before aligning anything.

All 64 callback anchors match the same actual ordinal and registration kind. For161of164 branches, the original nonblank source lines remain in the same order within the mapped current callback, allowing only comments and six explicitly identified shape-in-use tooltip insertions; arbitrary inserted branch code is rejected. Three Trigger algorithm branches now point to the actual callback invocation of `algorithm_selected`; the tool separately requires the exact original guarded Doctor enter/leave actions and records their helper implementation lines. No arbitrary moved or changed branch is accepted. All 284 existing controller anchors remain actual matched source lines.

The 119 historical manual IDs are retained by exact unique heading, with actual current slice text/line/hash. Six new sections receive distinct MAN.CURRENT IDs: Screen Options, UI Motion, Fragments, Interlock, Structure, Result and Reason. Existing MAN identities are not renumbered. The active ledger also pins the three production files changed by this task. The review JSON has its own digest in the active inventory, and `--check` fails for later unreviewed bytes.

## Result and scope

The full validator now passes **without skips or relaxed checks**, with 31 source files,64 callbacks,164 branches,284 retained controller anchors and125 manual sections. `generated/source-review-receipt.json` provides individual old/current callback, branch and controller locations plus all reviewed source identities. Seven focused tool tests verify benign inserted-comment alignment and rejection of unreviewed bytes, hash-only notes, changed branch action, an inserted branch action even when original lines survive, changed callback kind and mismatched historical source identity. `full-validator-green.log` and `source-review-tests.log` retain results.

No production Lua, runtime export, router rule, value domain, emulator, native oracle or tolerance was edited in this regeneration. This is an updated source ledger; it does not substitute for actual native UI/Doctor acceptance or claim exhaustive behaviour coverage. If README, cheat sheet or any pinned source changes again, the strict gate must fail until that exact changed meaning is reviewed and a new receipt regenerated.

The subsequent explicitly reviewed source receipt now pins 32 files, adding `lib/rhythm_doctor/file_mailbox.lua` after the Doctor owner's complete-path budget correction. It also pins the semantic-label follow-up and the modal-footer lifetime fix after their separate red evidence. The original source inventory and prior candidate receipts remain unchanged. Full validation passes for this current 32-file ledger; no historical identity was relabeled.
