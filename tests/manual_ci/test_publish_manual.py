import base64
import hashlib
import json
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".github" / "scripts"))
import publish_manual as publisher


def make_manifest(files):
    return {
        "schema_version": 1, "repository": publisher.REPOSITORY,
        "producer_workflow": publisher.PRODUCER_WORKFLOW,
        "producer_run_id": 123, "producer_run_attempt": 1,
        "producer_run_head_sha": "b" * 40,
        "pr_number": 42, "pr_head_sha": "a" * 40, "pr_base_ref": "main",
        "tested_commit_sha": "a" * 40, "tested_tree_sha": "c" * 40,
        "finalized_build_manifest_sha256": "d" * 64,
        "validation_scope": "controlled-manual-generation",
        "realtime_qualification": "pending-ci",
        "clock_mode": "controlled-experimental",
        "manual_generation_complete": True, "complete_regression_run": False,
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in files.items()},
    }


def producer_artifact_zip(temp, *, pr_number=42, pr_head_sha="a" * 40,
                          pr_base_ref="main", tree_sha="c" * 40,
                          tested_commit_sha=None, run_attempt=1):
    """Use the real static packager with a mocked successful build audit."""
    sys.path.insert(0, str(ROOT / ".github" / "scripts"))
    import manual_artifact as producer

    repo = Path(temp) / "source"
    evidence = Path(temp) / "evidence"
    repo.mkdir()
    evidence.mkdir()
    fixed = {
        "_config.yml": "exclude: []\n",
        "index.html": '<!doctype html><html><body><a href="manual/index.html">Manual</a></body></html>',

        "README.md": "# Manual\n",
        "cheat_sheet.html": "<!doctype html><html><body>Quick reference</body></html>",
        "config_creator.html": "<!doctype html><html><body>Config</body></html>",
        "manual/index.html": "<!doctype html><html><head><title>Manual</title></head><body>Book</body></html>",
        "manual/manual.css": "body { color: black; }\n",
        "manual/manual.js": "/* browser code */\n",
        "manual/book.js": "/* compiled book */\n",
        "manual/inventory.json": "{}\n",
        "manual/generated/book.json": "{}\n",
        "manual/generated/reader-index.json": json.dumps({"features": [], "navigation": [], "aliases": {}, "scenes": {}, "scene_chunks": {}, "audio_chunks": {}, "audio_examples": [], "learning_path": [], "teaching_contracts": {}, "prelude_receipts": {}}) + "\n",
        "manual/generated/pilot.json": json.dumps({"feature": {}, "audio": {}, "scenes": []}) + "\n",
        "manual/generated/audio-scenes.json": "{}\n",
        "images/logo.svg": '<svg xmlns="http://www.w3.org/2000/svg"></svg>\n',
    }
    for name, data in fixed.items():
        dest = repo / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(data, encoding="utf-8")
    tested_commit_sha = tested_commit_sha or pr_head_sha
    identity = {"schema_version": 1, "commit_sha": tested_commit_sha, "tree_sha": tree_sha}
    identity_path = Path(temp) / "source-identity.json"
    identity_path.write_text(json.dumps(identity), encoding="utf-8")
    build_manifest = {
        "schema_version": 1, "passed": True, "build_complete": False,
        "manual_generation_complete": True, "validation_scope": publisher.SCOPE,
        "realtime_qualification": "pending-ci", "clock_mode": "controlled-experimental",
        "complete_regression_run": False, "revision": tested_commit_sha, "renderer_validated": True,
    }
    (evidence / "manifest.json").write_text(json.dumps(build_manifest), encoding="utf-8")

    def strict_audit(_evidence, require_manual_generation_complete):
        assert require_manual_generation_complete is True
        return {"passed": True, "manual_generation_complete": True,
                "validation_scope": publisher.SCOPE,
                "realtime_qualification": "pending-ci",
                "complete_regression_run": False, "controlled_stages": [], "features": 1}

    out = Path(temp) / "producer-output"
    producer.make_artifact(
        repo, evidence, identity_path, out,
        {"repository": publisher.REPOSITORY, "producer_run_id": 123,
         "producer_run_attempt": run_attempt, "pr_number": pr_number,
         "pr_head_sha": pr_head_sha if pr_number is not None else None,
         "pr_base_ref": pr_base_ref if pr_number is not None else None},
        audit_function=strict_audit,
    )
    archive = Path(temp) / "producer.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for item in sorted(out.rglob("*")):
            if item.is_file():
                zf.write(item, item.relative_to(out).as_posix())
    return archive


class FakeGitHub:
    def __init__(self, _token, repository, *, run, pull, runs, artifact_zip, source_tree="c" * 40,
                 target_sha=None, target_tree=None):
        self.repository = repository
        self.run = run
        self.pull = pull
        self.runs = runs
        self.artifact_zip = Path(artifact_zip)
        self.source_tree = source_tree
        self.target_sha = target_sha
        self.target_tree = target_tree if target_tree is not None else source_tree
        self.tooling_tamper = None
        self.tooling_missing = None
        self.artifact_name = publisher.expected_artifact_name(
            123, 1, 42 if run.get("event") == "pull_request" else None)
        self.calls = []

    def json(self, path):
        self.calls.append(path)
        if "main.yml" in path or "behaviour.yml" in path:
            workflow = ".github/workflows/main.yml" if "main.yml" in path else ".github/workflows/behaviour.yml"
            requested_sha = path.split("head_sha=", 1)[1].split("&", 1)[0]
            return {"workflow_runs": [{"id": 700 if "main.yml" in workflow else 701,
                "head_sha": requested_sha, "path": workflow,
                "status": "completed", "conclusion": "success"}]}
        if path.endswith("/actions/runs/700/jobs?per_page=100"):
            return {"jobs": [{"name": "Run tests on Ubuntu", "status": "completed", "conclusion": "success"}]}
        if path.endswith("/actions/runs/701/jobs?per_page=100"):
            return {"jobs": [{"name": "Complete behaviour coverage", "status": "completed", "conclusion": "success"}]}
        if path.endswith("/actions/runs/123"):
            return self.run
        if path.endswith("/actions/runs/123/artifacts"):
            return {"artifacts": [{"id": 91,
                "name": self.artifact_name,
                "expired": False, "digest": "sha256:" + hashlib.sha256(self.artifact_zip.read_bytes()).hexdigest()}]}
        if "/actions/workflows/manual-build.yml/runs?" in path:
            return self.runs
        if path.endswith("/pulls/42"):
            return self.pull
        if "/commits/" in path:
            commit_sha = path.rsplit("/", 1)[-1]
            if commit_sha == self.target_sha:
                return {"sha": commit_sha, "commit": {"tree": {"sha": self.target_tree}}}
            return {"sha": commit_sha, "commit": {"tree": {"sha": self.source_tree}}}
        if "/contents/" in path:
            relative = path.split("/contents/", 1)[1].split("?ref=", 1)[0]
            if relative == self.tooling_missing:
                return {}
            content = (ROOT / relative).read_bytes()
            if relative == self.tooling_tamper:
                content = content + b"tampered"
            return {"path": relative, "encoding": "base64",
                    "content": base64.b64encode(content).decode("ascii")}
        raise AssertionError("Unexpected GitHub API path: " + path)

    def download(self, path, dest):
        self.calls.append(path)
        self.assert_artifact_path(path)
        shutil.copyfile(self.artifact_zip, dest)

    @staticmethod
    def assert_artifact_path(path):
        if path != f"/repos/{publisher.REPOSITORY}/actions/artifacts/91/zip":
            raise AssertionError("unexpected artifact download API path: " + path)


