"""The coverage job's report count must follow the base-shard matrix.

The count was hardcoded as 18 (16 shards + 2) and silently failed every run
after the matrix grew to 24 shards.
"""
import re
import unittest
import yaml
import os
import subprocess
import tempfile
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[3] / '.github' / 'workflows' / 'behaviour.yml'


class WorkflowCountTests(unittest.TestCase):
    def test_registration_runs_before_an_emulator_checkout_exists(self):
        workflow = yaml.safe_load(WORKFLOW.read_text())
        step = next(s for s in workflow['jobs']['base-midi']['steps']
                    if s.get('name') == 'Check behaviour test registration')
        with tempfile.TemporaryDirectory() as temp:
            env = dict(os.environ, MONOME_EMULATOR=str(Path(temp) / 'not-cloned'))
            env.update(step.get('env', {}))
            result = subprocess.run(step['run'], shell=True, env=env,
                                    cwd=WORKFLOW.parents[2], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_registration_precedes_expensive_native_work(self):
        workflow = yaml.safe_load(WORKFLOW.read_text())
        checked = 0
        for job in workflow['jobs'].values():
            steps = job.get('steps', [])
            builds = [i for i, step in enumerate(steps)
                      if step.get('name') == 'Build native runtimes']
            if not builds:
                continue
            collection = [i for i, step in enumerate(steps)
                          if 'test_suite.CollectionTests' in step.get('run', '')]
            self.assertEqual(len(collection), 1, job.get('name'))
            self.assertLess(collection[0], builds[0])
            checked += 1
        self.assertGreaterEqual(checked, 4)
        manual = yaml.safe_load(WORKFLOW.with_name('manual-build.yml').read_text())
        steps = manual['jobs']['record-audio']['steps']
        collection = next((i for i, step in enumerate(steps)
                           if 'test_suite.CollectionTests' in step.get('run', '')), None)
        self.assertIsNotNone(collection)
        runtime = next(i for i, step in enumerate(steps)
                       if step.get('name') == 'Restore the pinned emulator runtime')
        self.assertLess(collection, runtime)

    def test_fast_ci_checks_the_actual_suite_collection(self):
        main = WORKFLOW.with_name('main.yml').read_text()
        self.assertIn('PYTHONPATH: tests/behaviour', main)
        self.assertIn('python -m unittest test_suite.CollectionTests', main)

    def test_base_shards_install_manual_validator_dependencies_before_fast_layers(self):
        text = WORKFLOW.read_text()
        packages = re.search(r"(?ms)^      - &packages\n.*?^        run: \|\n(?P<run>.*?)^      - &checkout", text)
        self.assertIsNotNone(packages)
        self.assertIn("python3-jsonschema", packages.group("run"))
        self.assertIn("python3-yaml", packages.group("run"))
        self.assertLess(text.index("- &packages"), text.index("Run exhaustive base-MIDI shard"))

    def test_coverage_expects_every_base_shard_plus_the_two_profile_reports(self):
        text = WORKFLOW.read_text()
        shards = re.search(r'^\s*shard: \[([0-9, ]+)\]', text, re.M)
        self.assertIsNotNone(shards)
        shard_count = len([s for s in shards.group(1).split(',') if s.strip()])
        expected = re.search(r'test "\$\{#suites\[@\]\}" -eq (\d+)', text)
        self.assertIsNotNone(expected)
        self.assertEqual(int(expected.group(1)), shard_count + 2)
        # select-shard is asked for the same number of shards.
        counts = set(re.findall(r'select-shard\.py --profile base-midi --index \$\{\{ matrix\.shard \}\} --count (\d+)', text))
        self.assertEqual(counts, {str(shard_count)})


if __name__ == '__main__':
    unittest.main()
