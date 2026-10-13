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
        # channel-octave scope and one planned > sent row per voice; 27 September
        # 2026 the re-captured NO VOICING image, whose Failure details row shows OPEN >,
        # and Voice leading drawn as a list of its rows). Reviewed re-freeze, followup-cases:
        # revoice_workflow adds one expectation, the Masks Chord 1 cell reads 2nd after the
        # first E3 detent (README Adding Chords), before Harmony opens; nothing else changed.
        source_hashes = {
            'playback_note_messages': '15f8f3fc07b90038a1d8813e56b814975242f7b15d54ac9af2b4f249ed504218',
            'revoice_workflow': 'db78213502b15bf29b63f0ba0c0e349f24179e67c9d8dbaaffab51cca3985e20',
            'setup_pattern_harmony': '8925b4cce413ac9b432e5ef55bea29da14d6c853990bd879d8fc31659e1eebfc',
            'pattern_harmony_persistence_workflow': '4481ac7da164d5f3b2188aa42f8e4d665c347d279798da9158b2bc184ef1882f',
            'ensemble_polyrhythm_workflow': 'd07e29b5c09794797e29d774381465568373410294cdefedfffda1bb4d3b14a1',
            'no_voicing_fallback_workflow': 'fe7500378df9b51ac353eccea43ea0e11500e9ace48940207d7bcfada16ba35e',
            'held_step_precedence_workflow': 'bd8130c0b08f2422a5baec7bdb666ec04c96c41b9af1d27f01f552934ef0ff4e',
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
