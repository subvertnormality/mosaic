"""New stable manual citations and historical aliases remain capture-authorable."""
import copy
import unittest

import manual_model


class ManualModelCitationTests(unittest.TestCase):
    def scene(self, citation):
        data = manual_model.load()
        scene = copy.deepcopy(next(s for s in data["scenes"] if s["id"] == "mask-note-default-x"))
        data["scenes"] = [scene]
        for step in scene["steps"]:
            step["citation"] = citation
        return data

    def test_current_masks_authoring_accepts_stable_feature_citations(self):
        manual_model.validate(manual_model.load())

    def test_stable_feature_and_historical_citations(self):
        for citation in ("manual:masks", "manual:arm-live-record", "README.md#adding-note-masks", "characterisation:captured native display"):
            with self.subTest(citation=citation):
                manual_model.validate(self.scene(citation))

    def test_malformed_stable_citations_are_rejected(self):
        for citation in ("manual:", "manual:Masks", "manual:masks trailing", "manual:masks/step", "manual:-masks", "manual:masks-", "manual:masks--step", "manual:masks\n"):
            with self.subTest(citation=citation):
                with self.assertRaisesRegex(ValueError, "citation"):
                    manual_model.validate(self.scene(citation))


if __name__ == "__main__":
    unittest.main()
