"""Promote the continuous teaching course only from two independently audited lanes."""
import argparse,copy,hashlib,json,os,sys
from pathlib import Path
import yaml,jsonschema
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from manual_publication_verify import audit_reference

def digest_bytes(blob):return hashlib.sha256(blob).hexdigest()
def read_document(path):
 path=Path(path).resolve()
 if path.name!="reference-scenes.json" and not path.name.endswith(".json"):raise ValueError("Expected native reference report")
 blob=path.read_bytes();return path,blob,json.loads(blob)
def check_lane(document,clock,plan):
 if document.get("clock_mode")!=clock:raise ValueError("Course clock lane mismatch")
 if document.get("complete_regression_run") is not False:raise ValueError("Course must preserve partial campaign scope")
 expected={s["id"]:s for s in plan["scenes"]}
 scenes=document.get("scenes",[])
 if len(scenes)!=10 or len({s["id"] for s in scenes})!=10 or {s["id"] for s in scenes}!=set(expected):raise ValueError("Course scene inventory mismatch")
 if document.get("selected_scene_ids")!=[s["id"] for s in plan["scenes"]]:raise ValueError("Course scene selection changed")
 contexts=set();paths=set();total=0
 for scene in scenes:
  authored=expected[scene["id"]]
  if scene.get("feature_id")!=authored["feature_id"] or scene.get("behaviour_case")!="M-MANUAL-COURSE-001" or scene.get("session_ordinal")!=0:raise ValueError("Course scene ownership changed")
  steps=scene.get("steps",[]);wanted={step["id"]:step for step in authored["steps"]}
  if len(steps)!=len(wanted) or {s["id"] for s in steps}!=set(wanted):raise ValueError("Course checkpoint inventory mismatch")
  total+=len(steps)
  evidence=scene["evidence"];context=evidence["session_context"]
  if context.get("session_ordinal")!=0 or context.get("clock_mode")!=clock or context.get("finished") is not True or context.get("cleanup_verified") is not True or context.get("held_inputs")!=[]:raise ValueError("Course continuous session cleanup missing")
  participants=evidence.get("case_participants",[])
  if len(participants)!=1 or participants[0].get("session_context")!=context or Path(participants[0]["path"]).resolve()!=Path(evidence["path"]).resolve():raise ValueError("Course continuous participant mismatch")
  contexts.add(context["session_id"]);paths.add(str(Path(evidence["path"]).resolve()))
  for step in steps:
   binding=step.get("output",{}).get("binding",{})
   if binding.get("passed") is not True or not binding.get("semantic_assertions") or not binding.get("sha256") or not binding.get("grid_sha256"):raise ValueError("Course checkpoint lacks native semantic proof")
   assertion=binding.get("assertion",{})
   if any(assertion.get(k)!=v for k,v in wanted[step["id"]]["assertion"].items()):raise ValueError("Course checkpoint semantic selector changed")
 if total!=48:raise ValueError("Course checkpoint total must be 48")
 if len(contexts)!=1 or len(paths)!=1:raise ValueError("Course requires one continuous native session")
 return dict(clock_mode=clock,session_id=next(iter(contexts)),participant=next(iter(paths)),scenes=10,checkpoints=48)

def check_course(course,plan,verify_only):
 expected={s["feature_id"]:s for s in plan["scenes"]};routes=[c["id"] for c in course["learning_path"]]
 if len(routes)!=10 or len(set(routes))!=10 or set(routes)!=set(expected):raise ValueError("Course chapter inventory mismatch")
 mappings=[]
 for chapter in course["learning_path"]:
  scene=expected[chapter["id"]]
  if scene["id"]!="course-"+chapter["id"]:raise ValueError("Course scene route mapping mismatch")
  step_ids={s["id"] for s in scene["steps"]}
  for stage in chapter["stages"]:
   if stage["id"] not in step_ids:raise ValueError("Course stage mapping mismatch")
   mapping=dict(status="verified",scene=scene["id"],step=stage["id"])
   if verify_only and stage["binding"]!=mapping:raise ValueError("Course stage mapping is not verified")
   if not verify_only and stage["binding"]["status"]=="verified" and stage["binding"]!=mapping:raise ValueError("Existing course stage mapping differs")
   mappings.append(dict(stage=stage["id"],scene=scene["id"],step=stage["id"]))
 if len(mappings)!=38 or len({m["stage"] for m in mappings})!=38:raise ValueError("Course requires all 38 distinct teaching stages")
 if verify_only and course["project"]["capture_status"]!="verified":raise ValueError("Course project not verified")
 return mappings

