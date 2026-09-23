"""Harness characterisation: complete project content and exact cold replay."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from harmony_merge_workflow import pattern_harmony_persistence_workflow


class HarmonyPersistenceOracleTests(unittest.TestCase):
    def test_qualified_serializer_digest_keeps_pset_bytes_and_cold_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "qualified-norns"
            tabutil = source / "lua/lib/tabutil.lua"
            tabutil.parent.mkdir(parents=True)
            tabutil.write_text("return {}")
            install = root / "installation.json"
            install.write_text(json.dumps({"source": str(source)}))
            data = root / "data"
            data.mkdir()
            saved, pset = data / "autosave.ptn", data / "autosave.pset"
            saved.write_text("saved table")
            pset.write_text("exact parameter bytes")
            options = {"experimental_install": str(install)}
            c = SimpleNamespace(data_directory=data, out=root,
                                launch_options=options, results=[],
                                playback=Mock(), finish=Mock(), elapse=Mock(),
                                wait=lambda predicate, **_: predicate(None))
            loaded = SimpleNamespace(playback=Mock(), finish=Mock(), results=[])
            with patch("harmony_merge_workflow.setup_pattern_harmony"), \
                 patch("harmony_merge_workflow.documentation_frame"), \
                 patch("driver.Driver", return_value=loaded) as boot, \
                 patch("driver.digest", return_value="pset-byte-hash") as digest, \
                 patch("persisted_digest.project_digest", return_value="complete-project-hash") as project:
                pattern_harmony_persistence_workflow(c)

            project.assert_called_once_with(saved, str(source))
            digest.assert_called_once_with(pset)
            expected = [(1, [144, note, velocity]) for note, velocity in
                        ((60, 127), (86, 117), (88, 107), (89, 97))]
            c.playback.assert_called_once_with(expected, cycles=2, timeout=6)
            loaded.playback.assert_called_once_with(expected, cycles=2, timeout=6)
            boot.assert_called_once_with(root / "reloaded", project_seed=data, **options)
            self.assertEqual(loaded.results, [{
                "kind": "pattern-harmony-cold-replay",
                "hashes": ["complete-project-hash", "pset-byte-hash"],
                "passed": True,
            }])
            c.finish.assert_called_once_with()
            loaded.finish.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
