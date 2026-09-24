#!/usr/bin/env python3
"""Run explicit before/after UI gates for one profile at two immutable commits.

This is a partial, manual campaign. The exhaustive behaviour workflow is separate.
Every failed run and gate still leaves its original manifest and recipe/result files.
"""

import argparse
import ast
import hashlib
import importlib.util
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
    "tests/behaviour/contract_cases.json",
    "tests/behaviour/ui_verb_sources.json",
    "tests/behaviour/ci/test_targeted_ui_migration.py",
}
QUALIFIED_RUNTIME = {"real-time": "qualified", "controlled-experimental": "qualified"}
PINNED_GATE_PATHS = (
    "tests/behaviour/ui_migration_gate.py",
    "tests/behaviour/ci/targeted-ui-migration.py",
    "tests/behaviour/ci/compare_ptn_graph.lua",
)
HISTORICAL_ALLOWLIST_PATH = "tests/behaviour/ui_migration_allowlist.json"
HARMONY_ORACLE_PATH = "tests/behaviour/test_harmony_persistence_oracle.py"
HARMONY_OWNER_CASES = frozenset({
    "M-HARMONY-REVOICE-001", "M-HARMONY-PERSIST-001",
    "M-HARMONY-ENSEMBLE-001", "M-HARMONY-FAILURE-001",
    "M-HARMONY-HELD-001",
})
HARMONY_ORACLE_BLOBS = (
    "99a67dc31837652e5964b6509370260d43520a1b",
    "d151c2958aad3be193d01dd343c7e10f91cd0e2a",
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def behaviour_source_hashes(root):
    """Match run.py's source inventory for the checkout before an emulator run."""
    return {path.relative_to(root).as_posix(): sha256(path)
            for path in sorted((root / "tests/behaviour").rglob("*.py"))}


def manifest_behaviour_source_hashes(root):
    """Mirror only statically recognized source-hash inventories used by run.py."""
    run_path = root / "tests/behaviour/run.py"
    require(run_path.is_file(), "source checkout lacks tests/behaviour/run.py")
    tree = ast.parse(run_path.read_text())
    assignments = [node.value for node in ast.walk(tree)
                   if isinstance(node, ast.keyword)
                   and node.arg == "behaviour_source_sha256"]
    require(len(assignments) == 1,
            "source run.py has no unique behaviour source hash inventory")
    inventory = assignments[0]

    def is_name(node, name):
        return isinstance(node, ast.Name) and node.id == name

    def valid_inventory_expression(node, method, path_name, root_name, path_constructor):
        if not isinstance(node, ast.DictComp) or len(node.generators) != 1:
            return False
        generator = node.generators[0]
        if not is_name(generator.target, path_name):
            return False
        key = node.key
        if not (isinstance(key, ast.Call) and isinstance(key.func, ast.Attribute)
                and key.func.attr == "as_posix" and not key.args
                and isinstance(key.func.value, ast.Call)
                and isinstance(key.func.value.func, ast.Attribute)
                and key.func.value.func.attr == "relative_to"
                and is_name(key.func.value.func.value, path_name)
                and len(key.func.value.args) == 1
                and is_name(key.func.value.args[0], root_name)):
            return False
        value = node.value
        if not (isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
                and value.func.id == "digest" and len(value.args) == 1
                and is_name(value.args[0], path_name)):
            return False
        iterator = generator.iter
        if not (isinstance(iterator, ast.Call) and isinstance(iterator.func, ast.Name)
                and iterator.func.id == "sorted" and len(iterator.args) == 1):
            return False
        glob = iterator.args[0]
        if not (isinstance(glob, ast.Call) and isinstance(glob.func, ast.Attribute)
                and glob.func.attr == method and len(glob.args) == 1
                and isinstance(glob.args[0], ast.Constant)
                and glob.args[0].value == "*.py"):
            return False
        directory = glob.func.value
        if path_constructor:
            if not (isinstance(directory, ast.BinOp) and isinstance(directory.op, ast.Div)
                    and isinstance(directory.left, ast.Call)
                    and isinstance(directory.left.func, ast.Name)
                    and directory.left.func.id == "Path" and len(directory.left.args) == 1
                    and is_name(directory.left.args[0], root_name)
                    and isinstance(directory.right, ast.Constant)
                    and directory.right.value == "tests/behaviour"):
                return False
            return True
        return (isinstance(directory, ast.BinOp) and isinstance(directory.op, ast.Div)
                and is_name(directory.left, root_name)
                and isinstance(directory.right, ast.Constant)
                and directory.right.value == "tests/behaviour")

    if isinstance(inventory, ast.Call) and isinstance(inventory.func, ast.Name) \
            and inventory.func.id == "behaviour_source_hashes" and len(inventory.args) == 1:
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                     and node.name == "behaviour_source_hashes"]
        require(len(functions) == 1 and len(functions[0].body) == 1
                and isinstance(functions[0].body[0], ast.Return)
                and valid_inventory_expression(functions[0].body[0].value,
                                               "rglob", "path", "repo", True),
                "unrecognized recursive behaviour source hash schema")
        return behaviour_source_hashes(root), "recursive-python-v1"

    if isinstance(inventory, ast.DictComp):
        require(valid_inventory_expression(inventory, "glob", "p", "REPO", False),
                "unrecognized shallow behaviour source hash schema")
        paths = sorted((root / "tests/behaviour").glob("*.py"))
        return ({path.relative_to(root).as_posix(): sha256(path) for path in paths},
                "top-level-python-v1")
    raise ValueError("unrecognized behaviour source hash schema in source run.py")


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


