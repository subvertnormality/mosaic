import copy, hashlib, importlib.util, json, tempfile, unittest
from pathlib import Path
MODULE=Path(__file__).parent.parent/"tools"/"manual_metadata_transition.py"
spec=importlib.util.spec_from_file_location("transition",MODULE); transition=importlib.util.module_from_spec(spec); spec.loader.exec_module(transition)
def sha(b): return hashlib.sha256(b).hexdigest()
def write_json(p,v): p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+"\n")
def read(p): return json.loads(Path(p).read_bytes())
class CompleteTransitionFixture:
 def __init__(self,base):
  self.base=Path(base); self.root=self.base/"repo";self.external=self.base/"evidence";self.root.mkdir();self.external.mkdir();(self.root/".git").mkdir()
  self.paths=transition.METADATA; self.source_names=["manual/features/cookbook.yaml"]+[f"manual/features/generated-{i}.yaml" for i in range(5)]
  self.sources={n:f"source-{i}".encode() for i,n in enumerate(self.source_names)}
  for n,b in self.sources.items(): p=self.root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
  self.old_review={"baseline_inventory":"history/base.json","files":{n:{"sha256":sha(b),"meaning":"approved"} for n,b in self.sources.items()},"explicit_authored_review":{}}
  self.new_review=copy.deepcopy(self.old_review)
  self.inventory={"files":{n:sha(b) for n,b in self.sources.items()},"grid_registrations":[{"id":"reg-1","source":"lib/ui.lua","line":12,"branches":[{"id":"b1","outcome":"enter"}]}],"controller_units":[{"id":"controller-1"}],"manual_sections":[{"id":"section-1"}]}
  self.receipt={"files":copy.deepcopy(self.new_review["files"]),"branches":self.inventory["grid_registrations"],"baseline_sha256":sha((json.dumps(self.inventory,indent=2,ensure_ascii=False)+"\n").encode())}
  for rel,data in zip(self.paths,[self.old_review,self.inventory,self.receipt]):write_json(self.root/rel,data)
  self.before={rel:(self.root/rel).read_bytes() for rel in self.paths}
  # Prebuild overlay only changes bounded metadata fields.
  overlay_review=copy.deepcopy(self.new_review);overlay_review["explicit_authored_review"]={"kind":"bounded"}
  overlay_inventory=copy.deepcopy(self.inventory);overlay_receipt=copy.deepcopy(self.receipt)
  overlay_root=self.external/"bundle";self.bundle=overlay_root;before_root=overlay_root/"physical-source";after_root=overlay_root/"approved-review-overlay"
  for rel,data in zip(self.paths,[self.old_review,self.inventory,self.receipt]):write_json(before_root/rel,data)
  for rel,data in self.sources.items(): p=before_root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
  for rel,data in zip(self.paths,[overlay_review,overlay_inventory,overlay_receipt]):write_json(after_root/rel,data)
  deltas=[{"path":self.source_names[0],"kind":"authored-prerequisite-correction","current_sha256":sha(self.sources[self.source_names[0]])}]
  for n in self.source_names[1:]:
   archived=self.external/(n.replace("/","_")+".reproduced");archived.write_bytes(self.sources[n])
   deltas.append({"path":n,"kind":"historical-partial-generated-publication","current_sha256":sha(self.sources[n]),"serialization_reproduction":{"path":str(archived),"sha256":sha(archived.read_bytes())}})
  self.prior_strict=self.external/"prior-strict-validation.json";write_json(self.prior_strict,{"passed":True,"source_validation":"strict"})
  bounded={"reviewed_members":78,"manual_generation_complete":False,"member_deltas":deltas,"ghost_prerequisite_qualification":[]}
  self.bounded=self.external/"bounded.json";write_json(self.bounded,bounded)
  rows=[]
  for rel in self.paths:
   rows.append({"path":rel,"captured_before_sha256":sha((before_root/rel).read_bytes()),"approved_after_sha256":sha((after_root/rel).read_bytes())})
  b={"validation_scope":"controlled-manual-generation","launch_qualified":False,"native_launched":False,"physical_source_snapshot":{"files":{n:sha(data) for n,data in self.sources.items()}},"approved_review_overlay":{"files":rows,"bounded_review":{"path":str(self.bounded),"sha256":sha(self.bounded.read_bytes())},"prior_strict_validation":{"path":str(self.prior_strict),"sha256":sha(self.prior_strict.read_bytes())}}}
  self.bundle_manifest=overlay_root/"physical-source-and-review-overlay.json";write_json(self.bundle_manifest,b);self.bundle_sha=sha(self.bundle_manifest.read_bytes())
  ui=self.root/"docs/ui-reimplementation"; (ui/"history").mkdir(parents=True);write_json(ui/"history/base.json",self.inventory)
  # Minimal deterministic refresher used by both prebuild and final replay.
  (ui/"tools").mkdir(parents=True)
  (ui/"tools/refresh_source_inventory.py").write_text('''import copy,json\nfrom pathlib import Path\nROOT=Path(__file__).resolve().parents[1]\nREPO=ROOT.parents[1]\ndef refresh(baseline,review):\n old=json.loads(Path(baseline).read_bytes()); inv=copy.deepcopy(old); inv[\"files\"]={k:v[\"sha256\"] for k,v in review[\"files\"].items()}; rec={\"files\":copy.deepcopy(review[\"files\"]),\"branches\":old[\"grid_registrations\"],\"baseline_sha256\":__import__(\"hashlib\").sha256(Path(baseline).read_bytes()).hexdigest()}; return inv,rec\n''')
  self.build=self.external/"build";self.build.mkdir();self.manifest=self.build/"manifest.json";write_json(self.manifest,{"passed":True,"manual_generation_complete":True,"validation_scope":"controlled-manual-generation","source_files_after":{n:sha((self.root/n).read_bytes()) for n in self.source_names}})
  self.snapshot=self.external/"snapshot"; write_json(self.snapshot/"snapshot.json",{"files":{n:sha(b) for n,b in self.sources.items()}})
  write_json(self.snapshot/"docs/ui-reimplementation/current-source-review.json",self.old_review)
  # Fake pinned reconciler: pure derive adds a final post-build claim and output inventory.
  self.reconciler=self.external/"manual_reconcile_build.py"; self.refresher=ui/"tools/refresh_source_inventory.py"
  self.reconciler.write_text('''import json\nfrom pathlib import Path\nimport refresh_source_inventory as refresher\nROOT=Path(\"/\")\ndef verify_manifest(root,build,pin): return json.loads((Path(build)/\"manifest.json\").read_bytes())\ndef derive_review(root,build,pin,snapshot,m,snap,review):\n out=json.loads(json.dumps(review));out[\"post_build_review\"]={\"manifest_sha256\":pin,\"complete_regression_run\":False};return out\n''')
  # Alter current three ledgers to deterministic final outputs before proof creation.
  final=copy.deepcopy(overlay_review);final["post_build_review"]={"manifest_sha256":sha(self.manifest.read_bytes()),"complete_regression_run":False}
  final_inv=copy.deepcopy(self.inventory);final_inv["files"]={k:v["sha256"] for k,v in final["files"].items()}
  final_rec={"files":copy.deepcopy(final["files"]),"branches":self.inventory["grid_registrations"],"baseline_sha256":sha((json.dumps(self.inventory,indent=2,ensure_ascii=False)+"\n").encode())}
  self.final={rel:json.dumps(v,indent=2,ensure_ascii=False).encode()+b"\n" for rel,v in zip(self.paths,[final,final_inv,final_rec])}
  for rel,data in self.final.items():(self.root/rel).write_bytes(data)
  self.identity=self.external/"identity.json"; files=[{"path":f"mosaic/lib/f{i}.lua","sha256":"a"*64,"size":1} for i in range(243)]
  for rel,b in self.before.items():files.append({"path":"mosaic/"+rel,"sha256":sha(b),"size":len(b)})
  write_json(self.identity,{"application_identity":{"files":files,"digest":"digest"}})
 def create(self,proof):
  return transition.create_proof(self.root,proof,self.bundle,self.bundle_sha,self.build,self.snapshot,self.identity,self.reconciler,self.refresher)
