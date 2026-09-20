"""The interpreter matron embeds, which is what Mosaic's Lua must satisfy.

matron links liblua5.3.so.0.  A norns does ship standalone interpreters, but
neither is matron's: /usr/bin/lua is 5.1 and /usr/bin/luajit is LuaJIT 2.1.
LuaJIT has an FFI and matron does not, so a suite that validates Lua under
`luajit` can pass on the very device where the script cannot load at all --
which is exactly how FFI transports reached hardware green.
"""
from __future__ import annotations

import shutil
import subprocess

VERSION = "5.3"


def interpreter(which=None):
    """A Lua that reports matron's version, or nothing.

    A binary named `lua` is not evidence: on a norns it is 5.1.  Only the
    reported version counts, and a mismatch returns None so a caller fails
    loudly rather than proving something about the wrong interpreter.
    """
    which = which or shutil.which
    for name in ("lua" + VERSION, "lua"):
        binary = which(name)
        if not binary:
            continue
        probe = subprocess.run([binary, "-v"], capture_output=True, text=True)
        if VERSION in (probe.stdout + probe.stderr):
            return binary
    return None


LUA = interpreter()
SKIP_REASON = "requires the Lua " + VERSION + " interpreter matron embeds"
