"""Scheduled v2 corpus asset selection stays evidence-backed."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "tools" / "rhythm_doctor_corpus"))
from build_scheduled import verified_open_hat_asset


class ScheduledOpenHatAssets(unittest.TestCase):
    def test_uses_the_existing_open_hat_asset(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            asset = root / "hydrogen" / "gm" / "HatOpen-Med.wav"
            asset.parent.mkdir(parents=True)
            asset.write_bytes(b"verified fixture")
            self.assertEqual(
                verified_open_hat_asset(root, "hydrogen/gm"),
                "hydrogen/gm/HatOpen-Med.wav",
            )

    def test_missing_open_hat_fails_without_guessing_a_path(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "hydrogen" / "gm").mkdir(parents=True)
            with self.assertRaisesRegex(FileNotFoundError, "Refusing to invent a path"):
                verified_open_hat_asset(root, "hydrogen/gm")

    def test_ambiguous_open_hat_assets_fail_without_selecting_one(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            directory = root / "hydrogen" / "gm"
            directory.mkdir(parents=True)
            (directory / "HatOpen-Med.wav").write_bytes(b"first")
            (directory / "OpenHat-Long.wav").write_bytes(b"second")
            with self.assertRaisesRegex(FileNotFoundError, "exactly one verified"):
                verified_open_hat_asset(root, "hydrogen/gm")


if __name__ == "__main__":
    unittest.main()
