"""Refresh editorial receipts only after independent raw native publication audit.

CLI evidence must name a new directory. Previous captions, refreshed captions,
the independent audit and exact native publication hashes remain reviewable there.
Native publications, desired captions and all input/acceptance data are immutable.
"""
import argparse,copy,hashlib,json,os,uuid
from pathlib import Path
import yaml,jsonschema
from manual_caption_overlay import SCHEMA_PATH,apply_overlays,contract_sha256

ROOT=Path(__file__).resolve().parents[1]

def digest_bytes(value):
    return hashlib.sha256(value).hexdigest()

def native_snapshot(root):
    return {path.relative_to(root).as_posix():path.read_bytes()
            for path in sorted((root/"manual/generated").glob("*.json"))
            if path.name not in ("book.json","reader-index.json")}  # derived reader artifacts, not native publications

def catalogue(snapshot):
    result={}
    for name,raw in snapshot.items():
        document=json.loads(raw)
        for scene in document.get("scenes",[]):
            if scene["id"] in result:raise ValueError("Duplicate captured scene: "+scene["id"])
            result[scene["id"]]=dict(scene,data_path=Path(name).relative_to("manual").as_posix())
    return result

def audit_raw_publications(controlled_local=False):
    from manual_publication_verify import audit_raw_publications as independent_audit
    return independent_audit(controlled_local=True) if controlled_local else independent_audit()

def unchanged(root,source,before,native):
    if source.read_bytes()!=before:raise ValueError("Caption source changed during audit or refresh")
    if native_snapshot(root)!=native:raise ValueError("Native publication changed during audit or refresh")

def immutable_json(path,value):
    with path.open("x",encoding="utf-8") as handle:
        json.dump(value,handle,indent=2,ensure_ascii=False);handle.write("\n")

def immutable_bytes(path,value):
    with path.open("xb") as handle:handle.write(value)

def rebind(evidence,root=ROOT,auditor=None,controlled_local=False):
    """Audit first, validate every replacement, then commit one source update.

    A changed baseline caption requires editorial review. Fresh raw desired wording
    requires no historical rebind. Evidence/run/frame hashes may change only after
    the independent auditor accepts their actual native assertions and sources.
    """
    root=Path(root).resolve();evidence=Path(evidence).resolve()
    if evidence.exists():raise ValueError("Evidence already exists: "+str(evidence))
    source=root/"manual/scene-captions.yaml"
    before=source.read_bytes();native=native_snapshot(root)
    audit=auditor() if auditor else audit_raw_publications(controlled_local=controlled_local)
    if not isinstance(audit,dict) or audit.get("passed") is not True:
        raise ValueError("Independent raw audit did not pass")
    unchanged(root,source,before,native)
    original=yaml.safe_load(before);schema=json.loads(SCHEMA_PATH.read_text())
    try:jsonschema.Draft7Validator(schema).validate(original)
    except jsonschema.ValidationError as error:
        raise ValueError("Invalid caption overlay fields: "+error.message) from error
    scenes=catalogue(native);updated=copy.deepcopy(original)
    refreshed=[];fresh_wording=[]
    for entry in updated["overlays"]:
        scene=scenes.get(entry["scene_id"])
        if scene is None:raise ValueError("Unknown scene: "+entry["scene_id"])
        steps=[step for step in scene.get("steps",[]) if step["id"]==entry["step_id"]]
        if len(steps)!=1:raise ValueError("Unknown step: "+entry["step_id"])
        step=steps[0];identifier=entry["scene_id"]+"/"+entry["step_id"]
        caption_is_desired=step.get("caption")==entry["caption"]
        title_requests_are_desired=(
            ("scene_title" not in entry or scene.get("title")==entry["scene_title"])
            and ("step_title" not in entry or step.get("title")==entry["step_title"])
        )
        if caption_is_desired and title_requests_are_desired:
            fresh_wording.append(identifier);continue
        if not caption_is_desired and step.get("caption")!=entry["baseline_caption"]:
            raise ValueError("Caption baseline changed: "+identifier)
        contract=contract_sha256(scene)
        if contract!=entry["contract_sha256"]:
            entry["contract_sha256"]=contract;refreshed.append(identifier)
    apply_overlays(scenes,updated)
    after=yaml.safe_dump(updated,sort_keys=False,allow_unicode=True,width=100).encode("utf-8") if refreshed else before
    unchanged(root,source,before,native)
    evidence.mkdir(parents=True,exist_ok=False)
    immutable_bytes(evidence/"source-before.yaml",before)
    immutable_json(evidence/"audit.json",audit)
    audit_digest=digest_bytes((evidence/"audit.json").read_bytes())
    temporary=source.parent/(".scene-captions.rebind."+uuid.uuid4().hex+".tmp")
    try:
        if after!=before:
            with temporary.open("xb") as handle:
                handle.write(after);handle.flush();os.fsync(handle.fileno())
            unchanged(root,source,before,native)
            os.replace(str(temporary),str(source))
    finally:
        if temporary.exists():temporary.unlink()
    if source.read_bytes()!=after:raise ValueError("Changed caption source after replacement")
    if native_snapshot(root)!=native:raise ValueError("Native publication changed after replacement")
    immutable_bytes(evidence/"source-after.yaml",after)
    report=dict(passed=True,complete_regression_run=False,hardware_timing_verified=False,
                refreshed=refreshed,fresh_wording=fresh_wording,
                source_before_sha256=digest_bytes(before),source_after_sha256=digest_bytes(after),
                audit_sha256=audit_digest,native_publications={name:digest_bytes(raw) for name,raw in native.items()},
                raw_publications_unchanged=True,desired_captions_unchanged=True,
                evidence=str(evidence))
    immutable_json(evidence/"receipt.json",report)
    return report

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence",type=Path,required=True,help="New immutable receipt directory")
    parser.add_argument("--controlled-local",action="store_true",help="Audit raw publications in controlled manual-generation scope")
    options=parser.parse_args()
    print(json.dumps(rebind(options.evidence,controlled_local=options.controlled_local),indent=2))
if __name__=="__main__":main()
