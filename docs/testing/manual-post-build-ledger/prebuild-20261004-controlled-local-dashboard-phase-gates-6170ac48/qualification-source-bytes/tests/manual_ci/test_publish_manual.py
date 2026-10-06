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


def producer_artifact_zip(temp, *, pr_number=42):
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
        "manual/generated/pilot.json": "{}\n",
        "manual/generated/audio-scenes.json": "{}\n",
        "images/logo.svg": '<svg xmlns="http://www.w3.org/2000/svg"></svg>\n',
    }
    for name, data in fixed.items():
        dest = repo / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(data, encoding="utf-8")
    identity = {"schema_version": 1, "commit_sha": "a" * 40, "tree_sha": "c" * 40}
    identity_path = Path(temp) / "source-identity.json"
    identity_path.write_text(json.dumps(identity), encoding="utf-8")
    build_manifest = {
        "schema_version": 1, "passed": True, "build_complete": False,
        "manual_generation_complete": True, "validation_scope": publisher.SCOPE,
        "realtime_qualification": "pending-ci", "clock_mode": "controlled-experimental",
        "complete_regression_run": False, "revision": "a" * 40, "renderer_validated": True,
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
         "producer_run_attempt": 1, "pr_number": pr_number,
         "pr_head_sha": "a" * 40 if pr_number is not None else None,
         "pr_base_ref": "main" if pr_number is not None else None},
        audit_function=strict_audit,
    )
    archive = Path(temp) / "producer.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for item in sorted(out.rglob("*")):
            if item.is_file():
                zf.write(item, item.relative_to(out).as_posix())
    return archive


class FakeGitHub:
    def __init__(self, _token, repository, *, run, pull, runs, artifact_zip, source_tree="c" * 40):
        self.repository = repository
        self.run = run
        self.pull = pull
        self.runs = runs
        self.artifact_zip = Path(artifact_zip)
        self.source_tree = source_tree
        self.artifact_name = publisher.expected_artifact_name(
            123, 1, 42 if run.get("event") == "pull_request" else None)
        self.calls = []

    def json(self, path):
        self.calls.append(path)
        if path.endswith("/actions/runs/123"):
            return self.run
        if path.endswith("/actions/runs/123/artifacts"):
            return {"artifacts": [{"id": 91,
                "name": self.artifact_name,
                "expired": False}]}
        if "/actions/workflows/manual-build.yml/runs?" in path:
            return self.runs
        if path.endswith("/pulls/42"):
            return self.pull
        if path.endswith("/commits/" + "a" * 40):
            return {"sha": "a" * 40,
                    "commit": {"tree": {"sha": self.source_tree}}}
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
            "pages": "write", "id-token": "write", "actions": "read"})
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


if __name__ == "__main__":
    unittest.main()

