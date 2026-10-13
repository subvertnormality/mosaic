"""Apply authored starting states (editorial descriptions of a scene's prepared start)."""
import copy


def apply(scenes, document):
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise ValueError("Unsupported starting-state document")
    result = copy.deepcopy(scenes)
    seen = set()
    for entry in document.get("starting_states", []):
        scene_id, text = entry.get("scene_id"), entry.get("text")
        if scene_id in seen:
            raise ValueError("Duplicate starting state: " + str(scene_id))
        if scene_id not in result:
            raise ValueError("Unknown scene for starting state: " + str(scene_id))
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Starting state needs text: " + scene_id)
        steps = result[scene_id].get("steps") or []
        if steps and steps[0].get("id") == "start":
            raise ValueError("Scene has a start step that describes its starting point: " + scene_id)
        seen.add(scene_id)
        result[scene_id]["starting_state"] = text.strip()
    return result
