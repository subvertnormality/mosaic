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
        import inspect
        from ast_digest import ast_digest
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
        # Interpreter-stable digests (ast_digest) of FunctionDef ASTs at 9d26f841,
        # before the exact move; CI runs Python 3.8.
        source_hashes = {
            'playback_note_messages': '15f8f3fc07b90038a1d8813e56b814975242f7b15d54ac9af2b4f249ed504218',
            'revoice_workflow': 'c3d3c344b33ad56a5743d342578b8bb60993bd75052833639b0049f1e0eccae4',
            'setup_pattern_harmony': '15c6639c39907455e9a711879ffd894e9aa08428ac950e21bfe39d98b95e27ba',
            'pattern_harmony_persistence_workflow': 'f9a393dafc184d8ec3145c4247b6ec1d1af6c62b45a3030971514bbb231a2aab',
            'ensemble_polyrhythm_workflow': '834cc837fa60ad83f1c6b9a24c5da9a6b334694e39629ca5b936964a5f06d2e0',
            'no_voicing_fallback_workflow': '56cf8b65cfeb789b9dede676c6408aeaf35cdff82dbc3f0e3fcaf7e944ec94ba',
            'held_step_precedence_workflow': '1c5a913d8c9261ebe54905df561085f5152eeeed0a4b7d793ba9085edca21b65',
        }
        for name, expected_hash in source_hashes.items():
            with self.subTest(source=name):
                self.assertFalse(hasattr(original, name))
                self.assertEqual(
                    ast_digest(ast.parse(inspect.getsource(getattr(owner, name))).body[0]),
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
