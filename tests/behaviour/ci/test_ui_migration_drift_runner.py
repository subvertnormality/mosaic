import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).with_name("run-ui-migration-drift.py")
SPEC = importlib.util.spec_from_file_location("ui_migration_drift_runner", SCRIPT)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class DriftRunnerTests(unittest.TestCase):
    def test_workflow_dispatch_drift_job_isolated_from_other_modes(self):
        workflow = (SCRIPT.parents[3] / ".github/workflows/behaviour.yml").read_text(
            encoding="utf-8")
        self.assertIn("ui_migration_drift:", workflow)
        self.assertIn("ui_migration_drift_sha:", workflow)
        self.assertIn(
            "if: ${{ !inputs.ui_migration_targeted && !inputs.ui_migration_drift }}",
            workflow)
        self.assertEqual(workflow.count(
            "if: ${{ !inputs.ui_migration_targeted && !inputs.ui_migration_drift }}"), 4)
        self.assertIn("always() && !inputs.ui_migration_targeted && !inputs.ui_migration_drift",
                      workflow)
        self.assertIn(
            "if: ${{ github.event_name == 'workflow_dispatch' && inputs.ui_migration_targeted && !inputs.ui_migration_drift }}",
            workflow)
        self.assertIn(
            "if: ${{ github.event_name == 'workflow_dispatch' && inputs.ui_migration_drift }}",
            workflow)
        self.assertIn("name: ui-migration-drift-${{ github.run_id }}", workflow)
        self.assertIn("/tmp/mosaic-ui-drift/standalone/**", workflow)
        self.assertIn("/tmp/mosaic-ui-drift/control/**", workflow)
        self.assertIn("/tmp/mosaic-ui-drift/control-logs/**", workflow)
        self.assertIn("/tmp/mosaic-ui-drift/execution/mosaic-behaviour-runs/**", workflow)
        self.assertNotIn("/tmp/mosaic-ui-drift/execution/scratch-source/**", workflow)
        self.assertIn("scratch-commit.bundle", SCRIPT.read_text(encoding="utf-8"))
        self.assertIn("ui-migration-drill.json", SCRIPT.read_text(encoding="utf-8"))
        self.assertIn("contents: read", workflow)

    def test_swaps_only_the_two_requested_channel_pages(self):
        source = """from collections import OrderedDict
CHANNEL_PAGES = OrderedDict([
    (\"masks\", {\"title\": \"Note Masks\"}),
    (\"memory\", {\"title\": \"Memory\"}),
    (\"harmony\", {\"title\": \"Harmony\"}),
])
OTHER = 7
"""
        changed = runner.swap_channel_pages(source, ("masks", "memory"))
        self.assertEqual(runner.channel_page_keys(changed), ["memory", "masks", "harmony"])
        self.assertIn("OTHER = 7", changed)
        self.assertEqual(runner.swap_channel_pages(changed, ("masks", "memory")), source)

        reverse = runner.swap_channel_pages(source, ("harmony", "masks"))
        self.assertEqual(runner.channel_page_keys(reverse), ["harmony", "memory", "masks"])

    def test_swap_rejects_unknown_or_duplicate_page_names(self):
        source = "from collections import OrderedDict\nCHANNEL_PAGES = OrderedDict([('masks', {})])\n"
        for pages in (("masks", "masks"), ("masks", "memory")):
            with self.subTest(pages=pages), self.assertRaises(ValueError):
                runner.swap_channel_pages(source, pages)

    def test_failed_run_summary_must_name_the_selected_case_and_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest = Path(temp) / "manifest.json"
            manifest.write_text("{}\n", encoding="utf-8")
            completed = subprocess.CompletedProcess(
                args=[], returncode=1,
                stdout=json.dumps(dict(case="M-ONE", passed=False,
                                       manifest=str(manifest))) + "\n",
                stderr="")
            self.assertEqual(runner.failed_run_manifest(completed, "M-ONE"), manifest)

    def test_failed_run_summary_rejects_passes_wrong_cases_and_missing_manifest(self):
        invalid = (
            (0, dict(case="M-ONE", passed=True, manifest="run.json")),
            (1, dict(case="M-TWO", passed=False, manifest="run.json")),
            (1, dict(case="M-ONE", passed=False, manifest="missing.json")),
        )
        for returncode, row in invalid:
            with self.subTest(returncode=returncode, row=row):
                completed = subprocess.CompletedProcess(
                    args=[], returncode=returncode, stdout=json.dumps(row) + "\n", stderr="")
                with self.assertRaises(ValueError):
                    runner.failed_run_manifest(completed, "M-ONE")

    def test_control_requires_successful_matching_run(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "output"
            manifest = output / "control" / "M-ONE" / "run-1" / "manifest.json"

            def fake_run(*args, **kwargs):
                manifest.parent.mkdir(parents=True)
                manifest.write_text("{}\n", encoding="utf-8")
                self.assertIn("--clock-mode", args[0])
                self.assertIn("controlled-experimental", args[0])
                return subprocess.CompletedProcess(
                    args=[], returncode=0,
                    stdout=json.dumps(dict(case="M-ONE", passed=True,
                                           manifest=str(manifest))) + "\n", stderr="")

            with patch.object(runner.subprocess, "run", side_effect=fake_run):
                self.assertEqual(runner._run_control(
                    root / "candidate", output, "M-ONE", "base-midi",
                    "installation.json", None, 10), manifest)
            self.assertTrue((output / "control-logs" / "M-ONE.json").is_file())

    def test_control_rejects_failure_and_manifest_outside_upload(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            outside = root / "outside" / "manifest.json"
            outside.parent.mkdir()
            outside.write_text("{}\n", encoding="utf-8")
            for status, passed in ((1, False), (0, True)):
                completed = subprocess.CompletedProcess(
                    args=[], returncode=status,
                    stdout=json.dumps(dict(case="M-ONE", passed=passed,
                                           manifest=str(outside))) + "\n", stderr="")
                with self.subTest(status=status, passed=passed), patch.object(
                        runner.subprocess, "run", return_value=completed):
                    with self.assertRaises(ValueError):
                        runner._run_control(root / "candidate", root / ("output-" + str(status)),
                                            "M-ONE", "base-midi", "installation.json", None, 10)
                    log = root / ("output-" + str(status)) / "control-logs" / "M-ONE.json"
                    self.assertEqual(json.loads(log.read_text())["returncode"], status)

    def test_standalone_run_rejects_manifest_outside_uploaded_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = root / "outside" / "manifest.json"
            manifest.parent.mkdir()
            manifest.write_text("{}\n", encoding="utf-8")
            completed = subprocess.CompletedProcess(
                args=[], returncode=1,
                stdout=json.dumps(dict(case="M-ONE", passed=False,
                                       manifest=str(manifest))) + "\n",
                stderr="")
            with patch.object(runner.subprocess, "run", return_value=completed):
                with self.assertRaisesRegex(ValueError, "outside standalone artifact root"):
                    runner._run_case(root / "scratch", root / "output", "M-ONE",
                                     "base-midi", "installation.json", None, 10)

    def test_standalone_run_preserves_manifest_inside_uploaded_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "output"
            manifest = output / "standalone" / "M-ONE" / "run-1" / "manifest.json"

            def fake_run(*args, **kwargs):
                manifest.parent.mkdir()
                manifest.write_text("{}\n", encoding="utf-8")
                return subprocess.CompletedProcess(
                    args=[], returncode=1,
                    stdout=json.dumps(dict(case="M-ONE", passed=False,
                                           manifest=str(manifest))) + "\n",
                    stderr="")

            with patch.object(runner.subprocess, "run", side_effect=fake_run):
                self.assertEqual(
                    runner._run_case(root / "scratch", output, "M-ONE",
                                     "base-midi", "installation.json", None, 10),
                    manifest)
            self.assertTrue((output / "standalone-logs" / "M-ONE.json").is_file())

    def test_repeat_prepares_the_output_parent_required_by_repeat_py(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            scratch = root / "execution" / "scratch-source"
            repeats = scratch.parent / "mosaic-behaviour-runs"
            manifest = repeats / "repeat-one" / "manifest.json"

            def fake_run(*args, **kwargs):
                self.assertTrue(repeats.is_dir(), "repeat.py output parent is absent")
                manifest.parent.mkdir()
                manifest.write_text("{}\n", encoding="utf-8")
                return subprocess.CompletedProcess(args=[], returncode=1,
                                                   stdout="", stderr="")

            with patch.object(runner.subprocess, "run", side_effect=fake_run):
                self.assertEqual(
                    runner._run_repeat(scratch, root / "output", "M-ONE",
                                       "base-midi", "installation.json", None, 10),
                    manifest)

    def test_scratch_commit_changes_only_the_exact_page_order_and_bundles(self):
        source = """from collections import OrderedDict
CHANNEL_PAGES = OrderedDict([
    (\"masks\", {\"title\": \"Note Masks\"}),
    (\"memory\", {\"title\": \"Memory\"}),
    (\"harmony\", {\"title\": \"Harmony\"}),
])
"""
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp) / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (repo / "tests/behaviour").mkdir(parents=True)
            (repo / "tests/behaviour/ui_map.py").write_text(source, encoding="utf-8")
            subprocess.run(["git", "add", "--", "tests/behaviour/ui_map.py"],
                           cwd=repo, check=True, stdout=subprocess.PIPE)
            subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
                            "commit", "-m", "baseline"], cwd=repo, check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            baseline = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo,
                                               text=True).strip()
            scratch = Path(temp) / "scratch"
            scratch_sha = runner.make_scratch_commit(
                repo, baseline, ("masks", "memory"), "codex/ui-drift-test", scratch)
            changed = subprocess.check_output(
                ["git", "diff", "--name-only", baseline, scratch_sha], cwd=repo,
                text=True).splitlines()
            self.assertEqual(changed, [runner.MAP])
            self.assertEqual(runner.channel_page_keys(
                (scratch / runner.MAP).read_text(encoding="utf-8")),
                ["memory", "masks", "harmony"])
            output = Path(temp) / "artifact"
            output.mkdir()
            runner.preserve_scratch_commit(
                repo, output, baseline, scratch_sha, "codex/ui-drift-test")
            self.assertTrue((output / "scratch-commit.bundle").is_file())
            self.assertTrue((output / "scratch-commit.patch").is_file())
            self.assertTrue((output / "scratch-commit.txt").is_file())


if __name__ == "__main__":
    unittest.main()
