# Generate, review and publish the manual

Manual generation and the exhaustive behaviour campaign are separate jobs. Local generation and the manual CI job use controlled-time native input for navigation, musical MIDI outcomes, screen/grid captures and the continuing course. Genuine DSP and stereo-ADC recordings still run in real time because they produce the manual’s audio assets. The existing exhaustive CI campaign provides the separate required real-time qualification.

A generated manual must cover every authored plan/profile, finish its lessons, pass binding and publication audits, and pass the browser checks. A new feature requires comprehensive regression coverage and a complete teaching lesson. A changed feature requires its affected tests, instructions, controls, captures and lessons to be updated together.

## Teaching review order

Finish the current application, lesson and player fixes and their affected controlled-time checks before recording new clips. Then generate the complete authored audio inventory and rebuild the manual with those recordings. Do not begin the scored teaching review against a partial recording batch or a stale compiled book.

Review every example in each of its lesson contexts, with its audio available. Score coherence, usefulness, understandability, how well the interaction represents the lesson, and the granularity of its steps. Every criterion must reach at least 8 out of 10; improve and re-review examples that fall below that threshold. If a later change affects a recording's captured behaviour, update the affected asset and rebuild before re-reviewing it. Preserve the original recording and review evidence.

## Generate locally

Run from the fresh manual checkout. Every native installation must match its emulator checkout. Python requires PyYAML and jsonschema. Browser checks require Node and the isolated Playwright installation. Audio requires the independently built norns runtime, JACK, SuperCollider, supported voice sources and ffmpeg. Modulation sources are separate from audio voice sources.

```sh
python3 tools/manual_build.py \
  --controlled-local \
  --emulator /home/andy/projects/monome-emulator-ci-combined \
  --controlled-install /home/andy/projects/monome-runtime-candidates/final-qualification-controlled-01/installation.json \
  --audio-emulator /home/andy/projects/monome-emulator-behaviour-audio-crow \
  --audio-install /home/andy/projects/monome-emulator-behaviour-audio-crow/.runtime/combined-audio-crow-tools-01/installation.json \
  --mod-code-root /home/andy/mosaic-manual-voices \
  --modulation-code-root /home/andy/projects/mosaic-output-mods \
  --ffmpeg /home/andy/mosaic-manual-tools/imageio_ffmpeg/binaries/ffmpeg-linux64-v4.2.2 \
  --node-path /home/andy/mosaic-manual-tools/node_modules \
  --quick-output cheat_sheet.html
```

The paths above describe the local development installation; configure equivalent matching paths on another host. Controlled local generation does not require `--real-install` or `--readability-real-install`. Separate `--modulation-emulator` and `--modulation-controlled-install` options select another matching modulation installation when needed.

Add `--plan-only` to print the plan without starting native sessions or writing evidence. The current complete controlled plan has 44 stages. That count is a snapshot of the current plan inventory, not a fixed completion rule: the builder and auditor derive required plans and scenes from the authored sources.

Leaving `--plans` unset selects every `manual/scene-plans*.yaml`. Repeated `--plans FILE` options support focused development, but a subset does not establish complete manual generation. Keep browser checks enabled for completion; `--skip-browser-tests` is only a development option.

The controlled path publishes its controlled native scenes with explicit scope. It retains real-time asset work for the actual musical recordings and Doctor’s public stereo-ADC recordings. Device-picker projections come from successful audio runs and preserve their real source frames and actions. Controlled generation omits the separate Doctor option qualification campaign. The independent behaviour CI workflow runs all six Manual/Auto × Stereo/L/R ADC combinations in real time, plus setup and saved READY checks in both timing lanes. Manual/R supplies the genuine saved-project fixture used by both READY runs. These ten scoped runs are audited separately from aggregate behaviour coverage; their report does not claim a complete regression run or hardware timing equivalence. The CI artifact retains selected reports, observations and native journals, not a complete copy of every runtime or project fixture.

## Evidence and completion

Each build creates a fresh directory under `--artifacts` (by default the checkout’s sibling `mosaic-manual-build-runs`). It keeps authoring snapshots, stage logs, exact native report paths and hashes, receipts and the final manifest. Native runs use the shared lock and leave no running sessions, held keys, active notes or modified user projects. A failure retains its evidence and does not claim completion; earlier successful publication stages may already have changed generated files.

