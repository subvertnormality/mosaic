# Generate, review and publish the manual

Manual generation and the exhaustive behaviour campaign are separate jobs. Local generation and the manual CI job use controlled-time native input for navigation, musical MIDI outcomes, screen/grid captures and the continuing course. Genuine DSP and stereo-ADC recordings still run in real time because they produce the manual’s audio assets. The existing exhaustive CI campaign provides the separate required real-time qualification.

A generated manual must cover every authored plan/profile, finish its lessons, pass binding and publication audits, and pass the browser checks. A new feature requires comprehensive regression coverage and a complete teaching lesson. A changed feature requires its affected tests, instructions, controls, captures and lessons to be updated together.

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

Add `--plan-only` to print the plan without starting native sessions or writing evidence. The current complete controlled plan has 43 stages. That count is a snapshot of the current plan inventory, not a fixed completion rule: the builder and auditor derive required plans and scenes from the authored sources.

Leaving `--plans` unset selects every `manual/scene-plans*.yaml`. Repeated `--plans FILE` options support focused development, but a subset does not establish complete manual generation. Keep browser checks enabled for completion; `--skip-browser-tests` is only a development option.

The controlled path publishes its controlled native scenes with explicit scope. It retains real-time asset work for the actual musical recordings and Doctor’s public stereo-ADC recordings. Device-picker projections come from successful audio runs and preserve their real source frames and actions. Controlled generation omits the separate seven-run Doctor option qualification campaign; that real-time qualification belongs to the independent behaviour campaign.

## Evidence and completion

Each build creates a fresh directory under `--artifacts` (by default the checkout’s sibling `mosaic-manual-build-runs`). It keeps authoring snapshots, stage logs, exact native report paths and hashes, receipts and the final manifest. Native runs use the shared lock and leave no running sessions, held keys, active notes or modified user projects. A failure retains its evidence and does not claim completion; earlier successful publication stages may already have changed generated files.

After captures, the builder refreshes scene sources, rebinds captions, binds the continuing course and feature references, regenerates the inventory, compiles the book and quick reference, audits publications and runs the seven browser suites. Authoritative source and captured input/expectation identities must remain consistent. Historical failures and original captures remain immutable.

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

## Pilot and historical qualification

The previous complete builder plan had 72 stages covering separate real and controlled visual/MIDI lanes and additional qualification work. It is the legacy qualification path, not the current local/manual CI operator command. The controlled path above has 43 stages and keeps only genuine real-time asset recording alongside controlled manual generation.

The original pilot can still be reproduced for historical investigation with `tools/manual_capture.py`. Its visual/MIDI scenes and audio scope are narrower than the complete manual. `--visuals-only` is incomplete; controlled visual checks do not establish DSP or stereo-ADC recordings. The original capture checkouts were visual/MIDI `05fe7a1743f8517eaabb9184f2541e8bd6586935` and audio `801fcdcb9711e1054d898971942982862a30daf6`; use the exact matching installation when reproducing historical evidence.

`--reuse-visuals RUN_DIRECTORY` is a pilot recovery option with source/input/expectation and result/frame identity checks. It does not promise selective reuse of the complete current builder. A stage-gate resume is limited to that build’s exact paused coordination context; it does not create a general selective rebuild feature.

Focused model/schema tests and the full existing Lua suite remain useful development checks. They do not replace native user-input behaviour acceptance. Current browser acceptance covers inline rendering, captured controls, every feature route, screen/grid data, encoded audio and seeking, delayed audio loading, narrative navigation, course progression and control-to-page links. Controlled timing remains distinct from host scheduling and physical-norns evidence.
