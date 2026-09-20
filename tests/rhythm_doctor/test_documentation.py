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
            self.assertIn("CYM", document)
            # BASS was withdrawn: a lane the product does not have must not be
            # advertised to a player as one it does.
            self.assertNotIn("**BASS**", document)
            # OHH and TOM have no lane. The manual must not advertise one.
            self.assertNotIn("OHH", document)
            self.assertIn("stopped", document.lower())

    def test_both_documents_state_the_unconfigured_analysis_backend(self):
        manual = (ROOT / "README.md").read_text(encoding="utf-8")
        cheat_sheet = (ROOT / "cheat_sheet.html").read_text(encoding="utf-8")
        self.assertIn("ANALYSIS_BACKEND_UNAVAILABLE", manual)
        self.assertIn("ANALYSIS_BACKEND_UNAVAILABLE", cheat_sheet)
        self.assertIn("builds from source the", manual)
        self.assertIn("no Python packages are", manual)
        self.assertIn("not audio routing", cheat_sheet)

    def test_detector_document_names_the_pinned_pretrained_worker_contract(self):
        detector = (ROOT / "docs" / "rhythm-doctor" / "DETECTOR.md").read_text(encoding="utf-8")
        for setting in ("RHYTHM_DOCTOR_ANALYSIS_BACKEND",
                        "RHYTHM_DOCTOR_ANALYSIS_BACKEND_SHA256",
                        "RHYTHM_DOCTOR_DRUM_ARTIFACT_SHA256",
                        "RHYTHM_DOCTOR_BASS_ARTIFACT_SHA256",
                        "RHYTHM_DOCTOR_PRETRAINED_RUNTIME_FACTORY",
                        "RHYTHM_DOCTOR_PRETRAINED_RUNTIME_FACTORY_SHA256",
                        # The shipped model-free backend pins a template table
                        # rather than model artifacts, and an operator cannot
                        # configure it from a document that never names it.
                        "RHYTHM_DOCTOR_TEMPLATE_SHA256"):
            self.assertIn(setting, detector)
        self.assertIn("installs,\ndownloads, trains, and fine-tunes nothing", detector)


if __name__ == "__main__":
    unittest.main()
