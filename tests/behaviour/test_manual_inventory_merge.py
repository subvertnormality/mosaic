"""Inventory audit retention; characterisation outside the instrument manual."""
import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location("manual_inventory",ROOT/"tools/manual_inventory.py")
inventory=importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)
class InventoryMergeTests(unittest.TestCase):
 def test_regeneration_keeps_review_and_baseline_owner_identity(self):
  old=dict(id="masks",readme=dict(sha256="original"),controls=[dict(gesture="K2",result="Clear held step")],
    code_candidates=[dict(path="owner.lua",sha256="frozen",status="reviewed-source-owner")],
    audit_status="source-and-case-definitions-reviewed-awaiting-native-reference-replay",
    source_review=dict(native_replayed=False,source_sha256="immutable-evidence"),
    review=dict(status="pending",source_status="code-and-case-reviewed"))
  new=dict(id="masks",readme=dict(sha256="original"),controls=["noisy candidate"],
    code_candidates=[],audit_status="unreviewed")
  expected=copy.deepcopy(old)
  with tempfile.TemporaryDirectory() as directory:
   merged=inventory.merge_audit(new,old,root=Path(directory))
  self.assertEqual(merged["controls"],expected["controls"])
  self.assertEqual(merged["code_candidates"],expected["code_candidates"])
  self.assertEqual(merged["source_review"],expected["source_review"])
  self.assertEqual(merged["review"],expected["review"])
  self.assertEqual(old,expected,"Merging must not rewrite the preserved baseline")
 def test_source_drift_marks_review_stale_without_relabelling_evidence(self):
  old=dict(id="x",readme=dict(sha256="before"),
    code_candidates=[],audit_status="reviewed",
    source_review=dict(source_sha256="before",native_replayed=False))
  new=dict(id="x",readme=dict(sha256="after"),code_candidates=[],audit_status="unreviewed")
  merged=inventory.merge_audit(new,old)
  self.assertEqual(merged["audit_status"],"source-review-stale")
  self.assertEqual(merged["source_review"]["source_sha256"],"before")
  self.assertIn("readme",merged["review_drift"])
 def test_changed_owner_keeps_recorded_hash_and_names_drift(self):
  old=dict(id="x",readme=dict(sha256="same"),audit_status="reviewed",
    code_candidates=[dict(path="owner.lua",sha256="original-owner",status="reviewed-source-owner")],
    source_review=dict(native_replayed=False))
  new=dict(id="x",readme=dict(sha256="same"),code_candidates=[])
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);(root/"owner.lua").write_text("changed production source")
   merged=inventory.merge_audit(new,old,root=root)
  self.assertEqual(merged["code_candidates"][0]["sha256"],"original-owner")
  self.assertEqual(merged["review_drift"],["owner.lua"])
  self.assertEqual(merged["audit_status"],"source-review-stale")
 def test_book_destinations_preserve_hierarchy_and_authored_controls(self):
  feature=dict(id="first-sound",title="First sound",level=2,parent=None,category="learn",
    controls=[dict(gesture="K3",result="Choose output")],details=[],recipes=[],related=["devices"],
    sources=dict(readme="legacy/README.md#devices",behaviour_cases=[],code=[]),
    review=dict(status="pending",source_status="code-and-case-reviewed",cases=[]))
  result=inventory.book_entry(feature,{})
  self.assertEqual(result["id"],"first-sound")
  self.assertEqual(result["controls"],feature["controls"])
  self.assertEqual(result["parent"],None)
  self.assertEqual(result["source_review"]["native_replayed"],False)
 def test_current_native_status_uses_bindings_and_preserves_source_baseline(self):
  feature=dict(id="x",title="X",controls=[],details=[],recipes=[],related=[],scene_refs=["scene"],
    sources=dict(readme="legacy#x",behaviour_cases=["CASE"],code=[]),
    review=dict(status="verified",source_status="code-and-case-reviewed",applicability="native-ui",native_gap="Scoped example only."))
  old=dict(id="x",readme=dict(sha256="legacy",section_ids=[]),source_review=dict(native_replayed=False,source_sha256="baseline"),code_candidates=[])
  frame=dict(output=dict(binding=dict(passed=True,semantic_assertions=1,sha256="frame",grid_sha256="grid")))
  captures={"scene":dict(behaviour_case="CASE",steps=[frame],clock_mode="real-time")}
  result=inventory.book_entry(feature,old,captures=captures)
  self.assertEqual(result["audit_status"],"source-reviewed-with-native-reference-evidence")
  self.assertTrue(result["current_review"]["native_replayed"])
  self.assertFalse(result["current_review"]["complete_regression_run"])
  self.assertEqual(result["source_review"],old["source_review"])
 def test_verified_badge_cannot_hide_missing_or_failed_native_scenes(self):
  feature=dict(id="x",title="X",controls=[],details=[],recipes=[],related=[],scene_refs=["missing"],
    sources=dict(readme="legacy#x",behaviour_cases=[],code=[]),
    review=dict(status="verified",source_status="code-and-case-reviewed",applicability="native-ui"))
  result=inventory.book_entry(feature,{},captures={})
  self.assertFalse(result["current_review"]["native_replayed"])
  self.assertEqual(result["current_review"]["missing_scene_refs"],["missing"])
  self.assertEqual(result["audit_status"],"source-reviewed-native-reference-evidence-missing")
 def test_non_native_exception_is_explicit_and_does_not_claim_replay(self):
  feature=dict(id="install",title="Install",controls=[],details=[],recipes=[],related=[],scene_refs=[],
    sources=dict(readme="legacy#install",behaviour_cases=[],code=[]),
    review=dict(status="verified",source_status="code-and-case-reviewed",applicability="documentation-only",rationale="External installation workflow."))
  result=inventory.book_entry(feature,{},captures={})
  self.assertFalse(result["current_review"]["native_replayed"])
  self.assertEqual(result["audit_status"],"source-reviewed-native-not-applicable")
 def test_current_owner_reassessment_resolves_drift_without_rewriting_baseline(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);(root/"owner.lua").write_text("current owner")
   current=inventory.hashlib.sha256((root/"owner.lua").read_bytes()).hexdigest()
   feature=dict(id="development",title="Development",controls=[],details=[],recipes=[],related=[],scene_refs=[],
    sources=dict(readme="legacy#development",behaviour_cases=[],code=["owner.lua"]),
    review=dict(status="verified",source_status="code-and-case-reviewed",applicability="documentation-only",
      rationale="Development guidance.",current_source_review=dict(owners=[dict(path="owner.lua",sha256=current)],note="Inspected new tests.")))
   old=dict(id="development",readme=dict(sha256="legacy"),audit_status="source-review-stale",review_drift=["owner.lua"],
    source_review=dict(native_replayed=False,source_sha256="baseline"),code_candidates=[dict(path="owner.lua",sha256="historical")])
   result=inventory.book_entry(feature,old,root=root,captures={})
   self.assertTrue(result["current_review"]["source_drift_reassessed"])
   self.assertEqual(result["audit_status"],"source-reviewed-native-not-applicable")
   self.assertEqual(result["code_candidates"][0]["sha256"],"historical")
   self.assertEqual(result["source_review"],old["source_review"])
   feature["review"]["current_source_review"]["owners"][0]["sha256"]="incorrect"
   result=inventory.book_entry(feature,old,root=root,captures={})
   self.assertEqual(result["audit_status"],"source-review-stale")
if __name__=="__main__":unittest.main()
