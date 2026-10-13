"""Harness characterisation: saved-range serializer source in both clock lanes."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


class SerializerSourceTests(unittest.TestCase):
    def test_rejected_load_preservation_result_is_semantic_and_stable(self):
        from cases import rejected_saved_range

        rejected_load_preservation_result = rejected_saved_range.__globals__["rejected_load_preservation_result"]

        actual = rejected_load_preservation_result(2, {"autosave.ptn": "run-a", "autosave.pset": "run-b"})
        self.assertEqual(actual, {
            "kind": "rejected-load-file-preservation",
            "deadline": 2,
            "checked_filenames": ["autosave.pset", "autosave.ptn"],
            "preserved": True,
            "passed": True,
        })

    def test_real_time_uses_the_pinned_emulator_norns_checkout(self):
        from persisted_ranges import serializer_source

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tabutil = root / ".runtime/deps/norns/lua/lib/tabutil.lua"
            tabutil.parent.mkdir(parents=True)
            tabutil.write_text("return {}")
            with patch("persisted_ranges.EMULATOR_ROOT", root):
                source = serializer_source(SimpleNamespace(launch_options={
                    "experimental_install": None}))
            self.assertEqual(source, str(root / ".runtime/deps/norns"))

    def test_controlled_time_uses_the_qualified_install_source(self):
        from persisted_ranges import serializer_source

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "qualified-norns"
            tabutil = source / "lua/lib/tabutil.lua"
            tabutil.parent.mkdir(parents=True)
            tabutil.write_text("return {}")
            install = root / "installation.json"
            install.write_text(json.dumps({"source": str(source)}))
            with patch("persisted_ranges.EMULATOR_ROOT", root / "unused"):
                actual = serializer_source(SimpleNamespace(launch_options={
                    "experimental_install": str(install)}))
            self.assertEqual(actual, str(source))

    def test_missing_serializer_source_fails_closed(self):
        from persisted_ranges import serializer_source

        with tempfile.TemporaryDirectory() as directory:
            with patch("persisted_ranges.EMULATOR_ROOT", Path(directory)):
                with self.assertRaises(FileNotFoundError):
                    serializer_source(SimpleNamespace(launch_options={
                        "experimental_install": None}))


if __name__ == "__main__":
    unittest.main()