LANE_RESTRICTIONS = {"controlled_only": ("controlled-experimental",),
                     "real_time_only": ("real-time",)}


def registry_lane_restrictions(root, cases):
    """Read controlled_only/real_time_only declarations from the literal registry."""
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
        restriction = None
        for keyword in LANE_RESTRICTIONS:
            declarations = [item.value for item in definition.keywords
                            if item.arg == keyword]
            require(len(declarations) <= 1,
                    "duplicate %s declaration: %s" % (keyword, case))
            if not declarations:
                continue
            try:
                reason = ast.literal_eval(declarations[0])
            except (ValueError, TypeError) as error:
                raise ValueError("nonliteral %s declaration: %s" % (keyword, case)) from error
            require(isinstance(reason, str) and reason.strip(),
                    "invalid %s declaration: %s" % (keyword, case))
            require(restriction is None,
                    "case declares both controlled_only and real_time_only: " + case)
            restriction = keyword
        selected[case] = restriction
    return selected


def selected_case_lanes(before, after, cases):
    """Select lanes from pinned registry metadata, requiring source parity."""
    before_applicability = registry_lane_restrictions(before, cases)
    after_applicability = registry_lane_restrictions(after, cases)
    require(before_applicability == after_applicability,
            "lane applicability differs between before and after registries")
    return {case: (LANE_RESTRICTIONS[restriction] if restriction
                   else tuple(lane for lane, _ in LANES))
            for case, restriction in before_applicability.items()}


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


def historical_allowlist_removal(before, after, before_tests, after_tests,
                                 selected_sources, changed_tests):
    """Admit only selected-owner removals from old migration policy metadata."""
    path = HISTORICAL_ALLOWLIST_PATH
    before_entry = before_tests.get(path)
    require(before_entry is not None and before_entry[0] == "100644"
            and before_entry[1] == "blob",
            "before historical allowlist is not a regular tracked JSON file")

    def read_allowlist(side, source, entry):
        raw = subprocess.check_output(["git", "cat-file", "blob", entry[2]], cwd=source)
        try:
            names = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(side + " historical allowlist is invalid JSON") from error
        require(isinstance(names, list) and all(isinstance(name, str)
                and re.fullmatch(r"[a-z][a-z0-9_]*\.py", name) for name in names)
                and len(names) == len(set(names)),
                side + " historical allowlist is not a unique module list")
        return entry[2], hashlib.sha256(raw).hexdigest(), set(names)

    before_blob, before_hash, before_names = read_allowlist("before", before, before_entry)
    after_entry = after_tests.get(path)
    if after_entry is None:
        # The plan removes the file in the same change that empties its final
        # entries. Model absence as an empty list, then apply the same selected-
        # and-changed-owner check to every entry that disappeared.
        after_blob, after_hash, after_names = None, None, set()
    else:
        require(after_entry[0] == "100644" and after_entry[1] == "blob",
                "after historical allowlist is not a regular tracked JSON file")
        after_blob, after_hash, after_names = read_allowlist("after", after, after_entry)
    removed = before_names - after_names
    require(removed and not after_names - before_names,
            "historical allowlist must only remove selected modules")
    selected_owners = {Path(name).name for name in selected_sources
                       if name.startswith("tests/behaviour/")
                       and not name.startswith("tests/behaviour/contract/")}
    require(all(name in selected_owners
                and "tests/behaviour/" + name in changed_tests for name in removed),
            "historical allowlist removed an unselected or unchanged owner")
    return dict(before_blob=before_blob, after_blob=after_blob,
                before_sha256=before_hash, after_sha256=after_hash,
                removed_modules=sorted(removed))


