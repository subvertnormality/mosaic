"""Static checks for manual scene plans, run before any native capture.

Capture binds each step by matching its assertion against case result rows by
content, at the moment a row is appended. Two authoring mistakes therefore only
surface after a native run, as "Missing checkpoints" or a frame bound to the
wrong moment:

* YAML 1.1 reads unquoted yes/no/on/off as booleans, so a selector written
  `state: off` can never equal the string row value 'off'.
* Identical selectors in one scene all bind the first matching row unless each
  later one names its `occurrence:`.
"""
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
BOOL_TAG = "tag:yaml.org,2002:bool"


def ambiguous_booleans(text):
    """Plain scalars YAML resolves to bool from something other than true/false."""
    found = []

    def walk(node):
        if isinstance(node, yaml.ScalarNode):
            if node.tag == BOOL_TAG and node.style is None and node.value.lower() not in ("true", "false"):
                found.append((node.start_mark.line + 1, node.value))
        elif isinstance(node, yaml.SequenceNode):
            for item in node.value:
                walk(item)
        elif isinstance(node, yaml.MappingNode):
            for key, value in node.value:
                walk(key)
                walk(value)

    walk(yaml.compose(text))
    return found


def _selector_key(step):
    return json.dumps([step.get("assertion"), step.get("assertion_alternatives")], sort_keys=True)


def unordered_duplicate_selectors(plan):
    """Steps whose selector repeats an earlier step's without a later occurrence.

    Selectors match by content, so the nth identical selector in step order must
    bind the nth matching row: occurrences must strictly increase.
    """
    last = {}
    problems = []
    for step in plan["steps"]:
        if step.get("capture_stage") == "before-finish":
            continue
        key = _selector_key(step)
        occurrence = step.get("occurrence", 1)
        if key in last and occurrence <= last[key][1]:
            problems.append((step["id"], last[key][0], occurrence))
        if key not in last or occurrence > last[key][1]:
            last[key] = (step["id"], occurrence)
    return problems


def lint_plan_file(path):
    text = Path(path).read_text()
    errors = ["%s:%d: unquoted %r is a YAML boolean; quote it" % (Path(path).name, line, value)
              for line, value in ambiguous_booleans(text)]
    for plan in yaml.safe_load(text).get("scenes", []):
        for step_id, earlier, occurrence in unordered_duplicate_selectors(plan):
            errors.append("%s: %s/%s repeats the selector of %s but has occurrence %d; "
                          "give it the ordinal of its matching row"
                          % (Path(path).name, plan["id"], step_id, earlier, occurrence))
    return errors


def plan_files(root=ROOT):
    return sorted((Path(root) / "manual").glob("scene-plans*.yaml"))


def main(argv=None):
    paths = [Path(p) for p in (argv if argv is not None else sys.argv[1:])] or plan_files()
    errors = [error for path in paths for error in lint_plan_file(path)]
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