class FinalProofReplayTests(unittest.TestCase):
 def setUp(self): self.temp=tempfile.TemporaryDirectory();self.fixture=CompleteTransitionFixture(self.temp.name);self.proof=Path(self.temp.name)/"external/transition.json";self.fixture.create(self.proof)
 def tearDown(self): self.temp.cleanup()

 def test_scoped_context_resets_after_exception_and_checks_each_identity(self):
  second=self.fixture.external/"identity-audio.json"; ident=read(self.fixture.identity); ident["application_identity"]["files"].append({"path":"voice/lib/player.lua","sha256":"b"*64,"size":1});write_json(second,ident)
  with self.assertRaisesRegex(RuntimeError,"scope exit"):
   with transition.transition_scope(self.fixture.root,self.proof):
    self.assertEqual(transition.validate_identity_from_context(self.fixture.root,self.fixture.identity)["transitioned_metadata_files"],3)
    self.assertEqual(transition.validate_identity_from_context(self.fixture.root,second)["transitioned_metadata_files"],3)
    raise RuntimeError("scope exit")
  self.assertIsNone(transition.validate_identity_from_context(self.fixture.root,self.fixture.identity))
 def test_final_replay_creation_and_validation(self):
  self.assertEqual(transition.validate_proof(self.fixture.root,self.proof,self.fixture.identity),{"exact_application_files":243,"transitioned_metadata_files":3})
  p=read(self.proof);self.assertNotEqual(p["before"][transition.METADATA[0]]["sha256"],p["after"][transition.METADATA[0]]["sha256"])
 def test_recomputed_after_hash_cannot_replace_replayed_bytes(self):
  p=read(self.proof);rel=transition.METADATA[0];(self.fixture.root/rel).write_bytes(b"tampered");p["after"][rel]["sha256"]=sha(b"tampered");p["after"][rel]["size"]=len(b"tampered");write_json(self.proof,p)
  with self.assertRaisesRegex(ValueError,"deterministic metadata bytes"): transition.validate_proof(self.fixture.root,self.proof,self.fixture.identity)
 def test_wrong_refresher_pin_fails(self):
  p=read(self.proof);self.fixture.refresher.write_text(self.fixture.refresher.read_text()+"# drift\n")
  with self.assertRaisesRegex(ValueError,"tool pin"): transition.validate_proof(self.fixture.root,self.proof,self.fixture.identity)
 def test_current_reviewed_source_drift_fails(self):
  (self.fixture.root/self.fixture.source_names[0]).write_bytes(b"edited")
  with self.assertRaisesRegex(ValueError,"source"): transition.validate_proof(self.fixture.root,self.proof,self.fixture.identity)
 def test_source_inventory_semantics_are_preserved(self):
  p=read(self.proof); rel=transition.METADATA[1]; target=self.fixture.bundle/"approved-review-overlay"/rel; inv=read(target); inv["grid_registrations"][0]["id"]="forged";write_json(target,inv)
  bundle=read(self.fixture.bundle_manifest)
  row=next(x for x in bundle["approved_review_overlay"]["files"] if x["path"]==rel);row["approved_after_sha256"]=sha(target.read_bytes());write_json(self.fixture.bundle_manifest,bundle)
  p["overlay"]["bundle_sha256"]=sha(self.fixture.bundle_manifest.read_bytes());write_json(self.proof,p)
  with self.assertRaisesRegex(ValueError,"callbacks/branches/sections"): transition.validate_proof(self.fixture.root,self.proof,self.fixture.identity)
if __name__=="__main__": unittest.main()
