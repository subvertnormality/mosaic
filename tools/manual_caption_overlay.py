"""Apply verified editorial wording to compiled scenes; never edit captures."""
import copy
import hashlib
import json
from pathlib import Path

import jsonschema

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "manual/caption-overlays.schema.json"


def text_sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def contract_sha256(scene):
    """Bind every native field except the scene title, captions and catalogue path."""
    contract = copy.deepcopy(scene)
    contract.pop("title", None)
    contract.pop("data_path", None)
    for step in contract.get("steps", []):
        step.pop("caption", None)
        step.pop("caption_overlay", None)
    return text_sha256(json.dumps(contract, sort_keys=True, separators=(",", ":"), ensure_ascii=False))


def _validated_entries(source):
    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.Draft7Validator(schema).validate(source)
    except jsonschema.ValidationError as error:
        raise ValueError("Invalid caption overlay fields: " + error.message) from error
    if not isinstance(source, dict) or set(source) != {"schema_version", "overlays"} or source["schema_version"] != 1:
        raise ValueError("Invalid caption overlay source")
    if not isinstance(source["overlays"], list):
        raise ValueError("Invalid caption overlays")
    return source["overlays"]


def apply_overlays(scenes, source):
    """Validate all wording against original captures before returning edited copies.

    Captions-only version-1 entries remain valid. If every requested field
    already has its desired wording, the entry is a no-op and needs no historic
    receipt, matching the existing regenerated-caption behavior.
    """
    entries = _validated_entries(source)
    seen_steps = set()
    scene_title_requests = {}
    plans = []

    # This whole pass reads only the original input scenes. No presentation
    # edits are made until every entry, baseline and contract has passed.
    for entry in entries:
        allowed = {
            "scene_id", "step_id", "caption", "baseline_caption", "contract_sha256",
            "scene_title", "baseline_scene_title", "step_title", "baseline_step_title",
        }
        if not isinstance(entry, dict) or not set(entry).issubset(allowed):
            raise ValueError("Invalid caption overlay fields")
        required = {"scene_id", "step_id", "caption", "baseline_caption", "contract_sha256"}
        if not required.issubset(entry):
            raise ValueError("Invalid caption overlay fields")
        if ("scene_title" in entry) != ("baseline_scene_title" in entry):
            raise ValueError("Scene title and baseline must be supplied together")
        if ("step_title" in entry) != ("baseline_step_title" in entry):
            raise ValueError("Step title and baseline must be supplied together")
        if any(not isinstance(value, str) or not value for value in entry.values()):
            raise ValueError("Invalid caption overlay fields")

        key = (entry["scene_id"], entry["step_id"])
        if key in seen_steps:
            raise ValueError("Duplicate caption overlay")
        seen_steps.add(key)
        if key[0] not in scenes:
            raise ValueError("Unknown scene: " + key[0])
        matches = [step for step in scenes[key[0]].get("steps", []) if step.get("id") == key[1]]
        if len(matches) != 1:
            raise ValueError("Unknown step: " + key[1])
        scene = scenes[key[0]]
        step = matches[0]

        if "scene_title" in entry:
            request = (entry["baseline_scene_title"], entry["scene_title"])
            previous = scene_title_requests.get(key[0])
            if previous is not None and previous != request:
                raise ValueError("Contradictory scene title overlays: " + key[0])
            scene_title_requests[key[0]] = request

        requested = [("caption", step.get("caption"), entry["baseline_caption"], entry["caption"])]
        if "scene_title" in entry:
            requested.append(("scene_title", scene.get("title"),
                              entry["baseline_scene_title"], entry["scene_title"]))
        if "step_title" in entry:
            requested.append(("step_title", step.get("title"),
                              entry["baseline_step_title"], entry["step_title"]))

        pending = []
        for field, current, baseline, desired in requested:
            if current == desired:
                continue
            if current != baseline:
                label = {"caption": "Caption", "scene_title": "Scene title", "step_title": "Step title"}[field]
                raise ValueError(label + " baseline changed: " + str(key))
            pending.append((field, current, desired))

        # A fully regenerated desired entry is idempotent. Any partial change
        # still requires the exact raw contract from before presentation edits.
        if not pending:
            continue
        contract = contract_sha256(scene)
        if contract != entry["contract_sha256"]:
            raise ValueError("Caption semantic contract changed: " + str(key))

        for field, current, desired in pending:
            if field == "caption":
                receipt = {
                    "original_caption_sha256": text_sha256(current),
                    "caption_sha256": text_sha256(desired),
                    "contract_sha256": contract,
                }
            elif field == "scene_title":
                receipt = {
                    "original_title_sha256": text_sha256(current),
                    "title_sha256": text_sha256(desired),
                    "contract_sha256": contract,
                }
            else:
                receipt = {
                    "original_title_sha256": text_sha256(current),
                    "title_sha256": text_sha256(desired),
                    "contract_sha256": contract,
                }
            plans.append((key, field, desired, receipt))

    result = copy.deepcopy(scenes)
    applied_scene_titles = set()
    for (scene_id, step_id), field, desired, receipt in plans:
        scene = result[scene_id]
        step = next(row for row in scene["steps"] if row["id"] == step_id)
        if field == "caption":
            step["caption"] = desired
            step["caption_overlay"] = receipt
        elif field == "step_title":
            step["title"] = desired
            step["step_title_overlay"] = receipt
        elif scene_id not in applied_scene_titles:
            scene["title"] = desired
            scene["scene_title_overlay"] = receipt
            applied_scene_titles.add(scene_id)
    return result