def check_source_delta(before, after, cases, *, historical=False):
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
    if not historical:
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
            "tests/behaviour/cases.py",  # inline selected case bodies live here
            "tests/behaviour/ui.py", "tests/behaviour/ui_map.py",
            "tests/behaviour/frame_oracle.py"}
        require(bool(set(changed_tests) & ui_sources),
                "UI unit tests changed without selected UI source")
        allowed.update(ui_tests)
    historical_allowlist = None
    if historical and HISTORICAL_ALLOWLIST_PATH in changed_tests:
        historical_allowlist = historical_allowlist_removal(
            before, after, before_tests, after_tests, selected_sources, changed_tests)
    historical_harmony_oracle = None
    if (historical and HARMONY_ORACLE_PATH in changed_tests
            and set(cases) == HARMONY_OWNER_CASES):
        old_owner = "tests/behaviour/harmony_merge_workflow.py"
        new_owner = "tests/behaviour/contract/harmony_workflows.py"
        if ({old_owner, new_owner} <= selected_sources
                and {old_owner, new_owner} <= set(changed_tests)
                and before_tests.get(HARMONY_ORACLE_PATH)
                    == ("100644", "blob", HARMONY_ORACLE_BLOBS[0])
                and after_tests.get(HARMONY_ORACLE_PATH)
                    == ("100644", "blob", HARMONY_ORACLE_BLOBS[1])):
            # This exact test edit retargets the persistence oracle to its
            # extracted owner and pins the five moved function ASTs. No other
            # harness edit is exempted from the historical source gate.
            allowed.add(HARMONY_ORACLE_PATH)
            historical_harmony_oracle = dict(
                path=HARMONY_ORACLE_PATH,
                before_blob=HARMONY_ORACLE_BLOBS[0],
                after_blob=HARMONY_ORACLE_BLOBS[1])
    permitted = allowed | (set(PINNED_GATE_PATHS) if historical else set())
    if historical_allowlist is not None:
        permitted.add(HISTORICAL_ALLOWLIST_PATH)
    unexpected = sorted(set(changed_tests) - permitted)
    require(not unexpected, "unrelated behaviour harness/fixture source changed: "
            + ", ".join(unexpected))
    for side, entries in (("before", before_tests), ("after", after_tests)):
        unsafe = sorted(path for path in changed_tests if path in entries
                        and entries[path][0] not in ("100644", "100755"))
        require(not unsafe, "%s changed behaviour source is not a regular file: %s" %
                (side, ", ".join(unsafe)))
    result = dict(production_tree_unchanged=True, changed_behaviour_paths=changed_tests,
                  allowed_behaviour_paths=sorted(allowed))
    if historical:
        result["historical_tooling_paths"] = sorted(PINNED_GATE_PATHS)
        if historical_allowlist is not None:
            result["historical_allowlist"] = historical_allowlist
        if historical_harmony_oracle is not None:
            result["historical_harmony_oracle"] = historical_harmony_oracle
    return result


def historical_tooling_identity(root, expected):
    """Verify the clean pinned checkout that supplies the current comparison gate."""
    actual = source_identity(root, expected)
    hashes = {}
    for relative in PINNED_GATE_PATHS:
        path = root / relative
        require(path.is_file(), "pinned tooling file is missing: " + relative)
        require(not path.is_symlink(), "pinned tooling file is a symlink: " + relative)
        entry = tree_entries(root, relative).get(relative)
        require(entry is not None and entry[0] in ("100644", "100755")
                and entry[1] == "blob",
                "pinned tooling file is not a regular tracked file: " + relative)
        worktree_blob = subprocess.check_output(
            ["git", "hash-object", "--", str(path)], cwd=root, text=True).strip()
        require(worktree_blob == entry[2],
                "pinned tooling file differs from committed blob: " + relative)
        hashes[relative] = sha256(path)
    return dict(sha=actual, sha256=hashes)


def load_historical_gate(root):
    """Load the current gate from the already verified tooling checkout."""
    gate_path = root / "tests/behaviour/ui_migration_gate.py"
    spec = importlib.util.spec_from_file_location(
        "mosaic_pinned_ui_migration_gate", gate_path)
    require(spec is not None and spec.loader is not None,
            "cannot load pinned UI migration gate")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(callable(getattr(module, "check_session_roots", None)),
            "pinned UI migration gate has no check_session_roots")
    return module.check_session_roots


def require_no_symlink_ancestors(path):
    for component in (path, *path.parents):
        require(not component.is_symlink(), "symlinked evidence path: " + str(component))


