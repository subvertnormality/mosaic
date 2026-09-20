"""Every Rhythm Doctor Lua module must load on the interpreter norns actually runs.

matron embeds Lua 5.3 (liblua5.3.so.0), not LuaJIT.  A stock norns therefore
has no ffi, no bit, no luasocket and no posix binding.  The capture and
analysis transports were once written against the LuaJIT FFI and were only ever
exercised under a `luajit` binary that no device has, so they raised on the
first require, the runtime swallowed it in a pcall and retried forever: Record
did nothing on hardware while every suite stayed green.

These tests close that gap from both sides.  Each module is loaded under a real
Lua 5.3, and the source is scanned for the LuaJIT-only dependencies, so a
module that happens not to be loadable standalone still cannot reintroduce one.
"""
from pathlib import Path
import re
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from matron import LUA, SKIP_REASON, VERSION as MATRON_LUA

ROOT = Path(__file__).resolve().parents[2]
RHYTHM_DOCTOR = ROOT / "lib" / "rhythm_doctor"

# Modules LuaJIT provides and matron does not.  `bit32` is genuinely present on
# a norns and is deliberately absent from this list.
LUAJIT_ONLY = ("ffi", "bit", "jit")


@unittest.skipUnless(LUA, SKIP_REASON)
class MatronCompatibilityTests(unittest.TestCase):
    def test_every_rhythm_doctor_module_loads_under_matrons_lua(self):
        modules = sorted(path.stem for path in RHYTHM_DOCTOR.glob("*.lua"))
        self.assertTrue(modules, "no Rhythm Doctor modules found")
        for name in modules:
            with self.subTest(module=name):
                result = subprocess.run(
                    [LUA, "-e", "package.path='lib/?.lua;'..package.path; require('rhythm_doctor." + name + "')"],
                    cwd=ROOT, capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0,
                                 name + " does not load on a norns: " + (result.stderr.strip() or "(no output)"))

    def test_no_module_requires_a_luajit_only_dependency(self):
        pattern = re.compile(r"""require\s*\(?\s*['"](""" + "|".join(LUAJIT_ONLY) + r""")['"]""")
        for path in sorted(RHYTHM_DOCTOR.glob("*.lua")):
            with self.subTest(module=path.name):
                found = pattern.search(path.read_text(encoding="utf-8"))
                self.assertIsNone(found, path.name + " requires " + (found.group(1) if found else "")
                                  + ", which matron's Lua " + MATRON_LUA + " does not provide")


if __name__ == "__main__":
    unittest.main()