After captures, the builder refreshes scene sources, rebinds captions, binds the continuing course and feature references, compiles the book and quick reference, regenerates the inventory from those final files, audits publications and runs the eight browser suites. Authoritative source and captured input/expectation identities must remain consistent. Historical failures and original captures remain immutable.

A successful controlled manual build has `manual_generation_complete: true`, `passed: true` and `renderer_validated: true`. It also retains `build_complete: false`, `complete_regression_run: false`, `controlled_time_admitted: false` and `realtime_qualification: pending-ci`. These values distinguish a complete generated manual from exhaustive real-time or physical-hardware qualification.

Validate the finalized build directory with the strict API:

```sh
PYTHONPATH=tools python3 - "$BUILD_EVIDENCE" <<'PY'
import json
import sys
from manual_publication_verify import audit_controlled_manual_generation
report = audit_controlled_manual_generation(
    sys.argv[1], require_manual_generation_complete=True)
if report.get("passed") is not True or report.get("manual_generation_complete") is not True:
    raise SystemExit("Final controlled manual audit did not pass")
print(json.dumps(report, indent=2))
PY
```

Set `BUILD_EVIDENCE` to the exact completed build directory. The API raises on invalid receipts; the example also exits unsuccessfully if a completion flag is missing. The strict audit requires the finalized manifest, complete plan/profile inventory, immutable before sources and current after sources, unchanged native logs/reports, valid raw publications, current compiled scenes and the course’s continuous publication proof.

`python3 tools/manual_publication_verify.py --controlled-local --build-evidence PATH` is an intermediate audit: its current CLI invokes `require_manual_generation_complete=False`. It must not be substituted for the finalized strict check used to release an artifact.

The builder does not independently change README/AGENTS authority. Regenerate `cheat_sheet.html` with `--quick-output cheat_sheet.html` to keep the established quick-reference URL; without that flag the default output is `manual/generated/quick-reference.html`.

## CI build and PR preview

The separate producer workflow is `Build manual site` (`.github/workflows/manual-build.yml`). It runs for opened, synchronized, reopened and ready-for-review pull requests targeting `main`, `codex/1.4.0` or `codex/rhythm-doctor-phrase`, and for `workflow_dispatch`. There is no push trigger or after-merge rebuild. It generates and strictly validates the complete manual, then packages the validated site and its provenance manifest. A failed or incomplete build does not produce a releasable preview.

A clean CI runner first captures Masks in controlled time and records its actual DSP audio through the audio worker. This bootstrap supplies fresh raw audio evidence rather than relying on paths from an earlier developer machine. The complete builder then replays Masks with the other authored plans and performs the final strict audit. Only the audio recording uses real time.

For an on-demand build, open Actions → Build manual site → Run workflow and select the source ref. The CI entry point is:

```sh
bash .github/scripts/manual-build.sh
```

The wrapper requires the GitHub Actions workspace/run environment and a clean source checkout. It provisions pinned runtime, voices, modulation and browser dependencies, runs `tools/manual_build.py --controlled-local`, and calls `.github/scripts/manual_artifact.py package` with the exact source identity, final build evidence, run and attempt. Packaging invokes the strict audit with `require_manual_generation_complete=True` and rejects missing completion flags. This entry point is distinct from the local command above.

CI uses the default `manual/generated/quick-reference.html`. Its site package also preserves the maintained root `cheat_sheet.html` and its local assets.

For a pull request, open its successful manual workflow run and download the artifact named `manual-site-pr-<PR>-run-<run_id>-attempt-<attempt>`. An on-demand run uses `manual-site-dispatch-run-<run_id>-attempt-<attempt>`. Preserve the accompanying manifest when unpacking. Serve the extracted `manual-site/` directory with a local HTTP server and open `/manual/`; do not open the HTML directly from the filesystem.

To inspect the downloaded preview, run from its extracted directory:

```sh
python3 -m http.server 8000 --bind 127.0.0.1 --directory manual-site
```

Open `http://localhost:8000/manual/`. This serves the packaged candidate; it does not regenerate it.

The separate `manual-build-evidence-<run_id>-attempt-<attempt>` artifact contains the build snapshots, receipts and a digest index. Both downloadable artifacts are retained for 90 days by the producer workflow.

