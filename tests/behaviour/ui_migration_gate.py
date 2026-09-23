"""Fail-closed recipe and result comparison for one migrated case lane."""

import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


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
        if not isinstance(values, list):
            errors.append("%s results are not an array" % side)
            continue
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


PERSISTED_RESULT_KINDS = {
    "M-PATCH-008": "patch-autosave",
    "M-PATCH-009": "patch-autosave",
    "M-PATCH-051": "pre-policy-project-fixture",
    "M-PATCH-059": "pre-policy-project-fixture",
    "M-REC-PARAM-027": "recording-autosave-files",
}


def _normalise_verified_ptn_result_hash(values, result_kind, raw_sha, side):
    """Copy results and replace only the one verified .ptn SHA field."""
    copied = copy.deepcopy(values)
    matches = [entry for entry in copied
               if isinstance(entry, dict) and entry.get("kind") == result_kind]
    if len(matches) != 1:
        return None, ["%s results require exactly one %s entry (found %d)" %
                      (side, result_kind, len(matches))]
    entry = matches[0]
    if result_kind == "patch-autosave":
        files = entry.get("files")
        if not isinstance(files, list):
            return None, ["%s patch-autosave result has no files list" % side]
        ptn = [record for record in files
               if isinstance(record, dict) and record.get("name") == "autosave.ptn"]
        if len(ptn) != 1:
            return None, ["%s patch-autosave result requires exactly one autosave.ptn entry "
                          "(found %d)" % (side, len(ptn))]
        ptn_record = ptn[0]
        if ptn_record.get("sha256") != raw_sha:
            return None, ["%s patch-autosave autosave.ptn SHA differs from artifact" % side]
        ptn_record["sha256"] = "<verified-decoded-project-graph>"
    elif result_kind == "pre-policy-project-fixture":
        if entry.get("sha256") != raw_sha:
            return None, ["%s pre-policy fixture SHA differs from artifact" % side]
        entry["sha256"] = "<verified-decoded-project-graph>"
    elif result_kind == "recording-autosave-files":
        files = entry.get("files")
        if not isinstance(files, dict) or files.get("autosave.ptn") != raw_sha:
            return None, ["%s recording autosave .ptn SHA differs from artifact" % side]
        files["autosave.ptn"] = "<verified-decoded-project-graph>"
    else:
        return None, ["unsupported persisted project result kind: " + result_kind]
    return copied, []


def compare_results_with_verified_project(before, after, lane, result_kind,
                                           before_sha, after_sha):
    """Allow just the known .ptn hash after its decoded graph pair passes."""
    if not isinstance(before, list) or not isinstance(after, list):
        return compare_results(before, after, lane)
    errors = []
    before_normal, before_errors = _normalise_verified_ptn_result_hash(
        before, result_kind, before_sha, "before")
    after_normal, after_errors = _normalise_verified_ptn_result_hash(
        after, result_kind, after_sha, "after")
    errors.extend(before_errors)
    errors.extend(after_errors)
    if errors:
        return errors
    return compare_results(before_normal, after_normal, lane)


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


PERSISTED_PROJECTS = {
    "M-PATCH-008": ("generated-project/autosave.ptn",),
    "M-PATCH-009": ("generated-project/autosave.ptn",),
    "M-PATCH-051": ("pre-policy-seed/autosave.ptn",),
    "M-PATCH-059": ("pre-policy-seed/autosave.ptn",),
    "M-REC-PARAM-027": (
        "generated-project/autosave.ptn",
        "recording-reload-1/generated-project/autosave.ptn",
    ),
}
PROJECT_GRAPH_COMPARATOR = Path(__file__).with_name("ci") / "compare_ptn_graph.lua"


def _compare_persisted_projects(before, after, relative_paths):
    errors = []
    raw_hashes = {"before": {}, "after": {}}
    lua = shutil.which("lua5.3") or shutil.which("lua")
    if not lua:
        return (["Lua 5.3 runtime unavailable for persisted project graph comparison"],
                raw_hashes)
    for relative in relative_paths:
        before_project, after_project = before / relative, after / relative
        if not before_project.is_file():
            errors.append("before missing persisted project artifact: " + relative)
            continue
        if not after_project.is_file():
            errors.append("after missing persisted project artifact: " + relative)
            continue
        before_sha = hashlib.sha256(before_project.read_bytes()).hexdigest()
        after_sha = hashlib.sha256(after_project.read_bytes()).hexdigest()
        raw_hashes["before"][relative] = before_sha
        raw_hashes["after"][relative] = after_sha
        try:
            result = subprocess.run(
                [lua, str(PROJECT_GRAPH_COMPARATOR), str(before_project), str(after_project)],
                check=False, capture_output=True, text=True,
            )
        except OSError as error:
            errors.append("could not compare persisted project %s: %s" % (relative, error))
            continue
        if result.returncode != 0 or result.stdout.strip() != "equal":
            detail = (result.stdout.strip() or result.stderr.strip()
                      or "comparison exited %d" % result.returncode)
            errors.append("persisted project graphs differ for %s (raw sha256 %s / %s): %s" %
                          (relative, before_sha, after_sha, detail))
    return errors, raw_hashes


def check_session_roots(before, after, lane, case=None):
    errors = []
    persisted_kind = (PERSISTED_RESULT_KINDS.get(case)
                      if lane == "controlled" else None)
    persisted_result_counts = {"before": 0, "after": 0}
    project_errors = []
    project_hashes = {"before": {}, "after": {}}
    if lane == "controlled" and case in PERSISTED_PROJECTS:
        project_errors, project_hashes = _compare_persisted_projects(
            before, after, PERSISTED_PROJECTS[case])
        errors.extend(project_errors)
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
        if persisted_kind:
            persisted_result_counts["before"] += sum(
                isinstance(entry, dict) and entry.get("kind") == persisted_kind
                for entry in before_values) if isinstance(before_values, list) else 0
            persisted_result_counts["after"] += sum(
                isinstance(entry, dict) and entry.get("kind") == persisted_kind
                for entry in after_values) if isinstance(after_values, list) else 0
        if normalize_recipe(before_recipe) != normalize_recipe(after_recipe):
            errors.append("%s normalized recipes differ" % label)
        project_path = None
        if persisted_kind:
            candidate_path = ((session / "generated-project/autosave.ptn").as_posix()
                              if session != Path(".") else "generated-project/autosave.ptn")
            if candidate_path in PERSISTED_PROJECTS[case]:
                project_path = candidate_path
            elif session == Path(".") and len(PERSISTED_PROJECTS[case]) == 1:
                project_path = PERSISTED_PROJECTS[case][0]
        if project_path and not project_errors:
            result_errors = compare_results_with_verified_project(
                before_values, after_values, lane, persisted_kind,
                project_hashes["before"][project_path],
                project_hashes["after"][project_path])
        else:
            result_errors = compare_results(before_values, after_values, lane)
        errors.extend("%s: %s" % (label, error) for error in result_errors)
    if persisted_kind:
        for side, count in persisted_result_counts.items():
            expected = len(PERSISTED_PROJECTS[case])
            if count != expected:
                errors.append("%s evidence requires exactly %d %s results across sessions "
                              "(found %d)" % (side, expected, persisted_kind, count))
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
