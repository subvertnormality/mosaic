#!/usr/bin/env bash
# Regenerate pocketfft.c from numpy's copy. The FFT is numpy's own, so the
# native backend computes the same spectrogram as the Python reference.
set -euo pipefail
revision="${1:-v1.26.4}"
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
curl -sSL -o "$work/src.c" \
  "https://raw.githubusercontent.com/numpy/numpy/${revision}/numpy/fft/_pocketfft.c"
target="$(dirname "$0")/pocketfft.c"
{
  printf '/* Vendored FFT core, taken unmodified from numpy'"'"'s _pocketfft.c (numpy\n'
  printf ' * %s), with only the CPython wrapper removed. This is the exact\n' "$revision"
  printf ' * implementation numpy'"'"'s np.fft.rfft runs, so the native backend computes the\n'
  printf ' * same spectrogram as the Python reference without depending on numpy.\n *\n'
  printf ' * Upstream: https://github.com/numpy/numpy/blob/%s/numpy/fft/_pocketfft.c\n' "$revision"
  printf ' * pocketfft is 3-clause BSD, compatible with Mosaic'"'"'s GPL-3.\n */\n'
  sed -n '1,11p' "$work/src.c"
  sed -n '20,2194p' "$work/src.c"
} > "$target"
# numpy picked these up through Python.h.
sed -i 's|^#include <math.h>|/* numpy picked these up through Python.h; supplied directly here. */\n#include <assert.h>\n#include <math.h>|' "$target"
echo "wrote $target"
