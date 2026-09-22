"""Fail-closed recipe and result comparison for one migrated case lane."""

import argparse
import json
from pathlib import Path


def _without_monotonic(value):
    if isinstance(value, dict):
        return {key: _without_monotonic(item) for key, item in value.items()
                if key != "at_monotonic_ns"}
    if isinstance(value, list):
        return [_without_monotonic(item) for item in value]
    return value


def normalize_recipe(recipe):
    return _without_monotonic(recipe)


def compare_results(before, after, lane):
    errors = []
    for side, values in (("before", before), ("after", after)):
        for index, entry in enumerate(values):
            if not isinstance(entry, dict) or not entry.get("kind"):
                errors.append("%s result %d has no kind" % (side, index))
    if errors:
        return errors
    filtered_after = [entry for entry in after if entry["kind"] != "ui-confirm"]
    if lane == "controlled":
        if before != filtered_after:
            errors.append("controlled results differ beyond added ui-confirm entries")
    elif lane == "real-time":
        before_kinds = [entry["kind"] for entry in before]
        after_kinds = [entry["kind"] for entry in filtered_after]
        if before_kinds != after_kinds:
            errors.append("real-time result kind sequence differs: %r != %r" %
                          (before_kinds, after_kinds))
    else:
        errors.append("unknown lane %r" % lane)
    return errors


def _read(path):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        raise ValueError("missing evidence file: " + str(path))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("unreadable evidence file %s: %s" % (path, error)) from error


def _session_paths(side):
    recipes={path.parent.relative_to(side) for path in side.rglob("recipe.json")}
    results={path.parent.relative_to(side) for path in side.rglob("results.json")}
    return recipes,results


def check_session_roots(before, after, lane):
    errors = []
    before_recipes,before_results=_session_paths(before)
    after_recipes,after_results=_session_paths(after)
    if before_recipes != before_results:
        errors.append("before evidence has unmatched recipe/results sessions")
    if after_recipes != after_results:
        errors.append("after evidence has unmatched recipe/results sessions")
    if before_recipes != after_recipes:
        errors.append("before/after evidence session sets differ")
    sessions=before_recipes & before_results & after_recipes & after_results
    if Path('.') not in sessions:
        errors.append("missing root recipe/results evidence")
    for session in sorted(sessions,key=str):
        label="root" if session==Path('.') else session.as_posix()
        try:
            before_recipe=_read(before / session / "recipe.json")
            after_recipe=_read(after / session / "recipe.json")
            before_values=_read(before / session / "results.json")
            after_values=_read(after / session / "results.json")
        except ValueError as error:
            errors.append(str(error));continue
        if normalize_recipe(before_recipe) != normalize_recipe(after_recipe):
            errors.append("%s normalized recipes differ" % label)
        errors.extend("%s: %s" % (label,error)
                      for error in compare_results(before_values,after_values,lane))
    return errors


def check_lane(root, lane):
    return check_session_roots(root / "before", root / "after", lane)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--lane", choices=("controlled", "real-time"))
    args = parser.parse_args(argv)
    lane = args.lane or args.path.name
    errors = check_lane(args.path, lane)
    if errors:
        parser.exit(1, "\n".join(errors) + "\n")


if __name__ == "__main__":
    main()
