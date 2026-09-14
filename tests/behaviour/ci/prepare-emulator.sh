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

if [[ ! -f .runtime/ci-qualified/runtime/installation.json ]]; then
  rm -rf .runtime/ci-qualified
  python3 scripts/build_qualified_midi_runtime.py \
    --output .runtime/ci-qualified
fi

python3 -c "import json,sys; from pathlib import Path; sys.path.insert(0,str(Path('src').resolve())); from runtime.dependencies import verify_install; verify_install(json.load(open('.runtime/current.json'))); verify_install(json.load(open('.runtime/ci-qualified/runtime/installation.json')))"