The package layout is `manual-site/` plus `manual-artifact-manifest.json`. Run, attempt, tested tree and packaged file hashes identify the reviewed preview. The downloadable artifact is the exact candidate intended for subsequent deployment.

## Deploy after merging to main

`Publish manual site` (`.github/workflows/manual-publish.yml`) is a separate deploy-only consumer. Its consumer script is `.github/scripts/publish_manual.py`. It handles the successful producer completion and the pull-request merge to `main`, with on-demand dispatch on `main` as a fallback. The consumer downloads the successful producer’s artifact, validates its provenance, safely unpacks it and deploys the same validated site tree to GitHub Pages.

Deployment requires the tested tree to match the merged main tree. A preview for a different tree, a failed producer, an incomplete generation receipt or a modified package cannot be deployed. Producer completion and merge can arrive in either order; both conditions must be satisfied.

For the on-demand deployment fallback, open Actions → Publish manual site → Run workflow, select `main`, and enter the successful producer run ID in `producer_run_id`. The trusted consumer command in the workflow is:

```sh
python .github/scripts/publish_manual.py \
  --event-name "$GITHUB_EVENT_NAME" \
  --event-path "$GITHUB_EVENT_PATH" \
  --output-dir "$RUNNER_TEMP/verified"
```

The consumer uses the workflow’s read-only GitHub token to resolve and verify the producer, PR and artifact. Only its verified `manual-site/` subtree is passed to the Pages deployment job. An event with no matching merged and validated candidate does not deploy.

The publisher does not rebuild captures, scenes, audio, the compiled manual or the cheat sheet after merge. If main differs from the validated preview, generate and review a new matching artifact before deployment. The exhaustive real-time behaviour campaign remains a separate CI obligation; manual completion is not its replacement.

## Publish the merged 1.4.0 edition

The application work is merged to `codex/1.4.0`; the trusted Pages publisher still runs from `main`. To publish the validated static manual from that edition, use Actions → Publish manual site → Run workflow, select `main`, and set:

- `publication_policy`: `codex-1.4.0-promotion`.
- `promotion_artifact_kind`: `merged-pr` to reuse the original successful PR preview.
- `producer_run_id` and `producer_run_attempt`: the exact successful preview run and attempt.
- `promotion_pr_number`: the same-repository PR merged to `codex/1.4.0`.
- `promotion_pr_head_sha` and `promotion_pr_base_sha`: the head and base commits recorded on that merged PR.
- `expected_source_sha`: that PR's exact merge commit, which must still be the current `codex/1.4.0` branch tip.

The preview's tested tree must match the named merge tree. A different run attempt, fork, stale branch tip, unrelated descendant commit or modified artifact is rejected. Promotion preserves the original site and artifact manifest bytes; it does not merge application code into `main` or regenerate the manual. Automatic completion of a `codex/1.4.0` build does not publish it: this promotion route requires an explicit dispatch from trusted `main`.

If no eligible PR preview exists, use `promotion_artifact_kind: post-merge-dispatch` with a successful on-demand producer run on `codex/1.4.0` at that exact merge commit. Keep the other merged-PR identity inputs; this is a fallback, not a required second build.

Before deployment, the trusted publisher's versioned producer-tooling allowlist must contain the reviewed committed build workflow, driver and packager identities at the tested source ref, including any new producer dependencies. Working-tree candidate hashes alone do not establish a released allowlist. The publication receipt records both trusted publisher and tested edition identities alongside the original artifact hashes.

## Pilot and historical qualification

The previous complete builder plan had 73 stages covering separate real and controlled visual/MIDI lanes and additional qualification work. It is the legacy qualification path, not the current local/manual CI operator command. The controlled path above has 44 stages and keeps only genuine real-time asset recording alongside controlled manual generation.

The original pilot can still be reproduced for historical investigation with `tools/manual_capture.py`. Its visual/MIDI scenes and audio scope are narrower than the complete manual. `--visuals-only` is incomplete; controlled visual checks do not establish DSP or stereo-ADC recordings. The original capture checkouts were visual/MIDI `05fe7a1743f8517eaabb9184f2541e8bd6586935` and audio `801fcdcb9711e1054d898971942982862a30daf6`; use the exact matching installation when reproducing historical evidence.

