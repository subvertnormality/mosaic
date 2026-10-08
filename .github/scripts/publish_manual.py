#!/usr/bin/env python3
"""Fail-closed validator for publishing an already-built manual artifact."""
from __future__ import annotations
import argparse, base64, hashlib, json, os, re, shutil, stat, subprocess, sys, tempfile, urllib.error, urllib.parse, urllib.request, zipfile
from pathlib import Path, PurePosixPath

REPOSITORY = "subvertnormality/mosaic"
PRODUCER_WORKFLOW = ".github/workflows/manual-build.yml"
PRODUCER_NAME = "Build manual site"
SCOPE = "controlled-manual-generation"
MAX_ARCHIVE_BYTES = 1024 * 1024 * 1024
MAX_FILES = 10000
SHA256 = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
PRODUCER_TOOLING_POLICY_VERSION = "codex-manual-tooling-allowlist-v1-candidate"
PRODUCER_TOOLING_ALLOWLISTS = {
    # 2026-10-06 (Claude, owner-requested CI gap fixes): manual-build.yml a3aa1d41... and manual-build.sh daa921e9...
    # re-pinned after splitting real-time audio into its own job (adopted via --adopt-audio-report) and adding the
    # scene-plan lint and manual unit suites as a fail-fast preflight. Workflow re-pinned again the same day after
    # moving runner.temp paths out of job-level env (no runner context there), and installing git before checkout
    # in the bare container so checkout makes a real repository with submodules. Both re-pinned again after making
    # the emulator checkout in place under the restored runtime cache and naming the audio artifact per run, and the
    # script once more for a plain fetch (git 2.25 in the container rejects --filter without partial-clone config),
    # and again to give the builder MONOME_EMULATOR for in-process audio adoption. Both re-pinned for reusing a
    # recorded audio bundle across runs when the audio inputs are byte-identical (test files excluded from the identity).
    # 2026-10-07 (Claude): manual-build.sh re-pinned after giving the Masks provisioning capture MONOME_EMULATOR (CI run
    # 37503722733 failed there with "MONOME_EMULATOR is required").
    PRODUCER_TOOLING_POLICY_VERSION: {
        ".github/workflows/manual-build.yml": "a70fc1d76e359a4b086ad365a4c79a4bf16fd86ce2a4f336cad3aaa9a06f93e0",
        ".github/scripts/manual-build.sh": "b7d646e9de859612cf732e9a7fbf7ca061bb9828daabc5b5eb5b839d6b5e6d6e",
        ".github/scripts/manual_artifact.py": "7b9bc0bdb0f1e4a143370af2cd220a0db1f4cb65a640c72247408332ec1aaab6",
    },
}

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
                      pr_head_sha, pr_base_ref, main_tree_sha,
                      publication_policy="main-edition", expected_source_sha=None,
                      source_tree_sha=None, target_tree_sha=None,
                       promotion_artifact_kind="post-merge-dispatch"):
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
    if publication_policy == "main-edition":
        if pr_number is None:
            need(run.get("head_branch") == "main", "dispatch producer did not run on main")
            need(tested_commit == run.get("head_sha"), "dispatch tested commit differs from producer run")
        else:
            need(tested_commit == pr_head_sha, "PR tested commit differs from the exact PR head")
        need(tree_sha == main_tree_sha, "tested source tree does not match current main")
    elif publication_policy == "codex-1.4.0-promotion":
        need(isinstance(expected_source_sha, str) and GIT_SHA.fullmatch(expected_source_sha) is not None,
             "invalid pinned merged codex source SHA")
        if promotion_artifact_kind == "post-merge-dispatch":
            need(pr_number is None and pr_head_sha is None and pr_base_ref is None,
                 "post-merge dispatch artifact must not carry PR identity")
            need(run.get("event") == "workflow_dispatch" and run.get("head_branch") == "codex/1.4.0",
                 "producer is not the requested codex dispatch run")
            need(tested_commit == expected_source_sha == run.get("head_sha"),
                 "producer run source commit does not match the explicit source SHA")
        elif promotion_artifact_kind == "merged-pr":
            need(pr_number is not None and pr_head_sha is not None and pr_base_ref == "codex/1.4.0",
                 "merged PR artifact identity is incomplete or targets the wrong base")
            need(run.get("event") == "pull_request",
                 "producer is not the exact pull_request build")
            need(tested_commit == pr_head_sha,
                 "artifact tested commit does not equal the exact PR head")
        else:
            raise Reject("unsupported codex promotion artifact kind")
        need(isinstance(source_tree_sha, str) and isinstance(target_tree_sha, str) and
             tree_sha == source_tree_sha == target_tree_sha,
             "artifact tree does not match both the tested commit and merged codex source")
    else:
        raise Reject("unsupported publication policy")
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

