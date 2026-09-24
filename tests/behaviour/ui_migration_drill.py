"""Offline, fail-closed validation of the UI migration plan section 7 drift drill.

Reads committed selection evidence and real run.py/repeat.py artifacts. Never
starts an emulator or edits the map. --list is preparation, not drill evidence.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

from ui_baseline_import import verified_pair_files

BASELINES = "docs/testing/ui-migration-baselines/"
MAP = "tests/behaviour/ui_map.py"
REPO = Path(__file__).resolve().parents[2]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def decode(raw, label):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "duplicate JSON key in %s: %s" % (label, key))
            result[key] = value
        return result
    try:
        return json.loads(raw, object_pairs_hook=unique)
    except (ValueError, UnicodeError) as error:
        raise ValueError("invalid evidence %s: %s" % (label, error)) from error


def read(path):
    try:
        raw = Path(path).read_bytes()
    except OSError as error:
        raise ValueError("missing/unreadable evidence %s: %s" % (path, error)) from error
    return raw, decode(raw, str(path))


def derive_cases(files, registry, pages, channel_pages):
    """Use every committed controlled/after session, including nested restarts.

    files maps paths relative to BASELINES to bytes. Repeated confirmations are
    legitimate; repeated case declarations and JSON keys are not.
    """
    require(len(pages) == 2 and len(set(pages)) == 2 and set(pages) <= set(channel_pages),
            "select two distinct known channel-editor pages")
    require(len(registry) == len(set(registry)), "duplicate case IDs")
    sessions = {}
    for name, raw in sorted(files.items()):
        parts = PurePosixPath(name).parts
        if len(parts) < 4 or parts[1:3] != ("controlled", "after"):
            continue
        require(parts[0] in registry, "unknown case in after evidence: " + parts[0])
        require(not any(p in (".", "..") for p in parts), "unsafe evidence path")
        if parts[-1] not in ("recipe.json", "results.json"):
            continue
        session = PurePosixPath(*parts[3:-1]).as_posix()
        sessions.setdefault(parts[0], {}).setdefault(session, {})[parts[-1]] = (name, raw)
    require(sessions, "missing controlled/after evidence")
    selected = {}
    for case, case_sessions in sorted(sessions.items()):
        require("." in case_sessions, "missing root evidence: " + case)
        for session, pair in sorted(case_sessions.items()):
            require(set(pair) == {"recipe.json", "results.json"},
                    "missing recipe/results pair: %s/%s" % (case, session))
            for filename, (name, raw) in pair.items():
                entries = decode(raw, name)
                require(isinstance(entries, list), "evidence must be a list: " + name)
                key = "kind" if filename == "results.json" else "type"
                for index, entry in enumerate(entries):
                    require(isinstance(entry, dict) and isinstance(entry.get(key), str) and entry[key],
                            "entry missing %s: %s:%s" % (key, name, index))
                    if key != "kind" or entry["kind"] != "ui-confirm":
                        continue
                    page = entry.get("page")
                    require(isinstance(page, str) and page in channel_pages,
                            "unknown/missing ui-confirm page: %s:%s" % (name, index))
                    require(type(entry.get("channel")) is int and 1 <= entry["channel"] <= 16,
                            "missing/invalid ui-confirm channel: %s:%s" % (name, index))
                    if page in pages:
                        selected.setdefault(case, []).append(dict(
                            session=session, result_index=index, page=page,
                            channel=entry["channel"], path=BASELINES + name, sha256=sha(raw)))
    require(selected, "drill set is empty")
    return selected


def select_repeat(cases, profiles, requested=None):
    eligible = sorted(case for case in cases
                      if profiles.get(case, "base-midi") in ("base-midi", "midi-modulation"))
    require(eligible, "no base-midi or midi-modulation drill member for repeat.py")
    require(requested is None or requested in eligible, "repeat case is not an eligible drill member")
    return requested or eligible[0]


def validate_run(item, case, profile, revision, source_hashes, confirmations):
    require(isinstance(confirmations, list) and confirmations,
            "missing committed ui-confirm selection: " + case)
    require(isinstance(item, dict), "run manifest must be an object")
    require(item.get("case") == case, "inconsistent run case: " + case)
    require(item.get("passed") is False, "drill member passed or has no status: " + case)
    require(item.get("clock_mode") == "controlled-experimental", "wrong/missing controlled lane: " + case)
    require(item.get("profile") == profile, "wrong/missing profile: " + case)
    require(item.get("diagnostic_only") is True, "missing controlled diagnostic marker: " + case)
    require(item.get("mosaic_revision") == revision, "wrong/missing scratch revision: " + case)
    require(item.get("behaviour_source_sha256") == source_hashes, "wrong/missing behaviour sources: " + case)
    failure = item.get("failure")
    require(isinstance(failure, dict) and failure.get("type") == "UiMapError"
            and isinstance(failure.get("message"), str) and failure["message"].strip(),
            "first error is not UiMapError: " + case)
    frames = re.findall(r'^\s*File "([^"]+)", line \d+, in ([^\n]+)$',
                        failure.get("traceback", ""), re.MULTILINE)
    require(frames and frames[-1][1] == "confirm_header"
            and frames[-1][0].replace("\\", "/").endswith("/tests/behaviour/ui.py"),
            "UiMapError did not originate in Ui.confirm_header: " + case)
    traceback = failure["traceback"]
    final_line = traceback.rstrip("\r\n").splitlines()[-1] if isinstance(traceback, str) and traceback.strip() else ""
    require(final_line == "ui." + failure["type"] + ": " + failure["message"],
            "traceback exception differs from run failure: " + case)
    message = failure["message"]
    matched = False
    for confirmation in confirmations:
        expected = confirmation.get("expected_header") if isinstance(confirmation, dict) else None
        if not isinstance(expected, str) or not expected:
            continue
        if message == "expected %r, observed %r" % (expected, "<unmatched framebuffer>"):
            matched = True
            break
    require(matched, "UiMapError is not a selected ui-confirm header mismatch: " + case)
    return dict(type=failure["type"], message=failure["message"])


def validate_outcomes(cases, runs, profiles, revision, source_hashes):
    ids = [item.get("case") if isinstance(item, dict) else None for item in runs]
    require(all(isinstance(case, str) for case in ids), "missing run case")
    require(len(ids) == len(set(ids)), "duplicate run case")
    require(set(ids) == set(cases), "run set differs: missing=%r extra=%r" %
            (sorted(set(cases) - set(ids)), sorted(set(ids) - set(cases))))
    return [dict(case=item["case"], status="failed", first_error=validate_run(
        item, item["case"], profiles.get(item["case"], "base-midi"), revision, source_hashes,
        cases[item["case"]]))
        for item in sorted(runs, key=lambda item: item["case"])]


def git(repo, *args):
    try:
        return subprocess.check_output(["git", *args], cwd=repo, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as error:
        raise ValueError("git evidence read failed: " + error.stderr.decode(errors="replace")) from error


def blobs(repo, revision, paths):
    """Read the committed evidence in one git process, retaining exact bytes."""
    paths = list(paths)
    require(all("\n" not in path and "\r" not in path for path in paths), "invalid git evidence path")
    if not paths:
        return {}
    process = subprocess.run(["git", "cat-file", "--batch"], cwd=repo,
                             input="".join(revision + ":" + path + "\n" for path in paths).encode(),
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require(process.returncode == 0, "git batch evidence read failed")
    data, offset, result = process.stdout, 0, {}
    for path in paths:
        end = data.find(b"\n", offset)
        header = data[offset:end].split()
        require(end >= 0 and len(header) == 3 and header[1] == b"blob",
                "missing/non-blob committed evidence: " + path)
        size = int(header[2])
        offset = end + 1
        require(len(data) > offset + size and data[offset + size:offset + size + 1] == b"\n",
                "truncated committed evidence: " + path)
        require(path not in result, "duplicate committed path: " + path)
        result[path] = data[offset:offset + size]
        offset += size + 1
    require(offset == len(data), "unexpected extra git batch evidence")
    return result


def assignment(tree, name):
    values = [node.value for node in tree.body if isinstance(node, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == name for t in node.targets)]
    require(len(values) == 1, "expected one source assignment: " + name)
    return values[0]


def page_assignment(tree):
    node = assignment(tree, "CHANNEL_PAGES")
    require(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "OrderedDict" and len(node.args) == 1 and not node.keywords,
            "unrecognized CHANNEL_PAGES declaration")
    pairs = ast.literal_eval(node.args[0])
    require(isinstance(pairs, list) and all(isinstance(p, tuple) and len(p) == 2 for p in pairs),
            "invalid channel page pairs")
    require(len(dict(pairs)) == len(pairs), "duplicate channel pages")
    return node, pairs


def committed_plan(repo, revision, pages):
    revision = git(repo, "rev-parse", "--verify", revision + "^{commit}").decode().strip()
    names = git(repo, "ls-tree", "-r", "--name-only", revision, BASELINES).decode().splitlines()
    files = {name[len(BASELINES):]: raw for name, raw in blobs(repo, revision, [
        name for name in names if "/controlled/after/" in name
        and name.endswith(("/recipe.json", "/results.json"))]).items()}
    tree = ast.parse(git(repo, "show", revision + ":tests/behaviour/cases.py"))
    registry = assignment(tree, "CASES")
    require(isinstance(registry, ast.Dict), "expected explicit CASES registry")
    ids = [ast.literal_eval(key) for key in registry.keys]
    require(all(isinstance(case, str) and case for case in ids), "invalid case registry ID")
    require(len(ids) == len(set(ids)), "duplicate case IDs in registry")
    suite = ast.parse(git(repo, "show", revision + ":tests/behaviour/suite.py"))
    profiles_node = assignment(suite, "CASE_PROFILE")
    require(isinstance(profiles_node, ast.Dict), "expected explicit profile map")
    profile_keys = [ast.literal_eval(key) for key in profiles_node.keys]
    require(len(profile_keys) == len(set(profile_keys)), "duplicate case profiles")
    profiles = ast.literal_eval(profiles_node)
    require(set(profiles) <= set(ids), "unknown case in profile map")
    _, page_pairs = page_assignment(ast.parse(git(repo, "show", revision + ":" + MAP)))
    selected = derive_cases(files, ids, pages, dict(page_pairs))
    titles = {page: value.get("title") for page, value in page_pairs}
    for confirmations in selected.values():
        for confirmation in confirmations:
            title = titles.get(confirmation["page"])
            require(isinstance(title, str) and title,
                    "missing committed page title: " + confirmation["page"])
            confirmation["expected_header"] = "Ch. %s %s" % (confirmation["channel"], title)
    return revision, selected, profiles


def verify_swap(repo, baseline, scratch, pages):
    scratch = git(repo, "rev-parse", "--verify", scratch + "^{commit}").decode().strip()
    changed = git(repo, "diff", "--name-only", baseline, scratch).decode().splitlines()
    require(changed == [MAP], "scratch commit must change only ui_map.py")
    before = ast.parse(git(repo, "show", baseline + ":" + MAP))
    after = ast.parse(git(repo, "show", scratch + ":" + MAP))
    node, pairs = page_assignment(before)
    keys = [key for key, value in pairs]
    require(len(pages) == 2 and len(set(pages)) == 2 and set(pages) <= set(keys), "invalid page swap")
    left, right = [keys.index(page) for page in pages]
    node.args[0].elts[left], node.args[0].elts[right] = node.args[0].elts[right], node.args[0].elts[left]
    require(ast.dump(before) == ast.dump(after), "scratch change is not exactly the requested page-order swap")
    paths = git(repo, "ls-tree", "-r", "--name-only", scratch, "tests/behaviour").decode().splitlines()
    sources = {path: sha(raw) for path, raw in blobs(repo, scratch, [
        path for path in paths if path.endswith(".py")]).items()}
    return scratch, sources


def load_run(path):
    path = Path(path).resolve()
    raw, item = read(path)
    require(isinstance(item, dict), "run manifest must be an object")
    # Binds the actual root/nested inputs and results to their run manifest.
    verified_pair_files(item, path.parent)
    return item, dict(path=str(path), sha256=sha(raw))


def committed_sources(repo, revision):
    """Hash every Python source in the committed behaviour tree."""
    revision = git(repo, "rev-parse", "--verify", revision + "^{commit}").decode().strip()
    paths = git(repo, "ls-tree", "-r", "--name-only", revision,
                "tests/behaviour").decode().splitlines()
    return {path: sha(raw) for path, raw in blobs(repo, revision, [
        path for path in paths if path.endswith(".py")]).items()}


def validate_controls(cases, controls, profiles, revision, source_hashes):
    """Require one verified, successful controlled run per committed case."""
    loaded = [load_run(path) for path in controls]
    ids = [item.get("case") for item, ref in loaded]
    require(all(isinstance(case, str) for case in ids), "missing control case")
    require(len(ids) == len(set(ids)), "duplicate control case")
    require(set(ids) == set(cases), "control set differs: missing=%r extra=%r" %
            (sorted(set(cases) - set(ids)), sorted(set(ids) - set(cases))))
    rows = []
    for item, ref in sorted(loaded, key=lambda pair: pair[0]["case"]):
        case = item["case"]
        require(item.get("passed") is True, "baseline control did not pass: " + case)
        require("failure" in item and item["failure"] is None,
                "baseline control has a failure or missing failure field: " + case)
        require(item.get("mosaic_revision") == revision,
                "wrong/missing baseline revision: " + case)
        require(item.get("clock_mode") == "controlled-experimental",
                "wrong/missing controlled lane: " + case)
        require(item.get("diagnostic_only") is True,
                "missing controlled diagnostic marker: " + case)
        require("profile" in item and item["profile"] == profiles.get(case, "base-midi"),
                "wrong/missing profile: " + case)
        require(item.get("behaviour_source_sha256") == source_hashes,
                "wrong/missing baseline behaviour sources: " + case)
        sessions = {}
        for confirmation in cases[case]:
            session = confirmation["session"]
            if session not in sessions:
                _, sessions[session] = read(Path(ref["path"]).parent / session / "results.json")
            require(any(isinstance(entry, dict) and entry.get("kind") == "ui-confirm"
                        and entry.get("page") == confirmation["page"]
                        and entry.get("channel") == confirmation["channel"]
                        for entry in sessions[session]),
                    "baseline control missing selected ui-confirm: %s/%s/%s" %
                    (case, session, confirmation["page"]))
        rows.append(dict(case=case, status="passed", manifest=ref))
    return rows


def validate_repeat(path, case, profile, revision, sources, confirmations):
    path = Path(path).resolve()
    raw, item = read(path)
    require(isinstance(item, dict) and item.get("case") == case and item.get("profile") == profile,
            "repeat case/profile differs")
    require(item.get("passed") is False and item.get("diagnostic_only") is True,
            "repeat passed or missing controlled diagnostic marker")
    require(item.get("runs") == [], "repeat must fail in its first fresh process")
    failure = item.get("failure")
    require(isinstance(failure, dict) and failure.get("type") == "AssertionError",
            "unexpected repeat wrapper failure")
    processes = sorted(path.parent.glob("process-*.json"))
    require([p.name for p in processes] == ["process-0.json"], "missing/extra repeat process evidence")
    process_raw, process = read(processes[0])
    require(isinstance(process, dict) and type(process.get("returncode")) is int
            and process["returncode"] == 1, "repeat process did not fail normally")
    stdout, stderr = process.get("stdout"), process.get("stderr")
    require(isinstance(stdout, str) and isinstance(stderr, str), "missing repeat process output")
    require(failure.get("message") == stdout + stderr, "inconsistent repeat wrapper error")
    summaries = []
    for line in stdout.splitlines():
        if line.startswith('{"case"'):
            summaries.append(decode(line, "repeat stdout"))
    require(len(summaries) == 1, "missing/ambiguous repeat child summary")
    summary = summaries[0]
    require(summary.get("case") == case and summary.get("passed") is False
            and isinstance(summary.get("manifest"), str), "inconsistent repeat child summary")
    child, child_ref = load_run(summary["manifest"])
    error = validate_run(child, case, profile, revision, sources, confirmations)
    normalized_raw, normalized = read(path.parent / "normalized.json")
    require(normalized == [] and item.get("normalized_sha256") == sha(normalized_raw),
            "inconsistent repeat normalized evidence")
    return dict(case=case, status="failed", first_error=error,
                manifest=dict(path=str(path), sha256=sha(raw)),
                process=dict(path=str(processes[0]), sha256=sha(process_raw)), child=child_ref)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--baseline", required=True, help="committed final migration evidence revision")
    parser.add_argument("--pages", nargs=2, required=True, metavar=("FIRST", "SECOND"))
    parser.add_argument("--list", action="store_true", help="derive members only; never writes drill evidence")
    parser.add_argument("--scratch", help="commit containing only the page-order swap relative to baseline")
    parser.add_argument("--run", action="append", default=[], type=Path, help="one actual run.py manifest per drill member")
    parser.add_argument("--control", action="append", default=[], type=Path,
                        help="one passing baseline run.py manifest per drill member")
    parser.add_argument("--repeat", type=Path, help="actual repeat.py manifest")
    parser.add_argument("--repeat-case", help="eligible drill member; default first sorted eligible ID")
    parser.add_argument("--output", type=Path, help="default REPO/docs/testing/ui-migration-drill.json; never overwritten")
    args = parser.parse_args(argv)
    try:
        revision, cases, profiles = committed_plan(args.repo, args.baseline, args.pages)
        repeat_case = select_repeat(cases, profiles, args.repeat_case)
        if args.list:
            require(not args.run and not args.control and not args.repeat and not args.output and not args.scratch,
                    "--list cannot accept run, scratch or output evidence")
            print(json.dumps(dict(baseline_revision=revision, pages=args.pages,
                                  cases=cases, repeat_case=repeat_case), indent=2))
            return 0
        require(args.scratch and args.run and args.control and args.repeat,
                "actual scratch, baseline control, run and repeat evidence required")
        baseline_sources = committed_sources(args.repo, revision)
        controls = validate_controls(cases, args.control, profiles, revision, baseline_sources)
        scratch, sources = verify_swap(args.repo, revision, args.scratch, args.pages)
        loaded = [load_run(path) for path in args.run]
        rows = validate_outcomes(cases, [item for item, ref in loaded], profiles, scratch, sources)
        references = {item["case"]: ref for item, ref in loaded}
        for row in rows:
            row.update(manifest=references[row["case"]], confirmations=cases[row["case"]])
        repeated = validate_repeat(args.repeat, repeat_case, profiles.get(repeat_case, "base-midi"),
                                   scratch, sources, cases[repeat_case])
        require(repeated["child"]["path"] not in {ref["path"] for item, ref in loaded},
                "repeat must be a separate fresh-process run")
        report = dict(schema_version=1, passed=True, baseline_revision=revision, scratch_revision=scratch,
                      swapped_pages=args.pages, lane="controlled-experimental",
                      complete_regression_run=False, cases=rows, repeat=repeated,
                      controls=controls, behaviour_source_sha256=sources)
        output = args.output or args.repo / "docs/testing/ui-migration-drill.json"
        with output.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2)
            stream.write("\n")
        print(str(output))
        return 0
    except (ValueError, OSError, SyntaxError, TypeError) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
