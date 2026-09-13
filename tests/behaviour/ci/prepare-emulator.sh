#!/usr/bin/env bash
set -euo pipefail

: "${EMULATOR_ROOT:?EMULATOR_ROOT is required}"

cd "$EMULATOR_ROOT"

if [[ ! -f .runtime/current.json ]]; then
  ./dev/emu fetch --locked
  ./dev/emu build
else
  ./dev/emu doctor --json
fi

if [[ ! -f .runtime/ci-controlled/installation.json ]]; then
  rm -rf .runtime/ci-controlled-recipe .runtime/ci-controlled
  base_source="$(python3 -c "import json; print(json.load(open('.runtime/current.json'))['source'])")"
  python3 scripts/prepare_controlled_runtime.py \
    --source "$base_source" \
    --output .runtime/ci-controlled-recipe
  python3 scripts/build_controlled_candidate.py \
    --candidate .runtime/ci-controlled-recipe \
    --output .runtime/ci-controlled
fi

python3 -c "import json,sys; from pathlib import Path; sys.path.insert(0,str(Path('src').resolve())); from runtime.dependencies import verify_install; verify_install(json.load(open('.runtime/current.json'))); verify_install(json.load(open('.runtime/ci-controlled/installation.json')))"
