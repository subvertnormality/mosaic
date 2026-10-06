"""Explicit, fail-closed proof for the post-reconcile three-ledger metadata transition."""
from __future__ import annotations
import hashlib,json,importlib.util,sys,contextvars,tempfile,shutil,os
from pathlib import Path
METADATA=("docs/ui-reimplementation/current-source-review.json","docs/ui-reimplementation/source-inventory.json","docs/ui-reimplementation/generated/source-review-receipt.json")
PREBUILD={"generated_yaml_deltas":5,"authored_cookbook_delta":1}
def sha(raw): return hashlib.sha256(raw).hexdigest()
def read(path): return json.loads(Path(path).read_bytes())
def dumps(value): return (json.dumps(value,indent=2,ensure_ascii=False)+"\n").encode()
def safe(root,rel):
 root=Path(root).resolve(); p=(root/rel).resolve()
 if p==root or root not in p.parents: raise ValueError("unsafe metadata path")
 return p
def semantic_inventory(v): return {k:v[k] for k in ("grid_registrations","controller_units","manual_sections")}
def validate_prebuild_overlay(root,bundle_dir,bundle_sha256,check_current=True,check_sources=True):
 root=Path(root).resolve(); bundle_dir=Path(bundle_dir).resolve(); manifest=bundle_dir/"physical-source-and-review-overlay.json"
 if sha(manifest.read_bytes())!=bundle_sha256: raise ValueError("overlay bundle pin mismatch")
 bundle=read(manifest); spec=bundle["approved_review_overlay"]
 if bundle.get("validation_scope")!="controlled-manual-generation" or bundle.get("launch_qualified") is not False or bundle.get("native_launched") is not False: raise ValueError("overlay scope mismatch")
 before_root=bundle_dir/"physical-source"; overlay=bundle_dir/"approved-review-overlay"; rows=spec["files"]
 if tuple(x.get("path") for x in rows)!=METADATA: raise ValueError("prebuild metadata inventory mismatch")
 before={}; after={}
 for row in rows:
  rel=row["path"]; b=safe(before_root,rel).read_bytes(); a=safe(overlay,rel).read_bytes()
  if sha(b)!=row["captured_before_sha256"] or sha(a)!=row["approved_after_sha256"]: raise ValueError("overlay bytes differ from immutable pins")
  if check_current and safe(root,rel).read_bytes()!=b: raise ValueError("current source is not the captured prebuild ledger")
  before[rel]=b;after[rel]=a
 oldi=json.loads(before[METADATA[1]]); newi=json.loads(after[METADATA[1]])
 if semantic_inventory(oldi)!=semantic_inventory(newi): raise ValueError("prebuild inventory callbacks/branches/sections changed")
 oldr=json.loads(before[METADATA[0]]); newr=json.loads(after[METADATA[0]])
 if {k:v for k,v in oldr.items() if k not in ("files","explicit_authored_review")}!={k:v for k,v in newr.items() if k not in ("files","explicit_authored_review")}: raise ValueError("prebuild review semantics changed beyond bounded delta")
 oldc=json.loads(before[METADATA[2]]); newc=json.loads(after[METADATA[2]])
 if {k:v for k,v in oldc.items() if k!="files"}!={k:v for k,v in newc.items() if k!="files"}: raise ValueError("prebuild receipt branch projection changed")
 prior=spec.get("prior_strict_validation")
 if not isinstance(prior,dict) or not Path(prior.get("path","" )).is_file() or sha(Path(prior["path"]).read_bytes())!=prior.get("sha256"): raise ValueError("prior strict source validation receipt changed")
 support=Path(spec["bounded_review"]["path"])
 if sha(support.read_bytes())!=spec["bounded_review"]["sha256"]: raise ValueError("bounded-review receipt pin mismatch")
 bounded=read(support); deltas=bounded.get("member_deltas",[])
 authored=[x for x in deltas if x.get("kind")=="authored-prerequisite-correction"]
 generated=[x for x in deltas if x.get("kind")=="historical-partial-generated-publication"]
 if bounded.get("reviewed_members")!=78 or bounded.get("manual_generation_complete") is not False or len(authored)!=1 or authored[0].get("path")!="manual/features/cookbook.yaml" or len(generated)!=5: raise ValueError("bounded authored/generated review inventory mismatch")
 for row in authored+generated:
  if check_sources:
   p=safe(root,row["path"])
   if not p.is_file() or sha(p.read_bytes())!=row["current_sha256"]: raise ValueError("bounded source changed: "+row["path"])
  elif row in generated:
   reproduction=row.get("serialization_reproduction",{}); rp=Path(reproduction.get("path","" ))
   if not rp.is_file() or sha(rp.read_bytes())!=reproduction.get("sha256"): raise ValueError("preserved generated-source reproduction changed: "+row["path"])
 for proof in bounded.get("ghost_prerequisite_qualification",[]):
  p=Path(proof["path"])
  if not p.is_file() or sha(p.read_bytes())!=proof["sha256"]: raise ValueError("authored prerequisite proof changed")
 source_pins=bundle.get("physical_source_snapshot",{}).get("files",{})
 if not source_pins: raise ValueError("missing immutable physical-source file inventory")
 # Validate every preserved source byte, not only the reviewed YAML subset.
 for rel,digest in source_pins.items():
  physical=safe(before_root,rel)
  if not physical.is_file() or sha(physical.read_bytes())!=digest: raise ValueError("immutable physical source bytes changed: "+rel)
 for rel,record in newr.get("files",{}).items():
  if source_pins.get(rel)!=record.get("sha256"): raise ValueError("reviewed source differs from immutable before snapshot: "+rel)
  if check_sources:
   p=safe(root,rel)
   if not p.is_file() or sha(p.read_bytes())!=record.get("sha256"): raise ValueError("prebuild reviewed source changed: "+rel)
 # Replay the approved overlay against its preserved physical source tree, not live post-build YAML.
 baseline_rel=Path("docs/ui-reimplementation")/newr["baseline_inventory"]; live_baseline=root/baseline_rel
 old_receipt=json.loads(before[METADATA[2]])
 if not live_baseline.is_file() or sha(live_baseline.read_bytes())!=old_receipt.get("baseline_sha256"): raise ValueError("historical source inventory baseline pin mismatch")
 with tempfile.TemporaryDirectory(prefix="manual-source-review-replay-") as td:
  shadow=Path(td)/"source"; shutil.copytree(before_root,shadow)
  shadow_baseline=shadow/baseline_rel; shadow_baseline.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(live_baseline,shadow_baseline)
  marker=root/".git"
  if marker.is_dir(): git_dir=marker.resolve()
  elif marker.is_file():
   line=marker.read_text().strip()
   if not line.startswith("gitdir:"): raise ValueError("unrecognized repository metadata marker")
   worktree_git=(root/line.split(":",1)[1].strip()).resolve()
   commondir=(worktree_git/"commondir").read_text().strip(); git_dir=(worktree_git/commondir).resolve()
  else: raise ValueError("missing source repository history for refresher replay")
  refresher_path=root/"docs/ui-reimplementation/tools/refresh_source_inventory.py"
  rspec=importlib.util.spec_from_file_location("metadata_prebuild_refresher",refresher_path); refresher=importlib.util.module_from_spec(rspec);rspec.loader.exec_module(refresher)
  refresher.ROOT=shadow/"docs/ui-reimplementation"; refresher.REPO=shadow
  prior_git_dir=os.environ.get("GIT_DIR");prior_worktree=os.environ.get("GIT_WORK_TREE")
  try:
   os.environ["GIT_DIR"]=str(git_dir);os.environ["GIT_WORK_TREE"]=str(shadow)
   inv,receipt=refresher.refresh(shadow_baseline,newr)
  finally:
   if prior_git_dir is None:os.environ.pop("GIT_DIR",None)
   else:os.environ["GIT_DIR"]=prior_git_dir
   if prior_worktree is None:os.environ.pop("GIT_WORK_TREE",None)
   else:os.environ["GIT_WORK_TREE"]=prior_worktree
  if dumps(inv)!=after[METADATA[1]] or dumps(receipt)!=after[METADATA[2]]: raise ValueError("approved overlay does not reproduce from immutable physical source snapshot")
 return {"bundle":bundle,"before":before,"overlay":after,"bounded_review":bounded,"prebuild_scope":dict(PREBUILD)}
