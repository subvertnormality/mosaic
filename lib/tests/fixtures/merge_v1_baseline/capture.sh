#!/usr/bin/env bash
# Captures the Merge Shape v1 baseline oracle from the BASE revision.
#
# Usage: capture.sh <base-checkout>/mosaic
#
# <base-checkout>/mosaic must be a clean checkout of exactly f908a553 (the
# directory must be named "mosaic" so the harness's include() resolves) with
# submodules initialised and lib/tests/test_artefacts present. The scenario
# (scenario.lua) and the capture test (capture_tests.lua) from this directory
# are copied into that checkout, run there with the base's own lib/tests
# harness, and removed again. The v1 project files the base saved and the
# observations it made are written here with provenance headers, and
# MANIFEST.lua records the source revision and the sha256 of every capture
# input and output. The candidate replay test
# (lib/tests/lib/merge_v1_baseline_oracle_tests.lua) refuses fixtures whose
# hashes or inputs no longer match, so a candidate cannot regenerate them.
set -euo pipefail

BASE_REVISION=f908a5530e435a8c412a3f295783344a471a7b40
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
base="${1:?usage: capture.sh <base-checkout>/mosaic}"
base="$(cd "$base" && pwd)"

[ "$(basename "$base")" = mosaic ] || { echo "base checkout directory must be named mosaic" >&2; exit 2; }
head="$(git -C "$base" rev-parse HEAD)"
[ "$head" = "$BASE_REVISION" ] || { echo "base is $head, not $BASE_REVISION" >&2; exit 2; }
if [ -n "$(git -C "$base" status --porcelain --untracked-files=no)" ]; then
  echo "base checkout has tracked modifications" >&2; exit 2
fi
tree="$(git -C "$base" rev-parse 'HEAD^{tree}')"

scratch="$(mktemp -d)"
copied_scenario="$base/lib/tests/fixtures/merge_v1_baseline/scenario.lua"
copied_test="$base/lib/tests/lib/zz_merge_v1_baseline_capture_tests.lua"
cleanup() { rm -f "$copied_scenario" "$copied_test"; rmdir "$base/lib/tests/fixtures/merge_v1_baseline" "$base/lib/tests/fixtures" 2>/dev/null || true; rm -rf "$scratch"; }
trap cleanup EXIT
mkdir -p "$(dirname "$copied_scenario")"
cp "$here/scenario.lua" "$copied_scenario"
cp "$here/capture_tests.lua" "$copied_test"

(cd "$base/lib/tests" && MERGE_V1_CAPTURE_OUT="$scratch" lua run_tests.lua test_capture_merge_v1_baseline)

sha() { sha256sum "$1" | cut -d' ' -f1; }
inputs_scenario="$(sha "$here/scenario.lua")"
inputs_test="$(sha "$here/capture_tests.lua")"
inputs_script="$(sha "$here/capture.sh")"
lua_version="$(lua -v 2>&1 | head -1)"

header() {
  cat <<EOF
-- Merge Shape v1 baseline fixture: $1
-- Frozen observation of the BASE revision. DO NOT EDIT; recapture only with
-- lib/tests/fixtures/merge_v1_baseline/capture.sh against the base revision.
-- source_revision: $BASE_REVISION
-- source_tree: $tree
-- capture_script: lib/tests/fixtures/merge_v1_baseline/capture.sh
-- capture_inputs_sha256: scenario.lua=$inputs_scenario capture_tests.lua=$inputs_test capture.sh=$inputs_script
-- capture_interpreter: $lua_version
EOF
}

manifest_files=""
for body in "$scratch"/*.oracle.body; do
  name="$(basename "$body" .oracle.body)"
  { header "$name v1 project saved by the base's own project save"; cat "$scratch/$name.v1.ptn"; } > "$here/$name.v1.ptn"
  { header "$name observations (working patterns, MIDI, RNG, lookahead) by the base"; cat "$body"; } > "$here/$name.oracle.lua"
  manifest_files+="    [\"$name.v1.ptn\"] = \"$(sha "$here/$name.v1.ptn")\",
    [\"$name.oracle.lua\"] = \"$(sha "$here/$name.oracle.lua")\",
"
done

cat > "$here/MANIFEST.lua" <<EOF
-- Provenance of the Merge Shape v1 baseline oracle. Written by capture.sh;
-- DO NOT EDIT.
return {
  source_revision = "$BASE_REVISION",
  source_tree = "$tree",
  capture_script = "lib/tests/fixtures/merge_v1_baseline/capture.sh",
  capture_interpreter = "$lua_version",
  inputs = {
    ["scenario.lua"] = "$inputs_scenario",
    ["capture_tests.lua"] = "$inputs_test",
    ["capture.sh"] = "$inputs_script",
  },
  files = {
$manifest_files  },
}
EOF
echo "captured $(ls "$scratch"/*.oracle.body | wc -l) projects from $BASE_REVISION"
