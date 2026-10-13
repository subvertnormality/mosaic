import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "rhythm_doctor_analysis"))
import v11_adtof_priority_transfer as candidate


class PartitionTests(unittest.TestCase):
    def test_fixed_white_kit_validation_is_disjoint_from_training(self):
        clips = [
            {"id": "train-a", "split": "development", "kit_id": "pop_kit.nkm"},
            {"id": "train-b", "split": "development", "kit_id": "ar_modern_sparkle_kit_full.nkm"},
            {"id": "validation", "split": "development", "kit_id": candidate.VALIDATION_KIT},
            {"id": "held", "split": "held_out", "kit_id": "hydrogen-gmrock"},
        ]
        train, validation = candidate.partition_development(clips)
        self.assertEqual([clip["id"] for clip in train], ["train-a", "train-b"])
        self.assertEqual([clip["id"] for clip in validation], ["validation"])
        self.assertTrue({clip["kit_id"] for clip in train}.isdisjoint(
            {clip["kit_id"] for clip in validation}))

    def test_annotation_mapping_has_only_priority_lanes(self):
        self.assertEqual(candidate.LANES, ("BD", "SD", "HH"))
        self.assertEqual(candidate.OUTPUT_INDEX, {"BD": 0, "SD": 1, "HH": 3})

    def test_upstream_root_accepts_the_pinned_artifact_layout(self):
        root = ROOT / "tests" / "rhythm_doctor" / "artifacts" / "adtof-fullbackbone-priority-v5" / "upstream"
        self.assertEqual(candidate.upstream_import_root(root), root)


if __name__ == "__main__":
    unittest.main()