def api_run(*, event="pull_request", head_sha="b" * 40, pr_head="a" * 40,
            pr_number=42, conclusion="success", branch="feature"):
    return {
        "repository": {"full_name": publisher.REPOSITORY},
        "id": 123, "run_attempt": 1, "run_number": 50,
        "path": publisher.PRODUCER_WORKFLOW, "name": publisher.PRODUCER_NAME,
        "status": "completed", "conclusion": conclusion, "event": event,
        "head_sha": head_sha, "head_branch": branch,
        "pull_requests": ([{"number": pr_number, "head": {"sha": pr_head},
                            "head_repository": {"full_name": "contributor/mosaic"}}]
                          if event == "pull_request" else []),
    }


def api_pull(*, merged=True, base="main", head="a" * 40):
    return {"number": 42, "merged": merged, "base": {"ref": base, "sha": "d" * 40},
            "head": {"sha": head, "repo": {"full_name": "contributor/mosaic"}}}


class PublisherContractTests(unittest.TestCase):
    def test_run_identity_checks_repository_workflow_attempt_and_success(self):
        run = api_run()
        publisher.validate_run(run, repository=publisher.REPOSITORY, run_id=123, attempt=1)
        for delta in ({"repository": {"full_name": "attacker/repo"}},
                      {"path": ".github/workflows/other.yml"},
                      {"run_attempt": 2}, {"conclusion": "failure"}):
            with self.subTest(delta=delta), self.assertRaises(publisher.Reject):
                publisher.validate_run({**run, **delta}, repository=publisher.REPOSITORY,
                                       run_id=123, attempt=1)

    def test_workflow_trigger_and_permissions_are_isolated(self):
        import yaml
        workflow = yaml.load((ROOT / ".github/workflows/manual-publish.yml").read_text(),
                             Loader=yaml.BaseLoader)
        triggers = workflow["on"]
        self.assertEqual(set(triggers), {"workflow_run", "pull_request_target", "workflow_dispatch"})
        self.assertEqual(triggers["workflow_run"]["workflows"], ["Build manual site"])
        self.assertEqual(triggers["pull_request_target"]["types"], ["closed"])
        self.assertNotIn("push", triggers)
        verify = workflow["jobs"]["verify"]
        publish = workflow["jobs"]["publish"]
        self.assertEqual(verify["permissions"], {
            "actions": "read", "contents": "read", "pull-requests": "read"})
        self.assertEqual(publish["permissions"], {
            "pages": "write", "id-token": "write", "actions": "read",
            "contents": "read"})
        checkout = next(s for s in verify["steps"] if s.get("uses", "").startswith("actions/checkout"))
        self.assertEqual(checkout["with"]["ref"], "main")
        self.assertEqual(checkout["with"]["persist-credentials"], "false")
        self.assertNotIn("checkout", [s.get("uses", "").split("@")[0] for s in publish["steps"]])
        self.assertIn(".github/scripts/publish_manual.py",
                      next(s["run"] for s in verify["steps"] if s.get("id") == "verify"))
        self.assertNotIn("manual-build.sh", workflow)

    def test_exact_artifact_names_bind_run_attempt_and_pr(self):
        self.assertEqual(publisher.expected_artifact_name(7, 2, 42),
                         "manual-site-pr-42-run-7-attempt-2")
        self.assertEqual(publisher.expected_artifact_name(7, 2, None),
                         "manual-site-dispatch-run-7-attempt-2")

    def test_manifest_binds_pr_head_not_synthetic_run_head_and_scope(self):
        manifest = make_manifest({"manual-site/index.html": b"ok"})
        run = {"head_sha": "b" * 40}
        args = dict(repository=publisher.REPOSITORY, run=run, run_id=123, attempt=1,
                    pr_number=42, pr_head_sha="a" * 40, pr_base_ref="main",
                    main_tree_sha="c" * 40)
        publisher.validate_manifest(manifest, **args)
        for delta in ({"realtime_qualification": "qualified"},
                      {"manual_generation_complete": False},
                      {"complete_regression_run": True},
                      {"producer_run_id": "123"},
                      {"tested_tree_sha": "e" * 40},
                      {"pr_base_ref": "release"}):
            with self.subTest(delta=delta), self.assertRaises(publisher.Reject):
                publisher.validate_manifest({**manifest, **delta}, **args)

    def test_extracts_static_tree_after_exact_hash_check(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "input.zip"
            files = {"manual-site/index.html": b"<html>ok</html>",
                     "manual-site/app.js": b"static"}
            manifest = make_manifest(files)
            with zipfile.ZipFile(archive, "w") as zf:
                for name, data in files.items():
                    zf.writestr(name, data)
                zf.writestr("manual-artifact-manifest.json", json.dumps(manifest))
            result = publisher.validate_and_extract_zip(archive, Path(temp) / "out")
            self.assertEqual(result, manifest)
            self.assertEqual((Path(temp) / "out/manual-site/index.html").read_bytes(),
                             b"<html>ok</html>")

    def test_rejects_hash_mismatch_and_unlisted_file(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "input.zip"
            files = {"manual-site/index.html": b"<html>ok</html>"}
            manifest = make_manifest(files)
            manifest["files"]["manual-site/index.html"] = "0" * 64
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("manual-site/index.html", b"<html>ok</html>")
                zf.writestr("manual-artifact-manifest.json", json.dumps(manifest))
            with self.assertRaisesRegex(publisher.Reject, "SHA256 mismatch"):
                publisher.validate_and_extract_zip(archive, Path(temp) / "out")
            files["manual-site/extra.txt"] = b"extra"
            manifest = make_manifest({"manual-site/index.html": b"<html>ok</html>"})
            with zipfile.ZipFile(archive, "w") as zf:
                for name, data in files.items():
                    zf.writestr(name, data)
                zf.writestr("manual-artifact-manifest.json", json.dumps(manifest))
            with self.assertRaisesRegex(publisher.Reject, "exactly match"):
                publisher.validate_and_extract_zip(archive, Path(temp) / "out2")

    def test_rejects_traversal_symlink_and_unexpected_root(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "input.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("../outside.txt", b"bad")
            with self.assertRaises(publisher.Reject):
                publisher.validate_and_extract_zip(archive, Path(temp) / "one")
            with zipfile.ZipFile(archive, "w") as zf:
                info = zipfile.ZipInfo("manual-site/link")
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                zf.writestr(info, b"../../outside")
            with self.assertRaisesRegex(publisher.Reject, "symlink"):
                publisher.validate_and_extract_zip(archive, Path(temp) / "two")
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("untrusted/run.sh", b"echo unsafe")
            with self.assertRaisesRegex(publisher.Reject, "unexpected archive root"):
                publisher.validate_and_extract_zip(archive, Path(temp) / "three")

    def test_requires_new_extraction_destination(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "input.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("manual-site/index.html", b"ok")
                zf.writestr("manual-artifact-manifest.json",
                            json.dumps(make_manifest({"manual-site/index.html": b"ok"})))
            destination = Path(temp) / "existing"
            destination.mkdir()
            with self.assertRaisesRegex(publisher.Reject, "must be new"):
                publisher.validate_and_extract_zip(archive, destination)

    def test_api_client_rejects_external_initial_request_urls(self):
        client = publisher.GitHub("test-token", publisher.REPOSITORY)
        with self.assertRaisesRegex(publisher.Reject, "non-API"):
            client.request("https://attacker.invalid/collect")

    def test_build_finishes_before_merge_and_close_event_selects_exact_fork_head_run(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = producer_artifact_zip(temp)
            run = api_run()  # API workflow head_sha is synthetic/different from tested PR head.
            run["pull_requests"][0]["head"]["repo"] = {"full_name": "contributor/mosaic"}
            fake = FakeGitHub("x", publisher.REPOSITORY, run=run, pull=api_pull(),
                              runs={"total_count": 1, "workflow_runs": [run]},
                              artifact_zip=archive)
            out = Path(temp) / "out"
            event = Path(temp) / "event.json"
            event.write_text(json.dumps({"action": "closed", "pull_request": {
                "number": 42, "merged": True}}))
            args = types.SimpleNamespace(event_path=str(event),
                                         event_name="pull_request_target",
                                         output_dir=str(out))
            with patch.object(publisher, "GitHub", return_value=fake), \
                 patch.object(publisher.subprocess, "check_output", return_value="c" * 40 + "\n"), \
                 patch.dict("os.environ", {"GITHUB_TOKEN": "x",
                                           "GITHUB_REPOSITORY": publisher.REPOSITORY}):
                self.assertTrue(publisher.prepare(args))
            self.assertTrue((out / "manual-site/index.html").is_file())
            self.assertIn("/repos/subvertnormality/mosaic/commits/" + "a" * 40, fake.calls)
            self.assertEqual(fake.calls.count("/repos/subvertnormality/mosaic/pulls/42"), 2)

    def test_merge_before_build_skips_close_then_workflow_run_publishes(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = producer_artifact_zip(temp)
            run = api_run()
            fake = FakeGitHub("x", publisher.REPOSITORY, run=run, pull=api_pull(),
                              runs={"total_count": 0, "workflow_runs": []},
                              artifact_zip=archive)
            event = Path(temp) / "event.json"
            event.write_text(json.dumps({"action": "closed", "pull_request": {
                "number": 42, "merged": True}}))
            args = types.SimpleNamespace(event_path=str(event), event_name="pull_request_target",
                                         output_dir=str(Path(temp) / "skip"))
            with patch.object(publisher, "GitHub", return_value=fake), \
                 patch.dict("os.environ", {"GITHUB_TOKEN": "x",
                                           "GITHUB_REPOSITORY": publisher.REPOSITORY}):
                self.assertFalse(publisher.prepare(args))
            event.write_text(json.dumps({"workflow_run": {"id": 123, "run_attempt": 1}}))
            args.event_name = "workflow_run"
            args.output_dir = str(Path(temp) / "later")
            with patch.object(publisher, "GitHub", return_value=fake), \
                 patch.object(publisher.subprocess, "check_output", return_value="c" * 40 + "\n"), \
                 patch.dict("os.environ", {"GITHUB_TOKEN": "x",
                                           "GITHUB_REPOSITORY": publisher.REPOSITORY}):
                self.assertTrue(publisher.prepare(args))

    def test_unmerged_and_nonmain_workflow_runs_do_not_publish(self):
        with tempfile.TemporaryDirectory() as temp:
            run = api_run()
            fake = FakeGitHub("x", publisher.REPOSITORY, run=run,
                              pull=api_pull(merged=False), runs={"workflow_runs": []},
                              artifact_zip=Path(temp) / "unused.zip")
            event = Path(temp) / "event.json"
            event.write_text(json.dumps({"workflow_run": {"id": 123, "run_attempt": 1}}))
            args = types.SimpleNamespace(event_path=str(event), event_name="workflow_run",
                                         output_dir=str(Path(temp) / "out"))
            with patch.object(publisher, "GitHub", return_value=fake), \
                 patch.dict("os.environ", {"GITHUB_TOKEN": "x",
                                           "GITHUB_REPOSITORY": publisher.REPOSITORY}):
                self.assertFalse(publisher.prepare(args))
            fake.pull = api_pull(merged=True, base="release")
            with patch.object(publisher, "GitHub", return_value=fake), \
                 patch.dict("os.environ", {"GITHUB_TOKEN": "x",
                                           "GITHUB_REPOSITORY": publisher.REPOSITORY}):
                self.assertFalse(publisher.prepare(args))

    def test_codex_dispatch_workflow_run_is_a_clean_skip_but_other_branches_still_reject(self):
        for branch, expected in [("codex/1.4.0", False), ("feature", "reject")]:
            with self.subTest(branch=branch), tempfile.TemporaryDirectory() as temp:
                run = api_run(event="workflow_dispatch", head_sha="b" * 40,
                              pr_head="", pr_number=0, branch=branch)
                run["pull_requests"] = []
                fake = FakeGitHub("x", publisher.REPOSITORY, run=run, pull=api_pull(),
                                  runs={"workflow_runs": []},
                                  artifact_zip=Path(temp) / "unused.zip")
                event = Path(temp) / "event.json"
                event.write_text(json.dumps({"workflow_run": {"id": 123, "run_attempt": 1}}))
                args = types.SimpleNamespace(event_path=str(event), event_name="workflow_run",
                                             output_dir=str(Path(temp) / "out"))
                with patch.object(publisher, "GitHub", return_value=fake), \
                     patch.dict("os.environ", {"GITHUB_TOKEN": "x",
                                               "GITHUB_REPOSITORY": publisher.REPOSITORY}):
                    if expected is False:
                        self.assertFalse(publisher.prepare(args))
                    else:
                        with self.assertRaisesRegex(publisher.Reject, "did not run on main"):
                            publisher.prepare(args)

    def test_successful_dispatch_artifact_publishes_only_from_main(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = producer_artifact_zip(temp, pr_number=None)
            run = api_run(event="workflow_dispatch", head_sha="a" * 40,
                          pr_head="", pr_number=0, branch="main")
            run["pull_requests"] = []
            fake = FakeGitHub("x", publisher.REPOSITORY, run=run, pull=api_pull(),
                              runs={"workflow_runs": []}, artifact_zip=archive)
            event = Path(temp) / "event.json"
            event.write_text(json.dumps({"inputs": {"producer_run_id": "123"}}))
            args = types.SimpleNamespace(event_path=str(event), event_name="workflow_dispatch",
                                         output_dir=str(Path(temp) / "out"))
            with patch.object(publisher, "GitHub", return_value=fake), \
                 patch.object(publisher.subprocess, "check_output", return_value="c" * 40 + "\n"), \
                 patch.dict("os.environ", {"GITHUB_TOKEN": "x",
                                           "GITHUB_REPOSITORY": publisher.REPOSITORY,
                                           "GITHUB_REF": "refs/heads/main"}):
                self.assertTrue(publisher.prepare(args))
            self.assertTrue((Path(temp) / "out/manual-site/index.html").is_file())

    def test_dispatch_wrong_branch_and_commit_tree_mismatch_reject(self):
        with tempfile.TemporaryDirectory() as temp:
            run = api_run(event="workflow_dispatch", head_sha="a" * 40,
                          pr_head="", pr_number=0, branch="main")
            run["pull_requests"] = []
            fake = FakeGitHub("x", publisher.REPOSITORY, run=run, pull=api_pull(),
                              runs={"workflow_runs": []}, artifact_zip=Path(temp) / "unused.zip")
            event = Path(temp) / "event.json"
            event.write_text(json.dumps({"inputs": {"producer_run_id": "123"}}))
            args = types.SimpleNamespace(event_path=str(event), event_name="workflow_dispatch",
                                         output_dir=str(Path(temp) / "out"))
            with patch.object(publisher, "GitHub", return_value=fake), \
                 patch.dict("os.environ", {"GITHUB_TOKEN": "x",
                                           "GITHUB_REPOSITORY": publisher.REPOSITORY,
                                           "GITHUB_REF": "refs/heads/feature"}):
                with self.assertRaisesRegex(publisher.Reject, "only from main"):
                    publisher.prepare(args)

            archive = producer_artifact_zip(temp)
            fake = FakeGitHub("x", publisher.REPOSITORY, run=api_run(), pull=api_pull(),
                              runs={"workflow_runs": [api_run()]}, artifact_zip=archive,
                              source_tree="e" * 40)
            event.write_text(json.dumps({"action": "closed", "pull_request": {
                "number": 42, "merged": True}}))
            args.event_name = "pull_request_target"
            args.output_dir = str(Path(temp) / "tree-mismatch")
            with patch.object(publisher, "GitHub", return_value=fake), \
                 patch.object(publisher.subprocess, "check_output", return_value="c" * 40 + "\n"), \
                 patch.dict("os.environ", {"GITHUB_TOKEN": "x",
                                           "GITHUB_REPOSITORY": publisher.REPOSITORY}):
                with self.assertRaisesRegex(publisher.Reject, "commit tree"):
                    publisher.prepare(args)


class CodexPromotionContractTests(unittest.TestCase):
    SOURCE_SHA = "a" * 40
    SOURCE_TREE = "c" * 40
    MAIN_TREE = "d" * 40
    MERGE_SHA = "b" * 40
    PR_HEAD_SHA = "e" * 40
    PR_BASE_SHA = "8" * 40
    TARGET_SHA = "b" * 40

    def promotion_fixture(self, temp, *, artifact_kind="post-merge-dispatch",
                          run_attempt=1, source_sha=None, source_tree=None,
                          artifact_tree=None, target_tree=None, base="codex/1.4.0", merged=True,
                          compare_status="identical", merge_base=None,
                          expected_source_sha=None, branch_sha=None,
                          input_run_id=123, input_attempt=None, input_pr_number=42,
                          input_pr_head_sha=None, input_pr_base_sha=None,
                          pr_head_sha=None, pr_base_sha=None, run_pr_head=None,
                          run_pr_number=None, artifact_pr_number=42,
                          artifact_pr_head=None, artifact_pr_base="codex/1.4.0",
                          pr_head_repo=None, tooling_tamper=None, tooling_missing=None):
        source_sha = source_sha or self.TARGET_SHA
        expected_source_sha = expected_source_sha or source_sha
        source_tree = source_tree or self.SOURCE_TREE
        if artifact_kind == "merged-pr":
            artifact_head = artifact_pr_head or self.PR_HEAD_SHA
            archive = producer_artifact_zip(
                temp, pr_number=artifact_pr_number, pr_head_sha=artifact_head,
                pr_base_ref=artifact_pr_base,
                tree_sha=artifact_tree if artifact_tree is not None else source_tree)
            run = api_run(event="pull_request", head_sha="7" * 40,
                          pr_head=run_pr_head or self.PR_HEAD_SHA,
                          pr_number=run_pr_number if run_pr_number is not None else 42,
                          branch="topic")
        else:
            archive = producer_artifact_zip(
                temp, pr_number=None, tested_commit_sha=source_sha,
                tree_sha=artifact_tree if artifact_tree is not None else self.SOURCE_TREE)
            run = api_run(event="workflow_dispatch", head_sha=source_sha,
                          pr_head="", pr_number=0, branch="codex/1.4.0")
            run["pull_requests"] = []
        run["run_attempt"] = run_attempt
        pull = {
            "number": 42, "merged": merged,
            "base": {"ref": base, "sha": pr_base_sha or self.PR_BASE_SHA},
            "head": {"sha": pr_head_sha or self.PR_HEAD_SHA,
                     "repo": {"full_name": pr_head_repo or publisher.REPOSITORY}},
            "merge_commit_sha": self.MERGE_SHA,
        }
        fake = FakeGitHub("x", publisher.REPOSITORY, run=run, pull=pull,
                          runs={"workflow_runs": []}, artifact_zip=archive,
                          source_tree=source_tree, target_sha=expected_source_sha,
                          target_tree=target_tree if target_tree is not None else source_tree)
        fake.artifact_name = publisher.expected_artifact_name(
            123, run_attempt, 42 if artifact_kind == "merged-pr" else None)
        fake.tooling_tamper = tooling_tamper
        fake.tooling_missing = tooling_missing
        original_json = fake.json
        def fake_json(path):
            if "/actions/runs/" in path and path.rsplit("/", 1)[-1].isdigit():
                fake.calls.append(path)
                return run
            if "/compare/" in path:
                fake.calls.append(path)
                return {"status": compare_status,
                        "merge_base_commit": {"sha": merge_base or self.MERGE_SHA},
                        "head_commit": {"sha": expected_source_sha}}
            if path.endswith("/git/ref/heads/codex/1.4.0"):
                fake.calls.append(path)
                return {"object": {"sha": branch_sha or expected_source_sha}}
            if "/pulls/" in path:
                fake.calls.append(path)
                return pull
            return original_json(path)
        fake.json = fake_json
        event = Path(temp) / "event.json"
        event.write_text(json.dumps({"inputs": {
            "publication_policy": "codex-1.4.0-promotion",
            "promotion_artifact_kind": artifact_kind,
            "producer_run_id": str(input_run_id),
            "producer_run_attempt": str(input_attempt if input_attempt is not None else run_attempt),
            "promotion_pr_number": str(input_pr_number),
            "expected_source_sha": expected_source_sha,
            "promotion_pr_head_sha": input_pr_head_sha or self.PR_HEAD_SHA,
            "promotion_pr_base_sha": input_pr_base_sha or self.PR_BASE_SHA,
        }}))
        args = types.SimpleNamespace(event_path=str(event), event_name="workflow_dispatch",
                                     output_dir=str(Path(temp) / "verified"))
        return archive, run, pull, fake, args

    def execute_promotion(self, temp, **fixture_options):
        archive, run, pull, fake, args = self.promotion_fixture(temp, **fixture_options)
        with patch.object(publisher, "GitHub", return_value=fake), \
             patch.object(publisher.subprocess, "check_output", side_effect=["f" * 40 + chr(10), self.MAIN_TREE + chr(10)]), \
             patch.dict("os.environ", {"GITHUB_TOKEN": "x", "GITHUB_REPOSITORY": publisher.REPOSITORY,
                                       "GITHUB_REF": "refs/heads/main"}):
            result = publisher.prepare(args)
        return result, archive, run, pull, fake, args

    def test_codex_promotion_accepts_only_explicit_merged_run_and_preserves_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            result, archive, run, pull, fake, args = self.execute_promotion(temp)
            self.assertTrue(result)
            site = Path(args.output_dir) / "manual-site"
            with zipfile.ZipFile(archive) as zf:
                expected_site = {name: zf.read(name) for name in zf.namelist()
                                 if name.startswith("manual-site/") and not name.endswith("/")}
                manifest_bytes = zf.read("manual-artifact-manifest.json")
            self.assertEqual({p.relative_to(args.output_dir).as_posix(): p.read_bytes()
                              for p in site.rglob("*") if p.is_file()}, expected_site)
            self.assertEqual((Path(args.output_dir) / "manual-artifact-manifest.json").read_bytes(),
                             manifest_bytes)
            receipt = json.loads((Path(args.output_dir) / "promotion-receipt.json").read_text())
            self.assertEqual(receipt["publication_policy"], "codex-1.4.0-promotion")
            self.assertEqual(receipt["publisher"], {"repository": publisher.REPOSITORY,
                "commit_sha": "f" * 40, "tree_sha": self.MAIN_TREE})
            self.assertEqual(receipt["producer"], {"repository": publisher.REPOSITORY,
                "workflow_path": publisher.PRODUCER_WORKFLOW, "workflow_name": publisher.PRODUCER_NAME,
                "run_id": 123, "run_attempt": 1, "event": "workflow_dispatch",
                "head_branch": "codex/1.4.0", "run_head_sha": self.TARGET_SHA,
                "source_commit_sha": self.TARGET_SHA,
                "source_tree_sha": self.SOURCE_TREE, "artifact_id": 91,
                "artifact_name": "manual-site-dispatch-run-123-attempt-1",
                "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest()})
            self.assertEqual(receipt["promotion"], {"artifact_kind": "post-merge-dispatch",
                "pr_number": 42, "base_ref": "codex/1.4.0", "base_sha": self.PR_BASE_SHA,
                "head_sha": self.PR_HEAD_SHA, "merge_commit_sha": self.MERGE_SHA,
                "source_commit_sha": self.TARGET_SHA, "source_tree_sha": self.SOURCE_TREE})
            self.assertEqual(receipt["artifact"]["manifest_sha256"], hashlib.sha256(manifest_bytes).hexdigest())
            files = json.loads(manifest_bytes)["files"]
            map_bytes = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
            self.assertEqual(receipt["artifact"]["file_map_sha256"], hashlib.sha256(map_bytes).hexdigest())
            self.assertEqual(receipt["artifact"]["files"], files)
            self.assertIn("/repos/subvertnormality/mosaic/compare/" + self.MERGE_SHA + "..." + self.TARGET_SHA,
                          fake.calls)
            self.assertIn("/repos/subvertnormality/mosaic/commits/" + self.TARGET_SHA, fake.calls)

    def test_codex_promotion_rejects_wrong_attempt_source_pr_base_and_ancestry(self):
        cases = [
            ({"run_attempt": 2}, "attempt"),
            ({"input_attempt": 2}, "attempt"),
            ({"input_run_id": 124}, "run ID"),
            ({"input_pr_number": 43}, "PR number"),
            ({"input_pr_head_sha": "9" * 40}, "PR head SHA"),
            ({"input_pr_base_sha": "9" * 40}, "PR base SHA"),
            ({"pr_head_sha": "9" * 40}, "PR head SHA"),
            ({"pr_base_sha": "9" * 40}, "PR base SHA"),
            ({"expected_source_sha": "9" * 40}, "exact named PR merge commit"),
            ({"base": "main"}, "base"),
            ({"merged": False}, "merged"),
            ({"compare_status": "diverged"}, "exactly the named PR merge commit"),
            ({"merge_base": "8" * 40}, "merge base"),
            ({"source_tree": "7" * 40, "artifact_tree": "c" * 40}, "commit tree"),
            ({"branch_sha": "6" * 40}, "branch ref"),
        ]
        for options, message in cases:
            with self.subTest(options=options), tempfile.TemporaryDirectory() as temp:
                archive, run, pull, fake, args = self.promotion_fixture(temp, **options)
                with patch.object(publisher, "GitHub", return_value=fake), \
                     patch.object(publisher.subprocess, "check_output", side_effect=["f" * 40 + chr(10), self.MAIN_TREE + chr(10)]), \
                     patch.dict("os.environ", {"GITHUB_TOKEN": "x", "GITHUB_REPOSITORY": publisher.REPOSITORY,
                                               "GITHUB_REF": "refs/heads/main"}):
                    with self.assertRaisesRegex(publisher.Reject, message):
                        publisher.prepare(args)


    def test_merged_pr_promotion_reuses_original_pr_artifact_and_preserves_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            result, archive, run, pull, fake, args = self.execute_promotion(
                temp, artifact_kind="merged-pr")
            self.assertTrue(result)
            with zipfile.ZipFile(archive) as zf:
                manifest_bytes = zf.read("manual-artifact-manifest.json")
                expected_site = {name: zf.read(name) for name in zf.namelist()
                                 if name.startswith("manual-site/") and not name.endswith("/")}
            out = Path(args.output_dir)
            self.assertEqual((out / "manual-artifact-manifest.json").read_bytes(), manifest_bytes)
            self.assertEqual({p.relative_to(out).as_posix(): p.read_bytes()
                              for p in (out / "manual-site").rglob("*") if p.is_file()},
                             expected_site)
            manifest = json.loads(manifest_bytes)
            self.assertEqual((manifest["pr_number"], manifest["pr_head_sha"],
                              manifest["pr_base_ref"], manifest["tested_commit_sha"],
                              manifest["tested_tree_sha"]),
                             (42, self.PR_HEAD_SHA, "codex/1.4.0",
                              self.PR_HEAD_SHA, self.SOURCE_TREE))
            receipt = json.loads((out / "promotion-receipt.json").read_text())
            self.assertEqual(receipt["producer"]["event"], "pull_request")
            self.assertEqual(receipt["producer"]["run_head_sha"], "7" * 40)
            self.assertEqual(receipt["producer"]["source_commit_sha"], self.PR_HEAD_SHA)
            self.assertEqual(receipt["producer"]["artifact_name"],
                             "manual-site-pr-42-run-123-attempt-1")
            self.assertEqual(receipt["producer_tooling"]["version"],
                             publisher.PRODUCER_TOOLING_POLICY_VERSION)
            self.assertEqual(receipt["producer_tooling"]["files"],
                             publisher.PRODUCER_TOOLING_ALLOWLISTS[publisher.PRODUCER_TOOLING_POLICY_VERSION])
            self.assertEqual(receipt["promotion"], {
                "artifact_kind": "merged-pr", "pr_number": 42,
                "base_ref": "codex/1.4.0", "base_sha": self.PR_BASE_SHA,
                "head_sha": self.PR_HEAD_SHA, "merge_commit_sha": self.MERGE_SHA,
                "source_commit_sha": self.TARGET_SHA,
                "source_tree_sha": self.SOURCE_TREE})
            for tooling_path in publisher.PRODUCER_TOOLING_ALLOWLISTS[
                    publisher.PRODUCER_TOOLING_POLICY_VERSION]:
                self.assertIn(f"/repos/{publisher.REPOSITORY}/contents/{tooling_path}?ref={self.PR_HEAD_SHA}",
                              fake.calls)
            self.assertIn("/repos/subvertnormality/mosaic/commits/" + self.PR_HEAD_SHA,
                          fake.calls)
            self.assertIn("/repos/subvertnormality/mosaic/commits/" + self.TARGET_SHA,
                          fake.calls)
            self.assertIn("/repos/subvertnormality/mosaic/actions/artifacts/91/zip",
                          fake.calls)

    def test_merged_pr_promotion_rejects_stale_or_mismatched_identity_and_tree(self):
        cases = [
            ({"input_pr_number": 43}, "PR number"),
            ({"input_pr_head_sha": "9" * 40}, "PR head SHA"),
            ({"input_pr_base_sha": "9" * 40}, "PR base SHA"),
            ({"pr_head_sha": "9" * 40}, "PR head SHA"),
            ({"pr_base_sha": "9" * 40}, "PR base SHA"),
            ({"run_pr_number": 43}, "associated with the exact merged PR head"),
            ({"run_pr_head": "9" * 40}, "associated with the exact merged PR head"),
            ({"pr_head_repo": "contributor/mosaic"}, "from a same-repository branch, not a fork"),
            ({"artifact_pr_number": 43}, "PR number mismatch"),
            ({"artifact_pr_head": "9" * 40}, "tested commit does not equal the exact PR head"),
            ({"artifact_pr_base": "main"}, "PR base mismatch"),
            ({"target_tree": "9" * 40}, "both the tested commit and merged codex source"),
            ({"branch_sha": "9" * 40}, "branch ref"),
            ({"base": "main"}, "base is not codex/1.4.0"),
            ({"merged": False}, "not merged"),
            ({"compare_status": "diverged"}, "exactly the named PR merge commit"),
            ({"merge_base": "9" * 40}, "merge base"),
            ({"run_attempt": 2}, "attempt"),
            ({"tooling_tamper": ".github/workflows/manual-build.yml"}, "trusted release allowlist"),
            ({"tooling_tamper": ".github/scripts/manual-build.sh"}, "trusted release allowlist"),
            ({"tooling_tamper": ".github/scripts/manual_artifact.py"}, "trusted release allowlist"),
            ({"tooling_missing": ".github/scripts/manual-build.sh"}, "producer tooling response is invalid"),
        ]
        for options, message in cases:
            with self.subTest(options=options), tempfile.TemporaryDirectory() as temp:
                archive, run, pull, fake, args = self.promotion_fixture(
                    temp, artifact_kind="merged-pr", **options)
                with patch.object(publisher, "GitHub", return_value=fake), \
                     patch.object(publisher.subprocess, "check_output",
                                  side_effect=["f" * 40 + chr(10), self.MAIN_TREE + chr(10)]), \
                     patch.dict("os.environ", {"GITHUB_TOKEN": "x", "GITHUB_REPOSITORY": publisher.REPOSITORY,
                                               "GITHUB_REF": "refs/heads/main"}):
                    with self.assertRaisesRegex(publisher.Reject, message):
                        publisher.prepare(args)

    def test_codex_promotion_consumer_must_run_from_trusted_main(self):
        with tempfile.TemporaryDirectory() as temp:
            _archive, _run, _pull, fake, args = self.promotion_fixture(temp)
            with patch.object(publisher, "GitHub", return_value=fake),                  patch.dict("os.environ", {"GITHUB_TOKEN": "x",
                                           "GITHUB_REPOSITORY": publisher.REPOSITORY,
                                           "GITHUB_REF": "refs/heads/codex/1.4.0"}):
                with self.assertRaisesRegex(publisher.Reject, "trusted main"):
                    publisher.prepare(args)

    def test_workflow_keeps_main_trust_and_separate_deploy_privileges(self):
        import yaml
        workflow = yaml.load((ROOT / ".github/workflows/manual-publish.yml").read_text(),
                             Loader=yaml.BaseLoader)
        inputs = workflow["on"]["workflow_dispatch"]["inputs"]
        self.assertIn("publication_policy", inputs)
        self.assertEqual(inputs["publication_policy"]["default"], "main-edition")
        self.assertIn("promotion_artifact_kind", inputs)
        self.assertEqual(inputs["promotion_artifact_kind"]["default"], "merged-pr")
        for name in ("producer_run_attempt", "promotion_pr_number",
                     "expected_source_sha", "promotion_pr_head_sha",
                     "promotion_pr_base_sha"):
            self.assertIn(name, inputs)
        verify = workflow["jobs"]["verify"]
        publish = workflow["jobs"]["publish"]
        self.assertEqual(verify["permissions"], {
            "actions": "read", "contents": "read", "pull-requests": "read"})
        self.assertEqual(publish["permissions"], {
            "pages": "write", "id-token": "write", "actions": "read",
            "contents": "read"})
        checkout = next(s for s in verify["steps"] if s.get("uses", "").startswith("actions/checkout"))
        self.assertEqual(checkout["with"]["ref"], "main")
        self.assertEqual(checkout["with"]["persist-credentials"], "false")
        trusted_checkout = next(s for s in publish["steps"] if s.get("uses", "").startswith("actions/checkout"))
        self.assertEqual(trusted_checkout["with"]["ref"], "main")
        self.assertEqual(trusted_checkout["with"]["persist-credentials"], "false")
        self.assertTrue(any("Verify receipt bytes and exact transferred site tree" == s.get("name")
                            for s in publish["steps"]))
        downloads = [s for s in publish["steps"] if s.get("uses", "").startswith("actions/download-artifact")]
        self.assertEqual([s["with"]["name"] for s in downloads], ["verified-manual-site", "manual-publication-receipt"])
        uploads = [s for s in verify["steps"] if s.get("uses", "").startswith("actions/upload-artifact")]
        self.assertTrue(any(s.get("with", {}).get("name") == "manual-publication-receipt"
                            for s in uploads))
        pages_path = chr(36) + "{{ runner.temp }}/verified/manual-site/"
        self.assertTrue(any(s.get("with", {}).get("name") == "verified-manual-site"
                            and s.get("with", {}).get("path") == pages_path
                            for s in uploads))

    def test_staged_tree_digest_rejects_changed_added_and_missing_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            site = root / "site"
            site.mkdir()
            (site / "index.html").write_text("manual")
            (site / "manual.js").write_text("reader")
            rows = publisher.canonical_site_tree(site)
            receipt = root / "receipt.json"
            receipt.write_text(json.dumps({"artifact": {"site_tree_sha256": publisher.site_tree_sha256(rows)}}))
            self.assertEqual(publisher.verify_staged_site(site, receipt), publisher.site_tree_sha256(rows))
            for mutation in ("changed", "added", "missing"):
                with self.subTest(mutation=mutation):
                    if mutation == "changed":
                        (site / "manual.js").write_text("tampered")
                    elif mutation == "added":
                        (site / "extra.txt").write_text("extra")
                    else:
                        (site / "manual.js").unlink()
                    with self.assertRaisesRegex(publisher.Reject, "transferred Pages tree"):
                        publisher.verify_staged_site(site, receipt)
                    if mutation == "changed":
                        (site / "manual.js").write_text("reader")
                    elif mutation == "added":
                        (site / "extra.txt").unlink()
                    else:
                        (site / "manual.js").write_text("reader")

    def test_api_digest_is_compared_with_downloaded_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "producer.zip"
            archive.write_bytes(b"exact artifact bytes")
            expected = "sha256:" + hashlib.sha256(archive.read_bytes()).hexdigest()
            self.assertEqual(publisher.verify_api_zip_digest(expected, archive), expected[7:])
            with self.assertRaisesRegex(publisher.Reject, "API digest"):
                publisher.verify_api_zip_digest("sha256:" + "0" * 64, archive)
            with self.assertRaisesRegex(publisher.Reject, "missing or malformed"):
                publisher.verify_api_zip_digest(None, archive)

    def test_required_ci_fails_closed_for_a_missing_aggregate_job(self):
        class CI:
            def json(self, path):
                if "/workflows/" in path:
                    workflow = ".github/workflows/behaviour.yml" if "behaviour.yml" in path else ".github/workflows/main.yml"
                    return {"workflow_runs": [{"id": 9, "head_sha": "a" * 40, "path": workflow,
                                               "status": "completed", "conclusion": "success"}]}
                return {"jobs": [{"name": "partial shard", "status": "completed", "conclusion": "success"}]}
        with self.assertRaisesRegex(publisher.Reject, "required source-bound CI"):
            publisher.validate_required_ci(CI(), "a" * 40)


class PR98MergedMainPromotionTests(unittest.TestCase):
    PR_HEAD = "a" * 40
    PR_BASE = "b" * 40
    MERGE = "c" * 40
    MAIN = "d" * 40
    TREE = "e" * 40

    class GitHub:
        def __init__(self, archive, *, run=None, pull=None, input_options=None,
                     merge_sha=None, main_tree=None, compare_status="ahead",
                     merge_base=None, main_sha=None, pr_number=98):
            self.archive = Path(archive)
            self.run = run
            self.pull = pull
            self.input_options = input_options or {}
            self.merge_sha = merge_sha or PR98MergedMainPromotionTests.MERGE
            self.main_tree = main_tree or PR98MergedMainPromotionTests.TREE
            self.compare_status = compare_status
            self.merge_base = merge_base or self.merge_sha
            self.main_sha = main_sha or PR98MergedMainPromotionTests.MAIN
            self.pr_number = pr_number
            self.calls = []
            self.downloaded = []

        def json(self, path):
            self.calls.append(path)
            if path.endswith("/actions/runs/123"):
                return self.run
            if path.endswith("/actions/runs/123/artifacts"):
                return {"artifacts": [{"id": 91,
                    "name": "manual-site-pr-98-run-123-attempt-2", "expired": False,
                    "digest": "sha256:" + hashlib.sha256(self.archive.read_bytes()).hexdigest()}]}
            if path.endswith("/pulls/98"):
                return self.pull
            if path.endswith("/git/ref/heads/main"):
                return {"object": {"sha": self.main_sha}}
            if path.endswith("/actions/runs/700/jobs?per_page=100"):
                return {"jobs": [{"name": "Run tests on Ubuntu", "status": "completed", "conclusion": "success"}]}
            if path.endswith("/actions/runs/701/jobs?per_page=100"):
                return {"jobs": [{"name": "Complete behaviour coverage", "status": "completed", "conclusion": "success"}]}
            if "/actions/workflows/" in path:
                workflow = ".github/workflows/behaviour.yml" if "behaviour.yml" in path else ".github/workflows/main.yml"
                requested_sha = path.split("head_sha=", 1)[1].split("&", 1)[0]
                return {"workflow_runs": [{"id": 701 if "behaviour.yml" in workflow else 700,
                    "head_sha": requested_sha, "path": workflow, "status": "completed", "conclusion": "success"}]}
            if "/compare/" in path:
                if path.endswith("/compare/" + PR98MergedMainPromotionTests.PR_BASE + "..." + self.merge_sha):
                    return {"status": "ahead", "merge_base_commit": {"sha": self.merge_base},
                            "head_commit": {"sha": self.merge_sha}}
                return {"status": self.compare_status,
                        "merge_base_commit": {"sha": self.merge_base},
                        "head_commit": {"sha": self.main_sha}}
            if "/commits/" in path:
                sha = path.rsplit("/", 1)[-1]
                tree = self.main_tree
                if sha == PR98MergedMainPromotionTests.PR_HEAD:
                    tree = PR98MergedMainPromotionTests.TREE
                elif sha == self.merge_sha:
                    tree = self.main_tree
                return {"sha": sha, "commit": {"tree": {"sha": tree},
                        "parents": [{"sha": PR98MergedMainPromotionTests.PR_BASE}]}}
            if "/contents/" in path:
                rel = path.split("/contents/", 1)[1].split("?ref=", 1)[0]
                return {"path": rel, "encoding": "base64",
                        "content": base64.b64encode((ROOT / rel).read_bytes()).decode("ascii")}
            raise AssertionError("Unexpected GitHub API path: " + path)

        def download(self, path, dest):
            self.downloaded.append(path)
            self.assert_artifact_path(path)
            shutil.copyfile(self.archive, dest)

        @staticmethod
        def assert_artifact_path(path):
            if path != f"/repos/{publisher.REPOSITORY}/actions/artifacts/91/zip":
                raise AssertionError("unexpected artifact download API path: " + path)

    def fixture(self, temp, *, policy="pr98-merged-main-promotion", input_pr_number=98,
                artifact_kind="merged-pr", run_attempt=2, input_attempt=2,
                run_event="pull_request", run_pr_number=98, run_pr_head=None,
                run_base_ref="main", run_base_sha=None, merged=True, pull_number=98,
                pull_base="main", pull_head=None, pull_repo=None, pull_merge_sha=None,
                expected_merge=None, target_tree=None, current_main_tree=None,
                compare_status="ahead", merge_base=None, main_sha=None):
        archive = producer_artifact_zip(temp, pr_number=98, pr_head_sha=self.PR_HEAD,
            pr_base_ref="main", tree_sha=target_tree or self.TREE,
            tested_commit_sha=self.PR_HEAD, run_attempt=2)
        run = api_run(event=run_event, head_sha="f" * 40, pr_head=self.PR_HEAD,
                      pr_number=run_pr_number, branch="codex/1.4.0")
        run["run_attempt"] = run_attempt
        run["pull_requests"] = ([{"number": run_pr_number,
            "head": {"sha": run_pr_head or self.PR_HEAD},
            "base": {"ref": run_base_ref, "sha": run_base_sha or self.PR_BASE}}]
            if run_event == "pull_request" else [])
        pull = {"number": pull_number, "merged": merged,
            "base": {"ref": pull_base, "sha": self.MAIN},
            "head": {"sha": pull_head or self.PR_HEAD,
                     "repo": {"full_name": pull_repo or publisher.REPOSITORY}},
            "merge_commit_sha": pull_merge_sha or self.MERGE}
        fake = self.GitHub(archive, run=run, pull=pull,
            merge_sha=self.MERGE, main_tree=current_main_tree or target_tree or self.TREE,
            compare_status=compare_status, merge_base=merge_base or self.MERGE,
            main_sha=main_sha or self.MAIN)
        event = Path(temp) / "pr98-promotion-event.json"
        event.write_text(json.dumps({"inputs": {
            "publication_policy": policy,
            "promotion_artifact_kind": artifact_kind,
            "producer_run_id": "123",
            "producer_run_attempt": str(input_attempt),
            "promotion_pr_number": str(input_pr_number),
            "promotion_merge_commit_sha": expected_merge or self.MERGE,
            "promotion_pr_head_sha": self.PR_HEAD,
            "promotion_pr_base_sha": self.PR_BASE,
        }}))
        args = types.SimpleNamespace(event_path=str(event), event_name="workflow_dispatch",
                                    output_dir=str(Path(temp) / "verified-pr98"))
        return fake, args, archive

    def execute(self, temp, **options):
        fake, args, archive = self.fixture(temp, **options)
        with patch.object(publisher, "GitHub", return_value=fake), \
             patch.object(publisher.subprocess, "check_output",
                          side_effect=["9" * 40 + chr(10), self.TREE + chr(10)]), \
             patch.dict("os.environ", {"GITHUB_TOKEN": "x",
                 "GITHUB_REPOSITORY": publisher.REPOSITORY,
                 "GITHUB_REF": "refs/heads/main"}):
            result = publisher.prepare(args)
        return result, fake, args, archive

    def test_promotes_exact_pr98_ci_artifact_against_merged_main_tree(self):
        with tempfile.TemporaryDirectory() as temp:
            result, fake, args, archive = self.execute(temp)
            self.assertTrue(result)
            receipt = json.loads((Path(args.output_dir) / "promotion-receipt.json").read_text())
            self.assertEqual(receipt["publication_policy"], "pr98-merged-main-promotion")
            self.assertEqual(receipt["producer"]["run_id"], 123)
            self.assertEqual(receipt["producer"]["run_attempt"], 2)
            self.assertEqual(receipt["producer"]["artifact_name"],
                             "manual-site-pr-98-run-123-attempt-2")
            self.assertEqual(receipt["producer"]["source_commit_sha"], self.PR_HEAD)
            self.assertEqual(receipt["promotion"], {
                "artifact_kind": "merged-pr", "pr_number": 98, "base_ref": "main",
                "base_sha": self.PR_BASE, "head_sha": self.PR_HEAD,
                "merge_commit_sha": self.MERGE, "source_commit_sha": self.MERGE,
                "source_tree_sha": self.TREE})
            self.assertEqual(fake.downloaded,
                [f"/repos/{publisher.REPOSITORY}/actions/artifacts/91/zip"])
            self.assertIn(f"/repos/{publisher.REPOSITORY}/pulls/98", fake.calls)
            self.assertIn(f"/repos/{publisher.REPOSITORY}/git/ref/heads/main", fake.calls)

    def test_rejects_wrong_release_identity_or_rebuild_kind(self):
        cases = [
            ({"input_pr_number": 106}, "only PR 98"),
            ({"pull_number": 106}, "PR number mismatch"),
            ({"pull_base": "codex/1.4.0"}, "base is not main"),
            ({"merged": False}, "not merged"),
            ({"pull_repo": "contributor/mosaic"}, "must come from this repository"),
            ({"artifact_kind": "post-merge-dispatch"}, "requires the original merged-PR artifact"),
            ({"run_event": "workflow_dispatch"}, "exact pull_request producer run"),
            ({"expected_merge": "9" * 40}, "exact merged PR 98 commit"),
        ]
        for options, message in cases:
            with self.subTest(options=options), tempfile.TemporaryDirectory() as temp:
                fake, args, _archive = self.fixture(temp, **options)
                with patch.object(publisher, "GitHub", return_value=fake), \
                     patch.object(publisher.subprocess, "check_output",
                                  side_effect=["9" * 40 + chr(10), self.TREE + chr(10)]), \
                     patch.dict("os.environ", {"GITHUB_TOKEN": "x",
                         "GITHUB_REPOSITORY": publisher.REPOSITORY,
                         "GITHUB_REF": "refs/heads/main"}):
                    with self.assertRaisesRegex(publisher.Reject, message):
                        publisher.prepare(args)

    def test_rejects_stale_run_attempt_base_and_wrong_pr_head(self):
        cases = [
            ({"run_attempt": 3}, "attempt"),
            ({"input_attempt": 3}, "attempt"),
            ({"run_base_sha": "9" * 40}, "exact PR 98 base"),
            ({"run_base_ref": "codex/1.4.0"}, "exact PR 98 base"),
            ({"run_pr_number": 106}, "associated with PR 98 and the exact head"),
            ({"run_pr_head": "9" * 40}, "associated with PR 98 and the exact head"),
            ({"pull_head": "9" * 40}, "exact PR head SHA"),
        ]
        for options, message in cases:
            with self.subTest(options=options), tempfile.TemporaryDirectory() as temp:
                fake, args, _archive = self.fixture(temp, **options)
                with patch.object(publisher, "GitHub", return_value=fake), \
                     patch.object(publisher.subprocess, "check_output",
                                  side_effect=["9" * 40 + chr(10), self.TREE + chr(10)]), \
                     patch.dict("os.environ", {"GITHUB_TOKEN": "x",
                         "GITHUB_REPOSITORY": publisher.REPOSITORY,
                         "GITHUB_REF": "refs/heads/main"}):
                    with self.assertRaisesRegex(publisher.Reject, message):
                        publisher.prepare(args)

    def test_rejects_changed_merged_tree_or_main_moved_off_merge(self):
        cases = [
            ({"target_tree": "9" * 40}, "tested commit tree differs from the artifact source identity"),
            ({"current_main_tree": "9" * 40}, "trusted main checkout tree does not match the PR 98 merged tree"),
            ({"compare_status": "diverged"}, "PR 98 merge is not an ancestor of current main"),
            ({"merge_base": "9" * 40}, "PR 98 merge is not an ancestor of current main"),
        ]
        for options, message in cases:
            with self.subTest(options=options), tempfile.TemporaryDirectory() as temp:
                fake, args, _archive = self.fixture(temp, **options)
                with patch.object(publisher, "GitHub", return_value=fake), \
                     patch.object(publisher.subprocess, "check_output",
                                  side_effect=["9" * 40 + chr(10), self.TREE + chr(10)]), \
                     patch.dict("os.environ", {"GITHUB_TOKEN": "x",
                         "GITHUB_REPOSITORY": publisher.REPOSITORY,
                         "GITHUB_REF": "refs/heads/main"}):
                    with self.assertRaisesRegex(publisher.Reject, message):
                        publisher.prepare(args)

    def test_workflow_exposes_pr98_promotion_and_pages_read_permissions(self):
        import yaml
        workflow = yaml.load((ROOT / ".github/workflows/manual-publish.yml").read_text(),
                             Loader=yaml.BaseLoader)
        inputs = workflow["on"]["workflow_dispatch"]["inputs"]
        self.assertEqual(inputs["publication_policy"]["default"], "main-edition")
        self.assertIn("pr98-merged-main-promotion", inputs["publication_policy"]["options"])
        self.assertIn("promotion_merge_commit_sha", inputs)
        self.assertEqual(workflow["jobs"]["publish"]["permissions"], {
            "actions": "read", "contents": "read", "id-token": "write", "pages": "write"})


if __name__ == "__main__":
    unittest.main()