def bind(real_report,controlled_report,evidence,root=ROOT,verify_only=False):
 root=Path(root).resolve();course_path=root/"manual/course.yaml";before=course_path.read_bytes();course=yaml.safe_load(before)
 schema=json.loads((root/"manual/course.schema.json").read_text());jsonschema.Draft7Validator(schema).validate(course)
 plan_path=root/"manual/scene-plans-course.yaml";plan_blob=plan_path.read_bytes();plan=yaml.safe_load(plan_blob)
 mappings=check_course(course,plan,verify_only)
 reports=[read_document(p) for p in (real_report,controlled_report)]
 if reports[0][0]==reports[1][0]:raise ValueError("Course lanes must have independent reports")
 lanes=[]
 for (path,blob,document),clock in zip(reports,("real-time","controlled-experimental")):
  lane=check_lane(document,clock,plan)
  audited=audit_reference(document)
  if audited!=48:raise ValueError("Independent course audit did not verify all 48 checkpoints")
  lane.update(report=str(path),report_sha256=digest_bytes(blob),independent_audit_frames=audited)
  lanes.append(lane)
 if lanes[0]["session_id"]==lanes[1]["session_id"] or lanes[0]["participant"]==lanes[1]["participant"]:raise ValueError("Course lanes reused a native session")
 after=copy.deepcopy(course)
 for chapter in after["learning_path"]:
  for stage in chapter["stages"]:stage["binding"]=dict(status="verified",scene="course-"+chapter["id"],step=stage["id"])
 after["project"]["capture_status"]="verified"
 after_blob=before if verify_only else yaml.safe_dump(after,sort_keys=False,allow_unicode=True).encode()
 # Verify inputs again immediately before any mutation; captures stay immutable.
 if course_path.read_bytes()!=before or plan_path.read_bytes()!=plan_blob or any(path.read_bytes()!=blob for path,blob,doc in reports):raise ValueError("Course binding inputs changed during audit")
 receipt=dict(schema_version=1,passed=False,verify_only=verify_only,course_before_sha256=digest_bytes(before),course_after_sha256=digest_bytes(after_blob),plan_sha256=digest_bytes(plan_blob),lanes=lanes,mappings=mappings,complete_regression_run=False,hardware_timing_verified=False,course_written=False)
 evidence=Path(evidence).resolve()
 if evidence==root or root in evidence.parents and evidence==course_path.parent:raise ValueError("Evidence must be a fresh dedicated directory")
 evidence.mkdir(parents=True,exist_ok=False)
 (evidence/"course-before.yaml").write_bytes(before);(evidence/"course-after.yaml").write_bytes(after_blob)
 receipt_path=evidence/"binding-receipt.json";receipt_path.write_text(json.dumps(receipt,indent=2)+"\n")
 if not verify_only:
  temporary=course_path.with_name("course.yaml.binding-new")
  try:
   with temporary.open("xb") as output:output.write(after_blob);output.flush();os.fsync(output.fileno())
   if course_path.read_bytes()!=before:raise ValueError("Course changed before atomic replacement")
   temporary.replace(course_path);receipt["course_written"]=True
  finally:
   if temporary.exists():temporary.unlink()
 receipt["passed"]=True
 receipt_path.write_text(json.dumps(receipt,indent=2)+"\n")
 if not verify_only:
  public=dict(receipt,immutable_receipt=str(receipt_path),immutable_receipt_sha256=digest_bytes(receipt_path.read_bytes()))
  target=root/"manual/generated/course-binding.json";target.parent.mkdir(parents=True,exist_ok=True)
  temporary=target.with_name(target.name+".new")
  with temporary.open("xb") as output:output.write((json.dumps(public,indent=2)+"\n").encode());output.flush();os.fsync(output.fileno())
  temporary.replace(target)
 return receipt

