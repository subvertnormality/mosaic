"""Compile the complete field-guide catalogue without inventing capture evidence."""
import hashlib,json,re,sys
from pathlib import Path
import yaml,jsonschema
ROOT=Path(__file__).resolve().parents[1]
MANUAL=ROOT/"manual"
sys.path.insert(0,str(ROOT/"tests/behaviour"))
sys.path.insert(0,str(ROOT/"tools"))
from manual_authority import authoring_identity
from manual_caption_overlay import apply_overlays
def read(path):return yaml.safe_load(Path(path).read_text())
def load():
    config=read(MANUAL/"book.yaml");features=[]
    for name in config["sources"]:
        data=read(MANUAL/name)
        if "features" in data:features.extend(data["features"])
        else:
            feature=dict(data["feature"],scene_refs=[s["id"] for s in data["scenes"]],
                         review=dict(status="pilot-reviewed",cases=feature_cases(data)),
                         category=data["feature"].get("category","channel"),
                         parent=data["feature"].get("parent","channel-editor"),level=data["feature"].get("level",3))
            features.append(feature)
    result=dict(config,features=features)
    if config.get("course_source"):
        result["course"]=read(course_path(config["course_source"]))
        course=result["course"]
        result.update(course_title=course["title"],course_summary=course["summary"],project=course["project"],learning_path=course["learning_path"])
    return result
def course_path(source):
    path=(MANUAL/source).resolve()
    if MANUAL.resolve() not in path.parents:raise ValueError("Unsafe course source: "+source)
    return path
def feature_cases(data):return sorted({s["behaviour_case"] for s in data["scenes"]})
def resolve(data,identifier):return data.get("aliases",{}).get(identifier,identifier)
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def capture_catalogue():
    result={}
    for path in sorted((MANUAL/"generated").glob("*.json")):
        if path.name=="book.json":continue
        data=json.loads(path.read_text())
        for scene in data.get("scenes",[]):
            if scene["id"] in result:raise ValueError("Duplicate captured scene")
            result[scene["id"]]=dict(scene,data_path=path.relative_to(MANUAL).as_posix())
    return result
def validate(data):
    schema=json.loads((MANUAL/"book.schema.json").read_text())
    try:jsonschema.Draft7Validator(schema).validate(data)
    except jsonschema.ValidationError as error:raise ValueError(error.message) from error
    ids=[f["id"] for f in data["features"]]
    if len(set(ids))!=len(ids):raise ValueError("Duplicate feature ID")
    scenes=capture_catalogue()
    for feature in data["features"]:
        for related in feature["related"]:
            if resolve(data,related) not in ids:raise ValueError("Unknown related feature: "+related)
        if feature.get("parent") and feature["parent"] not in ids:raise ValueError("Unknown parent")
        for name in feature["sources"].get("code",[]):
            p=ROOT/name
            if p.resolve()!=ROOT and ROOT not in p.resolve().parents:
                raise ValueError("Unsafe source path")
            if not p.is_file():raise ValueError("Missing source: "+name)
        for scene in feature["scene_refs"]:
            if scene not in scenes:raise ValueError("Unknown scene: "+scene)
    if "course" in data:
        course_path(data["course_source"])
        validate_course(data["course"],ids,scenes)
    for old,new in data.get("aliases",{}).items():
        if new not in ids:raise ValueError("Unknown alias target")
    legacy=MANUAL/data["legacy_source"]
    if digest(legacy)!=data["legacy_source_sha256"]:raise ValueError("Legacy source identity changed")
    return data
def validate_course(course,feature_ids,scenes):
    schema=json.loads((MANUAL/"course.schema.json").read_text())
    try:jsonschema.Draft7Validator(schema).validate(course)
    except jsonschema.ValidationError as error:raise ValueError("Invalid course: "+error.message) from error
    routes=set();stages=set()
    for chapter in course["learning_path"]:
        route=chapter["id"]
        if route in routes:raise ValueError("Duplicate course route: "+route)
        routes.add(route)
        if route not in feature_ids:raise ValueError("Unknown course route: "+route)
        for stage in chapter["stages"]:
            if stage["id"] in stages:raise ValueError("Duplicate course stage: "+stage["id"])
            stages.add(stage["id"])
            binding=stage["binding"]
            if binding["scene"] is None:continue
            if binding["scene"] not in scenes:raise ValueError("Unknown course scene: "+binding["scene"])
            scene=scenes[binding["scene"]]
            matched=[step for step in scene["steps"] if step["id"]==binding["step"]]
            if len(matched)!=1:raise ValueError("Unknown course step: "+str(binding["step"]))
            if binding["status"]=="verified":
                proof=matched[0].get("output",{}).get("binding",{})
                if proof.get("passed") is not True or not proof.get("semantic_assertions") or not proof.get("sha256") or not proof.get("grid_sha256"):
                    raise ValueError("Unverified course binding: "+stage["id"])
    return course

def compile_book(data):
    validate(data)
    canonical=json.dumps(data,sort_keys=True,separators=(",",":")).encode()
    scenes=capture_catalogue()
    overlay_path=MANUAL/"scene-captions.yaml"
    if overlay_path.is_file():
        if "scene-captions.yaml" not in data.get("scene_sources",[]):
            raise ValueError("Caption overlay missing from authoring identity")
        scenes=apply_overlays(scenes,read(overlay_path))
    complete=all(f["review"]["status"] in ("verified","pilot-reviewed") for f in data["features"])
    course=data.get("course")
    if course:
        complete=complete and course["project"]["capture_status"]=="verified" and all(stage["binding"]["status"]=="verified" for chapter in course["learning_path"] for stage in chapter["stages"])
    course_scenes={stage["binding"]["scene"] for chapter in course["learning_path"] for stage in chapter["stages"]} if course else set()
    result=dict(schema_version=2,edition=data["edition"],title=data["title"],
                authoring_identity=authoring_identity(ROOT),
                source_sha256=hashlib.sha256(canonical).hexdigest(),
                legacy_source_sha256=data["legacy_source_sha256"],
                complete_manual=complete,aliases=data["aliases"],navigation=data["navigation"],
                features=data["features"],
                scenes={key:value for key,value in scenes.items() if key in course_scenes or any(key in f["scene_refs"] for f in data["features"])})
    if course:result.update(course_title=course["title"],course_summary=course["summary"],project=course["project"],learning_path=course["learning_path"])
    return result
def main():
    data=compile_book(load())
    (MANUAL/"generated/book.json").write_text(json.dumps(data,separators=(",",":"))+"\n")
    print(len(data["features"]),"stable feature destinations;",len(data["scenes"]),"verified scenes;", "complete" if data["complete_manual"] else "expansion in progress")
if __name__=="__main__":main()
