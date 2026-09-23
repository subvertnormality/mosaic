#!/usr/bin/env python3
"""Run explicit before/after UI gates for one profile at two immutable commits.

This is a partial, manual campaign. The exhaustive behaviour workflow is separate.
Every failed run and gate still leaves its original manifest and recipe/result files.
"""

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ui_migration_gate import check_session_roots

SHA = re.compile(r"[0-9a-f]{40}\Z")
CASE = re.compile(r"M-[A-Z0-9][A-Z0-9.-]*\Z")
LANES = (("real-time", "real-time"),
         ("controlled-experimental", "controlled"))
UI_SOURCE_ALLOWLIST = {
    "tests/behaviour/cases.py",  # selected case routing or inline case body
    "tests/behaviour/ui.py",
    "tests/behaviour/ui_map.py",
    "tests/behaviour/frame_oracle.py",
    "tests/behaviour/ui_migration_allowlist.json",
    "tests/behaviour/contract_cases.json",
    "tests/behaviour/ui_verb_sources.json",
    "tests/behaviour/ci/test_targeted_ui_migration.py",
}
PINNED_GATE_PATHS = (
    "tests/behaviour/ui_migration_gate.py",
    "tests/behaviour/ci/targeted-ui-migration.py",
    "tests/behaviour/ci/compare_ptn_graph.lua",
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cases_from_input(raw):
    cases = [item.strip() for item in raw.split(",")]
    require(cases and all(CASE.fullmatch(item) for item in cases),
            "case_ids must be comma-separated, nonempty case IDs")
    require(len(cases) == len(set(cases)), "duplicate case ID")
    return cases


def source_identity(root, expected):
    require(SHA.fullmatch(expected), "source ref must be a lowercase, full commit SHA")
    actual = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    require(actual == expected, "checkout is not requested commit: " + str(root))
    require(subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=root, text=True).strip() == "",
        "source checkout is dirty: " + str(root))
    return actual


def registry_profile(root):
    tree = ast.parse((root / "tests/behaviour/cases.py").read_text())
    entries = [node.value for node in tree.body if isinstance(node, ast.Assign)
               and any(isinstance(target, ast.Name) and target.id == "CASES"
                       for target in node.targets)]
    require(len(entries) == 1 and isinstance(entries[0], ast.Dict),
            "expected one literal CASES registry")
    names = [ast.literal_eval(key) for key in entries[0].keys]
    require(all(isinstance(name, str) for name in names) and len(names) == len(set(names)),
            "invalid or duplicate registry case IDs")
    suite = ast.parse((root / "tests/behaviour/suite.py").read_text())
    profiles = [node.value for node in suite.body if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "CASE_PROFILE"
                        for target in node.targets)]
    require(len(profiles) == 1 and isinstance(profiles[0], ast.Dict),
            "expected one literal CASE_PROFILE map")
    keys = [ast.literal_eval(key) for key in profiles[0].keys]
    require(len(keys) == len(set(keys)), "duplicate case profile IDs")
    profile_map = ast.literal_eval(profiles[0])
    require(set(profile_map) <= set(names), "profile map contains unknown case")
    return {name: profile_map.get(name, "base-midi") for name in names}


def registry_controlled_only(root, cases):
    """Read controlled-only declarations from the literal case registry."""
    tree = ast.parse((root / "tests/behaviour/cases.py").read_text())
    registries = [node.value for node in tree.body if isinstance(node, ast.Assign)
                  and any(isinstance(target, ast.Name) and target.id == "CASES"
                          for target in node.targets)]
    require(len(registries) == 1 and isinstance(registries[0], ast.Dict),
            "expected one literal CASES registry")
    entries = {ast.literal_eval(key): value
               for key, value in zip(registries[0].keys, registries[0].values)}
    require(len(entries) == len(registries[0].keys),
            "invalid or duplicate registry case IDs")
    selected = {}
    for case in cases:
        require(case in entries, "registry lacks case " + case)
        definition = entries[case]
        require(isinstance(definition, ast.Call)
                and isinstance(definition.func, ast.Name)
                and definition.func.id == "dict",
                "unrecognized case registration: " + case)
        declarations = [item.value for item in definition.keywords
                        if item.arg == "controlled_only"]
        require(len(declarations) <= 1,
                "duplicate controlled_only declaration: " + case)
        if declarations:
            try:
                reason = ast.literal_eval(declarations[0])
            except (ValueError, TypeError) as error:
                raise ValueError("nonliteral controlled_only declaration: " + case) from error
            require(isinstance(reason, str) and reason.strip(),
                    "invalid controlled_only declaration: " + case)
            selected[case] = True
        else:
            selected[case] = False
    return selected


