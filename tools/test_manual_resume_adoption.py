"""Portable source-level tests for controlled manual resume."""
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(os.environ.get("MOSAIC_REPO_ROOT", Path(__file__).resolve().parents[1])).resolve()
TOOLS = Path(os.environ.get("MOSAIC_RESUME_TEST_TOOLS", ROOT / "tools")).resolve()
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(ROOT / "tests" / "behaviour"))

import resume_adoption
import manual_publication_verify
from manual_publication_verify import resolve_scoped_witness, canonical_merge_witness_hash

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

class PortableResumeTests(unittest.TestCase):
    def test_adopted_row_without_lineage_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "no resume lineage"):
            resume_adoption.audit_resume_lineage(
                Path(tempfile.gettempdir()),
                {"stages": [{"name": "reference-controlled-example", "execution_status": "adopted-verified"}]},
                ROOT,
            )

    def test_final_inventory_hashes_match_current_exact_source_set(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            expected = {"manual/README.md", "cheat_sheet.html", "tests/behaviour/manual-inventory.json"}
            for relative in expected:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("current:" + relative)
            inventory_path = root / "manual/inventory.json"
            inventory_path.parent.mkdir(parents=True, exist_ok=True)
            inventory_path.write_text(json.dumps({"source_files": {relative: sha(root / relative) for relative in expected}}))
            self.assertTrue(manual_publication_verify.audit_inventory_source_hashes(root, inventory_path, expected)["passed"])
            data = json.loads(inventory_path.read_text())
            data["source_files"]["cheat_sheet.html"] = "0" * 64
            inventory_path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "source hash is stale: cheat_sheet.html"):
                manual_publication_verify.audit_inventory_source_hashes(root, inventory_path, expected)

    def test_inventory_source_map_cannot_omit_a_required_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inventory_path = root / "inventory.json"
            inventory_path.write_text(json.dumps({"source_files": {"cheat_sheet.html": "0" * 64}}))
            with self.assertRaisesRegex(ValueError, "identity set changed"):
                manual_publication_verify.audit_inventory_source_hashes(
                    root, inventory_path, {"cheat_sheet.html", "manual/README.md"}
                )

    def test_doctor_adoption_keeps_immutable_parent_report_and_rehashes_entire_tree(self):
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary);parent=base/"parent";evidence=base/"resume";parent.mkdir();evidence.mkdir()
            name="doctor-manual-real";report_dir=parent/"doctor-manual/native";report_dir.mkdir(parents=True)
            report=parent/"doctor-manual/report.json";report.write_text('{"passed":true}\n')
            (report_dir/"identity.json").write_text('{"runtime_identity":{},"emulator_identity":{}}\n')
            target=parent/"application";target.write_text("original app\n")
            (parent/"doctor-manual/code").mkdir()
            (parent/"doctor-manual/code/mosaic").symlink_to(target)
            ref={"path":str(report),"sha256":sha(report)}
            log=parent/(name+".log");log.write_text("completed\n")
            row={"name":name,"passed":True,"returncode":0,"native_report":ref,"log_sha256":sha(log)}
            (parent/(name+".json")).write_text(json.dumps(row))
            manifest={"passed":False,"build_complete":False,"controlled_local":True,
                      "tool_sha256":resume_adoption.SUPPORTED_PARENT_BUILDER_SHA256,
                      "stages":[row],**resume_adoption.SCOPE}
            manifest_path=parent/"manifest.json";manifest_path.write_text(json.dumps(manifest))
            tree=resume_adoption.doctor_evidence_files(report)
            item={"name":name,"kind":"doctor-capture","native_report":ref,
                  "parent_stage_receipt_sha256":sha(parent/(name+".json")),
                  "parent_log_sha256":sha(log),"doctor_evidence_files":tree,
                  "doctor_evidence_tree_sha256":hashlib.sha256(json.dumps(tree,sort_keys=True).encode()).hexdigest()}
            proof={"parent_manifest":str(manifest_path),"parent_manifest_sha256":sha(manifest_path),"adopted":[item]}
            (evidence/"resume-adoption.json").write_text(json.dumps(proof))
            record={"native_report":ref}
            with patch("manual_publication_verify.audit_doctor") as strict_audit, \
                 patch.object(resume_adoption,"verify_current_doctor_inputs") as current_inputs:
                result=resume_adoption.verify_adopted_doctor_stage(evidence,name,record,ROOT)
                self.assertEqual(result,str(report))
                strict_audit.assert_called_once_with(report)
                current_inputs.assert_called_once()
                (report_dir/"identity.json").write_text('{"changed":true}\n')
                with self.assertRaisesRegex(ValueError,"evidence tree changed"):
                    resume_adoption.verify_adopted_doctor_stage(evidence,name,record,ROOT)

    def test_resume_lineage_accepts_historical_migration_or_same_builder_only(self):
        # A failed build may resume from its own builder; previously only one historical
        # parent builder was accepted, so every current failure meant a full rebuild.
        old, current, other = resume_adoption.SUPPORTED_PARENT_BUILDER_SHA256, "a" * 64, "b" * 64
        self.assertTrue(resume_adoption.supported_lineage(old, current))
        self.assertTrue(resume_adoption.supported_lineage(current, current))
        self.assertFalse(resume_adoption.supported_lineage(other, current))
        self.assertFalse(resume_adoption.supported_lineage(None, current))
        self.assertFalse(resume_adoption.supported_lineage(current, None))

    def test_same_builder_parent_passes_the_lineage_gate_and_reaches_source_checks(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            manifest = {"passed": False, "build_complete": False, "controlled_local": True,
                        "tool_sha256": "c" * 64, "stages": [], **resume_adoption.SCOPE}
            (parent / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "Current builder hash does not match resume process"):
                resume_adoption.prepare_resume(parent, ROOT, [], expected_parent_manifest_sha256=sha(parent / "manifest.json"),
                    current_builder_sha="c" * 64, producer_hashes={}, audit_native=None, proof_path=parent / "proof.json")
            manifest["tool_sha256"] = "d" * 64
            (parent / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "Unsupported parent/current builder lineage"):
                resume_adoption.prepare_resume(parent, ROOT, [], expected_parent_manifest_sha256=sha(parent / "manifest.json"),
                    current_builder_sha="c" * 64, producer_hashes={}, audit_native=None, proof_path=parent / "proof.json")

    def test_repository_reconciler_matches_approved_source_pin(self):
        reconciler = TOOLS / "manual_reconcile_build.py"
        self.assertTrue(reconciler.is_file())
        self.assertEqual(sha(reconciler), resume_adoption.QUALIFIED_RECONCILER_SHA256)

    def test_merge_witness_resolves_only_unique_exact_linked_frame(self):
        row={"kind":"effective-foundation-musical-result","loops":2,"loop_steps":8,"expected":[]}
        witness={"start":{"midi_count":10,"observation_index":2},"end":{"midi_count":42,"observation_index":8}}
        frame={"kind":"documentation-frame","assertion_index":0,"assertion":row,
               "assertion_sha256":canonical_merge_witness_hash(row),"session_ordinal":3,
               "witness":witness,"midi_start_exclusive":10,"midi_end_inclusive":42}
        resolved=resolve_scoped_witness(0,[row,frame],expected_session_ordinal=3)
        self.assertEqual(resolved["witness"],witness)
        self.assertEqual((resolved["midi_start_exclusive"],resolved["midi_end_inclusive"]),(10,42))
        self.assertNotIn("witness",row)
        with self.assertRaisesRegex(ValueError,"another native session"):
            resolve_scoped_witness(0,[row,frame],expected_session_ordinal=4)
        with self.assertRaisesRegex(ValueError,"unique linked"):
            resolve_scoped_witness(0,[row,frame,frame],expected_session_ordinal=3)
        changed=dict(frame,assertion_sha256="0"*64)
        with self.assertRaisesRegex(ValueError,"assertion hash"):
            resolve_scoped_witness(0,[row,changed],expected_session_ordinal=3)
        changed=dict(frame,midi_end_inclusive=43)
        with self.assertRaisesRegex(ValueError,"boundaries differ"):
            resolve_scoped_witness(0,[row,changed],expected_session_ordinal=3)

    def test_current_plan_keeps_full_inventory_and_safe_inventory_order(self):
        builder_path = TOOLS / "manual_build.py"
        spec = importlib.util.spec_from_file_location("manual_build_under_test", builder_path)
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        builder.ROOT = ROOT
        plans = [p.name for p in sorted((ROOT / "manual").glob("scene-plans*.yaml"))]
        options = type("Options", (), dict(
            real_install="/qualified-real", emulator="/emu", audio_emulator="/audio-emu",
            audio_install="/audio-install", mod_code_root="/mods", ffmpeg="ffmpeg",
            controlled_install="/controlled", modulation_code_root="/mod-code",
            modulation_emulator="/mod-emu", modulation_controlled_install="/mod-controlled",
            readability_real_install="/readability-real", browser_tests=True, python="python3",
            node="node", quick_output="manual/generated/quick-reference.html",
        ))()
        stages = builder.plan(options, plans, controlled_local=True)
        names = [row["name"] for row in stages]
        self.assertEqual(len(names), len(set(names)))
        self.assertLess(names.index("compile-book"), names.index("quick-reference"))
        self.assertLess(names.index("quick-reference"), names.index("inventory"))
        self.assertLess(names.index("inventory"), names.index("publication-audit"))

if __name__ == "__main__":
    unittest.main()
