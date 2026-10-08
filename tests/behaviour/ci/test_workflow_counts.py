"""The coverage job's report count must follow the base-shard matrix.

The count was hardcoded as 18 (16 shards + 2) and silently failed every run
after the matrix grew to 24 shards.
"""
import re
import unittest
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[3] / '.github' / 'workflows' / 'behaviour.yml'


class WorkflowCountTests(unittest.TestCase):
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
