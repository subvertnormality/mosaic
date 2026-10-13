#!/usr/bin/env python3
"""Fail-closed validator for publishing an already-built manual artifact."""
from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, stat, subprocess, sys, tempfile, urllib.error, urllib.parse, urllib.request, zipfile
from pathlib import Path, PurePosixPath

REPOSITORY = "subvertnormality/mosaic"
PRODUCER_WORKFLOW = ".github/workflows/manual-build.yml"
PRODUCER_NAME = "Build manual site"
SCOPE = "controlled-manual-generation"
MAX_ARCHIVE_BYTES = 1024 * 1024 * 1024
MAX_FILES = 10000
SHA256 = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")

class Reject(ValueError):
    pass

def need(condition, message):
    if not condition:
        raise Reject(message)

def manifest_integer(value, label):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise Reject(f"invalid {label}")
    return value

def expected_artifact_name(run_id, attempt, pr_number):
    if pr_number is None:
        return f"manual-site-dispatch-run-{run_id}-attempt-{attempt}"
    return f"manual-site-pr-{pr_number}-run-{run_id}-attempt-{attempt}"

def validate_run(run, *, repository, run_id, attempt):
    need(repository == REPOSITORY, "publisher repository mismatch")
    need((run.get("repository") or {}).get("full_name") == repository, "producer run repository mismatch")
    need(run.get("id") == run_id, "producer run ID mismatch")
    need(run.get("run_attempt") == attempt, "producer run attempt mismatch")
    need(run.get("path") == PRODUCER_WORKFLOW, "unexpected producer workflow path")
    need(run.get("name") == PRODUCER_NAME, "unexpected producer workflow name")
    need(run.get("status") == "completed" and run.get("conclusion") == "success",
         "producer run is not successful and complete")

def validate_manifest(manifest, *, repository, run, run_id, attempt, pr_number,
                      pr_head_sha, pr_base_ref, main_tree_sha):
    need(manifest.get("schema_version") == 1, "unsupported artifact manifest schema")
    need(manifest.get("repository") == repository == REPOSITORY, "manifest repository mismatch")
    need(manifest.get("producer_workflow") == PRODUCER_WORKFLOW, "manifest workflow mismatch")
    need(manifest_integer(manifest.get("producer_run_id"), "manifest run ID") == run_id, "manifest run ID mismatch")
    need(manifest_integer(manifest.get("producer_run_attempt"), "manifest run attempt") == attempt, "manifest run attempt mismatch")
    need(manifest.get("validation_scope") == SCOPE, "manual validation scope mismatch")
    need(manifest.get("realtime_qualification") == "pending-ci", "unexpected realtime qualification")
    need(manifest.get("clock_mode") == "controlled-experimental", "unexpected clock mode")
    need(manifest.get("manual_generation_complete") is True, "manual generation is incomplete")
    need(manifest.get("complete_regression_run") is False, "artifact claims a complete regression run")
    tested_commit = manifest.get("tested_commit_sha")
    tree_sha = manifest.get("tested_tree_sha")
    need(isinstance(tested_commit, str) and GIT_SHA.fullmatch(tested_commit) is not None, "invalid tested commit SHA")
    need(isinstance(tree_sha, str) and GIT_SHA.fullmatch(tree_sha) is not None, "invalid tested tree SHA")
    if pr_number is None:
        need(run.get("head_branch") == "main", "dispatch producer did not run on main")
        need(tested_commit == run.get("head_sha"), "dispatch tested commit differs from producer run")
    else:
        need(tested_commit == pr_head_sha, "PR tested commit differs from the exact PR head")
    need(tree_sha == main_tree_sha, "tested source tree does not match current main")
    build_sha = manifest.get("finalized_build_manifest_sha256")
    need(isinstance(build_sha, str) and SHA256.fullmatch(build_sha) is not None,
         "invalid finalized build manifest SHA")
    actual_pr = manifest.get("pr_number")
    if pr_number is not None:
        actual_pr = manifest_integer(actual_pr, "manifest PR number")
    need(actual_pr == pr_number, "manifest PR number mismatch")
    need(manifest.get("pr_head_sha") == pr_head_sha, "manifest PR head mismatch")
    need(manifest.get("pr_base_ref") == pr_base_ref, "manifest PR base mismatch")
    files = manifest.get("files")
    need(isinstance(files, dict) and files, "manifest file map is empty or invalid")
    for name, digest in files.items():
        need(isinstance(name, str) and name.startswith("manual-site/"),
             "manifest contains a path outside manual-site")
        need(isinstance(digest, str) and SHA256.fullmatch(digest) is not None,
             f"invalid file SHA for {name!r}")
    return expected_artifact_name(run_id, attempt, pr_number)

