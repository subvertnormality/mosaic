#!/usr/bin/env bash
set -euo pipefail

ROOT="${GITHUB_WORKSPACE:?GITHUB_WORKSPACE is required}"
TEMP_ROOT="${RUNNER_TEMP:?RUNNER_TEMP is required}/mosaic-manual-ci"
EMULATOR_ROOT="${EMULATOR_ROOT:-$RUNNER_TEMP/monome-emulator}"
INSTALLATION="$EMULATOR_ROOT/.runtime/ci-qualified/runtime/installation.json"
AUDIO_BUILD="$TEMP_ROOT/audio-candidate"
AUDIO_TOOLS="$TEMP_ROOT/audio-tools"
AUDIO_INSTALL="$AUDIO_TOOLS/installation.json"
VOICE_ROOT="$TEMP_ROOT/voices"
MOD_ROOT="$TEMP_ROOT/output-mods"
NODE_ROOT="$TEMP_ROOT/playwright-node"
ARTIFACT_ROOT="$TEMP_ROOT/artifact"
EVIDENCE_ROOT="$TEMP_ROOT/build-runs"
EVIDENCE_ARTIFACT="$TEMP_ROOT/manual-build-evidence"
SOURCE_IDENTITY="$TEMP_ROOT/source-identity.json"
PROVISIONING_LOG="$TEMP_ROOT/provisioning.log"
# GitHub limits each job to six hours and real-time audio recording alone takes over three,
# so CI records audio in its own job (MODE=audio) and the build job (MODE=build) adopts that
# exact report through manual_build.py's strict --adopt-audio-report audits.
MODE="${MANUAL_CI_MODE:?MANUAL_CI_MODE must be audio or build}"
[[ "$MODE" == audio || "$MODE" == build ]] || { echo "Unknown MANUAL_CI_MODE $MODE" >&2; exit 2; }
AUDIO_BUNDLE_DIR="${AUDIO_BUNDLE_DIR:-$TEMP_ROOT/audio-bundle}"

mkdir -p "$TEMP_ROOT" "$EVIDENCE_ROOT" "$EVIDENCE_ARTIFACT"
if [[ -n "${PR_NUMBER:-}" ]]; then
  ARTIFACT_NAME="manual-site-pr-${PR_NUMBER}-run-${GITHUB_RUN_ID}-attempt-${GITHUB_RUN_ATTEMPT}"
else
  ARTIFACT_NAME="manual-site-dispatch-run-${GITHUB_RUN_ID}-attempt-${GITHUB_RUN_ATTEMPT}"
fi
echo "artifact_root=$ARTIFACT_ROOT" >> "$GITHUB_OUTPUT"
echo "evidence_root=$EVIDENCE_ARTIFACT" >> "$GITHUB_OUTPUT"
echo "artifact_name=$ARTIFACT_NAME" >> "$GITHUB_OUTPUT"
finalize() {
  local status=$?
  trap - EXIT
  set +e
  local found=()
  mapfile -t found < <(find "$EVIDENCE_ROOT" -mindepth 2 -maxdepth 2 -type f -name manifest.json -print 2>/dev/null)
  local args=(evidence-bundle --output "$EVIDENCE_ARTIFACT")
  if [[ "${#found[@]}" -eq 1 ]]; then args+=(--build-evidence "$(dirname "${found[0]}")"); fi
  if [[ -f "$SOURCE_IDENTITY" ]]; then args+=(--source-identity "$SOURCE_IDENTITY"); fi
  if [[ -f "$ARTIFACT_ROOT/manual-artifact-manifest.json" ]]; then args+=(--artifact-manifest "$ARTIFACT_ROOT/manual-artifact-manifest.json"); fi
  if [[ -f "$PROVISIONING_LOG" ]]; then args+=(--provisioning-log "$PROVISIONING_LOG"); fi
  local preflight_evidence="${PREFLIGHT_EVIDENCE:-}"
  if [[ -z "$preflight_evidence" && -f "$PROVISIONING_LOG" ]]; then
    preflight_evidence="$(awk '$1 == "Evidence" { path = $2 } END { print path }' "$PROVISIONING_LOG")"
  fi
  if [[ -n "$preflight_evidence" && -d "$preflight_evidence" ]]; then args+=(--extra-reference "$preflight_evidence"); fi
  python3 "$ROOT/.github/scripts/manual_artifact.py" "${args[@]}" || echo "Evidence bundle indexing reported a failure" >&2
  exit "$status"
}
trap finalize EXIT
exec > >(tee -a "$PROVISIONING_LOG") 2>&1
python3 - "$ROOT" "$SOURCE_IDENTITY" <<'PY'
import json
import subprocess
import sys
from pathlib import Path
root = Path(sys.argv[1])
status = subprocess.check_output(["git", "status", "--porcelain"], cwd=str(root), text=True)
if status.strip():
    raise SystemExit("Manual CI requires a clean source checkout")
commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(root), text=True).strip()
tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=str(root), text=True).strip()
out = Path(sys.argv[2])
out.write_text(json.dumps({"schema_version": 1, "commit_sha": commit, "tree_sha": tree}, indent=2) + "\n", encoding="utf-8")
print("Manual source identity:", commit, tree)
PY

if [[ -n "${PR_HEAD_SHA:-}" ]]; then
  actual_commit="$(git -C "$ROOT" rev-parse HEAD)"
  [[ "$actual_commit" == "$PR_HEAD_SHA" ]] || { echo "Checked-out source does not match PR head SHA" >&2; exit 2; }
fi

EMULATOR_REVISION="68ab70903d22500237ce68edc7e31c3b867cf179"
# The runtime cache restore may already have created $EMULATOR_ROOT/.runtime, so make
# the checkout in place rather than cloning into a non-empty directory.
if [[ ! -d "$EMULATOR_ROOT/.git" ]]; then
  mkdir -p "$EMULATOR_ROOT"
  git -C "$EMULATOR_ROOT" init -q
  git -C "$EMULATOR_ROOT" remote add origin https://github.com/subvertnormality/monome-emulator.git
  git -C "$EMULATOR_ROOT" fetch -q --filter=blob:none origin "$EMULATOR_REVISION"
fi
git -C "$EMULATOR_ROOT" checkout -q --detach "$EMULATOR_REVISION"
[[ "$(git -C "$EMULATOR_ROOT" rev-parse HEAD)" == "$EMULATOR_REVISION" ]]

# Reuse the behavior CI's qualified native provisioning and verifier.
EMULATOR_ROOT="$EMULATOR_ROOT" MONOME_EMULATOR="$EMULATOR_ROOT" \
  EMULATOR_REVISION="$EMULATOR_REVISION" bash "$ROOT/tests/behaviour/ci/prepare-emulator.sh"
test -s "$INSTALLATION"

# Fail in seconds on authoring mistakes before hours of native capture: the scene-plan
# lint (YAML booleans, unordered repeated selectors) and the manual tool unit suites.
# The two parameter-readout suites need a local report and are excluded.
if [[ "$MODE" == audio ]]; then
python3 "$ROOT/tools/manual_plan_lint.py"
mapfile -t MANUAL_UNIT_TESTS < <(cd "$ROOT" && ls tools/test_*.py tests/behaviour/test_manual_*.py | grep -v parameter_readout)
(cd "$ROOT" && MONOME_EMULATOR="$EMULATOR_ROOT" MOSAIC_REPO_ROOT="$ROOT" PYTHONPATH=tools:tests/behaviour PYTHONDONTWRITEBYTECODE=1 \
  python3 -m pytest -p no:cacheprovider -q "${MANUAL_UNIT_TESTS[@]}")
fi

