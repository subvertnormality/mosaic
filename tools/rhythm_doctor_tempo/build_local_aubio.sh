#!/bin/sh
set -eu
root=${RD_TEMPO_AUBIO_ROOT:-/tmp/rd-tempo-aubio-0.4.9/extracted}
output=${1:?output path required}
if [ "${RD_TEMPO_SYSTEM_AUBIO:-0}" = 1 ]; then
  version=$(pkg-config --modversion aubio)
  libdir=$(pkg-config --variable=libdir aubio)
  library=$libdir/libaubio.so
  test -f "$library"
  library_sha256=$(sha256sum "$library" | awk '{print $1}')
  gcc -std=c11 -O2 -Wall -Wextra -Werror $(pkg-config --cflags aubio) \
    tools/rhythm_doctor_tempo/rd_tempo.c $(pkg-config --libs aubio) -lm -o "$output"
  binary_sha256=$(sha256sum "$output" | awk '{print $1}')
  printf '{"mode":"system-pkg-config","aubio_version":"%s","library":"%s","library_sha256":"%s","binary_sha256":"%s"}\n' \
    "$version" "$library" "$library_sha256" "$binary_sha256" > "$output.aubio-build.json"
  exit 0
fi
test -f "$root/usr/include/aubio/aubio.h"
test -f "$root/usr/lib/x86_64-linux-gnu/libaubio.so.5.4.8"
exec gcc -std=c11 -O2 -Wall -Wextra -Werror -I"$root/usr/include" \
  tools/rhythm_doctor_tempo/rd_tempo.c "$root/usr/lib/x86_64-linux-gnu/libaubio.so.5.4.8" \
  -Wl,-rpath,"$root/usr/lib/x86_64-linux-gnu" -lm -o "$output"
