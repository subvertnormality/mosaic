"""Portable pixel regression for the Matrix two-decimal depth display."""
import base64
import hashlib
import json
import os
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests" / "behaviour"))

from frame_oracle import selected_value


class MatrixDepthDisplayFrameTests(unittest.TestCase):
    def test_preserved_native_frame_matches_two_decimal_display(self):
        fixture = ROOT / "tests" / "fixtures" / "modulation-depth-readout-v10-cc0a121c.bgra"
        provenance_path = fixture.with_suffix(".json")
        pixels = fixture.read_bytes()
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        self.assertEqual(hashlib.sha256(pixels).hexdigest(), provenance["frame_sha256"])
        self.assertEqual(len(pixels), provenance["width"] * provenance["height"] * 4)
        self.assertEqual(provenance["format"], "BGRA8")

        oracle_path = ROOT / "tests" / "behaviour" / "frame_oracle.py"
        ui_map_path = ROOT / "tests" / "behaviour" / "ui_map.py"
        helper_path = ROOT / "tools" / "manual_extra_matrix_macro_modest.py"
        self.assertEqual(hashlib.sha256(oracle_path.read_bytes()).hexdigest(),
                         provenance["frame_oracle_sha256"])
        self.assertEqual(hashlib.sha256(ui_map_path.read_bytes()).hexdigest(),
                         provenance["ui_map_sha256"])
        self.assertEqual(hashlib.sha256(helper_path.read_bytes()).hexdigest(),
                         provenance["corrected_helper_sha256"])

        state = {"frame": {
            "width": provenance["width"],
            "height": provenance["height"],
            "format": provenance["format"],
            "pixels_base64": base64.b64encode(pixels).decode("ascii"),
        }}
        # frame_oracle.selected_value uses driver.EMULATOR_ROOT from
        # MONOME_EMULATOR to load the norns font. No session is started.
        self.assertTrue(os.environ.get("MONOME_EMULATOR"),
                        "Set MONOME_EMULATOR for the existing frame_oracle font resolver")
        self.assertFalse(selected_value(state, "0.1"))
        self.assertTrue(selected_value(state, "0.10"))


if __name__ == "__main__":
    unittest.main()
