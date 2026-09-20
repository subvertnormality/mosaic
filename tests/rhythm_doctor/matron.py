"""The interpreter matron embeds, which is what Mosaic's Lua must satisfy.

matron links liblua5.3.so.0.  A norns has no `luajit` binary at all, so a suite
that validates Lua under LuaJIT proves nothing about the device -- that is
exactly how FFI transports that could never load reached hardware green.
"""
from __future__ import annotations

import shutil
import subprocess

VERSION = "5.3"


def interpreter():
    for name in ("lua" + VERSION, "lua"):
        binary = shutil.which(name)
        if not binary:
            continue
        probe = subprocess.run([binary, "-v"], capture_output=True, text=True)
        if VERSION in (probe.stdout + probe.stderr):
            return binary
    return None


LUA = interpreter()
SKIP_REASON = "requires the Lua " + VERSION + " interpreter matron embeds"