def replay_final_metadata(root,build_evidence,manifest_sha256,prebuild_snapshot,reconciler_path,refresher_path,approved_review_path=None):
 """Regenerate final review/inventory/receipt exactly as the pinned reconciler will."""
 root=Path(root).resolve(); build=Path(build_evidence).resolve(); snapshot=Path(prebuild_snapshot).resolve()
 if sha((build/"manifest.json").read_bytes())!=manifest_sha256: raise ValueError("final build manifest pin mismatch")
 # Load copied, pinned tool modules; never execute generated artifact content.
 sys.path[:0]=[str(root/"tools"),str(root/"docs/ui-reimplementation/tools")]
 spec=importlib.util.spec_from_file_location("metadata_transition_reconciler",reconciler_path); rec=importlib.util.module_from_spec(spec);spec.loader.exec_module(rec);rec.ROOT=root;rec.refresher.ROOT=root/"docs/ui-reimplementation";rec.refresher.REPO=root
 m=rec.verify_manifest(root,build,manifest_sha256); snap_data=read(snapshot/"snapshot.json")
 review_path=Path(approved_review_path) if approved_review_path is not None else snapshot/"docs/ui-reimplementation/current-source-review.json"
 review=read(review_path)
 # Pure authored-output derivation; prepare() remains the mandatory full native audit before reconciliation.
 review=rec.derive_review(root,build,manifest_sha256,snapshot,m,snap_data,review)
 baseline=root/"docs/ui-reimplementation"/review["baseline_inventory"]
 # Re-load the exact refresher currently used by reconciler and bind ROOT explicitly.
 rspec=importlib.util.spec_from_file_location("metadata_transition_refresher",refresher_path); refresher=importlib.util.module_from_spec(rspec);rspec.loader.exec_module(refresher);refresher.ROOT=root/"docs/ui-reimplementation";refresher.REPO=root
 inventory,receipt=refresher.refresh(baseline,review)
 return {METADATA[0]:dumps(review),METADATA[1]:dumps(inventory),METADATA[2]:dumps(receipt)}