`--reuse-visuals RUN_DIRECTORY` is a pilot recovery option with source/input/expectation and result/frame identity checks. It does not promise selective reuse of the complete current builder. A stage-gate resume is limited to that build’s exact paused coordination context. Cross-run checkpoint recovery is a separate opt-in controlled-only path described below; it is not an incremental CI cache.

Focused model/schema tests and the full existing Lua suite remain useful development checks. They do not replace native user-input behaviour acceptance. Current browser acceptance covers inline rendering, captured controls, every feature route, screen/grid data, encoded audio and seeking, delayed audio loading, narrative navigation, course progression and control-to-page links. Controlled timing remains distinct from host scheduling and physical-norns evidence.

## Recovering a failed controlled generation

Default generation and CI start fresh. For a failed controlled generation produced by the supported builder (`cdf8b1cb1fdca9d6d2384e7e954acc7f992ddf6e4ca0d9e5a3b48d3cc8afd0cc`), the controlled command above can additionally take:

```text
--resume-from /absolute/path/to/failed-build-directory
--resume-manifest-sha256 SHA256_OF_ITS_TERMINAL_MANIFEST
```

Both arguments are required together. Recovery creates a new attempt and preserves the failed parent. Each adopted reference stage must pass current source, runtime, emulator, native evidence and exact published-output checks. Doctor recordings can be reused only after the same current-source checks and a complete evidence-tree hash check; their original immutable report paths remain intact. Reused stages are explicitly marked `adopted-verified`, never presented as fresh executions. An unsupported parent builder or invalid lineage is rejected. A rejected individual capture is regenerated.

Masks and first-sound captures run fresh. A failed musical recording stage normally runs again with the corrected current setup. The independently reviewed recovery for the preserved eight-example music run is an explicit exception: `tools/manual_audio.py --resume-from /absolute/path/to/that-preserved-run` requires `--controlled-local` and the complete authored inventory, with the normal required runtime and encoder arguments. It verifies the pinned origin, current source/runtime identities, native results and provenance before adopting the 22 valid WAVs and recording the remaining 13 examples/32 WAVs. This is recovery of one qualified run, not a general cache. Its original failed report stays immutable; the new report must pass the full audio inventory and publication audit. Finish current fixes before recording, and make the completed audio available before scored teaching review. All downstream binding, compilation, inventory, publication and browser stages run fresh. The strict final audit rechecks parent lineage and current file hashes. Recovery does not establish real-time or hardware qualification; those remain pending CI. Actual audio recording is allowed when needed to generate an asset.
A recovered build can begin with historical native-captured review ledgers and a separately approved review of current lesson sources. Keep these distinct: changing the ledgers before reuse invalidates native source identity. The captured application files remain exact throughout generation. A physical prebuild snapshot must preserve the original three ledgers and the source bytes identified by the approved overlay.

After the complete build and its ordinary strict native audit pass, explicit reconciliation can update the documentary review ledgers:

```sh
python3 tools/manual_reconcile_build.py \
  --build-evidence "$BUILD_EVIDENCE" \
  --manifest-sha256 "$BUILD_MANIFEST_SHA256" \
  --prebuild-snapshot "$PHYSICAL_PREBUILD_SNAPSHOT" \
  --approved-review-overlay "$APPROVED_OVERLAY_BUNDLE" \
  --overlay-sha256 "$APPROVED_OVERLAY_SHA256" \
  --metadata-transition-proof "$EXTERNAL_TRANSITION_PROOF" \
  --native-identity "$ORIGINAL_NATIVE_IDENTITY" \
  --evidence "$RECONCILIATION_EVIDENCE"
```

The overlay, snapshot and completed manifest are pinned separately. Reconciliation reproduces generated scene sources and binding metadata, preserves teaching text and native callback/controller/manual identities, and regenerates the inventory from the qualified sources. It rolls back all three ledgers if source validation, deterministic proof replay or the final native audit fails. Keep the transition proof outside the repository.

The explicit post-reconciliation strict audit adds `metadata_transition_proof=EXTERNAL_TRANSITION_PROOF` to the API example above. It proves that **243 of the 246 Mosaic application identity files match exactly, while the three documented review-ledger files pass the verified metadata transition**. The original captured bytes still have to match their native identities. Lua, capture helpers, other metadata, voices and runtime inputs receive no exception. Default fresh CI and audits continue to require all native application files to match exactly.
