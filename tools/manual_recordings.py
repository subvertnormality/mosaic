"""Compile authored recording context without changing audio evidence or native contracts."""
from pathlib import Path
import copy,hashlib,json,yaml,jsonschema
_SOURCE_MODELS={}
def _read(path):
 path=Path(path);raw=path.read_bytes();key=(str(path.resolve()),hashlib.sha256(raw).hexdigest())
 if key not in _SOURCE_MODELS:_SOURCE_MODELS[key]=yaml.safe_load(raw.decode("utf-8"))
 return copy.deepcopy(_SOURCE_MODELS[key])

def known_recordings(root):
 root=Path(root);config=_read(root/"manual/book.yaml");ids=set()
 for name in config.get("audio_sources",[]):
  path=(root/"manual"/name).resolve()
  if root.resolve() not in path.parents:raise ValueError("Unsafe recording identity source")
  for row in _read(path).get("examples",[]):
   if row["id"] in ids:raise ValueError("Duplicate authored recording identity")
   ids.add(row["id"])
 for name in config.get("sources",[]):
  path=(root/"manual"/name).resolve()
  if root.resolve() not in path.parents:raise ValueError("Unsafe feature audio identity source")
  audio=_read(path).get("audio")
  if audio:
   stems={Path(f).stem for f in audio["files"]}
   if len(stems)!=1:raise ValueError("Feature audio files disagree on recording identity")
   rid=next(iter(stems))
   if rid in ids:raise ValueError("Duplicate feature recording identity")
   ids.add(rid)
 return ids

def compile_context(source,data,root,source_path):
 root=Path(root);path=Path(source_path).resolve()
 if root.resolve() not in path.parents:raise ValueError("Unsafe recording context source")
 if source!=_read(path):raise ValueError("Recording context source changed")
 schema=json.loads((root/"manual/recordings.schema.json").read_text())
 try:jsonschema.Draft7Validator(schema).validate(source)
 except jsonschema.ValidationError as e:raise ValueError("Invalid recording context: "+e.message)from e
 features={f["id"]:f for f in data["features"]};course=data.get("course",{});chapters=course.get("learning_path",data.get("learning_path",[]));stages={s["id"]:ch["id"] for ch in chapters for s in ch["stages"]}
 recordings={}
 for authored in source["recordings"]:
  row=copy.deepcopy(authored);rid=row["id"]
  if rid in recordings:raise ValueError("Duplicate recording context ID: "+rid)
  for rel in row["lesson_relations"]:
   kind=rel["kind"]
   if kind=="course-stage":
    sid=rel["course_stage_id"]
    if sid not in stages:raise ValueError("Unknown recording course stage: "+sid)
    route="#"+stages[sid]+"/lesson/"+sid
   else:
    fid=rel["feature_id"]
    if fid not in features:raise ValueError("Unknown recording feature: "+fid)
    feature=features[fid]
    if kind=="feature-lesson":
     lid=rel["lesson_id"]
     if len([l for l in feature.get("teaching_bindings",[])if l["id"]==lid])!=1:raise ValueError("Unknown recording feature lesson: "+lid)
     route="#"+fid+"/lesson/"+lid
    else:
     i=rel["recipe_index"]
     if i>len(feature["recipes"])or feature["recipes"][i-1]["title"]!=rel["recipe_title"]:raise ValueError("Recording recipe index/title changed")
     route="#"+fid+"/recipe/"+str(i)
   rel["canonical_route"]=route
  recordings[rid]=row
 if set(recordings)!=known_recordings(root):raise ValueError("Recording context inventory differs from exact authored audio IDs")
 return {"schema_version":1,"source":{"path":path.relative_to(root.resolve()).as_posix(),"sha256":hashlib.sha256(path.read_bytes()).hexdigest()},"recordings":recordings}