def validate_identity_transition(root,proof,identity_path,expected_payloads=None,expected_manifest=None):
 root=Path(root).resolve(); identity_path=Path(identity_path).resolve(); ident_raw=identity_path.read_bytes(); ident=read(identity_path); app=ident["application_identity"]
 if expected_manifest is not None:
  bm=Path(expected_manifest).resolve(); bmraw=bm.read_bytes()
  if proof.get("build_manifest")!={"path":str(bm),"sha256":sha(bmraw)}: raise ValueError("build manifest pin mismatch")
 if proof.get("schema_version")!=1 or proof.get("kind")!="post-reconcile-metadata-transition" or proof.get("metadata_paths")!=list(METADATA): raise ValueError("metadata transition schema/scope mismatch")
 if expected_payloads is None: expected_payloads={rel:None for rel in METADATA}
 if len(expected_payloads)!=3 or tuple(expected_payloads)!=METADATA: raise ValueError("metadata replay inventory mismatch")
 # Every capture context independently pins the original three bytes. Do not require a single identity path.
 entries={row["path"]:row for row in app.get("files",[])}
 transition=proof.get("before",{})
 for rel in METADATA:
  key="mosaic/"+rel; row=entries.get(key); record=transition.get(rel)
  if row is None or record is None or row["sha256"]!=record["sha256"] or row["size"]!=record["size"]: raise ValueError("captured original ledger mismatch: "+rel)
  current=safe(root,rel).read_bytes(); post=proof["after"].get(rel,{})
  if expected_payloads[rel] is not None and expected_payloads[rel]!=current: raise ValueError("current ledger differs from deterministic reconciler replay: "+rel)
  if sha(current)!=post.get("sha256") or len(current)!=post.get("size"): raise ValueError("post-reconcile bytes not pinned: "+rel)
 mosaic=[x for x in app.get("files",[]) if x["path"].startswith("mosaic/")]
 if len(mosaic)!=246: raise ValueError("unexpected Mosaic native source inventory")
 return {"exact_application_files":243,"transitioned_metadata_files":3}