def verify_publication(root=ROOT):
 """Recheck current course and immutable native reports without writing artifacts."""
 root=Path(root).resolve();target=root/"manual/generated/course-binding.json"
 if not target.is_file():raise ValueError("Missing durable course binding receipt")
 public=json.loads(target.read_text())
 if public.get("schema_version")!=1 or public.get("passed") is not True or public.get("course_written") is not True or public.get("verify_only") is not False or public.get("complete_regression_run") is not False or public.get("hardware_timing_verified") is not False:raise ValueError("Forged course binding receipt status")
 try:
  immutable=Path(public["immutable_receipt"]).resolve();blob=immutable.read_bytes()
  if digest_bytes(blob)!=public["immutable_receipt_sha256"]:raise ValueError("Changed immutable course binding receipt")
  original=json.loads(blob);expected={k:v for k,v in public.items() if k not in ("immutable_receipt","immutable_receipt_sha256")}
  if original!=expected:raise ValueError("Durable course receipt differs from immutable receipt")
  for name,key in (("course-before.yaml","course_before_sha256"),("course-after.yaml","course_after_sha256")):
   if digest_bytes((immutable.parent/name).read_bytes())!=public[key]:raise ValueError("Changed immutable course authoring snapshot")
  course_blob=(root/"manual/course.yaml").read_bytes()
  if digest_bytes(course_blob)!=public["course_after_sha256"]:raise ValueError("Current course differs from binding receipt")
  course=yaml.safe_load(course_blob);jsonschema.Draft7Validator(json.loads((root/"manual/course.schema.json").read_text())).validate(course)
  plan_blob=(root/"manual/scene-plans-course.yaml").read_bytes()
  if digest_bytes(plan_blob)!=public["plan_sha256"]:raise ValueError("Current course plan differs from binding receipt")
  plan=yaml.safe_load(plan_blob);mappings=check_course(course,plan,True)
  if mappings!=public["mappings"]:raise ValueError("Course publication mapping changed")
  stored=public["lanes"]
  if len(stored)!=2:raise ValueError("Course binding receipt requires both lanes")
  lanes=[]
  for receipt,clock in zip(stored,("real-time","controlled-experimental")):
   path,blob,document=read_document(receipt["report"])
   if digest_bytes(blob)!=receipt["report_sha256"]:raise ValueError("Changed course native report")
   lane=check_lane(document,clock,plan);audited=audit_reference(document)
   if audited!=48:raise ValueError("Course independent publication audit omitted checkpoints")
   lane.update(report=str(path),report_sha256=digest_bytes(blob),independent_audit_frames=audited)
   if lane!=receipt:raise ValueError("Course lane receipt changed")
   lanes.append(lane)
  if lanes[0]["session_id"]==lanes[1]["session_id"] or lanes[0]["participant"]==lanes[1]["participant"]:raise ValueError("Course publication reused a native session")
 except (KeyError,OSError,TypeError,json.JSONDecodeError,jsonschema.ValidationError) as error:raise ValueError("Malformed course publication receipt: "+str(error)) from error
 return dict(passed=True,course_sha256=public["course_after_sha256"],receipt_sha256=digest_bytes(target.read_bytes()),lanes=lanes,mappings=mappings,complete_regression_run=False,hardware_timing_verified=False)

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument("--real-report",required=True,type=Path);parser.add_argument("--controlled-report",required=True,type=Path)
 parser.add_argument("--evidence",required=True,type=Path);parser.add_argument("--verify-only",action="store_true")
 options=parser.parse_args();print(json.dumps(bind(options.real_report,options.controlled_report,options.evidence,verify_only=options.verify_only),indent=2))
if __name__=="__main__":main()
