"""Apply verified editorial captions only to compiled scenes; never edit captures."""
import copy,hashlib,json
from pathlib import Path
import jsonschema
SCHEMA_PATH=Path(__file__).resolve().parents[1]/"manual/caption-overlays.schema.json"

def text_sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def contract_sha256(scene):
    """Bind every native field except the scene title, captions and catalogue path."""
    contract=copy.deepcopy(scene)
    contract.pop("title",None)
    contract.pop("data_path",None)
    for step in contract.get("steps",[]):
        step.pop("caption",None)
        step.pop("caption_overlay",None)
    return text_sha256(json.dumps(contract,sort_keys=True,separators=(",",":"),ensure_ascii=False))

def apply_overlays(scenes,source):
    """Validate the complete overlay against originals before returning edited copies.

    A fresh capture with the desired wording needs no historic overlay receipt.
    Input scenes and immutable generated capture files are never modified.
    """
    try:
        jsonschema.Draft7Validator(json.loads(SCHEMA_PATH.read_text())).validate(source)
    except jsonschema.ValidationError as error:
        raise ValueError("Invalid caption overlay fields: "+error.message) from error
    if not isinstance(source,dict) or set(source)!={"schema_version","overlays"} or source["schema_version"]!=1:
        raise ValueError("Invalid caption overlay source")
    if not isinstance(source["overlays"],list):raise ValueError("Invalid caption overlays")
    fields={"scene_id","step_id","caption","baseline_caption","contract_sha256"}
    seen=set();changes=[]
    for entry in source["overlays"]:
        if not isinstance(entry,dict) or set(entry)!=fields or any(not isinstance(v,str) or not v for v in entry.values()):
            raise ValueError("Invalid caption overlay fields")
        key=(entry["scene_id"],entry["step_id"])
        if key in seen:raise ValueError("Duplicate caption overlay")
        seen.add(key)
        if key[0] not in scenes:raise ValueError("Unknown scene: "+key[0])
        matches=[step for step in scenes[key[0]].get("steps",[]) if step["id"]==key[1]]
        if len(matches)!=1:raise ValueError("Unknown step: "+key[1])
        step=matches[0]
        if step.get("caption")==entry["caption"]:continue
        if step.get("caption")!=entry["baseline_caption"]:raise ValueError("Caption baseline changed: "+str(key))
        contract=contract_sha256(scenes[key[0]])
        if contract!=entry["contract_sha256"]:raise ValueError("Caption semantic contract changed: "+str(key))
        receipt={"original_caption_sha256":text_sha256(step["caption"]),
                 "caption_sha256":text_sha256(entry["caption"]),"contract_sha256":contract}
        changes.append((key,entry["caption"],receipt))
    result=copy.deepcopy(scenes)
    for (scene_id,step_id),caption,receipt in changes:
        step=next(s for s in result[scene_id]["steps"] if s["id"]==step_id)
        step["caption"]=caption
        step["caption_overlay"]=receipt
    return result