def selected_case_lanes(before, after, cases):
    """Select lanes from pinned registry metadata, requiring source parity."""
    before_applicability = registry_controlled_only(before, cases)
    after_applicability = registry_controlled_only(after, cases)
    require(before_applicability == after_applicability,
            "lane applicability differs between before and after registries")
    return {case: tuple(lane for lane, _ in LANES
                         if lane == "controlled-experimental" or not controlled_only)
            for case, controlled_only in before_applicability.items()}


def selected_case_modules(root, cases):
    """Only the modules owning selected registry callables may change."""
    tree = ast.parse((root / "tests/behaviour/cases.py").read_text())
    imports = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            for alias in node.names:
                name = alias.asname or alias.name
                require(name not in imports, "ambiguous imported case callable: " + name)
                imports[name] = node.module
    registries = [node.value for node in tree.body if isinstance(node, ast.Assign)
                  and any(isinstance(target, ast.Name) and target.id == "CASES"
                          for target in node.targets)]
    require(len(registries) == 1 and isinstance(registries[0], ast.Dict),
            "expected one literal CASES registry")
    entries = {ast.literal_eval(key): value
               for key, value in zip(registries[0].keys, registries[0].values)}
    result = set()
    for case in cases:
        definition = entries[case]
        require(isinstance(definition, ast.Call) and isinstance(definition.func, ast.Name)
                and definition.func.id == "dict", "unrecognized case registration: " + case)
        runs = [item.value for item in definition.keywords if item.arg == "run"]
        require(len(runs) == 1, "unrecognized run callable: " + case)
        run = runs[0]
        if isinstance(run, ast.Name):
            symbol = run.id
        elif isinstance(run, ast.Lambda) and isinstance(run.body, ast.Call) \
                and isinstance(run.body.func, ast.Name):
            symbol = run.body.func.id
        else:
            raise ValueError("unrecognized run callable: " + case)
        module = imports.get(symbol)
        if module is not None:
            path = "tests/behaviour/" + module.replace(".", "/") + ".py"
            require((root / path).is_file(), "missing selected case module: " + path)
            result.add(path)
            result.update(contract_reexport_owners(root, path, symbol))
    return result


def contract_reexport_owners(root, path, symbol):
    """Follow only pure re-exports of the selected callable into contract/."""
    owners = set()
    while True:
        tree = ast.parse((root / path).read_text())
        body = tree.body
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                and isinstance(body[0].value.value, str):
            body = body[1:]
        if any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
               and node.name == symbol for node in body):
            return owners
        if len(body) != 1 or not isinstance(body[0], ast.ImportFrom) \
                or body[0].level != 0 or not body[0].module:
            return set()
        node = body[0]
        parts = node.module.split(".")
        if len(parts) != 2 or parts[0] != "contract" \
                or not re.fullmatch(r"[a-z][a-z0-9_]*", parts[1]):
            return set()
        selected = [alias for alias in node.names
                    if (alias.asname or alias.name) == symbol and alias.name != "*"]
        if len(selected) != 1:
            return set()
        target = "tests/behaviour/contract/" + parts[1] + ".py"
        require(target not in owners and target != path,
                "selected contract re-export cycle: " + target)
        require((root / target).is_file(),
                "missing selected contract implementation: " + target)
        owners.add(target)
        path, symbol = target, selected[0].name


def tree_entries(root, *paths):
    """Git object identity includes executable modes, symlinks and gitlinks."""
    raw = subprocess.check_output(
        ["git", "ls-tree", "-r", "-z", "HEAD", "--", *paths], cwd=root)
    entries = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        metadata, separator, encoded_path = record.partition(b"\t")
        parts = metadata.split()
        require(separator and len(parts) == 3, "malformed git tree entry")
        path = encoded_path.decode("utf-8")
        require(path not in entries, "duplicate git tree entry: " + path)
        entries[path] = tuple(part.decode("ascii") for part in parts)
    return entries


