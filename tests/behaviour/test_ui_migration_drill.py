"""Characterisation outside the manual: UI migration plan section 7 step 4."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from ui_migration_drill import (derive_cases, select_repeat, validate_run, validate_outcomes,
                                committed_plan, verify_swap, validate_repeat, main, sha)


class DriftDrillTests(unittest.TestCase):
    def setUp(self):
        self.files = {
            "A/controlled/after/recipe.json": b"[]",
            "A/controlled/after/results.json": b'[{"kind":"ui-confirm","page":"masks","channel":1}]',
            "B/controlled/after/recipe.json": b"[]",
            "B/controlled/after/results.json": b'[{"kind":"grid"}]',
            "B/controlled/after/restarted/recipe.json": b"[]",
            "B/controlled/after/restarted/results.json": b'[{"kind":"ui-confirm","page":"memory","channel":2}]',
            "C/real-time/after/results.json": b'[{"kind":"ui-confirm","page":"memory","channel":1}]',
        }
        self.registry = {"A", "B", "C"}
        self.pages = ("masks", "memory")

    def derive(self):
        return derive_cases(self.files, self.registry, self.pages, {"masks", "memory", "clock_mods"})

    def test_set_includes_nested_sessions_and_excludes_real_time(self):
        result = self.derive()
        self.assertEqual(set(result), {"A", "B"})
        self.assertEqual(result["B"][0]["session"], "restarted")

    def test_multiple_confirmations_select_case_once(self):
        self.files["A/controlled/after/results.json"] = json.dumps([
            dict(kind="ui-confirm", page="masks", channel=1),
            dict(kind="ui-confirm", page="memory", channel=1),
        ]).encode()
        self.assertEqual(len(self.derive()["A"]), 2)

    def test_missing_nested_pair_and_root_fail_closed(self):
        for path in ("B/controlled/after/restarted/recipe.json", "B/controlled/after/results.json"):
            with self.subTest(path=path):
                original = self.files.pop(path)
                with self.assertRaises(ValueError):
                    self.derive()
                self.files[path] = original

    def test_malformed_results_fail_even_for_unselected_case(self):
        for value in (b"{", b"{}", b'[{}]', b'[{"kind":"ui-confirm"}]',
                      b'[{"kind":"ui-confirm","page":"unknown","channel":1}]',
                      b'[{"kind":"ui-confirm","page":"masks","channel":true}]',
                      b'[{"kind":"ui-confirm","page":"masks","channel":17}]',
                      b'[{"kind":"grid","kind":"ui-confirm"}]'):
            with self.subTest(value=value):
                self.files["B/controlled/after/results.json"] = value
                with self.assertRaises(ValueError):
                    self.derive()

    def test_unknown_case_and_empty_selection_are_rejected(self):
        self.registry.remove("B")
        with self.assertRaises(ValueError):
            self.derive()
        self.registry.add("B")
        with self.assertRaisesRegex(ValueError, "duplicate case IDs"):
            derive_cases(self.files, ["A", "B", "C", "A"], ("masks", "memory"),
                         {"masks", "memory"})
        with self.assertRaisesRegex(ValueError, "drill set is empty"):
            derive_cases(self.files, self.registry, ("clock_mods", "harmony"),
                         {"masks", "memory", "clock_mods", "harmony"})
        self.pages = ("clock_mods", "clock_mods")
        with self.assertRaises(ValueError):
            self.derive()

    def test_repeat_selection_is_deterministic_and_requires_member(self):
        self.assertEqual(select_repeat({"B", "A"}, {"A": "nb-audio"}), "B")
        self.assertEqual(select_repeat({"A", "B"}, {"B": "midi-modulation"}, "B"), "B")
        for selected, profiles, requested in (({"A"}, {"A": "crow-jf"}, None), ({"A"}, {}, "B")):
            with self.assertRaises(ValueError):
                select_repeat(selected, profiles, requested)

    def run_manifest(self, case="A"):
        return dict(case=case, passed=False, failure=dict(type="UiMapError", message="expected masks, observed memory"),
                    clock_mode="controlled-experimental", profile="base-midi", diagnostic_only=True,
                    mosaic_revision="scratch", behaviour_source_sha256={"tests/behaviour/ui_map.py": "map-hash"})

    def test_run_requires_exact_failure_lane_profile_and_source(self):
        good = self.run_manifest()
        self.assertEqual(validate_run(good, "A", "base-midi", "scratch", {"tests/behaviour/ui_map.py": "map-hash"})["type"], "UiMapError")
        for change in (dict(passed=True), dict(failure=None), dict(failure=dict(type="AssertionError", message="UiMapError")),
                       dict(clock_mode="real-time"), dict(profile="midi-modulation"), dict(case="B"),
                       dict(mosaic_revision="before"), dict(behaviour_source_sha256={}), dict(diagnostic_only=False)):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_run(dict(good, **change), "A", "base-midi", "scratch", {"tests/behaviour/ui_map.py": "map-hash"})

    def test_outcomes_reject_missing_extra_and_duplicate_cases(self):
        for runs in ([self.run_manifest()], [self.run_manifest(), self.run_manifest()],
                     [self.run_manifest(), self.run_manifest("B"), self.run_manifest("C")]):
            with self.subTest(runs=runs), self.assertRaises(ValueError):
                validate_outcomes({"A", "B"}, runs, {}, "scratch", {"tests/behaviour/ui_map.py": "map-hash"})


class DriftArtifactTests(unittest.TestCase):
    """Characterisation outside the manual: synthetic artifacts, never an emulator run."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Drill test")
        self.git("config", "user.email", "drill@example.invalid")
        self.map_source = ('from collections import OrderedDict\n'
                           'CHANNEL_PAGES = OrderedDict([("masks", {"title": "Masks"}), '
                           '("memory", {"title": "Memory"})])\n')
        self.put("tests/behaviour/ui_map.py", self.map_source)
        self.put("tests/behaviour/cases.py", 'CASES = {"A": {}, "B": {}}\n')
        self.put("tests/behaviour/suite.py", 'CASE_PROFILE = {}\n')
        self.put("tests/behaviour/contract/nested_probe.py", 'NESTED_SOURCE = True\n')
        root = "docs/testing/ui-migration-baselines/A/controlled/after/"
        self.put(root + "recipe.json", [])
        self.put(root + "results.json", [dict(kind="ui-confirm", page="masks", channel=1)])
        self.commit()
        self.baseline = self.git("rev-parse", "HEAD")
        self.put("tests/behaviour/ui_map.py",
                 self.map_source.replace('[("masks", {"title": "Masks"}), ("memory", {"title": "Memory"})]',
                                         '[("memory", {"title": "Memory"}), ("masks", {"title": "Masks"})]'))
        self.commit()
        self.scratch, self.sources = verify_swap(self.repo, self.baseline, "HEAD", ("masks", "memory"))

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.repo, stderr=subprocess.PIPE).decode().strip()

    def commit(self):
        self.git("add", ".")
        self.git("commit", "-qm", "Synthetic unit fixture")

    def put(self, path, value):
        path = self.repo / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value if isinstance(value, str) else json.dumps(value))
        return path

    def run_evidence(self, folder):
        artifacts = []
        for name, data in (("recipe.json", [dict(type="enc", n=1, delta=1)]), ("results.json", [])):
            path = self.put(folder + "/" + name, data)
            raw = path.read_bytes()
            artifacts.append(dict(path=name, size=len(raw), sha256=sha(raw)))
        item = dict(case="A", profile="base-midi", passed=False, diagnostic_only=True,
                    clock_mode="controlled-experimental", mosaic_revision=self.scratch,
                    behaviour_source_sha256=self.sources, artifacts=artifacts,
                    failure=dict(type="UiMapError", message="expected masks, observed memory"))
        return self.put(folder + "/manifest.json", item)

    def repeat_evidence(self):
        child = self.run_evidence("repeat-child")
        stdout = json.dumps(dict(case="A", passed=False, manifest=str(child))) + "\n"
        self.put("repeat/process-0.json", dict(returncode=1, stdout=stdout, stderr=""))
        normalized = self.put("repeat/normalized.json", [])
        return self.put("repeat/manifest.json", dict(
            case="A", profile="base-midi", passed=False, diagnostic_only=True, runs=[],
            failure=dict(type="AssertionError", message=stdout), normalized_sha256=sha(normalized.read_bytes())))

    def test_committed_selection_ignores_working_tree_edits(self):
        self.put("docs/testing/ui-migration-baselines/A/controlled/after/results.json", [])
        revision, selected, profiles = committed_plan(self.repo, self.baseline, ("masks", "memory"))
        self.assertEqual(revision, self.baseline)
        self.assertEqual(set(selected), {"A"})
        self.assertEqual(profiles, {})

    def test_scratch_sources_match_recursive_runner_hashes(self):
        nested = "tests/behaviour/contract/nested_probe.py"
        self.assertIn(nested, self.sources)
        expected = {
            path.relative_to(self.repo).as_posix(): sha(path.read_bytes())
            for path in sorted((self.repo / "tests/behaviour").rglob("*.py"))
        }
        self.assertEqual(self.sources, expected)
        self.put(nested, 'NESTED_SOURCE = "uncommitted"\n')
        _, committed_sources = verify_swap(
            self.repo, self.baseline, self.scratch, ("masks", "memory"))
        self.assertEqual(committed_sources, expected)

    def test_list_never_creates_report(self):
        self.assertEqual(main(["--repo", str(self.repo), "--baseline", self.baseline,
                               "--pages", "masks", "memory", "--list"]), 0)
        self.assertFalse((self.repo / "docs/testing/ui-migration-drill.json").exists())

    def test_scratch_requires_exact_swap_and_no_other_change(self):
        for source in (self.map_source, self.map_source.replace("Masks", "Renamed")):
            with self.subTest(source=source):
                self.put("tests/behaviour/ui_map.py", source)
                self.commit()
                with self.assertRaises(ValueError):
                    verify_swap(self.repo, self.baseline, "HEAD", ("masks", "memory"))
        self.put("other.txt", "not a map edit")
        self.commit()
        with self.assertRaises(ValueError):
            verify_swap(self.repo, self.baseline, "HEAD", ("masks", "memory"))

    def test_repeat_unwraps_actual_first_error_and_rejects_wrong_error_or_missing_run(self):
        repeat = self.repeat_evidence()
        result = validate_repeat(repeat, "A", "base-midi", self.scratch, self.sources)
        self.assertEqual(result["first_error"]["type"], "UiMapError")
        child = self.repo / "repeat-child/manifest.json"
        item = json.loads(child.read_text())
        item["failure"]["type"] = "RuntimeError"
        self.put("repeat-child/manifest.json", item)
        with self.assertRaisesRegex(ValueError, "first error"):
            validate_repeat(repeat, "A", "base-midi", self.scratch, self.sources)
        child.unlink()
        with self.assertRaises(ValueError):
            validate_repeat(repeat, "A", "base-midi", self.scratch, self.sources)

    def test_repeat_rejects_pass_and_inconsistent_wrapper(self):
        for target, update in (
                ("repeat-child/manifest.json", dict(passed=True)),
                ("repeat/manifest.json", dict(passed=True)),
                ("repeat/manifest.json", dict(failure=dict(type="AssertionError", message="other"))),
                ("repeat/manifest.json", dict(runs=[dict(manifest="a passed child")]))):
            with self.subTest(target=target, update=update):
                repeat = self.repeat_evidence()
                item = json.loads((self.repo / target).read_text())
                self.put(target, dict(item, **update))
                with self.assertRaises(ValueError):
                    validate_repeat(repeat, "A", "base-midi", self.scratch, self.sources)

    def test_report_requires_all_actual_artifacts_and_never_overwrites(self):
        output = self.repo / "docs/testing/ui-migration-drill.json"
        prefix = ["--repo", str(self.repo), "--baseline", self.baseline, "--pages", "masks", "memory"]
        with self.assertRaises(SystemExit):
            main(prefix)
        self.assertFalse(output.exists())
        run, repeat = self.run_evidence("ordinary-run"), self.repeat_evidence()
        command = prefix + ["--scratch", self.scratch, "--run", str(run), "--repeat", str(repeat)]
        self.assertEqual(main(command), 0)
        original = output.read_bytes()
        report = json.loads(original)
        self.assertTrue(report["passed"])
        self.assertFalse(report["complete_regression_run"])
        self.assertEqual(report["cases"][0]["first_error"]["type"], "UiMapError")
        with self.assertRaises(SystemExit):
            main(command)
        self.assertEqual(output.read_bytes(), original)

    def test_missing_or_tampered_pair_and_missing_repeat_process_leave_no_report(self):
        run, repeat = self.run_evidence("ordinary-run"), self.repeat_evidence()
        prefix = ["--repo", str(self.repo), "--baseline", self.baseline, "--pages", "masks", "memory",
                  "--scratch", self.scratch, "--run", str(run), "--repeat", str(repeat)]
        self.put("ordinary-run/results.json", [dict(kind="tampered")])
        with self.assertRaises(SystemExit):
            main(prefix)
        self.assertFalse((self.repo / "docs/testing/ui-migration-drill.json").exists())
        self.run_evidence("ordinary-run")
        (self.repo / "repeat/process-0.json").unlink()
        with self.assertRaises(SystemExit):
            main(prefix)
        self.assertFalse((self.repo / "docs/testing/ui-migration-drill.json").exists())


if __name__ == "__main__":
    unittest.main()
