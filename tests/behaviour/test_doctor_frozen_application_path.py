"""Doctor source path containment for the already-verified frozen application."""
import hashlib, json, sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import manual_publication_verify as verify
class DoctorFrozenApplicationPath(unittest.TestCase):
 def setUp(self):
  self.original_root=verify.ROOT
 def tearDown(self):
  verify.ROOT=self.original_root
 def tree(self, base, target_app=None, rel="mosaic/source.lua"):
  out=base/"run"; app=out/"frozen-app"; code=out/"code"; native=out/"native"
  app.mkdir(parents=True); code.mkdir(); native.mkdir()
  relative=Path(rel)
  actual=app.joinpath(*relative.parts[1:]) if relative.parts and relative.parts[0]=="mosaic" else app/"source.lua"
  actual.parent.mkdir(parents=True,exist_ok=True); actual.write_bytes(b"pinned source")
  (code/"mosaic").symlink_to(target_app or app,target_is_directory=True)
  sha=hashlib.sha256(actual.read_bytes()).hexdigest()
  ident={"application_identity":{"code_root":str(code),"digest":"test-digest","files":[{"path":rel,"sha256":sha,"size":actual.stat().st_size}]}}
  (native/"identity.json").write_text(json.dumps(ident))
  repo=base/"repo"; repo.mkdir(exist_ok=True)
  repo_file=repo.joinpath(*relative.parts[1:]) if relative.parts and relative.parts[0]=="mosaic" else repo/"source.lua"
  repo_file.parent.mkdir(parents=True,exist_ok=True); repo_file.write_bytes(actual.read_bytes())
  verify.ROOT=repo
  return out,app,actual,native/"identity.json"
 def check(self,out,app):
  return verify.native_source_identity(out,application_root=app)
 def test_old_unscoped_policy_reproduces_frozen_app_rejection(self):
  with tempfile.TemporaryDirectory() as tmp:
   out,app,_,_=self.tree(Path(tmp))
   with self.assertRaisesRegex(ValueError,"Unsafe native application path"):
    verify.native_source_identity(out)
 def test_verified_frozen_application_passes_with_exact_source_identity(self):
  with tempfile.TemporaryDirectory() as tmp:
   out,app,_,_=self.tree(Path(tmp))
   self.assertEqual(self.check(out,app)["application_digest"],"test-digest")
 def test_wrong_symlink_target_and_parent_traversal_remain_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   base=Path(tmp); rogue=base/"rogue"; rogue.mkdir(); (rogue/"source.lua").write_bytes(b"pinned source")
   out,app,_,_=self.tree(base,target_app=rogue)
   with self.assertRaisesRegex(ValueError,"Unsafe native application path"): self.check(out,app)
  with tempfile.TemporaryDirectory() as tmp:
   out,app,_,_=self.tree(Path(tmp),rel="mosaic/../escape.lua")
   with self.assertRaisesRegex(ValueError,"Unsafe native application path"): self.check(out,app)
 def test_absolute_identity_path_remains_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   out,app,_,identity_path=self.tree(Path(tmp))
   ident=json.loads(identity_path.read_text()); ident["application_identity"]["files"][0]["path"]="/tmp/outside.lua"; identity_path.write_text(json.dumps(ident))
   with self.assertRaisesRegex(ValueError,"Unsafe native application path"): self.check(out,app)
 def test_explicit_root_does_not_allow_non_mosaic_symlink(self):
  with tempfile.TemporaryDirectory() as tmp:
   out,app,_,identity_path=self.tree(Path(tmp))
   (out/"code"/"elsewhere").symlink_to(app,target_is_directory=True)
   ident=json.loads(identity_path.read_text()); ident["application_identity"]["files"][0]["path"]="elsewhere/source.lua"; identity_path.write_text(json.dumps(ident))
   with self.assertRaisesRegex(ValueError,"Unsafe native application path"): self.check(out,app)
 def test_digest_and_size_changes_remain_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   out,app,actual,identity_path=self.tree(Path(tmp)); actual.write_bytes(b"changed source")
   with self.assertRaisesRegex(ValueError,"Changed native application source"): self.check(out,app)
  with tempfile.TemporaryDirectory() as tmp:
   out,app,_,identity_path=self.tree(Path(tmp)); ident=json.loads(identity_path.read_text()); ident["application_identity"]["files"][0]["size"]+=1; identity_path.write_text(json.dumps(ident))
   with self.assertRaisesRegex(ValueError,"Changed native application source"): self.check(out,app)
if __name__=="__main__": unittest.main()
