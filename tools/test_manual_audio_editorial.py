import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

import manual_audio as audio
import manual_audio_resume as resume


def native_run(directory, examples, extra=None):
    run = Path(directory); source = dict(schema_version=1, examples=examples, **(extra or {}))
    (run / "source.yaml").write_text(yaml.safe_dump(source)); (run / "audio-scenes.json").write_text("{}")
    return run, hashlib.sha256((run / "audio-scenes.json").read_bytes()).hexdigest()


def example(**fields):
    return dict(dict(id="a", bpm=90, bars=4, tracks=[1], feature_ids=["x"]), **fields)


class EditorialPublication(unittest.TestCase):
    def check(self, native_examples, current_examples, **publication):
        with tempfile.TemporaryDirectory() as directory, patch.object(audio, "validate", lambda data: data):
            run, digest = native_run(directory, native_examples)
            report = dict(publication=dict(kind="editorial-refresh", native_report_sha256=digest, editorial_fields=["feature_ids"], **publication))
            audio.verify_editorial_publication(report, run, dict(schema_version=1, examples=current_examples))

    def test_feature_ids_may_change(self):
        self.check([example()], [example(feature_ids=["y", "z"])])

    def test_any_other_field_change_is_rejected(self):
        for change in (dict(bpm=91), dict(tracks=[2]), dict(title="new"), dict(bars=8)):
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "recorded field"):
                self.check([example()], [example(**change)])

    def test_inventory_change_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "inventory"):
            self.check([example()], [example(id="b")])

    def test_changed_native_baseline_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(audio, "validate", lambda data: data):
            run, _ = native_run(directory, [example()])
            report = dict(publication=dict(kind="editorial-refresh", native_report_sha256="0" * 64, editorial_fields=["feature_ids"]))
            with self.assertRaisesRegex(ValueError, "baseline changed"):
                audio.verify_editorial_publication(report, run, dict(schema_version=1, examples=[example()]))

    def test_unknown_kind_and_fields_are_rejected(self):
        for publication in (dict(kind="other", editorial_fields=["feature_ids"]), dict(kind="editorial-refresh", editorial_fields=["feature_ids", "bpm"])):
            with self.subTest(publication=publication), self.assertRaisesRegex(ValueError, "kind"):
                audio.verify_editorial_publication(dict(publication=publication), Path("."), dict(examples=[]))

    def test_non_example_authoring_change_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(audio, "validate", lambda data: data):
            run, digest = native_run(directory, [example()], extra=dict(note="a"))
            report = dict(publication=dict(kind="editorial-refresh", native_report_sha256=digest, editorial_fields=["feature_ids"]))
            with self.assertRaisesRegex(ValueError, "non-example"):
                audio.verify_editorial_publication(report, run, dict(schema_version=1, examples=[example()], note="b"))


class SharedDefinitions(unittest.TestCase):
    def test_editorial_fields_agree_across_modules(self):
        self.assertEqual(audio.EDITORIAL_FIELDS, resume.EDITORIAL_FIELDS)

    def test_native_source_identity_prefers_the_publication_record(self):
        self.assertEqual(audio.native_source_sha256(dict(source_sha256="new", publication=dict(native_source_sha256="old"))), "old")
        self.assertEqual(audio.native_source_sha256(dict(source_sha256="only")), "only")

    def test_editorial_view_drops_only_editorial_fields(self):
        self.assertEqual(audio.editorial_view(dict(id="a", feature_ids=["x"])), dict(id="a"))


if __name__ == "__main__":
    unittest.main()
