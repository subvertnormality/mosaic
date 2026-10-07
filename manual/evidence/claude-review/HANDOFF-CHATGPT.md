# Handoff to ChatGPT: finish the Mosaic 1.4.0 interactive manual (written 2026-10-06 ~18:45 BST by Claude)

Round 4 has NOT started. Everything below is verified against the files, logs and GitHub on 2026-10-06 evening unless marked "unverified".

## STATE AT HAND-OFF (2026-10-07 morning, written by Claude; supersedes any "build is running" statement below)

- **No controlled-local build has completed.** Resume chain `-08` to `-19` (under `/home/andy/mosaic-manual-build-runs/`) fixed one latent defect per pass. Passing now: every capture and Doctor stage, `musical-audio-assets` (refreshed audio report adopted), `raw-publication-audit`, `caption-rebind`, `course-bind`, `feature-bind`, `compile-book`. Failing: `reader-projection` (Codex's teaching bindings, see below). Not yet run in this lineage: the 8 browser suites, final publication audit, reconcile.
- **Per owner: do NOT rerun the build for Round 4.** Review the outputs as they stand (`manual/generated/*.json` including `book.json`, `reader-*`; the audio under `manual/audio/`; `manual/features/`, `manual/course.yaml`). Build fixes continue separately.
- **What this session fixed** (all in this commit): resume adoption lineage for doctor/reference stages; pilot audio receipt refresh in controlled mode (`refresh_pilot_editorial`); Song queued-transition audit now 32 steps; independent native verifiers for `manual-motion-pose`, `manual-song-repeat-advance`, `manual-modulation-cc-phase`; motion proof allows pose rows between mini proof and summary; native-public-gaps verifier selects one playback per Start segment; `reader-index.json` excluded from native scene catalogues (`caption-rebind`, `feature-bind`); `feature-bind` accepts `controlled-verified` input; removed duplicate `course-getting-started` starting state (a `start` step replaces it); course teaching bindings: four stages now `interval` where finer capture steps were added, Masks "Restore the channel default" now binds to its playback step, `masks-clear` starts from it, and Sequence composition "bass-route" covers device, assign, range and octave while "both" is play only.
- **Audio editorial refresh (new):** `note-merge-modes` listed scene id `merged-pentatonic-off` as a feature; corrected to `lock-merged-to-pentatonic` in `manual/audio-scenes.yaml`. Instead of re-recording 3.3 h, `tools/manual_audio_editorial.py` re-published the passed report with only `feature_ids` changed (`publication.kind: editorial-refresh`); the native report `3a90ec4d...` is preserved in the native run `/home/andy/mosaic-manual-audio-runs/b0e3fb65e8df41be94c83aacc6ff191c/audio-scenes.json`; refreshed report sha256 `3396e9e75f11dd66482fb85c3dc58997efdcb591801c37622dcd49a1ff1fe0bd`. The audit enforces that nothing but `feature_ids` differs from the native recording's own `source.yaml`. NOTE: CI records its own audio from the corrected source (new identity, ~3 h).
- **Next known failure, `reader-projection`:** run it standalone in about a minute with a scratch copy of `proj_try.py` (wrap `manual_teaching_v8._native` / `_validate_output` to print the failing scene) instead of a full resume. Latest: scene `mask-precedence`, step `clear-channel` (feature binding in `manual/features/reference-workflow.yaml` and `reference-locks.yaml`): "Mask readout must resolve to one exact source-authored checkpoint in the transition". Expect more of the same class across Codex's 127 teaching bindings; fix each in `manual/course.yaml` / `manual/features/*.yaml`, re-run `python3 tools/manual_book.py` (about 30 s) then the standalone projection.
- **CI:** manual run 37503722733: audio job passed, build job failed immediately because the Masks provisioning `manual_capture.py` call in `.github/scripts/manual-build.sh` lacked `MONOME_EMULATOR` (fixed and re-pinned in `publish_manual.py`). Behaviour run 37503722722 failed for missing `python3-yaml` (added to `behaviour.yml`). Push triggers fresh runs of both; expect further first-time failures.
- **Not committed:** generated outputs (`manual/audio/*`, `manual/generated/*`, `manual/features/*` rewrites by bind stages, `manual/book.yaml`, `manual/scene-captions.yaml`, evidence) stay in the local checkout `/home/andy/mosaic-manual-1.4.0` only, because they come from an unfinished build. Disk: freed about 19 GB from `/home/andy/mosaic-manual-runs` (unreferenced runs only).
- **Reviewer/refiner models (owner):** ChatGPT 6.1 Sol low-effort agents score; ChatGPT 6.1 medium-effort agents refine.

## 0. Mission

Take the Mosaic 1.4.0 interactive manual from "full build passing" to "published", through these gates, in order:

1. A complete controlled-local build passes (in progress, section 2) and the same build passes in GitHub CI (section 3).
2. Round 4 scoring: every unit scores at least 8 on coherence, usefulness, understandability, representation and granularity. Iterate fix, recapture, rescore until true.
3. Reconcile and strict audit; reinstall `authority-controlled-activation-20261004` and activate authority.
4. Astra (adversarial) final review covering F01 to F11; update `ASTRA-REVIEW-CLOSURE.md`; leave `manual/ADVERSARIAL_REVIEW.md` unchanged.
5. Publish: PR to `codex/1.4.0` (draft PR #106 already exists) plus a separate docs-only Pages branch based on `main`. Never merge application changes to `main`. Publication is approved only for a finished edition.

The owner's standing priority: quality over wall clock. Do structural fixes, not wording workarounds, to reach the score thresholds.

## 1. Where things are

- Checkout: `/home/andy/mosaic-manual-1.4.0`, branch `manual/1.4.0-interactive`. Its local HEAD is `1867886c`; `origin/manual/1.4.0-interactive` is 4 commits ahead (`815ddae2`, `01afe9eb`, `02ed31ef`, `8d7de4df`), made from a scratchpad worktree (`claude/retakes`, same tip as origin). The checkout's working tree also holds uncommitted build outputs (`manual/audio/*`, `manual/generated/*`, evidence). `tools/audio_report_adoption.py` and its test are already byte-identical to origin. Before pulling, run `git diff origin/manual/1.4.0-interactive -- tools .github tests` and reconcile deliberately. Never reset, clean, stash or checkout over this tree.
- PR: https://github.com/subvertnormality/mosaic/pull/106 (draft, base `codex/1.4.0`). The auto-mode classifier refused `gh pr create` for Claude; the owner opened it. Do not work around such denials; ask the owner.
- Prior state notes: top of `manual/evidence/claude-review/HANDOFF-CODEX.md` (Codex) and its Claude sections at the bottom. Receipts: `/home/andy/mosaic-manual-build-operators/*-20261006-*`. Review rounds 1 to 3: `/home/andy/mosaic-manual-build-operators/claude-review-round{1,2,3}`; improvement rounds: `.../claude-improve-round{1,2,3}` (`impl/*.md` has the implementation reports); round-4 tooling: `.../claude-review-planning/` (`make_dispatch.py`, `validate_review_reports.py`, `focused_recapture.py`).
- Round 3 result for calibration: only 6 of 203 units were at least 8 on all five dimensions; 734 sub-8 scores, mostly 6 and 7, weakest on representation, understandability and granularity; nobody questioned the overall structure. Since then 189 proposals plus structural fixes (finer course stages, new behaviour cases, two real Strum bugs fixed, new audio lessons, Codex's 127 teaching bindings) landed, so expect a much better round 4, but one more fix-and-rebuild cycle is likely.

## 2. The local build now running

- Build `-08`: log `/home/andy/mosaic-manual-build-runs/full-controlled-local-20261006-08.log`, evidence dir `.../full-controlled-local-20261006-08/<run-id>/`. Started ~18:22; at 18:39 it was on stage 3 (closure capture). Expected 1.5 to 2 hours.
- It RESUMES from failed build `-05` (manifest `/home/andy/mosaic-manual-build-runs/full-controlled-local-20261006-05/8f6cd816b829401e9b989538e0c814c3`, sha256 `64dffc9b8e6df3e2373eff96d353eed69c9c202442e4cfc59fc6a13590d1ad77`): 19 capture/Doctor stages adopted, 5 re-run because the strict adoption proof rejected them (closure: "Changed literal Song queued transition contract"; extra and musical: "not an exact reconstruction"; modulation-macro: unsupported kind `manual-modulation-cc-phase`; native-public-gaps: "relative complete native MIDI differs"). If a re-run of those fails, that is a real signal; investigate, do not bypass.
- It ADOPTS the complete audio report from the audio-only resume run: all 21 examples, `manual/generated/audio-scenes.json` sha256 `3a90ec4dc5c824d98f70f8e955844d2c98615e3e5dc6331746f52a572eae6b81` (provenance kind `strict-same-lineage-audio-resume`). Adoption already passed its strict audits.
- Exact command (cwd the checkout; `MONOME_EMULATOR` is required for in-process audio adoption):

```
MONOME_EMULATOR=/home/andy/projects/monome-emulator-behaviour-audio-crow /usr/bin/python3 tools/manual_build.py \
  --emulator /home/andy/projects/monome-emulator-ci-combined \
  --real-install I --controlled-install I --readability-real-install I \
  --audio-emulator /home/andy/projects/monome-emulator-behaviour-audio-crow \
  --audio-install /home/andy/projects/monome-emulator-behaviour-audio-crow/.runtime/screen-shutdown-tools-01/installation.json \
  --mod-code-root /home/andy/mosaic-manual-voices --modulation-code-root /home/andy/projects/mosaic-output-mods \
  --ffmpeg /home/andy/mosaic-manual-tools/imageio_ffmpeg/binaries/ffmpeg-linux64-v4.2.2 \
  --node-path /home/andy/mosaic-manual-tools/node_modules \
  --artifacts <NEW dir under /home/andy/mosaic-manual-build-runs> --quick-output cheat_sheet.html --controlled-local \
  [--resume-from <failed build dir> --resume-manifest-sha256 <its manifest sha>] \
  [--adopt-audio-report manual/generated/audio-scenes.json --adopt-audio-report-sha256 <sha>]
```
  where `I=/home/andy/projects/monome-runtime-candidates/final-qualification-controlled-01/installation.json`.
- While it runs: do NOT edit `lib/`, `tests/behaviour/` or `manual/` sources (any edit invalidates in-flight captures as "source changed"); a `.pytest_cache` in the tree does the same, so run pytest with `-p no:cacheprovider` and `PYTHONDONTWRITEBYTECODE=1`. Appending to `manual/evidence/**` markdown has been safe. Keep CPU free during any real-time audio recording: a local test run caused a 19 ms late onset and a failed take.
- When it finishes: check `manifest.json` (`passed`, `build_complete`, every stage `returncode` 0), the audio inventory (21 examples), the 8 browser suites and the publication audit. Then commit the generated outputs on top of origin's tip (see section 1).
- If a stage fails late, RESUME instead of restarting: stage resume works from a parent built by the same builder (`resume_adoption.supported_lineage`); every adopted stage is re-proved against current sources, so edits to sources that a stage depends on make it re-run. Audio resume (`tools/manual_audio.py ... --controlled-local --resume-from <failed audio run dir>`) reuses completed examples only when the recording identity is byte-identical, including `tools/manual_audio.py` itself. Do not edit `manual_audio.py` between a failure and its resume. The checkout's copy lacks the retake helper that origin has (commit `815ddae2`); pulling it changes the tool hash, so a failed run recorded without it cannot be resumed after the pull.

## 3. CI state (the part most likely to bite you)

Workflows: `.github/workflows/manual-build.yml` (two jobs: `record-audio`, then `build-controlled-manual` after `needs`), `manual-publish.yml`, and the existing `behaviour.yml`. `.github/scripts/publish_manual.py` pins `manual-build.yml` and `manual-build.sh` by SHA-256; re-pin both (dated comment) whenever either changes, and run `tests/manual_ci` (33 tests).

- Run 37503722733 (commit `8d7de4df`) "Build manual site" is in progress. Audio job started ~17:25 and should take ~3 h; it stores its bundle as artifact `manual-audio-src-<identity>` (30 days) so later pushes with identical audio inputs skip recording. Then the build job (~2.5 to 3 h). Both jobs have a 6 h limit.
- Run 37503722722 "Full behaviour suite" FAILED: every Base MIDI shard, the profile jobs and coverage. Cause (from a shard's `suite.json`): `ModuleNotFoundError: No module named 'yaml'` at `tests/behaviour/manual_authority.py` imported by `tests/behaviour/run.py`. The apt line for the behaviour jobs in `.github/workflows/behaviour.yml` (lines ~78 and ~479) lacks `python3-yaml` (and possibly `python3-jsonschema`). Ten new test modules were also unclassified; that was fixed in `8d7de4df`. Adding `python3-yaml` is the likely next fix; expect further, different failures after it. Push it only AFTER the audio job above has uploaded its `manual-audio-src-*` artifact (check the run's artifacts): a push cancels the in-progress manual run (concurrency `cancel-in-progress`), and the audio identity excludes workflow files, so the next run then reuses the audio.
- `Run tests` and `Rhythm Doctor components` pass.
- CI differs from local: Ubuntu 20.04 container, Python 3.8, pytest 4.6 (`python3-pytest`), git 2.25 (no `fetch --filter` without partial-clone config), emulator pinned at `68ab709` (local `monome-emulator-ci-combined` differs only by an opt-in perf-profile feature the manual never enables; a CI-vs-local capture-hash comparison is still owed and would prove it), audio runtime built with `--sdl-ownership --screen-worker-shutdown`. Python 3.8 and 3.11 produce different `ast.dump` hashes, so the AST pins in `tests/behaviour/test_manual_build.py` are per-version. Lint workflows with `actionlint` (no shellcheck).
- Real-time lanes for the new behaviour cases (both Strum fixes, M-TRANS-010/011, M-RANGE-LCM-001, M-RANGE-REJECT-006, M-CHORDSHAPE-260, M-LIVEUI-SHAPETRIG-002, closure cases) are in the behaviour campaign and still unproven in CI; they are the expected next failure surface after the yaml fix.

## 4. Round 4 (owner's instructions, latest)

**Owner directives for this phase (override anything below):**
- Do NOT rerun the manual build. Do not start, resume or restart `tools/manual_build.py` or any capture/audio stage. Go straight to the Round 4 review on the existing build outputs (the local build `-08` is Claude's to finish; use its outputs, or the latest passing outputs, as they stand).
- Reviewers/scorers: ChatGPT 6.1 Sol agents at LOW effort.
- Refinement (fixing sub-8 units): ChatGPT 6.1 at MEDIUM effort.
- Rebuilds only happen later, once refinement is done and the owner says so.

1. Verify the book and reader on the fresh build; serve it for the owner to look at (they use Windows and WSL; the user can read `\\wsl.localhost\Ubuntu-20.04\home\andy\mosaic-manual-1.4.0`).
2. Score with parallel independent reviewers using `claude-review-planning/make_dispatch.py` and validate with `validate_review_reports.py`; reports are JSON with per-dimension score, reason, evidence and improvement. Units are scenes, recipes, course stages and audio recordings (203 in round 3). Use ChatGPT 6.1 Sol low-effort reviewers (per owner); keep scoring independent of authoring.
3. Concentrate first on Codex's new, never-reviewed material: 127 teaching bindings across 58 features, the practical Masks lessons, new course stages. A small early sample will show systematic problems before the full round.
4. For every sub-8 score make a structural fix (new or finer scenes, placement, step size, captions tied to the capture), recapture only affected plans with `focused_recapture.py <newdir> [--keep-going] [scene-plans-*.yaml ...]`, then do one more full build and rescore only failing units.
5. Then: reconcile and strict audit; reinstall and activate authority; Astra final review (F01 to F11); update `ASTRA-REVIEW-CLOSURE.md`; put evidence in `manual/evidence/claude-review/`; publish.
6. Still owed: a save/load case for slot-specific Strum; re-freeze the musical-plan pin in `tests/behaviour/test_manual_documentation_frame_selectors.py` (with review).

## 5. What was learned today (so you do not relearn it)

None of these were Mosaic bugs except where stated; all were pipeline authoring or environment faults.

- Macro 1 lesson (`tools/manual_extra_matrix_macro_modest.py`, a read-only file; `chmod u+w` to edit, then restore): a CC is sent once at playback start for a device parameter (not per onset); the menu route back after the halfway phase is M-MOD-004's `E1 -4, K3 x3` with no K1.
- UI motion pair row, probability readout binding and occurrences, and YAML booleans: fixed; `tools/manual_plan_lint.py` (in the unit suite and CI) now rejects unquoted yes/no/on/off and repeated identical selectors without increasing `occurrence:`; capture fails fast on out-of-order binding.
- Audio: a part entering after step 0 (song-sections Polyperc enters on step 18) was timed from the first heard onset; fixed with `witness_origin()` in `tools/manual_audio.py`. Real-time takes can miss the 10 ms tolerance under host contention; `take_with_retakes` retakes at most twice, only for "Musical onset"/"Musical gate" misses, keeps failed takes as evidence. Local audio must use `.runtime/screen-shutdown-tools-01` (the default `combined-audio-crow-tools-01` lacks teardown fixes and matron segfaults at shutdown).
- `tools/audio_report_adoption.py` accepted only `.cjs` harness names; now `.py` and `.cjs` bare names.
- Earlier this session: two real Strum bugs fixed in `lib/` (slot-specific strum gate release, per-slot stock trig params), a Lua suite of 2455 tests passes from a full copy named `mosaic` (the repo's `test.sh` fails in place).

## 6. Standing constraints (all from the owner)

- Never restart WSL. No global filesystem sync. Do not kill unrelated processes (parallax `measure_currentness.py`, mutmut, paranoia sessions, the `node manual_teaching_fixture.cjs` preview).
- Local behavioural checks use controlled time only; real time only for genuine audio assets and real-time CI. Keep native jobs serial (`/tmp/mosaic-manual-native.lock`).
- Do not reset or clean the worktree. Do not change the monome emulator to imitate a Mosaic bug. Do not weaken oracles, tolerances or cleanup. Do not fabricate screenshots, MIDI or audio, and do not hand-edit compiled JSON.
- Preserve failed evidence and never relabel it. Leave `manual/ADVERSARIAL_REVIEW.md` unchanged. Respect auto-mode classifier denials (do not retry another way).
- Disk was 18 GB free at 18:40 (350 GB volume). Run evidence under `/home/andy/mosaic-manual-runs` (~49 GB) and `.../mosaic-manual-audio-runs` (~19 GB) is kept on purpose; prune only superseded runs after a reference check, and never other projects' temp (parallax holds ~32 GB in `/tmp/claude-1000`).
- Test commands: Python suites `PYTHONPATH=tools:tests/behaviour PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider`, excluding `tools/test_manual_parameter_readout.py` and `tools/test_manual_teaching_parameter_readout.py` (they need env vars). Run CI-exact checks under `/usr/bin/python3` (3.8) with pytest 4.6.9; the throwaway copy lived in Claude's scratchpad (`.../scratchpad/pytest38`, may be gone: `pip install --target <dir> --python-version 3.8 --only-binary=:all: pytest==4.6.9`).