mkdir -p "$VOICE_ROOT" "$MOD_ROOT"
python3 "$ROOT/.github/scripts/manual_runtime.py" clone-voices --lock "$ROOT/manual/voices.lock.json" --output "$VOICE_ROOT"

fetch_pin() {
  local name="$1" url="$2" sha="$3"
  local target="$MOD_ROOT/$name"
  git clone --no-checkout "$url" "$target"
  git -C "$target" checkout --detach "$sha"
  [[ "$(git -C "$target" rev-parse HEAD)" == "$sha" ]]
}
python3 "$ROOT/.github/scripts/manual_runtime.py" clone-modulation --output "$MOD_ROOT"

# The audio asset runtime is distinct from the qualified MIDI behavior runtime.
python3 "$ROOT/.github/scripts/manual_runtime.py" build-audio --emulator "$EMULATOR_ROOT" --output "$AUDIO_BUILD" --monitor-output "$AUDIO_TOOLS"
test -s "$AUDIO_INSTALL"

if [[ "$MODE" == audio ]]; then
  # The exact musical-audio-assets stage command from manual_build.plan (controlled-local).
  MONOME_EMULATOR="$EMULATOR_ROOT" python3 "$ROOT/tools/manual_audio.py" \
    --mod-code-root "$VOICE_ROOT" \
    --audio-install "$AUDIO_INSTALL" \
    --ffmpeg "$(command -v ffmpeg)" \
    --midi-emulator "$EMULATOR_ROOT" \
    --midi-controlled-install "$INSTALLATION" \
    --controlled-local
  # The audits reopen native evidence by absolute path, so bundle it with absolute paths.
  mkdir -p "$AUDIO_BUNDLE_DIR"
  python3 - "$ROOT" "$AUDIO_BUNDLE_DIR" <<'PY'
import hashlib, json, sys
from pathlib import Path
root, out = Path(sys.argv[1]), Path(sys.argv[2])
report = root / "manual/generated/audio-scenes.json"
data = json.loads(report.read_text())
runs = set()
for example in data["examples"]:
    for row in [example] + list(example.get("solo_contributions", [])):
        runs.add(str(Path(row["evidence"]["path"]).parent))
paths = sorted(runs) + [str(report), str(root / "manual/audio")]
(out / "paths.txt").write_text("".join(p.lstrip("/") + "\n" for p in paths))
(out / "report.sha256").write_text(hashlib.sha256(report.read_bytes()).hexdigest() + "\n")
print("Audio bundle:", len(runs), "native runs; report", (out / "report.sha256").read_text().strip())
PY
  tar -C / -cf "$AUDIO_BUNDLE_DIR/audio.tar" -T "$AUDIO_BUNDLE_DIR/paths.txt"
  exit 0
fi

# Restore the audio job's report, published clips and native evidence at their original
# absolute paths, after the clean-checkout identity check above.
tar -C / -xf "$AUDIO_BUNDLE_DIR/audio.tar"
AUDIO_REPORT_SHA256="$(cat "$AUDIO_BUNDLE_DIR/report.sha256")"
[[ "$(sha256sum "$ROOT/manual/generated/audio-scenes.json" | cut -d' ' -f1)" == "$AUDIO_REPORT_SHA256" ]]

# Browser tests use a versioned local dependency and browser cache; nothing is installed globally.
mkdir -p "$NODE_ROOT"
npm install --prefix "$NODE_ROOT" --no-audit --no-fund --save-exact playwright@1.51.1
export NODE_PATH="$NODE_ROOT/node_modules"
export PLAYWRIGHT_BROWSERS_PATH="$TEMP_ROOT/playwright-browsers"
"$NODE_ROOT/node_modules/.bin/playwright" install --with-deps chromium

