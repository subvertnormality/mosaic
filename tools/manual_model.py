"""Load and validate the review pilot. Runtime rendering consumes generated JSON."""
import hashlib
import json
import re
from pathlib import Path
import yaml
import jsonschema

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "manual"

def load(path=None):
    return yaml.safe_load(Path(path or MANUAL / "features/masks.yaml").read_text())

def validate(data):
    schema = json.loads((MANUAL / "schema.json").read_text())
    try:
        jsonschema.Draft7Validator(schema).validate(data)
    except jsonschema.ValidationError as error:
        raise ValueError(error.message) from error
    case_source = (ROOT / "tests/behaviour/cases.py").read_text()
    ids = set()
    for scene in data["scenes"]:
        if scene["id"] in ids:
            raise ValueError("Duplicate scene ID")
        ids.add(scene["id"])
        if scene["behaviour_case"] not in case_source:
            raise ValueError("Unknown behaviour case")
        held = set()
        for step in scene["steps"]:
            for action in step["inputs"]:
                if action["type"] in ("key", "grid") and "state" in action:
                    key = (action["type"], action.get("n"), action.get("x"), action.get("y"))
                    if action["state"]:
                        if key in held: raise ValueError("Duplicate press")
                        held.add(key)
                    elif key not in held:
                        raise ValueError("Release without press")
                    else: held.remove(key)
        if held: raise ValueError("Scene leaves controls held")
    for filename in data["audio"]["files"]:
        if not re.fullmatch(r"audio/[a-z0-9-]+\.(ogg|mp3)", filename):
            raise ValueError("Unsafe audio path")
    return data

def validate_capture(capture):
    for key, size in (("levels", 8192), ("grid", 128)):
        values = capture[key]
        if len(values) != size or any(type(v) is not int or not 0 <= v <= 15 for v in values):
            raise ValueError("Invalid " + key + " dimensions or brightness")

def source_hash(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",",":")).encode()).hexdigest()

if __name__ == "__main__":
    data = validate(load())
    print("Valid:", data["feature"]["id"], len(data["scenes"]), "scenes")