def safe_member_name(name):
    need("\x00" not in name and "\\" not in name, f"unsafe archive path {name!r}")
    need(not name.startswith("/") and not re.match(r"^[A-Za-z]:", name),
         f"absolute archive path {name!r}")
    normalized = name[:-1] if name.endswith("/") else name
    parts = normalized.split("/")
    need(parts and all(p not in ("", ".", "..") for p in parts), f"non-normal archive path {name!r}")
    need(":" not in normalized, f"colon in archive path {name!r}")
    need(parts[0] in ("manual-site", "manual-artifact-manifest.json"),
         f"unexpected archive root {name!r}")
    if parts[0] == "manual-artifact-manifest.json":
        need(len(parts) == 1 and not name.endswith("/"), "invalid manifest archive path")
    else:
        need(len(parts) > 1 or name.endswith("/"), "manual-site root must be a directory")
    return normalized, name.endswith("/")

def _check_safe_destination(destination):
    destination = Path(destination)
    need(not destination.exists() and not destination.is_symlink(),
         "extraction destination must be new and must not be a symlink")
    for parent in (destination.parent, *destination.parent.parents):
        if parent.exists():
            need(not parent.is_symlink() and parent.is_dir(),
                 "extraction path has a symlink or non-directory ancestor")

def validate_and_extract_zip(archive, destination):
    archive = Path(archive)
    destination = Path(destination)
    need(archive.stat().st_size <= MAX_ARCHIVE_BYTES, "artifact archive exceeds size limit")
    _check_safe_destination(destination)
    destination.mkdir(parents=True, exist_ok=False)
    seen, file_bytes = set(), {}
    total_size = 0
    with zipfile.ZipFile(archive) as zf:
        infos = zf.infolist()
        need(0 < len(infos) <= MAX_FILES, "artifact has invalid member count")
        for info in infos:
            name, is_dir = safe_member_name(info.filename)
            need(name not in seen, f"duplicate archive member {name!r}")
            seen.add(name)
            mode = (info.external_attr >> 16) & 0xFFFF
            kind = stat.S_IFMT(mode)
            need(kind in (0, stat.S_IFREG, stat.S_IFDIR), f"special or symlink member {name!r}")
            need(is_dir == (kind == stat.S_IFDIR) or kind == 0, f"archive mode/type mismatch for {name!r}")
            if is_dir:
                continue
            total_size += info.file_size
            need(total_size <= MAX_ARCHIVE_BYTES, "artifact expands beyond size limit")
            data = zf.read(info)
            need(len(data) == info.file_size, f"truncated archive member {name!r}")
            file_bytes[name] = data
    need("manual-artifact-manifest.json" in file_bytes, "artifact manifest missing")
    need(any(p.startswith("manual-site/") for p in file_bytes), "manual-site is empty")
    try:
        manifest = json.loads(file_bytes["manual-artifact-manifest.json"])
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Reject(f"invalid artifact manifest: {exc}") from exc
    expected = manifest.get("files") if isinstance(manifest, dict) else None
    need(isinstance(expected, dict), "manifest file map missing")
    actual = {p for p in file_bytes if p.startswith("manual-site/")}
    need(actual == set(expected), "archive files do not exactly match manifest")
    for name in sorted(actual):
        need(hashlib.sha256(file_bytes[name]).hexdigest() == expected[name], f"SHA256 mismatch for {name}")
    need("manual-site/index.html" in actual, "manual site entry point missing")
    for name, data in file_bytes.items():
        target = destination.joinpath(*PurePosixPath(name).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return manifest

class NoCrossHostAuthRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None and urllib.parse.urlsplit(req.full_url).netloc.lower() != urllib.parse.urlsplit(newurl).netloc.lower():
            new.remove_header("Authorization")
            new.unredirected_hdrs.pop("Authorization", None)
        return new

class GitHub:
    def __init__(self, token, repository):
        need(repository == REPOSITORY, "unexpected GITHUB_REPOSITORY")
        self.token, self.repository = token, repository
        self.opener = urllib.request.build_opener(NoCrossHostAuthRedirect())
    def request(self, path, accept="application/vnd.github+json"):
        need(path.startswith("/repos/"), "refusing non-API GitHub request path")
        url = "https://api.github.com" + path
        req = urllib.request.Request(url, headers={"Accept": accept,
            "Authorization": f"Bearer {self.token}", "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "mosaic-trusted-manual-publisher"})
        try:
            return self.opener.open(req, timeout=60)
        except urllib.error.HTTPError as exc:
            raise Reject(f"GitHub API request failed with HTTP {exc.code}") from exc
    def json(self, path):
        with self.request(path) as response:
            return json.loads(response.read())
    def download(self, path, dest):
        with self.request(path) as response, Path(dest).open("wb") as out:
            shutil.copyfileobj(response, out)
        need(Path(dest).stat().st_size > 0, "downloaded artifact is empty")
        need(Path(dest).stat().st_size <= MAX_ARCHIVE_BYTES, "downloaded artifact exceeds size limit")

def run_identity(gh, event, event_name, dispatch_run_id):
    if event_name == "workflow_run":
        wr = event.get("workflow_run") or {}
        rid, attempt = int(wr.get("id", 0)), int(wr.get("run_attempt", 0))
        need(rid > 0 and attempt > 0, "workflow_run event lacks producer run identity")
        run = gh.json(f"/repos/{REPOSITORY}/actions/runs/{rid}")
        if run.get("status") != "completed" or run.get("conclusion") != "success":
            return rid, attempt, None, None, None, False
        validate_run(run, repository=REPOSITORY, run_id=rid, attempt=attempt)
        prs = run.get("pull_requests") or []
        if run.get("event") == "workflow_dispatch":
            need(run.get("head_branch") == "main", "dispatch producer did not run on main")
            return rid, attempt, None, None, None, True
        need(run.get("event") == "pull_request" and prs,
             "producer event is not pull_request or workflow_dispatch")
        number = int(prs[0].get("number", 0))
        need(number > 0, "producer run has invalid pull request association")
        current = gh.json(f"/repos/{REPOSITORY}/pulls/{number}")
        if not current.get("merged") or (current.get("base") or {}).get("ref") != "main":
            return rid, attempt, number, None, None, False
        head = (current.get("head") or {}).get("sha")
        need(any(int(x.get("number", 0)) == number and
                 (x.get("head") or {}).get("sha") == head for x in prs),
             "producer run is not tied to the current merged PR head")
        return rid, attempt, number, head, "main", True

    if event_name in ("pull_request", "pull_request_target"):
        pr = event.get("pull_request") or {}
        if event.get("action") != "closed" or not pr.get("merged"):
            return 0, 0, None, None, None, False
        number = int(pr.get("number", 0))
        need(number > 0, "closed PR event lacks PR number")
        current = gh.json(f"/repos/{REPOSITORY}/pulls/{number}")
        need(current.get("merged") and (current.get("base") or {}).get("ref") == "main",
             "PR is not merged into main")
        head = (current.get("head") or {}).get("sha")
        matches = []
        for page in range(1, 11):
            runs = gh.json(f"/repos/{REPOSITORY}/actions/workflows/manual-build.yml/runs?event=pull_request&status=success&per_page=100&page={page}")
            batch = runs.get("workflow_runs", [])
            matches.extend(r for r in batch
                           if any(int(p.get("number", 0)) == number and
                                  (p.get("head") or {}).get("sha") == head
                                  for p in (r.get("pull_requests") or [])))
            if len(batch) < 100 or int(runs.get("total_count", 0)) <= page * 100:
                break
        if not matches:
            # The merge event can beat producer completion. The later
            # workflow_run event will retry the same verified publication path.
            return 0, 0, None, None, None, False
        chosen = max(matches, key=lambda x: (int(x.get("run_number", 0)),
                                               int(x.get("run_attempt", 0))))
        rid, attempt = int(chosen["id"]), int(chosen["run_attempt"])
        run = gh.json(f"/repos/{REPOSITORY}/actions/runs/{rid}")
        validate_run(run, repository=REPOSITORY, run_id=rid, attempt=attempt)
        need(run.get("event") == "pull_request", "selected producer run has wrong event")
        return rid, attempt, number, head, "main", True

    if event_name == "workflow_dispatch":
        need(os.environ.get("GITHUB_REF") == "refs/heads/main",
             "manual publishing is allowed only from main")
        need(dispatch_run_id and str(dispatch_run_id).isdigit(),
             "workflow_dispatch requires producer_run_id input")
        rid = int(dispatch_run_id)
        run = gh.json(f"/repos/{REPOSITORY}/actions/runs/{rid}")
        attempt = int(run.get("run_attempt", 0))
        validate_run(run, repository=REPOSITORY, run_id=rid, attempt=attempt)
        need(run.get("event") == "workflow_dispatch" and run.get("head_branch") == "main",
             "manual producer run must target main")
        return rid, attempt, None, None, None, True
    raise Reject(f"unsupported publisher event {event_name!r}")

def prepare(args):
    event = json.loads(Path(args.event_path).read_text(encoding="utf-8"))
    token = os.environ.get("GITHUB_TOKEN", "")
    gh = GitHub(token, os.environ.get("GITHUB_REPOSITORY", ""))
    need(token, "GITHUB_TOKEN is missing")
    dispatch_id = (event.get("inputs") or {}).get("producer_run_id") if args.event_name == "workflow_dispatch" else None
    rid, attempt, number, head, base, publishable = run_identity(gh, event, args.event_name, dispatch_id)
    if not publishable:
        return False
    run = gh.json(f"/repos/{REPOSITORY}/actions/runs/{rid}")
    validate_run(run, repository=REPOSITORY, run_id=rid, attempt=attempt)
    if number is not None:
        pr = gh.json(f"/repos/{REPOSITORY}/pulls/{number}")
        need(pr.get("merged") and (pr.get("base") or {}).get("ref") == "main",
             "pull request is not merged into main")
        need((pr.get("head") or {}).get("sha") == head, "merged pull request head changed")
    tree_sha = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], text=True).strip()
    name = expected_artifact_name(rid, attempt, number)
    artifacts = gh.json(f"/repos/{REPOSITORY}/actions/runs/{rid}/artifacts")
    found = [a for a in artifacts.get("artifacts", []) if a.get("name") == name]
    need(len(found) == 1, "exact producer artifact is missing or ambiguous")
    artifact = found[0]
    need(not artifact.get("expired"), "producer artifact has expired")
    artifact_id = artifact.get("id")
    need(isinstance(artifact_id, int) and not isinstance(artifact_id, bool) and artifact_id > 0,
         "producer artifact has invalid API ID")
    with tempfile.TemporaryDirectory(prefix="manual-publish-") as temp:
        archive = Path(temp) / "artifact.zip"
        gh.download(f"/repos/{REPOSITORY}/actions/artifacts/{artifact_id}/zip", archive)
        manifest = validate_and_extract_zip(archive, args.output_dir)
    validate_manifest(manifest, repository=REPOSITORY, run=run, run_id=rid,
        attempt=attempt, pr_number=number, pr_head_sha=head, pr_base_ref=base,
        main_tree_sha=tree_sha)
    tested_commit = manifest["tested_commit_sha"]
    source_commit = gh.json(f"/repos/{REPOSITORY}/commits/{tested_commit}")
    need(source_commit.get("sha") == tested_commit, "GitHub returned a different tested commit")
    source_tree = ((source_commit.get("commit") or {}).get("tree") or {}).get("sha")
    need(source_tree == manifest["tested_tree_sha"],
         "tested commit tree differs from the artifact source identity")
    return True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-path", default=os.environ.get("GITHUB_EVENT_PATH"))
    parser.add_argument("--event-name", default=os.environ.get("GITHUB_EVENT_NAME"))
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    try:
        need(args.event_path and args.event_name, "GitHub event context is missing")
        ok = prepare(args)
        output = os.environ.get("GITHUB_OUTPUT")
        if output:
            with open(output, "a", encoding="utf-8") as stream:
                stream.write(f"publishable={'true' if ok else 'false'}\n")
        print("publishable" if ok else "not publishable for this event")
        return 0
    except (Reject, OSError, KeyError, ValueError, subprocess.CalledProcessError,
            urllib.error.URLError, zipfile.BadZipFile) as exc:
        print(f"manual publisher rejected artifact: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())