def validate_proof(root,proof_path,identity_path=None):
 root=Path(root).resolve(); proof_path=Path(proof_path).resolve(); identity_path=Path(identity_path).resolve() if identity_path is not None else None
 if proof_path==root or root in proof_path.parents: raise ValueError("proof must remain external to repository")
 proof=read(proof_path)
 if proof.get("schema_version")!=1 or proof.get("kind")!="post-reconcile-metadata-transition" or proof.get("metadata_paths")!=list(METADATA): raise ValueError("metadata transition scope mismatch")
 reconciler=Path(proof["tools"]["reconciler_path"]); refresher=Path(proof["tools"]["refresher_path"])
 if sha(reconciler.read_bytes())!=proof["tools"]["reconciler_sha256"] or sha(refresher.read_bytes())!=proof["tools"]["refresher_sha256"]: raise ValueError("metadata transform tool pin mismatch")
 build=Path(proof["build_manifest"]["path"]).parent; manifest=build/"manifest.json"; raw=manifest.read_bytes()
 if sha(raw)!=proof["build_manifest"]["sha256"]: raise ValueError("final build manifest pin mismatch")
 m=read(manifest)
 if m.get("passed") is not True or m.get("manual_generation_complete") is not True or m.get("validation_scope")!="controlled-manual-generation": raise ValueError("final build is not complete controlled generation")
 bounded=read(Path(proof["overlay"]["bounded_review"]["path"]))
 source_after=m.get("source_files_after",{})
 for row in bounded.get("member_deltas",[]):
  p=safe(root,row["path"]); actual=sha(p.read_bytes())
  if source_after.get(row["path"])!=actual: raise ValueError("completed build does not pin bounded source after bytes: "+row["path"])
 snapshot=Path(proof["prebuild_snapshot"])
 overlay=proof["overlay"]
 pre=validate_prebuild_overlay(root,overlay["bundle_dir"],overlay["bundle_sha256"],check_current=False,check_sources=False)
 approved_review=Path(overlay["bundle_dir"])/"approved-review-overlay"/METADATA[0]
 replay=replay_final_metadata(root,build,sha(raw),snapshot,reconciler,refresher,approved_review)
 # The final inventory must preserve the native captured callback, branch, section and controller semantics.
 original=json.loads(pre["before"][METADATA[1]]); final=json.loads(replay[METADATA[1]])
 if semantic_inventory(original)!=semantic_inventory(final): raise ValueError("final ledger changed captured callback/branch/controller semantics")
 # Replayed final authoring hashes must identify current reviewed source bytes, including the separately approved cookbook update.
 final_review=json.loads(replay[METADATA[0]])
 for rel,item in final_review.get("files",{}).items():
  p=safe(root,rel)
  if not p.is_file() or sha(p.read_bytes())!=item.get("sha256"): raise ValueError("final review source hash mismatch: "+rel)
 for rel in METADATA:
  actual=safe(root,rel).read_bytes(); after=proof["after"].get(rel)
  if after is None or sha(actual)!=after["sha256"] or actual!=replay[rel] or len(actual)!=after["size"]: raise ValueError("final deterministic metadata bytes mismatch: "+rel)
 if identity_path is not None:
  ident=read(identity_path); app=ident["application_identity"]; entries={x["path"]:x for x in app.get("files",[])}
  for rel in METADATA:
   row=entries.get("mosaic/"+rel); before=proof["before"].get(rel)
   if row is None or before is None or row["sha256"]!=before["sha256"] or row["size"]!=before["size"]: raise ValueError("captured original metadata mismatch: "+rel)
  mosaic=[x for x in app.get("files",[]) if x["path"].startswith("mosaic/")]
  if len(mosaic)!=246: raise ValueError("unexpected Mosaic application identity inventory")
 return {"exact_application_files":243,"transitioned_metadata_files":3}

