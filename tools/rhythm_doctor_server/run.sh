#!/bin/sh
# Start the analysis server with sensible defaults.
#
# Binds to every interface so a norns on the same network can reach it. Bind to
# 127.0.0.1 instead if you only want local clients.
set -e
cd "$(dirname "$0")"
exec python3 server.py --host "${RD_HOST:-0.0.0.0}" --port "${RD_PORT:-8420}" "$@"
