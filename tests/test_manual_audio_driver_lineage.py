from pathlib import Path
import hashlib,json,shutil,tempfile,unittest
from manual_audio_driver_lineage import Rejected,verify_driver_lineage,_verify_extracted_proof_package,verify_lineage_binding,verified_proof_package
import manual_audio_resume as resume
REPO=Path(__file__).resolve().parents[1]
FIXTURES=REPO/"tests/fixtures"
HARNESS=FIXTURES/"manual-audio-historical-harness-v1"
ARCHIVE=FIXTURES/"manual-audio-driver-equivalence-v08.tar.gz"
class Tests(unittest.TestCase):
 def workspace(self,base):
  root=base/"root";run=base/"run"
  (root/"tests/behaviour").mkdir(parents=True);(root/"manual").mkdir();(root/"tests/fixtures").mkdir(parents=True);run.mkdir()
  shutil.copy2(ARCHIVE,root/"tests/fixtures"/ARCHIVE.name)
  with verified_proof_package(root) as (proof,_):
   shutil.copy2(proof/"candidate/tests/behaviour/driver.py",root/"tests/behaviour/driver.py")
   shutil.copy2(proof/"candidate/tests/behaviour/output-profiles.json",root/"tests/behaviour/output-profiles.json")
   shutil.copy2(proof/"candidate/manual/case-scenes.schema.json",root/"manual/case-scenes.schema.json")
   shutil.copy2(proof/"old/tests/behaviour/driver.py",run/"driver.py")
   shutil.copy2(proof/"origin-report.json",run/"report.json")
  report=json.loads((run/"report.json").read_text())
  harness_manifest=json.loads((HARNESS/"fixture-manifest.json").read_text())
  self.assertEqual(harness_manifest["origin_report_sha256"],hashlib.sha256((run/"report.json").read_bytes()).hexdigest())
  self.assertEqual(harness_manifest["harness_sha256"],{name:report["harness_sha256"][name] for name in ("ui.py","ui_map.py","pcm_oracle.py","channel_gestures.py")})
  for name,expected in harness_manifest["harness_sha256"].items():
   source=HARNESS/name
   self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),expected)
   shutil.copy2(source,run/name);shutil.copy2(source,root/"tests/behaviour"/name)
  return root,run,report
 def test_relocated_checkout_recomputes_exact_historical_to_current_pair(self):
  with tempfile.TemporaryDirectory() as d:
   root,run,report=self.workspace(Path(d));result=verify_driver_lineage(root,run,report)
   self.assertTrue(result["passed"]);self.assertEqual(result["old_examples"],8);self.assertEqual(result["deferred_raw_wavs"],32)
 def test_changed_current_driver_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root,run,report=self.workspace(Path(d));p=root/"tests/behaviour/driver.py";p.write_text(p.read_text()+"\\n# changed\\n")
   with self.assertRaises(Rejected):verify_driver_lineage(root,run,report)
 def test_changed_historical_driver_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root,run,report=self.workspace(Path(d));p=run/"driver.py";p.write_text(p.read_text()+"\\n# changed\\n")
   with self.assertRaises(Rejected):verify_driver_lineage(root,run,report)
 def test_historical_report_driver_map_cannot_be_relabelled(self):
  with tempfile.TemporaryDirectory() as d:
   root,run,report=self.workspace(Path(d));report["harness_sha256"]["driver.py"]="0"*64
   with self.assertRaises(Rejected):verify_driver_lineage(root,run,report)
 def test_pinned_origin_receipts_resolve_inside_repository_fixture_tree(self):
  for name,key in (("campaign-cleanup-verification-v2.json","cleanup_receipt"),("runtime-identity-reuse-check.json","identity_receipt")):
   path=resume.origin_fixture(name)
   self.assertEqual(path.parent,REPO/"tests/fixtures/manual-audio-resume-origin-v1")
   self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),resume.PIN[key])
 def test_tampered_archive_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root,run,report=self.workspace(Path(d));p=root/"tests/fixtures"/ARCHIVE.name;p.write_bytes(p.read_bytes()+b"x")
   with self.assertRaises(Rejected):verify_driver_lineage(root,run,report)
 def test_extracted_manifest_tamper_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root,run,report=self.workspace(Path(d))
   with verified_proof_package(root) as (proof,_):
    p=proof/"snapshot-manifest.json";p.write_text("{}")
    with self.assertRaises(Rejected):_verify_extracted_proof_package(proof)
 def test_report_marker_and_recomputed_lineage_must_match_exactly(self):
  proof={"old_driver_sha256":"old","current_driver_sha256":"new","passed":True}
  self.assertTrue(verify_lineage_binding(proof,dict(proof),dict(proof)))
  for report,marker,current in ((proof,{**proof,"current_driver_sha256":"other"},proof),(proof,proof,{**proof,"proof_receipt_sha256":"other"}),({**proof,"proof_manifest_sha256":"other"},proof,proof)):
   with self.assertRaises(Rejected):verify_lineage_binding(report,marker,current)
 def test_resume_harness_gate_accepts_only_exact_old_snapshot_and_proved_current_driver(self):
  with tempfile.TemporaryDirectory() as d:
   root,run,report=self.workspace(Path(d));result=resume.verify_harness_lineage(root,run,report)
   self.assertEqual(result["old_driver_sha256"],"924cf69c0c32ce6e06657587585ed893ba72ce5af5ee288a5a3b4fbf81e47007")
   self.assertEqual(result["current_driver_sha256"],"f38b4e2d329fdda79609b6a288a22f63cc5d99b20f4b01fc12fe3a732f251aba")
if __name__=="__main__":unittest.main()