def check_source_delta(before, after, cases):
    production_before = tree_entries(before, "mosaic.lua", "lib", ".gitmodules",
                                     "README.md", "cheat_sheet.html")
    production_after = tree_entries(after, "mosaic.lua", "lib", ".gitmodules",
                                    "README.md", "cheat_sheet.html")
    require("mosaic.lua" in production_before and "mosaic.lua" in production_after
            and any(path.startswith("lib/") for path in production_before)
            and any(path.startswith("lib/") for path in production_after),
            "missing production tree in source checkout")
    changed_production = sorted(path for path in production_before.keys() | production_after.keys()
                                if production_before.get(path) != production_after.get(path))
    require(not changed_production, "production/manual source changed between runs: "
            + ", ".join(changed_production))
    before_tests = tree_entries(before, "tests/behaviour")
    after_tests = tree_entries(after, "tests/behaviour")
    for path in PINNED_GATE_PATHS:
        require(path in before_tests and before_tests[path] == after_tests.get(path),
                "targeted gate/runner differs or is absent between source commits: " + path)
    selected_sources = selected_case_modules(before, cases) \
        | selected_case_modules(after, cases)
    allowed = UI_SOURCE_ALLOWLIST | selected_sources
    changed_tests = sorted(path for path in before_tests.keys() | after_tests.keys()
                           if before_tests.get(path) != after_tests.get(path))
    ui_tests = {"tests/behaviour/test_ui.py",
                "tests/behaviour/test_ui_layer.py"}
    if ui_tests & set(changed_tests):
        ui_sources = selected_sources | {
            "tests/behaviour/ui.py", "tests/behaviour/ui_map.py",
            "tests/behaviour/frame_oracle.py"}
        require(bool(set(changed_tests) & ui_sources),
                "UI unit tests changed without selected UI source")
        allowed.update(ui_tests)
    unexpected = sorted(set(changed_tests) - allowed)
    require(not unexpected, "unrelated behaviour harness/fixture source changed: "
            + ", ".join(unexpected))
    for side, entries in (("before", before_tests), ("after", after_tests)):
        unsafe = sorted(path for path in changed_tests if path in entries
                        and entries[path][0] not in ("100644", "100755"))
        require(not unsafe, "%s changed behaviour source is not a regular file: %s" %
                (side, ", ".join(unsafe)))
    return dict(production_tree_unchanged=True, changed_behaviour_paths=changed_tests,
                allowed_behaviour_paths=sorted(allowed))


def require_no_symlink_ancestors(path):
    for component in (path, *path.parents):
        require(not component.is_symlink(), "symlinked evidence path: " + str(component))


def verified_manifest(manifest_path, case, lane, revision, profile="base-midi"):
    require_no_symlink_ancestors(manifest_path)
    item = json.loads(manifest_path.read_text())
    require(isinstance(item, dict), "run manifest is not an object")
    for key, expected in (("case", case), ("clock_mode", lane),
                          ("mosaic_revision", revision), ("profile", profile)):
        require(item.get(key) == expected, "run manifest %s differs" % key)
    require(item.get("campaign_complete") is False and item.get("passed") is True
            and item.get("failure") is None, "before/after run did not pass")
    require(item.get("diagnostic_only") is (lane == "controlled-experimental"),
            "run diagnostic marker differs")
    artifacts = item.get("artifacts")
    require(isinstance(artifacts, list), "missing artifact digest inventory")
    seen = set()
    for record in artifacts:
        require(isinstance(record, dict), "invalid artifact record")
        name = record.get("path")
        require(isinstance(name, str) and name and "\\" not in name,
                "invalid artifact path")
        parts = Path(name).parts
        require(not Path(name).is_absolute() and all(part not in (".", "..") for part in parts)
                and not {"code", "data"} & set(parts), "unsafe artifact path")
        require(name not in seen, "duplicate artifact path")
        seen.add(name)
        path = manifest_path.parent / name
        require_no_symlink_ancestors(path)
        require(path.is_file() and record.get("sha256") == sha256(path)
                and record.get("size") == path.stat().st_size,
                "artifact missing or digest differs: " + name)
    present = {path.relative_to(manifest_path.parent).as_posix()
               for path in manifest_path.parent.rglob("*") if path.is_file()
               and path != manifest_path
               and not {"code", "data"} & set(path.relative_to(manifest_path.parent).parts)}
    require(seen == present, "artifact inventory does not cover all run evidence")
    recipes = {name for name in seen if name.endswith("recipe.json")}
    results = {name for name in seen if name.endswith("results.json")}
    require("recipe.json" in recipes and "results.json" in results,
            "missing root recipe/results evidence")
    require({name[:-len("recipe.json")] for name in recipes}
            == {name[:-len("results.json")] for name in results},
            "unmatched nested recipe/results evidence")
    return item


def single_manifest(output):
    paths = list(output.glob("*/manifest.json"))
    require(len(paths) == 1, "expected exactly one fresh run manifest in " + str(output))
    return paths[0]


