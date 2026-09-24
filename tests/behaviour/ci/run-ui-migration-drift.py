#!/usr/bin/env python3
"""Run the UI migration page-order drift drill in an isolated Git worktree.

The run intentionally creates failed controlled cases. It preserves their run
directories, the independent repeat.py output, the scratch commit, and the
validator report under one new output directory. It never pushes a branch.
"""
import argparse
import ast
import json
import os
from pathlib import Path
import re
import subprocess
import sys


MAP = "tests/behaviour/ui_map.py"
PAGE_KEYS = ("masks", "merge_shape")


def git(repo, *args, check=True):
    result = subprocess.run(["git", *args], cwd=repo, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and result.returncode:
        raise ValueError("git %s failed: %s" % (" ".join(args), result.stderr.strip()))
    return result


def _page_list_node(source):
    tree = ast.parse(source)
    matches = [node.value for node in tree.body if isinstance(node, ast.Assign)
               and any(isinstance(target, ast.Name) and target.id == "CHANNEL_PAGES"
                       for target in node.targets)]
    if (len(matches) != 1 or not isinstance(matches[0], ast.Call)
            or not isinstance(matches[0].func, ast.Name)
            or matches[0].func.id != "OrderedDict" or len(matches[0].args) != 1
            or not isinstance(matches[0].args[0], ast.List)):
        raise ValueError("expected one CHANNEL_PAGES OrderedDict list")
    pairs = matches[0].args[0].elts
    keys = []
    for pair in pairs:
        if not isinstance(pair, ast.Tuple) or len(pair.elts) != 2:
            raise ValueError("invalid CHANNEL_PAGES entry")
        try:
            keys.append(ast.literal_eval(pair.elts[0]))
        except (ValueError, TypeError) as error:
            raise ValueError("channel page keys must be literals") from error
    if any(not isinstance(key, str) for key in keys) or len(set(keys)) != len(keys):
        raise ValueError("channel page keys must be unique strings")
    return tree, pairs, keys


def channel_page_keys(source):
    return _page_list_node(source)[2]


def swap_channel_pages(source, pages):
    """Return source with exactly the requested CHANNEL_PAGES entries swapped."""
    if len(pages) != 2 or pages[0] == pages[1]:
        raise ValueError("select two distinct channel page keys")
    before, pairs, keys = _page_list_node(source)
    if any(page not in keys for page in pages):
        raise ValueError("requested page is absent from CHANNEL_PAGES")
    left, right = (keys.index(page) for page in pages)
    raw = source.encode("utf-8")
    offsets = [0]
    for line in raw.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))

    def bounds(node):
        return (offsets[node.lineno - 1] + node.col_offset,
                offsets[node.end_lineno - 1] + node.end_col_offset)

    left_start, left_end = bounds(pairs[left])
    right_start, right_end = bounds(pairs[right])
    replacements = sorted(((left_start, left_end, raw[right_start:right_end]),
                           (right_start, right_end, raw[left_start:left_end])))
    (first_start, first_end, first_text), (second_start, second_end, second_text) = replacements
    changed = (raw[:first_start] + first_text + raw[first_end:second_start]
               + second_text + raw[second_end:])
    result = changed.decode("utf-8")
    after, after_pairs, after_keys = _page_list_node(result)
    expected = ast.parse(source)
    expected_node = next(node.value for node in expected.body if isinstance(node, ast.Assign)
                         and any(isinstance(target, ast.Name) and target.id == "CHANNEL_PAGES"
                                 for target in node.targets))
    expected_node.args[0].elts[left], expected_node.args[0].elts[right] = (
        expected_node.args[0].elts[right], expected_node.args[0].elts[left])
    if ast.dump(after) != ast.dump(expected):
        raise ValueError("swap changed source beyond the two CHANNEL_PAGES entries")
    if after_keys[left] != pages[1] or after_keys[right] != pages[0]:
        raise ValueError("page swap did not produce the requested order")
    return result


def failed_run_manifest(completed, case):
    """Accept a normal run.py expected-failure summary and return its manifest."""
    if completed.returncode != 1:
        raise ValueError("run.py must exit 1 for the expected drift failure")
    rows = []
    for line in completed.stdout.splitlines():
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict) and "manifest" in value:
            rows.append(value)
    if len(rows) != 1:
        raise ValueError("run.py output must contain exactly one manifest summary")
    row = rows[0]
    if row.get("case") != case or row.get("passed") is not False:
        raise ValueError("run.py summary does not identify the expected failed case")
    path = Path(row["manifest"]).resolve()
    if not path.is_file():
        raise ValueError("run.py did not preserve its manifest: " + str(path))
    return path


