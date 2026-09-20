"""Nothing Mosaic runs on a Norns may import a third-party Python package.

A Norns has the Python standard library and nothing else. The analysis backend
used to need numpy, which is why Rhythm Doctor could not work on a stock
install at all. That is now a native backend, and this keeps it that way: an
import added to the runtime path would not fail on a developer machine, where
numpy is present for the reference implementation and the corpus tooling, but
would break every device.
"""
import ast
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools" / "rhythm_doctor"

# Entry points the Lua hosts execute on the device.
ENTRY_POINTS = ("launch_worker.py", "launch_analysis_worker.py", "rd_analysis_worker.py")

STDLIB = set(getattr(sys, "stdlib_module_names", ()))
# Python 3.9 on a Norns has no sys.stdlib_module_names, so fall back to the set
# these programs actually use; anything new has to be added deliberately.
FALLBACK = {
    "__future__", "argparse", "ast", "collections", "contextlib", "dataclasses",
    "errno", "fcntl", "hashlib", "io", "json", "math", "os", "pathlib", "re",
    "select", "selectors", "shutil", "signal", "socket", "struct", "subprocess",
    "sys", "tempfile", "time", "types", "typing", "wave",
}


def imported_modules(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level:            # relative import, resolved within the tree
                continue
            if node.module:
                found.add(node.module.split(".")[0])
    return found


def reachable(entry):
    """Entry point plus any sibling module it imports, followed transitively."""
    seen, queue, modules = set(), [entry], set()
    while queue:
        path = queue.pop()
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        for name in imported_modules(path):
            modules.add(name)
            sibling = TOOLS / (name + ".py")
            if sibling.is_file():
                queue.append(sibling)
    return seen, modules


class RuntimeDependencyTests(unittest.TestCase):
    def test_device_entry_points_use_only_the_standard_library(self):
        allowed = STDLIB | FALLBACK
        for name in ENTRY_POINTS:
            entry = TOOLS / name
            self.assertTrue(entry.is_file(), name)
            files, modules = reachable(entry)
            outside = sorted(m for m in modules if m not in allowed)
            self.assertEqual(outside, [], "%s (via %s) imports non-stdlib: %s" % (
                name, ", ".join(sorted(p.name for p in files)), outside))

    def test_the_native_backend_needs_no_python_at_all(self):
        source = TOOLS / "rd_analysis_backend.c"
        self.assertTrue(source.is_file())
        text = source.read_text(encoding="utf-8")
        self.assertIn("#include \"pocketfft.c\"", text,
                      "the FFT must come from the vendored numpy implementation")
        for forbidden in ("Python.h", "numpy/"):
            self.assertNotIn(forbidden, text, forbidden)

    def test_the_vendored_fft_is_free_of_cpython(self):
        text = (TOOLS / "pocketfft.c").read_text(encoding="utf-8")
        for forbidden in ("#include <Python.h>", "PyObject", "PyMODINIT_FUNC", "numpy/arrayobject.h"):
            self.assertNotIn(forbidden, text,
                             "the CPython wrapper must be stripped: " + forbidden)


if __name__ == "__main__":
    unittest.main()
