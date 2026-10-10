import importlib.util, json, tempfile, unittest, hashlib
from pathlib import Path
MODULE=Path(__file__).parent.parent/"tools"/"manual_metadata_transition.py"
spec=importlib.util.spec_from_file_location("transition",MODULE); transition=importlib.util.module_from_spec(spec); spec.loader.exec_module(transition)
def sha(b): return hashlib.sha256(b).hexdigest()
class TransitionIdentityTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)/"repo"; self.root.mkdir()
  self.evidence=Path(self.tmp.name)/"external"; self.evidence.mkdir()
  self.manifest=self.evidence/"manifest.json"; self.manifest.write_text(json.dumps({"passed":True,"manual_generation_complete":True,"validation_scope":"controlled-manual-generation"}))
  self.paths=transition.METADATA
  self.before={}; self.after={}
  for i,rel in enumerate(self.paths):
   p=self.root/rel; p.parent.mkdir(parents=True,exist_ok=True); self.before[rel]=f"old-{i}".encode();self.after[rel]=f"new-{i}".encode();p.write_bytes(self.after[rel])
  files=[]
  for i in range(243):
   rel=f"mosaic/lib/f{i}.lua"; files.append({"path":rel,"sha256":"a"*64,"size":1})
  for rel in self.paths:
   files.append({"path":"mosaic/"+rel,"sha256":sha(self.before[rel]),"size":len(self.before[rel])})
  self.app={"files":files,"digest":"d"*64}; self.identity=self.evidence/"identity.json"; self.write_identity()
  self.proof={"schema_version":1,"kind":"post-reconcile-metadata-transition","metadata_paths":list(self.paths),"build_manifest":{"path":str(self.manifest.resolve()),"sha256":sha(self.manifest.read_bytes())},"tools":{"reconciler_sha256":"r","refresher_sha256":"f"},"reconciler_sha256":"r","refresher_sha256":"f","before":{rel:{"sha256":sha(self.before[rel]),"size":len(self.before[rel])} for rel in self.paths},"after":{rel:{"sha256":sha(self.after[rel]),"size":len(self.after[rel])} for rel in self.paths}}
  self.payloads={rel:self.after[rel] for rel in self.paths}
 def tearDown(self): self.tmp.cleanup()
 def write_identity(self): self.identity.write_text(json.dumps({"application_identity":self.app}))
 def test_explicit_scope_reports_243_exact_and_three_transitions(self):
  result=transition.validate_identity_transition(self.root,self.proof,self.identity,self.payloads,self.manifest)
  self.assertEqual(result,{"exact_application_files":243,"transitioned_metadata_files":3})
 def test_default_source_identity_claim_is_not_implied(self):
  self.assertNotIn("all_246_current",self.proof)
  self.assertEqual(len([x for x in self.app["files"] if x["path"].startswith("mosaic/")]),246)
 def test_changed_transition_byte_fails(self):
  rel=self.paths[1]; (self.root/rel).write_bytes(b"tampered")
  with self.assertRaisesRegex(ValueError,"deterministic reconciler replay"):
   transition.validate_identity_transition(self.root,self.proof,self.identity,self.payloads,self.manifest)
 def test_wrong_captured_old_hash_fails_for_each_identity(self):
  self.app["files"][-1]["sha256"]="b"*64;self.write_identity()
  with self.assertRaisesRegex(ValueError,"captured original ledger"):
   transition.validate_identity_transition(self.root,self.proof,self.identity,self.payloads,self.manifest)
 def test_voice_roots_do_not_change_mosaic_count(self):
  self.app["files"].append({"path":"norns/lib/audio.lua","sha256":"c"*64,"size":1});self.write_identity()
  self.assertEqual(transition.validate_identity_transition(self.root,self.proof,self.identity,self.payloads,self.manifest)["exact_application_files"],243)
 def test_fourth_metadata_path_is_never_admitted(self):
  self.proof["metadata_paths"].append("docs/ui-reimplementation/extra.json")
  with self.assertRaisesRegex(ValueError,"schema/scope"):
   transition.validate_identity_transition(self.root,self.proof,self.identity,self.payloads,self.manifest)
if __name__=="__main__": unittest.main()