# Recreate the authored Masks proof and its audio asset in this ephemeral runner.
# This is controlled visual generation plus real-time DSP asset recording; it is
# not the separate real-time visual/MIDI qualification campaign.
python3 "$ROOT/tools/manual_capture.py" \
  --source "$ROOT/manual/features/masks.yaml" \
  --controlled-local \
  --clock-mode controlled-experimental \
  --experimental-install "$INSTALLATION" \
  --audio-emulator "$EMULATOR_ROOT" \
  --audio-install "$AUDIO_INSTALL" \
  --mod-code-root "$VOICE_ROOT" \
  --ffmpeg "$(command -v ffmpeg)"
PREFLIGHT_EVIDENCE="$(awk '$1 == "Evidence" { path = $2 } END { print path }' "$PROVISIONING_LOG")"
[[ -n "$PREFLIGHT_EVIDENCE" && -d "$PREFLIGHT_EVIDENCE" ]] || { echo "Fresh Masks asset evidence was not recorded" >&2; exit 4; }
echo "Fresh controlled Masks and audio asset evidence: $PREFLIGHT_EVIDENCE"

python3 "$ROOT/tools/manual_build.py" \
  --controlled-local \
  --emulator "$EMULATOR_ROOT" \
  --audio-emulator "$EMULATOR_ROOT" \
  --controlled-install "$INSTALLATION" \
  --audio-install "$AUDIO_INSTALL" \
  --mod-code-root "$VOICE_ROOT" \
  --modulation-code-root "$MOD_ROOT" \
  --modulation-emulator "$EMULATOR_ROOT" \
  --modulation-controlled-install "$INSTALLATION" \
  --ffmpeg "$(command -v ffmpeg)" \
  --node "$(command -v node)" \
  --node-path "$NODE_PATH" \
  --quick-output "cheat_sheet.html" \
  --adopt-audio-report "$ROOT/manual/generated/audio-scenes.json" \
  --adopt-audio-report-sha256 "$AUDIO_REPORT_SHA256" \
  --artifacts "$EVIDENCE_ROOT"

mapfile -t manifests < <(find "$EVIDENCE_ROOT" -mindepth 2 -maxdepth 2 -type f -name manifest.json -print)
[[ "${#manifests[@]}" -eq 1 ]] || { echo "Expected exactly one final manual build manifest" >&2; exit 3; }
BUILD_EVIDENCE="$(dirname "${manifests[0]}")"
# Per-stage wall time, so runner headroom against the job timeout stays visible.
python3 - "${manifests[0]}" <<'PY'
import datetime, json, sys
parse = lambda value: datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
stages = json.load(open(sys.argv[1]))["stages"]
timed = [(s["name"], (parse(s["finished_utc"]) - parse(s["started_utc"])).total_seconds() / 60)
         for s in stages if s.get("started_utc") and s.get("finished_utc")]
for name, minutes in timed:
    print("%7.1f min  %s" % (minutes, name))
print("%7.1f min  total across %d timed stages" % (sum(m for _, m in timed), len(timed)))
PY

PACKAGE_ARGS=(
  package
  --repo-root "$ROOT"
  --build-evidence "$BUILD_EVIDENCE"
  --source-identity "$SOURCE_IDENTITY"
  --output "$ARTIFACT_ROOT"
  --repository "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
  --run-id "${GITHUB_RUN_ID:?GITHUB_RUN_ID is required}"
  --run-attempt "${GITHUB_RUN_ATTEMPT:?GITHUB_RUN_ATTEMPT is required}"
)
if [[ -n "${PR_NUMBER:-}" ]]; then
  PACKAGE_ARGS+=(--pr-number "$PR_NUMBER" --pr-head-sha "$PR_HEAD_SHA" --pr-base-ref "$PR_BASE_REF")
fi
python3 "$ROOT/.github/scripts/manual_artifact.py" "${PACKAGE_ARGS[@]}"
python3 "$ROOT/.github/scripts/manual_artifact.py" verify-site --site-root "$ARTIFACT_ROOT/manual-site" --node "$(command -v node)"