def create_proof(root,proof_path,bundle_dir,bundle_sha256,build_evidence,prebuild_snapshot,identity_path,reconciler_path,refresher_path):
 root=Path(root).resolve(); proof_path=Path(proof_path).resolve(); build=Path(build_evidence).resolve(); snapshot=Path(prebuild_snapshot).resolve()
 if proof_path==root or root in proof_path.parents: raise ValueError("proof must remain external to repository")
 rec=Path(reconciler_path).resolve(); ref=Path(refresher_path).resolve(); manifest=build/"manifest.json"; raw=manifest.read_bytes(); m=read(manifest)
 if m.get("passed") is not True or m.get("manual_generation_complete") is not True or m.get("validation_scope")!="controlled-manual-generation": raise ValueError("build manifest is not complete")
 pre=validate_prebuild_overlay(root,bundle_dir,bundle_sha256,check_current=False,check_sources=False)
 bounded=pre["bounded_review"]
 source_after=m.get("source_files_after",{})
 for row in bounded.get("member_deltas",[]):
  p=safe(root,row["path"]); actual=sha(p.read_bytes())
  if source_after.get(row["path"])!=actual: raise ValueError("completed build does not pin bounded source after bytes: "+row["path"])
 approved_review=Path(bundle_dir).resolve()/"approved-review-overlay"/METADATA[0]
 replay=replay_final_metadata(root,build,sha(raw),snapshot,rec,ref,approved_review)
 for rel,data in replay.items():
  if safe(root,rel).read_bytes()!=data: raise ValueError("reconciled file differs from deterministic output: "+rel)
 ip=Path(identity_path).resolve(); app=read(ip)["application_identity"]; index={x["path"]:x for x in app["files"]}; before={}
 for rel in METADATA:
  row=index.get("mosaic/"+rel)
  if row is None or row["sha256"]!=sha(pre["before"][rel]) or row["size"]!=len(pre["before"][rel]): raise ValueError("native identity does not pin original metadata: "+rel)
  before[rel]={"sha256":row["sha256"],"size":row["size"]}
 after={rel:{"sha256":sha(data),"size":len(data)} for rel,data in replay.items()}
 proof={"schema_version":1,"kind":"post-reconcile-metadata-transition","metadata_paths":list(METADATA),"build_manifest":{"path":str(manifest.resolve()),"sha256":sha(raw)},"build_evidence":str(build),"prebuild_snapshot":str(snapshot),"overlay":{"bundle_dir":str(Path(bundle_dir).resolve()),"bundle_sha256":bundle_sha256,"bounded_review":{"path":str(Path(pre["bundle"]["approved_review_overlay"]["bounded_review"]["path"]).resolve()),"sha256":pre["bundle"]["approved_review_overlay"]["bounded_review"]["sha256"]}},"tools":{"reconciler_path":str(rec),"reconciler_sha256":sha(rec.read_bytes()),"refresher_path":str(ref),"refresher_sha256":sha(ref.read_bytes())},"before":before,"after":after,"counts":{"exact_application_files":243,"transitioned_metadata_files":3}}
 proof_path.parent.mkdir(parents=True,exist_ok=True); proof_path.write_text(json.dumps(proof,indent=2)+"\n"); return proof

_TRANSITION_CONTEXT=contextvars.ContextVar("manual_metadata_transition",default=None)
def load_transition_context(root,proof_path):
 proof_path=Path(proof_path).resolve()
 validate_proof(root,proof_path,None)
 return read(proof_path)
def validate_identity_from_context(root,identity_path):
 proof=_TRANSITION_CONTEXT.get()
 if proof is None: return None
 return validate_identity_transition(root,proof,identity_path)
class transition_scope:
 def __init__(self,root,proof_path): self.root=root; self.proof_path=proof_path; self.token=None; self.proof=None
 def __enter__(self):
  self.proof=load_transition_context(self.root,self.proof_path); self.token=_TRANSITION_CONTEXT.set(self.proof); return self.proof
 def __exit__(self,typ,value,tb):
  _TRANSITION_CONTEXT.reset(self.token)
  return False
