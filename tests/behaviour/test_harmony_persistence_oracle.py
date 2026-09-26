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
        # Interpreter-stable digests (ast_digest) of FunctionDef ASTs; CI runs
        # Python 3.8. Unchanged functions keep their 9d26f841 (pre-move)
        # digests; the others pin their live-UI migration (Channel tasks,
        # focused-screen field oracles; 25 September 2026 dashboard/detail rows,
        # channel-octave scope and one planned > sent row per voice).
        source_hashes = {
            'playback_note_messages': '15f8f3fc07b90038a1d8813e56b814975242f7b15d54ac9af2b4f249ed504218',
            'revoice_workflow': 'c3d3c344b33ad56a5743d342578b8bb60993bd75052833639b0049f1e0eccae4',
            'setup_pattern_harmony': 'cf50f9e6dd7980965bc5f3b2fe77efb122302668809d29d5dc2297fd112a7523',
            'pattern_harmony_persistence_workflow': '55cb04854f2688df167806e83dfbdad4f079b93c72b57a7f39b05ffe357fa899',
            'ensemble_polyrhythm_workflow': '3f720d2a1bf5dc9bd8f13289875ad12322ebded27a7cfe00cee58cfd919dd3ac',
            'no_voicing_fallback_workflow': 'def020ee1ac22e01507fa616d4e9bb850365eae9e959b662b7cf124223243dff',
            'held_step_precedence_workflow': '03edaef1a80402c4b48bfdd3156b1f74265d854270f526b658859aeffeef0ce3',
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
