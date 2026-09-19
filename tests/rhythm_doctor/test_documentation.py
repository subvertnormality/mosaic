"""Keep the Rhythm Doctor quick reference aligned with the user manual."""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class RhythmDoctorDocumentationTests(unittest.TestCase):
    def test_manual_and_cheat_sheet_name_the_same_lanes_and_stop_gate(self):
        manual = (ROOT / "README.md").read_text(encoding="utf-8")
        cheat_sheet = (ROOT / "cheat_sheet.html").read_text(encoding="utf-8")
        for document in (manual, cheat_sheet):
            self.assertIn("Rhythm Doctor", document)
            self.assertIn("BD", document)
            self.assertIn("SD", document)
            self.assertIn("CHH", document)
            self.assertIn("OHH", document)
            self.assertIn("BASS", document)
            self.assertIn("stopped", document.lower())

    def test_both_documents_state_the_unconfigured_analysis_backend(self):
        manual = (ROOT / "README.md").read_text(encoding="utf-8")
        cheat_sheet = (ROOT / "cheat_sheet.html").read_text(encoding="utf-8")
        self.assertIn("ANALYSIS_BACKEND_UNAVAILABLE", manual)
        self.assertIn("ANALYSIS_BACKEND_UNAVAILABLE", cheat_sheet)
        self.assertIn("does not configure the required pretrained analysis executable", manual)
        self.assertIn("not audio routing", cheat_sheet)


if __name__ == "__main__":
    unittest.main()
