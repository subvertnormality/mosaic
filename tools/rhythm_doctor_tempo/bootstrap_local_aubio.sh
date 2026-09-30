#!/bin/sh
set -eu
cache=${1:-/tmp/rd-tempo-aubio-0.4.9}
mkdir -p "$cache"
cd "$cache"
apt-get download libaubio-dev=0.4.9-4build1 libaubio5=0.4.9-4build1
echo 'c73ce0e3fe93bdf2d6c22b35f29bb7e9e4ff4a18798dbb6596c86cc4a23e49d0  libaubio-dev_0.4.9-4build1_amd64.deb' | sha256sum -c -
echo '8923e8179e14c4de336d4d32cd394ca36bf5a602b1697374de9273c953c50c5f  libaubio5_0.4.9-4build1_amd64.deb' | sha256sum -c -
rm -rf extracted
mkdir extracted
dpkg-deb -x libaubio-dev_0.4.9-4build1_amd64.deb extracted
dpkg-deb -x libaubio5_0.4.9-4build1_amd64.deb extracted
