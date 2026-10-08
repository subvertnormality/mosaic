import hashlib
import json
import os
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".github" / "scripts"))
import manual_artifact as artifact
import manual_runtime as runtime


class BuildManifestContractTests(unittest.TestCase):
    def fixture(self, root):
        repo = root / "repo"
        evidence = root / "evidence"
        evidence.mkdir()
        repo.mkdir()
        commit = "a" * 40
        tree = "b" * 40
        identity = root / "source-identity.json"
        identity.write_text(json.dumps({"schema_version": 1, "commit_sha": commit, "tree_sha": tree}))
        manifest = {
            "schema_version": 1, "passed": True, "revision": commit,
            "build_complete": False, "manual_generation_complete": True,
            "validation_scope": "controlled-manual-generation",
            "realtime_qualification": "pending-ci", "clock_mode": "controlled-experimental",
            "complete_regression_run": False, "renderer_validated": True,
        }
        (evidence / "manifest.json").write_text(json.dumps(manifest))
        return repo, evidence, identity, manifest

    @staticmethod
    def audit(evidence, require_manual_generation_complete):
        assert require_manual_generation_complete is True
        return {"passed": True, "manual_generation_complete": True,
                "validation_scope": "controlled-manual-generation",
                "realtime_qualification": "pending-ci", "complete_regression_run": False,
                "controlled_stages": [{"name": "reference-controlled-example-base-midi"}], "features": 1}

    def test_only_final_controlled_generation_with_ci_pending_is_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            repo, evidence, identity, manifest = self.fixture(Path(temp))
            result = artifact.verify_build(repo, evidence, identity, self.audit)
            self.assertEqual(result[0]["build_complete"], False)
            self.assertEqual(result[0]["manual_generation_complete"], True)
            self.assertEqual(result[0]["complete_regression_run"], False)
            for field, value in (("build_complete", True), ("manual_generation_complete", False),
                                 ("realtime_qualification", "qualified"),
                                 ("complete_regression_run", True), ("clock_mode", "real-time"),
                                 ("renderer_validated", False)):
                bad = dict(manifest, **{field: value})
                (evidence / "manifest.json").write_text(json.dumps(bad))
                with self.subTest(field=field), self.assertRaises(ValueError):
                    artifact.verify_build(repo, evidence, identity, self.audit)

    def test_final_audit_is_mandatory_and_stale_git_identity_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            repo, evidence, identity, _ = self.fixture(Path(temp))
            calls = []
            def fail_closed(path, require_manual_generation_complete):
                calls.append(require_manual_generation_complete)
                raise ValueError("strict audit failure")
            with self.assertRaisesRegex(ValueError, "strict audit"):
                artifact.verify_build(repo, evidence, identity, fail_closed)
            self.assertEqual(calls, [True])
            (evidence / "manifest.json").write_text(json.dumps({
                "schema_version": 1, "passed": True, "revision": "c" * 40,
                "build_complete": False, "manual_generation_complete": True,
                "validation_scope": "controlled-manual-generation", "realtime_qualification": "pending-ci",
                "clock_mode": "controlled-experimental", "complete_regression_run": False,
                "renderer_validated": True,
            }))
            with self.assertRaisesRegex(ValueError, "stale"):
                artifact.verify_build(repo, evidence, identity, self.audit)
            identity.write_text(json.dumps({"schema_version": 1, "commit_sha": "a" * 40, "tree_sha": "e" * 64}))
            with self.assertRaisesRegex(ValueError, "Git source identity"):
                artifact.verify_build(repo, evidence, identity, self.audit)