def run_one(source, case, lane, output, install, profile="base-midi",
            mod_code_root=None, mod_patches=False):
    output.mkdir(parents=True, exist_ok=False)
    command = [sys.executable, str(source / "tests/behaviour/run.py"),
               "--case", case, "--artifacts", str(output), "--clock-mode", lane]
    if lane == "controlled-experimental":
        command.extend(("--experimental-install", str(install)))
    if profile != "base-midi":
        command.extend(("--profile", profile, "--mod-code-root", str(mod_code_root)))
        if mod_patches:
            command.append("--mod-patches")
    # This is inert converter metadata. Keep the real-time emulator launch options
    # identical while making the pinned norns source available to migration cases.
    environment = os.environ.copy()
    environment["MOSAIC_BEHAVIOUR_INSTALLATION"] = str(install)
    with (output / "process.log").open("w") as log:
        status = subprocess.run(command, cwd=source, stdout=log,
                                stderr=subprocess.STDOUT, check=False,
                                env=environment).returncode
    return status, single_manifest(output)


def execute(args):
    cases = cases_from_input(args.case_ids)
    require(args.before.resolve() != args.after.resolve(), "source checkouts must be distinct")
    before_sha = source_identity(args.before, args.before_sha)
    after_sha = source_identity(args.after, args.after_sha)
    require(before_sha != after_sha, "before and after commits must differ")
    require(args.profile in ("base-midi", "midi-modulation"),
            "unsupported targeted profile: " + args.profile)
    if args.profile == "midi-modulation":
        require(args.mod_code_root is not None and args.mod_code_root.is_dir(),
                "midi-modulation requires its pinned output fixture root")
        require(args.mod_patches, "midi-modulation requires the declared fixture patches")
    else:
        require(args.mod_code_root is None and not args.mod_patches,
                "modulation fixtures are only valid for midi-modulation")
    for label, source in (("before", args.before), ("after", args.after)):
        profiles = registry_profile(source)
        for case in cases:
            require(case in profiles, "%s source lacks case %s" % (label, case))
            require(profiles[case] == args.profile,
                    "%s is not %s in %s source" % (case, args.profile, label))
    case_lanes = selected_case_lanes(args.before, args.after, cases)
    report_lanes = [lane for lane, _ in LANES
                    if any(lane in selected for selected in case_lanes.values())]
    source_delta = check_source_delta(args.before, args.after, cases)
    require(args.install.is_file(), "missing qualified controlled-time installation")
    emulator_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=args.emulator, text=True).strip()
    report = dict(schema_version=1, complete_regression_run=False, profile=args.profile,
                  before_sha=before_sha, after_sha=after_sha,
                  emulator_sha=emulator_sha, selected_cases=cases,
                  source_delta=source_delta,
                  lanes=report_lanes, cases=[], passed=False)
    try:
        for case in cases:
            row = dict(case=case, lanes=[])
            report["cases"].append(row)
            for lane in case_lanes[case]:
                gate_lane = dict(LANES)[lane]
                lane_row = dict(lane=lane, runs={}, gate_errors=[])
                row["lanes"].append(lane_row)
                roots = {}
                for side, source, revision in (("before", args.before, before_sha),
                                               ("after", args.after, after_sha)):
                    output = args.output / case / lane / side
                    try:
                        status, manifest = run_one(source, case, lane, output, args.install,
                                                   args.profile, args.mod_code_root,
                                                   args.mod_patches)
                        lane_row["runs"][side] = dict(returncode=status,
                            manifest=str(manifest.relative_to(args.output)),
                            manifest_sha256=sha256(manifest))
                        require(status == 0, "%s run exited %d" % (side, status))
                        verified_manifest(manifest, case, lane, revision, args.profile)
                        roots[side] = manifest.parent
                    except (ValueError, OSError, subprocess.SubprocessError) as error:
                        lane_row["gate_errors"].append("%s: %s" % (side, error))
                if len(roots) == 2:
                    lane_row["gate_errors"].extend(check_session_roots(
                        roots["before"], roots["after"], gate_lane, case=case))
    finally:
        report["passed"] = (len(report["cases"]) == len(cases) and all(
            len(row["lanes"]) == len(case_lanes[row["case"]]) and all(
                not lane["gate_errors"] and len(lane["runs"]) == 2
                for lane in row["lanes"]) for row in report["cases"]))
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "targeted-ui-migration.json").write_text(
            json.dumps(report, indent=2) + "\n")
        print(json.dumps(dict(passed=report["passed"], report=str(
            args.output / "targeted-ui-migration.json"))), flush=True)
    return 0 if report["passed"] else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--before-sha", required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--after-sha", required=True)
    parser.add_argument("--case-ids", required=True)
    parser.add_argument("--profile", choices=("base-midi", "midi-modulation"),
                        default="base-midi")
    parser.add_argument("--mod-code-root", type=Path)
    parser.add_argument("--mod-patches", action="store_true")
    parser.add_argument("--emulator", type=Path, required=True)
    parser.add_argument("--install", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        return execute(args)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
