from __future__ import annotations
import hashlib,importlib.util,json,shutil,tarfile,tempfile
from contextlib import contextmanager
from pathlib import Path,PurePosixPath
OLD_DRIVER="924cf69c0c32ce6e06657587585ed893ba72ce5af5ee288a5a3b4fbf81e47007"
CURRENT_DRIVER="f38b4e2d329fdda79609b6a288a22f63cc5d99b20f4b01fc12fe3a732f251aba"
PROOF_ARCHIVE="c46a8ad7106e3243e6cfdacb74ede06fb1d9a734727576b61b228effa5e65a77"
PROOF_MANIFEST="6e0a69ab125fa3ca16df768c3c87d40ca48690e376b4d60d7e97aa1d91ea5eaa"
PROOF_TOOL="c5640fa87a0baebe3cc736bd3826ea6af1beba1df1bed50dac8fbaee14985a86"
PROOF_RECEIPT="e5735c5e9303df9569fcfcbf1cbc32fe84b1b1ae9ca2012805f420bed1d07da1"
FIXTURE_REL=Path("tests/fixtures/manual-audio-driver-equivalence-v08.tar.gz")
PROOF_FILES=("README.md","candidate.patch","candidate/manual/case-scenes.schema.json","candidate/tests/behaviour/driver.py","candidate/tests/behaviour/output-profiles.json","focused-tests.log","old/manual/case-scenes.schema.json","old/tests/behaviour/driver.py","old/tests/behaviour/output-profiles.json","origin-audio-scenes.yaml","origin-driver.py","origin-report.json","origin8-receipt.json","patch-application-v08.log","patch-application.log","proof-run.json","source-equivalence-receipt.json","tests/test_driver_compat_proof.py","tools/driver_compat_proof.py")
class Rejected(ValueError): pass
def need(ok,message):
 if not ok: raise Rejected(message)
def sha(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as f:
  for block in iter(lambda:f.read(1048576),b""): h.update(block)
 return h.hexdigest()
def _verify_extracted_proof_package(proof_root):
 proof_root=Path(proof_root).resolve(strict=True);manifest_path=proof_root/"snapshot-manifest.json"
 need(sha(manifest_path)==PROOF_MANIFEST,"source-equivalence proof manifest changed")
 manifest=json.loads(manifest_path.read_text())
 need(set(manifest.get("files_sha256",{}))==set(PROOF_FILES),"source-equivalence proof inventory changed")
 for rel,expected in manifest["files_sha256"].items():
  p=proof_root/rel
  need(p.is_file() and sha(p)==expected,"source-equivalence proof input changed: "+rel)
 need(sha(proof_root/"tools/driver_compat_proof.py")==PROOF_TOOL,"proof implementation hash changed")
 receipt_path=proof_root/"source-equivalence-receipt.json"
 need(sha(receipt_path)==PROOF_RECEIPT,"proof receipt hash changed")
 return receipt_path
@contextmanager
def verified_proof_package(root):
 root=Path(root).resolve(strict=True);archive=root/FIXTURE_REL
 need(archive.is_file() and sha(archive)==PROOF_ARCHIVE,"repository source-equivalence fixture missing or changed")
 expected={"proof/"+name for name in PROOF_FILES+("snapshot-manifest.json",)}
 with tempfile.TemporaryDirectory(prefix="mosaic-audio-driver-proof-") as temp:
  proof_root=Path(temp)/"proof";proof_root.mkdir()
  try:
   with tarfile.open(archive,mode="r:gz") as tar:
    members=tar.getmembers();names=[m.name for m in members]
    need(len(names)==len(set(names)) and set(names)==expected,"source-equivalence archive member inventory changed")
    for member in members:
     parts=PurePosixPath(member.name)
     need(not parts.is_absolute() and all(x not in ("",".","..") for x in parts.parts),"unsafe archive path")
     need(member.isfile() and not member.issym() and not member.islnk(),"non-regular proof archive member")
     rel=Path(*parts.parts[1:]);target=proof_root/rel
     target.parent.mkdir(parents=True,exist_ok=True)
     source=tar.extractfile(member);need(source is not None,"unreadable proof archive member")
     with source,target.open("xb") as out:shutil.copyfileobj(source,out)
  except (tarfile.TarError,OSError) as exc:
   raise Rejected("source-equivalence archive extraction failed") from exc
  receipt_path=_verify_extracted_proof_package(proof_root)
  yield proof_root,receipt_path
def verify_driver_lineage(root,run,report):
 root=Path(root).resolve(strict=True);run=Path(run).resolve(strict=True)
 old_driver=run/"driver.py";current_driver=root/"tests/behaviour/driver.py"
 need(sha(old_driver)==OLD_DRIVER,"historical run Driver bytes changed")
 need(sha(current_driver)==CURRENT_DRIVER,"current Driver is not the reviewed manual-player-ui source")
 with verified_proof_package(root) as (proof_root,receipt_path):
  spec=importlib.util.spec_from_file_location("_pinned_manual_audio_driver_compat_proof",proof_root/"tools/driver_compat_proof.py")
  need(spec is not None and spec.loader is not None,"cannot load pinned source-equivalence proof")
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  result=module.prove(old_driver,current_driver,
   proof_root/"old/tests/behaviour/output-profiles.json",root/"tests/behaviour/output-profiles.json",
   proof_root/"old/manual/case-scenes.schema.json",root/"manual/case-scenes.schema.json",
   old_driver,run/"report.json",proof_root/"origin8-receipt.json")
  sealed=json.loads(receipt_path.read_text())
  need(result==sealed and result.get("passed") is True,"recomputed source-equivalence result differs from sealed proof receipt")
  need(report.get("harness_sha256",{}).get("driver.py")==OLD_DRIVER,"historical audio report Driver pin changed")
 return {"kind":"proved-historical-audio-driver-equivalence-v08","old_driver_sha256":OLD_DRIVER,
  "current_driver_sha256":CURRENT_DRIVER,"proof_archive_sha256":PROOF_ARCHIVE,
  "proof_manifest_sha256":PROOF_MANIFEST,"proof_tool_sha256":PROOF_TOOL,
  "proof_receipt_sha256":PROOF_RECEIPT,"historical_report_sha256":sealed["origin_report_sha256"],
  "historical_completion_flags":False,"old_examples":8,"old_raw_wavs":22,
  "deferred_examples":13,"deferred_raw_wavs":32,"passed":True}
def verify_lineage_binding(provenance_lineage,marker_lineage,recomputed_lineage):
 need(isinstance(provenance_lineage,dict) and isinstance(marker_lineage,dict) and isinstance(recomputed_lineage,dict),"Driver lineage record missing")
 need(provenance_lineage==marker_lineage,"durable marker Driver lineage differs from report")
 need(provenance_lineage==recomputed_lineage,"recomputed historical/current Driver lineage differs from report")
 return True
