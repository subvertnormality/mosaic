#!/usr/bin/env bash
set -euo pipefail

# The current v2.9.4 release is the same commit as the native CI runtime.
# Fetch that immutable source directly rather than querying the floating,
# unauthenticated releases/latest API before every Lua test run.
norns_revision="14bbeae8646c6717f6bb44c8cd60250bf94b6042"
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
destination="$root/lib/tests/test_artefacts/norns_test_artefact"
[[ ! -e "$destination/lua" ]] || { echo "Refusing to overwrite an existing norns Lua test source" >&2; exit 1; }
source_dir="$(mktemp -d "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/mosaic-norns-lua.XXXXXX")"
trap 'rm -rf -- "$source_dir"' EXIT
git -C "$source_dir" init --quiet
export GIT_TERMINAL_PROMPT=0
git -C "$source_dir" fetch --quiet --depth 1 https://github.com/monome/norns.git "$norns_revision"
[[ "$(git -C "$source_dir" rev-parse FETCH_HEAD)" == "$norns_revision" ]]
mkdir -p "$destination"
git -C "$source_dir" archive "$norns_revision" lua | tar -x -C "$destination"
test -f "$destination/lua/core/norns.lua"
printf '%s\n' "$norns_revision" > "$destination/.mosaic-test-source-revision"
echo "Pinned norns Lua test source: $norns_revision"
