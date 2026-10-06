"""Keep the Rhythm Doctor quick reference aligned with the user manual."""
import unittest
import yaml
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANUAL_FEATURE_ID = "rhythm-doctor"
MANUAL_CITATION = "manual:" + MANUAL_FEATURE_ID


def authoritative_feature_text(root=ROOT, feature_id=MANUAL_FEATURE_ID):
    """Read current authored feature text, never the overview or generated cache."""
    manual = root / "manual"
    index = yaml.safe_load((manual / "book.yaml").read_text(encoding="utf-8"))
    matches = []
    for name in index["sources"]:
        source = yaml.safe_load((manual / name).read_text(encoding="utf-8"))
        features = source.get("features", [])
        if "feature" in source:
            features = features + [source["feature"]]
        matches.extend(feature for feature in features if feature["id"] == feature_id)
    if len(matches) != 1:
        raise ValueError("Expected one authoritative manual feature: " + feature_id)
    feature = matches[0]
    fields = [feature["title"], feature.get("prose", "")]
    fields.extend(detail["title"] + " " + detail.get("text", detail.get("body", ""))
                  for detail in feature.get("details", []))
    fields.extend(control["gesture"] + " " + control["result"]
                  for control in feature.get("controls", []))
    return "\n".join(fields)


class RhythmDoctorDocumentationTests(unittest.TestCase):
    def test_manual_and_cheat_sheet_name_the_same_lanes_and_stop_gate(self):
        manual = authoritative_feature_text()  # manual:rhythm-doctor
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
        manual = authoritative_feature_text()  # manual:rhythm-doctor
        cheat_sheet = (ROOT / "cheat_sheet.html").read_text(encoding="utf-8")
        self.assertIn("ANALYSIS_BACKEND_UNAVAILABLE", manual)
        self.assertIn("ANALYSIS_BACKEND_UNAVAILABLE", cheat_sheet)
        self.assertIn("builds from source the", manual)
        self.assertIn("no Python packages are", manual)
        self.assertIn("Stereo records both inputs", cheat_sheet)
        for document in (manual, cheat_sheet):
            self.assertIn("Manual uses", document)
            self.assertIn("Alignment", document)

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


class DocumentationAuthorityMigrationTests(unittest.TestCase):
    def fixture(self, directory, features):
        root = Path(directory)
        (root / "manual/features").mkdir(parents=True)
        (root / "manual/book.yaml").write_text(yaml.safe_dump({"sources": ["features/current.yaml"]}))
        (root / "manual/features/current.yaml").write_text(yaml.safe_dump({"features": features}))
        (root / "README.md").write_text("Overview only; forbidden fallback")
        (root / "manual/legacy").mkdir()
        (root / "manual/legacy/README-1.4.0.md").write_text("Historical corpus; forbidden fallback")
        return root

    def test_reads_current_stable_feature_prose_details_and_controls(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory, [{"id": MANUAL_FEATURE_ID, "title": "Rhythm Doctor",
                "prose": "Current capture workflow", "details": [{"title": "Local lanes", "text": "BD SD CYM"}],
                "controls": [{"gesture": "Stop then record", "result": "A real bank"}]}])
            actual = authoritative_feature_text(root)
            self.assertIn("Current capture workflow", actual)
            self.assertIn("Local lanes BD SD CYM", actual)
            self.assertIn("Stop then record A real bank", actual)
            self.assertNotIn("forbidden fallback", actual)
            self.assertEqual(MANUAL_CITATION, "manual:rhythm-doctor")

    def test_missing_or_duplicate_feature_fails_instead_of_falling_back(self):
        for features in ([], [{"id": MANUAL_FEATURE_ID}] * 2):
            with self.subTest(features=len(features)), tempfile.TemporaryDirectory() as directory:
                root = self.fixture(directory, features)
                with self.assertRaisesRegex(ValueError, "one authoritative manual feature"):
                    authoritative_feature_text(root)


if __name__ == "__main__":
    unittest.main()