def canonical_site_tree(site_root):
    root = Path(site_root).resolve(strict=True)
    need(root.is_dir() and not root.is_symlink(), "verified site root is invalid")
    rows = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise Reject("verified site contains a symlink")
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            need(safe_member_name("manual-site/" + relative)[0] == "manual-site/" + relative,
                 "verified site contains an unsafe path")
            rows[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    need("index.html" in rows, "verified site entry point missing")
    return rows

def site_tree_sha256(rows):
    encoded = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

def verify_api_zip_digest(api_digest, archive):
    need(isinstance(api_digest, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", api_digest) is not None,
         "GitHub artifact API digest is missing or malformed")
    digest = hashlib.sha256()
    with Path(archive).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    need(api_digest == "sha256:" + actual, "downloaded ZIP differs from GitHub artifact API digest")
    return actual

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
            if run.get("head_branch") == "codex/1.4.0":
                return rid, attempt, None, None, None, False
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

def positive_workflow_input(value, label):
    need(isinstance(value, str) and re.fullmatch(r"[1-9][0-9]*", value) is not None,
         f"invalid {label}")
    return int(value)


def validate_producer_tooling(gh, *, source_sha):
    expected = PRODUCER_TOOLING_ALLOWLISTS[PRODUCER_TOOLING_POLICY_VERSION]
    for path, expected_sha in expected.items():
        quoted = urllib.parse.quote(path, safe="/")
        response = gh.json(
            f"/repos/{REPOSITORY}/contents/{quoted}?ref={source_sha}")
        need(response.get("path") == path and response.get("encoding") == "base64",
             f"producer tooling response is invalid for {path}")
        try:
            content = base64.b64decode(response.get("content", ""), validate=True)
        except (ValueError, TypeError) as exc:
            raise Reject(f"producer tooling content is invalid for {path}") from exc
        need(hashlib.sha256(content).hexdigest() == expected_sha,
             f"producer tooling is not in the trusted release allowlist: {path}")
    return {"version": PRODUCER_TOOLING_POLICY_VERSION,
            "files": dict(expected)}


def validate_codex_promotion(gh, *, run_id, attempt, pr_number, expected_source_sha,
                             expected_pr_head_sha, expected_pr_base_sha,
                             promotion_artifact_kind):
    need(GIT_SHA.fullmatch(expected_source_sha or "") is not None,
         "invalid explicit merged codex source SHA")
    need(GIT_SHA.fullmatch(expected_pr_head_sha or "") is not None,
         "invalid pinned PR head SHA")
    need(GIT_SHA.fullmatch(expected_pr_base_sha or "") is not None,
         "invalid pinned PR base SHA")
    run = gh.json(f"/repos/{REPOSITORY}/actions/runs/{run_id}")
    validate_run(run, repository=REPOSITORY, run_id=run_id, attempt=attempt)

    pull = gh.json(f"/repos/{REPOSITORY}/pulls/{pr_number}")
    need(pull.get("number") == pr_number, "merged PR number mismatch")
    need(pull.get("merged") is True, "promotion PR is not merged")
    need((pull.get("base") or {}).get("ref") == "codex/1.4.0",
         "promotion PR base is not codex/1.4.0")
    need((pull.get("head") or {}).get("sha") == expected_pr_head_sha,
         "promotion PR head SHA does not match the explicit pin")
    need(((pull.get("head") or {}).get("repo") or {}).get("full_name") == REPOSITORY,
         "promotion PR head must come from a same-repository branch, not a fork")
    need((pull.get("base") or {}).get("sha") == expected_pr_base_sha,
         "promotion PR base SHA does not match the explicit pin")
    merge_sha = pull.get("merge_commit_sha")
    need(isinstance(merge_sha, str) and GIT_SHA.fullmatch(merge_sha) is not None,
         "promotion PR has an invalid merge commit SHA")
    need(expected_source_sha == merge_sha,
         "promotion source SHA must equal the exact named PR merge commit")

    if promotion_artifact_kind == "merged-pr":
        need(run.get("event") == "pull_request",
             "merged PR promotion requires the original pull_request producer run")
        need(any(int(item.get("number", 0)) == pr_number and
                 (item.get("head") or {}).get("sha") == expected_pr_head_sha
                 for item in (run.get("pull_requests") or [])),
             "producer run is not associated with the exact merged PR head")
    elif promotion_artifact_kind == "post-merge-dispatch":
        need(run.get("event") == "workflow_dispatch" and
             run.get("head_branch") == "codex/1.4.0",
             "producer is not the requested codex dispatch run")
        need(run.get("head_sha") == expected_source_sha,
             "producer run source commit does not match the explicit source SHA")
    else:
        raise Reject("unsupported codex promotion artifact kind")

    comparison = gh.json(f"/repos/{REPOSITORY}/compare/{merge_sha}...{expected_source_sha}")
    need(comparison.get("status") == "identical",
         "codex source commit is not exactly the named PR merge commit")
    need(((comparison.get("merge_base_commit") or {}).get("sha")) == merge_sha,
         "codex source compare merge base does not equal the PR merge commit")
    need(((comparison.get("head_commit") or {}).get("sha")) == expected_source_sha,
         "codex source compare head does not equal the explicit source SHA")
    branch_ref = gh.json(f"/repos/{REPOSITORY}/git/ref/heads/codex/1.4.0")
    need(((branch_ref.get("object") or {}).get("sha")) == expected_source_sha,
         "codex branch ref no longer points to the explicit source SHA")
    return run, pull, merge_sha



def json_sha256(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

def validate_required_ci(gh, source_sha):
    requirements = {
        ".github/workflows/main.yml": {"Run tests on Ubuntu"},
        ".github/workflows/behaviour.yml": {"Complete behaviour coverage"},
    }
    for workflow, required_jobs in requirements.items():
        encoded_workflow = workflow.split("/")[-1]
        runs = gh.json(f"/repos/{REPOSITORY}/actions/workflows/{encoded_workflow}/runs?head_sha={source_sha}&status=completed&per_page=100")
        candidates = [run for run in runs.get("workflow_runs", [])
                      if run.get("head_sha") == source_sha and run.get("path") == workflow
                      and run.get("status") == "completed" and run.get("conclusion") == "success"]
        passed = False
        for run in candidates:
            jobs = gh.json(f"/repos/{REPOSITORY}/actions/runs/{run['id']}/jobs?per_page=100")
            names = {job.get("name") for job in jobs.get("jobs", [])
                     if job.get("status") == "completed" and job.get("conclusion") == "success"}
            if required_jobs.issubset(names):
                passed = True
                break
        need(passed, "required source-bound CI is missing or failed: " + workflow)

def verify_staged_site(site_root, receipt_path):
    receipt = json.loads(Path(receipt_path).read_text(encoding="utf-8"))
    expected = receipt.get("artifact", {}).get("site_tree_sha256")
    need(isinstance(expected, str) and SHA256.fullmatch(expected) is not None,
         "publication receipt has no canonical site tree digest")
    actual = site_tree_sha256(canonical_site_tree(site_root))
    need(actual == expected, "transferred Pages tree differs from the verified producer artifact")
    return actual

def prepare(args):
    event = json.loads(Path(args.event_path).read_text(encoding="utf-8"))
    inputs = event.get("inputs") or {}
    policy = inputs.get("publication_policy", "main-edition")
    need(policy in ("main-edition", "codex-1.4.0-promotion"), "unsupported publication policy")
    need(policy == "main-edition" or args.event_name == "workflow_dispatch",
         "codex promotion is available only through explicit workflow_dispatch")

    token = os.environ.get("GITHUB_TOKEN", "")
    gh = GitHub(token, os.environ.get("GITHUB_REPOSITORY", ""))
    need(token, "GITHUB_TOKEN is missing")
    promotion = None
    if policy == "codex-1.4.0-promotion":
        need(os.environ.get("GITHUB_REF") == "refs/heads/main",
             "codex promotion consumer must run from trusted main")
        rid = positive_workflow_input(inputs.get("producer_run_id"), "producer run ID")
        attempt = positive_workflow_input(inputs.get("producer_run_attempt"), "producer run attempt")
        pr_number = positive_workflow_input(inputs.get("promotion_pr_number"), "promotion PR number")
        expected_source_sha = inputs.get("expected_source_sha")
        expected_pr_head_sha = inputs.get("promotion_pr_head_sha")
        expected_pr_base_sha = inputs.get("promotion_pr_base_sha")
        promotion_artifact_kind = inputs.get("promotion_artifact_kind", "post-merge-dispatch")
        need(promotion_artifact_kind in ("merged-pr", "post-merge-dispatch"),
             "unsupported codex promotion artifact kind")
        run, pr, merge_sha = validate_codex_promotion(
            gh, run_id=rid, attempt=attempt, pr_number=pr_number,
            expected_source_sha=expected_source_sha,
            expected_pr_head_sha=expected_pr_head_sha,
            expected_pr_base_sha=expected_pr_base_sha,
            promotion_artifact_kind=promotion_artifact_kind)
        if promotion_artifact_kind == "merged-pr":
            number, head, base = pr_number, expected_pr_head_sha, "codex/1.4.0"
        else:
            number, head, base = None, None, None
        publishable = True
        promotion = dict(artifact_kind=promotion_artifact_kind, pr_number=pr_number,
                         base_ref="codex/1.4.0", base_sha=expected_pr_base_sha,
                         head_sha=expected_pr_head_sha, merge_commit_sha=merge_sha,
                         source_commit_sha=expected_source_sha)
        tooling_source_sha = (expected_pr_head_sha if promotion_artifact_kind == "merged-pr"
                              else expected_source_sha)
        producer_tooling = validate_producer_tooling(gh, source_sha=tooling_source_sha)
    else:
        dispatch_id = inputs.get("producer_run_id") if args.event_name == "workflow_dispatch" else None
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
            promotion = dict(pr_number=number, base_ref="main",
                             merge_commit_sha=pr.get("merge_commit_sha"),
                             source_commit_sha=head)

    publisher_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    publisher_tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], text=True).strip()
    need(GIT_SHA.fullmatch(publisher_commit) is not None and GIT_SHA.fullmatch(publisher_tree) is not None,
         "invalid trusted publisher source identity")
    name = expected_artifact_name(rid, attempt, number)
    artifacts = gh.json(f"/repos/{REPOSITORY}/actions/runs/{rid}/artifacts")
    found = [a for a in artifacts.get("artifacts", []) if a.get("name") == name]
    need(len(found) == 1, "exact producer artifact is missing or ambiguous")
    artifact = found[0]
    need(not artifact.get("expired"), "producer artifact has expired")
    api_digest = artifact.get("digest")
    need(isinstance(api_digest, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", api_digest) is not None,
         "GitHub artifact API digest is missing or malformed")
    artifact_id = artifact.get("id")
    need(isinstance(artifact_id, int) and not isinstance(artifact_id, bool) and artifact_id > 0,
         "producer artifact has invalid API ID")
    with tempfile.TemporaryDirectory(prefix="manual-publish-") as temp:
        archive = Path(temp) / "artifact.zip"
        gh.download(f"/repos/{REPOSITORY}/actions/artifacts/{artifact_id}/zip", archive)
        archive_sha = verify_api_zip_digest(api_digest, archive)
        manifest = validate_and_extract_zip(archive, args.output_dir)
        site_rows = canonical_site_tree(Path(args.output_dir) / "manual-site")
        site_digest = site_tree_sha256(site_rows)
        expected_rows = {name[len("manual-site/"):]: digest
                         for name, digest in manifest["files"].items()
                         if name.startswith("manual-site/")}
        need(site_rows == expected_rows, "extracted site differs from producer file map")
    tested_commit = manifest["tested_commit_sha"]
    source_commit = gh.json(f"/repos/{REPOSITORY}/commits/{tested_commit}")
    need(source_commit.get("sha") == tested_commit, "GitHub returned a different tested commit")
    source_tree = ((source_commit.get("commit") or {}).get("tree") or {}).get("sha")
    need(source_tree == manifest["tested_tree_sha"],
         "tested commit tree differs from the artifact source identity")
    validate_required_ci(gh, tested_commit)
    target_tree = source_tree
    if policy == "codex-1.4.0-promotion":
        target_sha = (promotion or {}).get("source_commit_sha")
        target_commit = gh.json(f"/repos/{REPOSITORY}/commits/{target_sha}")
        need(target_commit.get("sha") == target_sha,
             "GitHub returned a different merged codex source commit")
        target_tree = ((target_commit.get("commit") or {}).get("tree") or {}).get("sha")
    validate_manifest(manifest, repository=REPOSITORY, run=run, run_id=rid,
        attempt=attempt, pr_number=number, pr_head_sha=head, pr_base_ref=base,
        main_tree_sha=publisher_tree, publication_policy=policy,
        expected_source_sha=(promotion or {}).get("source_commit_sha"),
        source_tree_sha=source_tree, target_tree_sha=target_tree,
        promotion_artifact_kind=inputs.get("promotion_artifact_kind", "post-merge-dispatch"))
    if policy == "codex-1.4.0-promotion":
        promotion["source_tree_sha"] = target_tree

    manifest_path = Path(args.output_dir) / "manual-artifact-manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    receipt = {
        "schema_version": 1,
        "publication_policy": policy,
        "publisher": {"repository": REPOSITORY, "commit_sha": publisher_commit,
                      "tree_sha": publisher_tree},
        "producer": {"repository": REPOSITORY, "workflow_path": PRODUCER_WORKFLOW,
                     "workflow_name": PRODUCER_NAME, "run_id": rid, "run_attempt": attempt,
                     "event": run.get("event"), "head_branch": run.get("head_branch"),
                     "run_head_sha": run.get("head_sha"),
                     "source_commit_sha": tested_commit, "source_tree_sha": source_tree,
                     "artifact_id": artifact_id, "artifact_name": name,
                     "archive_sha256": archive_sha},
        "promotion": promotion,
        "producer_tooling": producer_tooling if policy == "codex-1.4.0-promotion" else None,
        "artifact": {"manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
                     "file_map_sha256": json_sha256(manifest["files"]),
                     "finalized_build_manifest_sha256": manifest["finalized_build_manifest_sha256"],
                     "files": manifest["files"], "site_tree_sha256": site_digest},
    }
    receipt_path = Path(args.output_dir) / "promotion-receipt.json"
    receipt_path.write_text(json.dumps(receipt, sort_keys=True, indent=2) + chr(10), encoding="utf-8")
    receipt_sha = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as stream:
            stream.write(f"receipt_sha256={receipt_sha}\\n")
    return True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-path", default=os.environ.get("GITHUB_EVENT_PATH"))
    parser.add_argument("--event-name", default=os.environ.get("GITHUB_EVENT_NAME"))
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--verify-staged-site", action="store_true")
    parser.add_argument("--site-root")
    parser.add_argument("--receipt")
    args = parser.parse_args()
    if args.verify_staged_site:
        need(args.site_root and args.receipt, "staged-site verification needs site root and receipt")
        verify_staged_site(args.site_root, args.receipt)
        print("verified staged Pages tree")
        return 0
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