class StaticSitePackageTests(unittest.TestCase):
    def site_fixture(self, root):
        repo = root / "repo"
        files = {
            "_config.yml": "exclude: []\n",
            "index.html": "<!doctype html><title>Existing site entry</title>\n",
            "README.md": "# Mosaic\n![manual](images/readme.png)\n",
            "cheat_sheet.html": '<img src="images/cheat.png"><link rel="stylesheet" href="quick.css">',
            "quick.css": "body { background: url('images/quick-bg.png'); }",
            "config_creator.html": "<!doctype html><title>Config creator</title>",
            "images/logo.svg": "<svg></svg>",
            "images/readme.png": "readme-png", "images/cheat.png": "cheat-png",
            "images/quick-bg.png": "background-png", "images/scene.png": "scene-png",
            "manual/index.html": '<link rel="stylesheet" href="manual.css"><script src="manual.js"></script><script src="book.js"></script><a href="../README.md">README</a><a href="BUILD.md">Build</a>',
            "manual/manual.css": "body { background: url('../images/scene.png'); }",
            "manual/manual.js": 'fetch("generated/pilot.json");',
            "manual/book.js": 'const footer="<a href=\"BUILD.md\">Capture notes</a>";',
            "manual/inventory.json": json.dumps({"features": [{"id": "masks"}]}),
            "manual/generated/book.json": json.dumps({"features": [{"id": "masks"}], "scenes": {"masks": {"evidence": {"path": "/runner/private/report.json"}, "image": "images/scene.png"}}}),
            "manual/generated/reader-index.json": json.dumps({"features": [], "navigation": [], "aliases": {}, "scenes": {}, "scene_chunks": {}, "audio_chunks": {}, "audio_examples": [], "learning_path": [], "teaching_contracts": {}, "prelude_receipts": {}, "source_sha256": "private"}),
            "manual/generated/pilot.json": json.dumps({"feature": {"id": "masks"}, "audio": {"files": ["manual/audio/demo.ogg"]}, "scenes": [{"id": "masks"}], "evidence": {"path": "/runner/private/pilot.json"}}),
            "manual/generated/audio-scenes.json": json.dumps({"examples": [{"files": ["audio/demo.ogg"]}], "evidence": {"path": "/runner/private/audio.json"}}),
            "manual/audio/demo.ogg": "opus-audio",
        }
        for relative, text in files.items():
            path = repo / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        return repo, files

    def test_package_is_static_complete_and_excludes_internal_evidence_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo, source = self.site_fixture(root)
            site = root / "site"
            files = artifact.collect_public_site(repo, site)
            self.assertIn("images/logo.svg", files)
            self.assertIn("images/scene.png", files)
            self.assertIn("images/quick-bg.png", files)
            self.assertIn("manual/audio/demo.ogg", files)
            self.assertEqual((site / "index.html").read_text(), source["index.html"])
            self.assertTrue((site / "manual/generated/reader-index.json").is_file())
            self.assertFalse((site / "manual/generated/book.json").exists())
            self.assertFalse((site / "manual/generated/audio-scenes.json").exists())
            self.assertNotIn("source_sha256", (site / "manual/generated/reader-index.json").read_text())
            self.assertNotIn('href="BUILD.md"', (site / "manual/book.js").read_text())
            self.assertTrue((site / "README.md").is_file())
            self.assertTrue((site / "config_creator.html").is_file())
            self.assertFalse((site / "manual/evidence").exists())

    def test_public_reader_keeps_runtime_chunk_hashes_but_drops_provenance(self):
        index = {"features": [], "navigation": [], "aliases": {}, "scenes": {},
                 "scene_chunks": {"s": {"path": "reader-chunks/s.json", "sha256": "a" * 64}},
                 "audio_chunks": {}, "audio_examples": [], "learning_path": [],
                 "teaching_contracts": {"lesson": {"scene_chunk_sha256": "a" * 64}},
                 "prelude_receipts": {}, "source_sha256": "secret", "authoring_identity": {"commit": "secret"}}
        public = artifact.public_reader_index(index)
        self.assertEqual(public["scene_chunks"]["s"]["sha256"], "a" * 64)
        self.assertEqual(public["teaching_contracts"]["lesson"]["scene_chunk_sha256"], "a" * 64)
        self.assertNotIn("source_sha256", public)
        self.assertNotIn("authoring_identity", public)

    def test_reader_chrome_has_no_visible_capture_receipts_or_build_links(self):
        index = (ROOT / "manual/index.html").read_text()
        book = (ROOT / "manual/book.js").read_text()
        player = (ROOT / "manual/manual.js").read_text()
        self.assertNotIn("INVENTORY.md", index)
        self.assertNotIn("VOICES.md", index)
        self.assertNotIn("JSON.stringify({contract_id", book)
        self.assertNotIn("controlled-time captures", book)
        self.assertNotIn("data.source_sha256", player)
        self.assertIn("scene_chunk_sha256", book)  # Runtime verification remains wired.

    def test_rejects_encoded_traversal_and_source_symlink(self):
        for value in ("../outside", "%2e%2e/outside", "/etc/passwd", "manual/%2E%2E/private"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                artifact.safe_relative(value)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo, _ = self.site_fixture(root)
            (repo / "images/logo.svg").unlink()
            (repo / "images/logo.svg").symlink_to(Path("/etc/passwd"))
            with self.assertRaisesRegex(ValueError, "Symlink"):
                artifact.collect_public_site(repo, root / "out")

    def test_missing_referenced_asset_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo, _ = self.site_fixture(root)
            (repo / "images/scene.png").unlink()
            with self.assertRaises(FileNotFoundError):
                artifact.collect_public_site(repo, root / "out")

    def test_artifact_manifest_binds_git_identity_and_each_static_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo, _ = self.site_fixture(root)
            evidence = root / "build"
            evidence.mkdir()
            build = {"schema_version": 1, "passed": True, "revision": "a" * 40,
                     "build_complete": False, "manual_generation_complete": True,
                     "validation_scope": "controlled-manual-generation", "realtime_qualification": "pending-ci",
                     "clock_mode": "controlled-experimental", "complete_regression_run": False,
                     "renderer_validated": True}
            (evidence / "manifest.json").write_text(json.dumps(build))
            identity = root / "identity.json"
            identity.write_text(json.dumps({"schema_version": 1, "commit_sha": "a" * 40, "tree_sha": "b" * 40}))
            result = artifact.make_artifact(repo, evidence, identity, root / "out", {
                "repository": "owner/mosaic", "producer_run_id": 17, "producer_run_attempt": 2,
                "pr_number": 42, "pr_head_sha": "a" * 40, "pr_base_ref": "main",
            }, BuildManifestContractTests.audit)
            self.assertIs(type(result["producer_run_id"]), int)
            self.assertEqual(result["tested_commit_sha"], "a" * 40)
            self.assertEqual(result["tested_tree_sha"], "b" * 40)
            self.assertEqual(result["files"]["manual-site/manual/generated/reader-index.json"],
                             hashlib.sha256((root / "out/manual-site/manual/generated/reader-index.json").read_bytes()).hexdigest())
            self.assertEqual({p.name for p in (root / "out").iterdir()}, {"manual-site", "manual-artifact-manifest.json"})


class RuntimeAndWorkflowContractTests(unittest.TestCase):
    def test_fetch_pin_resolves_all_targets_under_set_u(self):
        wrapper = (ROOT / ".github/scripts/manual-build.sh").read_text()
        start = wrapper.index("fetch_pin() {")
        end = wrapper.index("\n}", start) + 2
        function = wrapper[start:end]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            log = root / "git.log"
            expected_sha = "1" * 40
            fake_git = fake_bin / "git"
            fake_git.write_text("""#!/usr/bin/env bash
set -eu
printf '%s\n' "$*" >> "$GIT_LOG"
if [[ "$1" == "clone" ]]; then
  for target in "$@"; do :; done
  mkdir -p "$target"
elif [[ "$1" == "-C" && "$3" == "rev-parse" ]]; then
  printf '%s\n' "$EXPECTED_SHA"
fi
""")
            fake_git.chmod(0o755)
            driver = root / "driver.sh"
            driver.write_text("""#!/usr/bin/env bash
set -eu
MOD_ROOT="$1"
export GIT_LOG="$2" EXPECTED_SHA="$3"
PATH="$4:$PATH"
export PATH
""" + function + """
fetch_pin matrix https://example.invalid/matrix.git "$EXPECTED_SHA"
""")
            completed = subprocess.run(
                ["bash", str(driver), str(root / "mods"), str(log), expected_sha, str(fake_bin)],
                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            rows = log.read_text().splitlines()
            target = str(root / "mods/matrix")
            self.assertEqual(rows, [
                "clone --no-checkout https://example.invalid/matrix.git " + target,
                "-C " + target + " checkout --detach " + expected_sha,
                "-C " + target + " rev-parse HEAD",
            ])

    def test_audio_voice_pins_match_current_locked_allowed_voices(self):
        pins = runtime.validate_voice_lock(ROOT / "manual/voices.lock.json")
        self.assertEqual(set(pins), {"oilcan", "nb_polyperc", "doubledecker"})
        with tempfile.TemporaryDirectory() as temp:
            lock = json.loads((ROOT / "manual/voices.lock.json").read_text())
            lock["oilcan"]["commit"] = "0" * 40
            path = Path(temp) / "voices.json"
            path.write_text(json.dumps(lock))
            with self.assertRaisesRegex(ValueError, "oilcan"):
                runtime.validate_voice_lock(path)

    def test_audio_runtime_uses_ci_asset_build_not_midi_only_install(self):
        commands = runtime.audio_runtime_commands("/tmp/emulator", "/tmp/audio", "/tmp/monitor")
        self.assertEqual(commands[0], ["python3", "scripts/build_audio_candidate.py", "--output", "/tmp/audio", "--sdl-ownership", "--screen-worker-shutdown"])
        self.assertEqual(commands[1][-2:], ["--output", "/tmp/monitor"])
        self.assertIn("/tmp/audio/installation.json", commands[1])

    def test_fresh_masks_capture_precedes_full_builder_and_is_asset_scoped(self):
        wrapper = (ROOT / ".github/scripts/manual-build.sh").read_text()
        capture = wrapper.index('python3 "$ROOT/tools/manual_capture.py"')
        builder = wrapper.index('python3 "$ROOT/tools/manual_build.py"')
        block = wrapper[capture:builder]
        for required in ("--source", "manual/features/masks.yaml", "--controlled-local",
                         "--clock-mode controlled-experimental", "--experimental-install",
                         "--audio-emulator", "--audio-install", "--mod-code-root"):
            self.assertIn(required, block)
        self.assertIn("real-time DSP asset recording", wrapper)
        self.assertIn("--extra-reference", wrapper)

    def test_evidence_bundle_exports_exact_preflight_report_and_audio_assets(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            build = root / "build"
            build.mkdir()
            (build / "manifest.json").write_text(json.dumps({"stages": []}))
            capture = root / "capture-123"
            capture.mkdir()
            wav = capture / "output.wav"
            wav.write_bytes(b"captured-audio")
            report = capture / "report.json"
            report.write_text(json.dumps({"passed": True, "audio": {
                "evidence": {"path": str(wav), "sha256": hashlib.sha256(wav.read_bytes()).hexdigest()}
            }}))
            destination = root / "bundle"
            result = artifact.make_evidence_bundle(None, destination, extra_references=[str(capture)])
            self.assertIn(str(capture), result["source_path_map"])
            self.assertEqual(result["source_path_map"][str(capture)]["status"], "copied")
            self.assertTrue(any(Path(name).suffix == ".wav" for name in result["files"]))
            self.assertEqual(result["source_path_map"][str(wav)]["status"], "copied")
            self.assertFalse(result["build_directory_present"])

    def test_workflow_has_only_pr_and_dispatch_build_triggers(self):
        workflow = (ROOT / ".github/workflows/manual-build.yml").read_text()
        self.assertIn("pull_request:", workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("  push:", workflow)
        self.assertNotIn("types: [closed", workflow)
        self.assertIn("manual-build.sh", workflow)
        wrapper = (ROOT / ".github/scripts/manual-build.sh").read_text()
        self.assertIn("--controlled-local", wrapper)
        self.assertIn("--quick-output \"cheat_sheet.html\"", wrapper)
        package = wrapper.index('python3 "$ROOT/.github/scripts/manual_artifact.py" "${PACKAGE_ARGS[@]}"')
        browser = wrapper.index('python3 "$ROOT/.github/scripts/manual_artifact.py" verify-site')
        self.assertLess(package, browser)
        self.assertIn("manual-site-dispatch-run-", wrapper)


if __name__ == "__main__":
    unittest.main()