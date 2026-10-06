"""refresh-editorial on a controlled generation audits the controlled Masks publication.

Regression for build ce0abee4f92e4656bf2f33d1d0f64cae (stage refresh-editorial):
a controlled-local Masks publication correctly records pilot_complete False
(real-time pilot qualification is pending CI), but refresh-editorial applied the
real-time pilot audit and failed with "Fresh pilot incomplete".
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import yaml

REPO = Path(os.environ.get("MOSAIC_MANUAL_ROOT", Path(__file__).resolve().parents[1]))
sys.path[:0] = [str(REPO / "tools"), str(REPO / "tests/behaviour")]
import manual_publication_verify as verify

CONTROLLED = dict(validation_scope="controlled-manual-generation", realtime_qualification="pending-ci",
                  clock_mode="controlled-experimental", complete_regression_run=False,
                  scene_build_complete=True, pilot_complete=False)


class ControlledEditorialRefresh(unittest.TestCase):
    def publish(self, validation):
        manual = Path(self.tmp.name)
        (manual / "generated").mkdir(); (manual / "features").mkdir()
        authored = {"scenes": [], "audio": {}}
        (manual / "features/masks.yaml").write_text(yaml.safe_dump(authored))
        (manual / "generated/pilot.json").write_text(json.dumps(dict(source_sha256=verify.source_hash(authored), validation=validation)))
        return manual

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)

    def test_controlled_publication_uses_the_controlled_audit_and_keeps_audio_receipts(self):
        manual = self.publish(CONTROLLED)
        with patch.object(verify, "MANUAL", manual), \
             patch.object(verify, "audit_controlled_pilot", return_value=dict(frames=118)) as controlled, \
             patch.object(verify, "refresh_compression_receipt") as receipt:
            result = verify.refresh_pilot_editorial()
        controlled.assert_called_once_with()
        receipt.assert_not_called()
        self.assertEqual(result["verified"], dict(frames=118))
        self.assertEqual(result["validation_scope"], "controlled-manual-generation")
        self.assertEqual(result["realtime_qualification"], "pending-ci")

    def test_incomplete_publication_without_controlled_scope_still_fails(self):
        manual = self.publish(dict(CONTROLLED, validation_scope=None))
        with patch.object(verify, "MANUAL", manual):
            with self.assertRaisesRegex(ValueError, "Fresh pilot incomplete"):
                verify.refresh_pilot_editorial()


if __name__ == "__main__":
    unittest.main()
