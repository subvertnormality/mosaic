"""Harness characterisation: complete project content and exact cold replay."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from contract.harmony_workflows import pattern_harmony_persistence_workflow


class HarmonyPersistenceOracleTests(unittest.TestCase):
    def test_five_harmony_cases_have_exact_contract_owners(self):
        import ast
        import hashlib
        import inspect
        from cases import CASES
        import contract.harmony_workflows as owner
        import harmony_merge_workflow as original

        owners = {
            'M-HARMONY-REVOICE-001': 'revoice_workflow',
            'M-HARMONY-ENSEMBLE-001': 'ensemble_polyrhythm_workflow',
            'M-HARMONY-FAILURE-001': 'no_voicing_fallback_workflow',
            'M-HARMONY-HELD-001': 'held_step_precedence_workflow',
            'M-HARMONY-PERSIST-001': 'pattern_harmony_persistence_workflow',
        }
        for case_id, name in owners.items():
            with self.subTest(case_id=case_id):
                run = CASES[case_id]['run']
                self.assertIs(run, getattr(owner, name))
                self.assertEqual(run.__module__, owner.__name__)
                self.assertIsNone(run.__closure__)
        # Hashes of FunctionDef ASTs at 9d26f841, before the exact move.
        source_hashes = {
            'playback_note_messages': '2668a8e1136a8789af9ac7f7bdb4a291668d4e0355d9af0860a45115fbbc39b9',
            'revoice_workflow': 'cb7434ef16036ea4c05699ae203eb36503f2b7b5201b3cabf622bbfb4b2a08b6',
            'setup_pattern_harmony': '978b9cf5c3e8c139533bc8809b8311baec6eba3a767e4f73095a01f12f4395b5',
            'pattern_harmony_persistence_workflow': 'a255d5aea15901fedfb3a730087b705be4951370134971ced97226d7d4d458fe',
            'ensemble_polyrhythm_workflow': 'a85967ab52239a99767c71a35b010a330ffbf473bc7aa60f768f0653df38e5ac',
            'no_voicing_fallback_workflow': '8a286ba45b8f540213135ba1861daabf3bdaecb8b6dee5e760eb688487f1dcf8',
            'held_step_precedence_workflow': '5a12453f73f9aea7fcd8d9ab7bd7448a4143c2b8ebb62491a5dd5233e332369c',
        }
        for name, expected_hash in source_hashes.items():
            with self.subTest(source=name):
                self.assertFalse(hasattr(original, name))
                self.assertEqual(
                    hashlib.sha256(ast.dump(ast.parse(inspect.getsource(
                        getattr(owner, name))).body[0]).encode()).hexdigest(),
                    expected_hash,
                )

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
            with patch("contract.harmony_workflows.setup_pattern_harmony"), \
                 patch("contract.harmony_workflows.documentation_frame"), \
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
