# CI stage and AST guard audit — 2026-10-08

**Decision:** Accept the strict plan/AST re-pin in candidate v04 for the focused CI test correction only. This does not qualify a complete build or campaign.

The reviewed source snapshot is commit `9efbd8ad7fe3ae96e36db7386e3a3d0fa5be5ca0`, tree `13bc90a62d0e176d2ab8d80c9e091cf90aa28534`. Its current inventory has 22 plan files, 82 full-build stages, and 49 controlled-local stages. The 82-stage full plan adds exactly `fresh-target-midi-producer`, `reference-real-scene-plans-save-dialog-base-midi`, and `reference-controlled-scene-plans-save-dialog-base-midi` on top of the old 79-stage expected count. Controlled-local includes only the controlled Save Dialog stage, yielding 49.

The pinned -23 run manifest SHA-256 is `a8a3d59ade436592ee118658b6b720943c7551f4dd3f1a203b5bbe8737b42b0b`. It contains 48 passed stage receipts over 21 selected plan files, is `manual_generation_complete=true`, and remains `build_complete=false`; it does not include the Save Dialog plan. Therefore -23 supports the prior controlled-local baseline, but does not qualify either the new Save Dialog stage or the full-only producer.

The two Save Dialog rows come from `manual/scene-plans-save-dialog.yaml` (SHA-256 `e1a7a6aafc5730805131177bf29e8b0d50b850fe7ca0926828e2512927af86ec`). Separate native acceptance `ACCEPTANCE.json` (SHA-256 `27dcdde32a229ff4dd1644b8a0e6218bc75f0f63239333c933bd5c492090514c`) passed nine checkpoints and verified 259 cache files, but explicitly limits itself to one supplementary controlled scene; it is not full campaign or realtime qualification.

The full-only fresh MIDI producer is source-bound to the full-build path: its targets must resolve beneath the current build evidence root, per-scene evidence files and identity are hashed, and projection/publication rechecks the producer receipt, manifest and log. The source SHA-256 is `a1b3e3f56f62afa0982a3f094ad2cfb2a583868c090a287f43816c15f6adb82b`. The retained-target admission receipt (`8a5aca9c…8446a`) remains the explicit controlled-local route. I found no dedicated unit test importing `manual_fresh_target_midi.py`, so this source inspection does not independently qualify its implementation.

Candidate v04 patch SHA-256 is `258ee8664fb6ef4afd011234a07f77fbab8f5f4b05d71d0bba0c32a92da330dc`; candidate manifest SHA-256 is `5a2e9adfef1c9c44fc73e4945ec0d715c0ed668028e20789a9ed9acde98c93e7`. It keeps the strict whole-plan/AST guard, separates the 2026-10-06 receipted stages from the three 2026-10-08 source-derived stages, and asserts producer ordering (`compile-book < producer < reader-projection`) and real-before-controlled Save Dialog ordering.

Python 3.8.5 AST pins: `plan` `bb30ac13547f93247bc0f3e7a578c99405ddf5c11d0daf6423479f01ccb6f030`; `stage_command` `22493e17bf42d6d3f55b23e5dd811ae88b11e2c294d1d9157511f5113b405ca6`; `run_stage` `1e9e336208e2984f2398337a64016ec12d3f3b78cee671a992905480c654bd4e`. Python 3.11.9 pins: `plan` `9eba758e7929c0a1a07d62d4696032ab07b219d2dea273bb8f5b8b8d3b6f3450`; `stage_command` `33bf4501400164ff560fcaeac4d116b7498ba94f6e35f36bcd439cc68738f5e0`; `run_stage` `45e39ed119b3eafc264bf891046f380f6fcac75d7cfd015e2f9f641e32f7289c`.

I independently reran candidate v04 tests: build-plan suite 62/62 on Python 3.8.5 and 3.11.9; reconcile plan suite 63/63 on Python 3.8.5; publication verifier 73 passed with two `MONOME_EMULATOR`-only skips. Candidate manifest records controlled-generation integrity 2/2 passed (unchanged from v03). The baseline AST test was confirmed red on Python 3.8.5 at the expected stale `plan` pin (`bb30ac…` versus old `78cf0c…`).

No production files were changed and no native jobs, builds, or audio captures were launched.