def verified_manifest(manifest_path, case, lane, revision, profile="base-midi", *,
                      expected_behaviour_source_sha256):
    require_no_symlink_ancestors(manifest_path)
    item = json.loads(manifest_path.read_text())
    require(isinstance(item, dict), "run manifest is not an object")
    for key, expected in (("case", case), ("clock_mode", lane),
                          ("mosaic_revision", revision), ("profile", profile)):
        require(item.get(key) == expected, "run manifest %s differs" % key)
    require(isinstance(expected_behaviour_source_sha256, dict)
            and isinstance(item.get("behaviour_source_sha256"), dict)
            and item["behaviour_source_sha256"] == expected_behaviour_source_sha256,
            "run manifest behaviour_source_sha256 differs from pre-run source")
    require(item.get("campaign_complete") is False and item.get("passed") is True
            and item.get("failure") is None, "before/after run did not pass")
    require(item.get("diagnostic_only") is True,
            "run was not launched on the qualified runtime")
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
               "--case", case, "--artifacts", str(output), "--clock-mode", lane,
               # Both lanes use the qualified runtime, as suite.py does for the
               # full campaign. The emulator's default runtime lacks its JACK,
               # screen-worker and SDL teardown fixes, so matron can SIGSEGV
               # after a passing real-time run; that remains a hard failure.
               "--experimental-install", str(install)]
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
    historical = bool(getattr(args, "historical_source", False))
    tooling_root = getattr(args, "tooling_root", None)
    tooling_sha = getattr(args, "tooling_sha", None)
    tooling_identity = None
    gate_check = check_session_roots
    if historical:
        require(tooling_root is not None and tooling_sha is not None,
                "historical-source mode requires --tooling-root and --tooling-sha")
        require(tooling_root.resolve() not in (args.before.resolve(), args.after.resolve()),
                "historical tooling checkout must be distinct from source checkouts")
        tooling_identity = historical_tooling_identity(tooling_root, tooling_sha)
        require(sha256(Path(__file__).resolve())
                == tooling_identity["sha256"][PINNED_GATE_PATHS[1]],
                "running targeted gate/runner differs from pinned tooling checkout")
        gate_check = load_historical_gate(tooling_root)
    else:
        require(tooling_root is None and tooling_sha is None,
                "--tooling-root and --tooling-sha require --historical-source")
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
    source_delta = check_source_delta(args.before, args.after, cases,
                                     historical=historical)
    require(args.install.is_file(), "missing qualified controlled-time installation")
    emulator_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=args.emulator, text=True).strip()
    report = dict(schema_version=1, complete_regression_run=False, profile=args.profile,
                  before_sha=before_sha, after_sha=after_sha,
                  emulator_sha=emulator_sha, runtime=QUALIFIED_RUNTIME,
                  selected_cases=cases,
                  source_delta=source_delta,
                  lanes=report_lanes, cases=[], passed=False)
    if historical:
        report["tooling"] = tooling_identity
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
                        source_identity(source, revision)
                        (expected_behaviour_source_sha256,
                         source_hash_schema) = manifest_behaviour_source_hashes(source)
                        status, manifest = run_one(source, case, lane, output, args.install,
                                                   args.profile, args.mod_code_root,
                                                   args.mod_patches)
                        lane_row["runs"][side] = dict(returncode=status,
                            manifest=str(manifest.relative_to(args.output)),
                            manifest_sha256=sha256(manifest),
                            behaviour_source_hash_schema=source_hash_schema)
                        require(status == 0, "%s run exited %d" % (side, status))
                        verified_manifest(
                            manifest, case, lane, revision, args.profile,
                            expected_behaviour_source_sha256=
                                expected_behaviour_source_sha256)
                        source_identity(source, revision)
                        roots[side] = manifest.parent
                    except (ValueError, OSError, subprocess.SubprocessError) as error:
                        lane_row["gate_errors"].append("%s: %s" % (side, error))
                if len(roots) == 2:
                    try:
                        if historical:
                            require(historical_tooling_identity(tooling_root, tooling_sha)
                                    == tooling_identity,
                                    "pinned tooling identity changed during migration run")
                        gate_errors = gate_check(
                            roots["before"], roots["after"], gate_lane, case=case)
                        if historical:
                            require(historical_tooling_identity(tooling_root, tooling_sha)
                                    == tooling_identity,
                                    "pinned tooling identity changed during migration gate")
                        lane_row["gate_errors"].extend(gate_errors)
                    except (ValueError, OSError, subprocess.SubprocessError) as error:
                        lane_row["gate_errors"].append("tooling: " + str(error))
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
    parser.add_argument("--historical-source", action="store_true",
                        help="allow old source commits to omit current gate tooling")
    parser.add_argument("--tooling-root", type=Path,
                        help="clean pinned current checkout used for historical gating")
    parser.add_argument("--tooling-sha",
                        help="full commit SHA of the pinned historical gate tooling")
    args = parser.parse_args(argv)
    try:
        return execute(args)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