def successful_run_manifest(completed, case):
    """Require a normal successful control run from the unchanged candidate."""
    if completed.returncode != 0:
        raise ValueError("unmodified control run did not pass: " + case)
    rows = []
    for line in completed.stdout.splitlines():
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict) and "manifest" in value:
            rows.append(value)
    if len(rows) != 1 or rows[0].get("case") != case or rows[0].get("passed") is not True:
        raise ValueError("control summary did not identify one passing case: " + case)
    path = Path(rows[0]["manifest"]).resolve()
    if not path.is_file():
        raise ValueError("control run did not preserve its manifest: " + str(path))
    return path


def write_json_once(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def make_scratch_commit(repo, baseline, pages, branch, scratch):
    git(repo, "worktree", "add", "-b", branch, str(scratch), baseline)
    if (scratch / ".gitmodules").is_file():
        git(scratch, "submodule", "update", "--init", "--recursive")
    map_path = scratch / MAP
    original = map_path.read_text(encoding="utf-8")
    map_path.write_text(swap_channel_pages(original, pages), encoding="utf-8", newline="")
    git(scratch, "add", "--", MAP)
    git(scratch, "-c", "user.name=github-actions[bot]",
        "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com",
        "commit", "-m", "test: swap channel pages for UI drift drill")
    return git(scratch, "rev-parse", "HEAD").stdout.strip()


def preserve_scratch_commit(repo, output, baseline, scratch_sha, branch):
    bundle = output / "scratch-commit.bundle"
    git(repo, "bundle", "create", str(bundle), "refs/heads/" + branch,
        "^" + baseline)
    git(repo, "bundle", "verify", str(bundle))
    patch = git(repo, "format-patch", "--stdout", "-1", scratch_sha)
    (output / "scratch-commit.patch").write_text(patch.stdout, encoding="utf-8", newline="")
    (output / "scratch-commit.txt").write_text(
        git(repo, "show", "--format=fuller", "--no-patch", scratch_sha).stdout,
        encoding="utf-8", newline="")
    return bundle


def _load_drill_module(repo):
    behaviour = repo / "tests" / "behaviour"
    sys.path.insert(0, str(behaviour))
    import ui_migration_drill
    return ui_migration_drill


def _run_case(scratch, output, case, profile, install, mod_root, timeout):
    root = output / "standalone" / case
    root.mkdir(parents=True, exist_ok=False)
    command = [sys.executable, str(scratch / "tests/behaviour/run.py"),
               "--case", case, "--artifacts", str(root),
               "--clock-mode", "controlled-experimental",
               "--experimental-install", install, "--profile", profile]
    if profile == "midi-modulation":
        if not mod_root or not Path(mod_root).is_dir():
            raise ValueError("midi-modulation drift cases require --mod-code-root")
        command.extend(["--mod-code-root", mod_root, "--mod-patches"])
    completed = subprocess.run(command, cwd=scratch, text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               timeout=timeout)
    manifest = failed_run_manifest(completed, case)
    if manifest.name != "manifest.json" or manifest.parent.parent != root.resolve():
        raise ValueError("run.py manifest is outside standalone artifact root")
    log = dict(command=command, returncode=completed.returncode,
               stdout=completed.stdout, stderr=completed.stderr,
               manifest=str(manifest))
    write_json_once(output / "standalone-logs" / (case + ".json"), log)
    return manifest


def _run_control(candidate, output, case, profile, install, mod_root, timeout):
    root = output / "control" / case
    root.mkdir(parents=True, exist_ok=False)
    command = [sys.executable, str(candidate / "tests/behaviour/run.py"),
               "--case", case, "--artifacts", str(root),
               "--clock-mode", "controlled-experimental",
               "--experimental-install", install, "--profile", profile]
    if profile == "midi-modulation":
        if not mod_root or not Path(mod_root).is_dir():
            raise ValueError("midi-modulation controls require --mod-code-root")
        command.extend(["--mod-code-root", mod_root, "--mod-patches"])
    completed = subprocess.run(command, cwd=candidate, text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               timeout=timeout)
    write_json_once(output / "control-logs" / (case + ".json"), dict(
        command=command, returncode=completed.returncode,
        stdout=completed.stdout, stderr=completed.stderr))
    manifest = successful_run_manifest(completed, case)
    if manifest.name != "manifest.json" or manifest.parent.parent != root.resolve():
        raise ValueError("control manifest is outside uploaded artifact root")
    return manifest


def _run_repeat(scratch, output, case, profile, install, mod_root, timeout):
    repeats_root = scratch.parent / "mosaic-behaviour-runs"
    repeats_root.mkdir(parents=True, exist_ok=False)
    before = set()
    command = [sys.executable, str(scratch / "tests/behaviour/repeat.py"),
               "--case", case, "--experimental-install", install]
    if profile == "midi-modulation":
        if not mod_root or not Path(mod_root).is_dir():
            raise ValueError("midi-modulation repeat requires --mod-code-root")
        command.extend(["--profile", profile, "--mod-code-root", mod_root, "--mod-patches"])
    completed = subprocess.run(command, cwd=scratch, text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               timeout=timeout)
    after = set(repeats_root.glob("repeat-*")) if repeats_root.exists() else set()
    created = sorted(after - before)
    if completed.returncode != 1 or len(created) != 1:
        raise ValueError("repeat.py must preserve exactly one expected failing first process")
    manifest = created[0] / "manifest.json"
    if not manifest.is_file():
        raise ValueError("repeat.py did not preserve its manifest")
    write_json_once(output / "repeat-wrapper.json", dict(
        command=command, returncode=completed.returncode,
        stdout=completed.stdout, stderr=completed.stderr,
        manifest=str(manifest.resolve())))
    return manifest.resolve()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path,
                        help="clean candidate checkout containing the final evidence")
    parser.add_argument("--baseline", required=True,
                        help="full SHA of the final migration/evidence commit")
    parser.add_argument("--pages", nargs=2, default=PAGE_KEYS, metavar=("FIRST", "SECOND"))
    parser.add_argument("--experimental-install", required=True)
    parser.add_argument("--mod-code-root", help="pinned output mods for modulation cases")
    parser.add_argument("--repeat-case", help="eligible member for the separate repeat.py run")
    parser.add_argument("--output", required=True, type=Path,
                        help="new artifact directory; it must not already exist")
    parser.add_argument("--run-timeout", type=int, default=1800)
    parser.add_argument("--branch-suffix", default=os.environ.get("GITHUB_RUN_ID", "local"))
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[0-9a-f]{40}", args.baseline):
        parser.error("--baseline must be a full lowercase 40-character SHA")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", args.branch_suffix):
        parser.error("invalid branch suffix")
    repo = args.repo.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    execution = output / "execution"
    execution.mkdir()
    if git(repo, "rev-parse", "HEAD").stdout.strip() != args.baseline:
        parser.error("candidate checkout HEAD does not equal --baseline")

    drill = _load_drill_module(repo)
    baseline, cases, profiles = drill.committed_plan(repo, args.baseline, args.pages)
    repeat_case = drill.select_repeat(cases, profiles, args.repeat_case)
    selected = sorted(cases)
    if any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", case) for case in selected):
        raise ValueError("unsafe case ID in committed drill selection")
    selected_profiles = {case: profiles.get(case, "base-midi") for case in selected}
    if any(profile not in ("base-midi", "midi-modulation")
           for profile in selected_profiles.values()):
        raise ValueError("controlled drift selection includes an unsupported profile")
    repeat_profile = selected_profiles[repeat_case]
    selection = dict(baseline_revision=baseline, swapped_pages=list(args.pages),
                     cases=cases, selected_cases=selected,
                     profiles=selected_profiles, repeat_case=repeat_case,
                     repeat_profile=repeat_profile)
    write_json_once(output / "drill-selection.json", selection)

    control_manifests = []
    for case in selected:
        control_manifests.append(_run_control(
            repo, output, case, selected_profiles[case], args.experimental_install,
            args.mod_code_root, args.run_timeout))

    branch = "codex/ui-drift-" + args.branch_suffix
    scratch = execution / "scratch-source"
    scratch_sha = make_scratch_commit(repo, baseline, args.pages, branch, scratch)
    preserve_scratch_commit(repo, output, baseline, scratch_sha, branch)

    run_manifests = []
    for case in selected:
        run_manifests.append(_run_case(
            scratch, output, case, selected_profiles[case], args.experimental_install,
            args.mod_code_root, args.run_timeout))
    repeat_manifest = _run_repeat(
        scratch, output, repeat_case, repeat_profile, args.experimental_install,
        args.mod_code_root, args.run_timeout)

    report = output / "docs" / "testing" / "ui-migration-drill.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    validator_args = ["--repo", str(repo), "--baseline", baseline,
                      "--scratch", scratch_sha, "--pages", *args.pages,
                      "--repeat", str(repeat_manifest), "--output", str(report)]
    for path in control_manifests:
        validator_args.extend(["--control", str(path)])
    for path in run_manifests:
        validator_args.extend(["--run", str(path)])
    drill.main(validator_args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
