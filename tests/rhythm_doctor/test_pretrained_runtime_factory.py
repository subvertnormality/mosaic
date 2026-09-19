"""Unit contracts for the fail-closed local pretrained runtime factory."""
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock
import wave


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "rhythm_doctor"))
from pretrained_bass_backend import PCM
import pretrained_runtime_factory as factory


class PretrainedRuntimeFactoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="rd-runtime-factory-")
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def checkout(self):
        for name in ("wrapper_func.py", "beat_for_drum.py"):
            path = self.root / "omnizart" / "feature" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# test source\n", encoding="utf-8")
        return self.root

    def test_checkout_requires_the_exact_v042_commit(self):
        root = self.checkout()
        good = types.SimpleNamespace(returncode=0, stdout=factory.OMNIZART_V042_HEAD + "\n")
        self.assertEqual(factory.verify_omnizart_checkout(root, lambda *args, **kwargs: good), root.resolve())
        bad = types.SimpleNamespace(returncode=0, stdout="0" * 40)
        with self.assertRaisesRegex(factory.RuntimeFactoryError, "OMNIZART_SOURCE_REVISION_MISMATCH"):
            factory.verify_omnizart_checkout(root, lambda *args, **kwargs: bad)

    def test_every_runtime_path_is_explicitly_required(self):
        with self.assertRaisesRegex(factory.RuntimeFactoryError, "RHYTHM_DOCTOR_RUNTIME_PATH_REQUIRED"):
            factory.configured_paths({})

    def test_numpy_aliases_are_installed_only_when_absent_for_old_librosa(self):
        numpy_stub = types.SimpleNamespace(complex128="complex128", float64="float64", int64="int64")
        factory._install_librosa_numpy_compatibility(numpy_stub)
        self.assertEqual((numpy_stub.complex, numpy_stub.float, numpy_stub.int),
                         ("complex128", "float64", "int64"))

    def test_exact_frontend_receives_a_temporary_pcm_wav_derives_bpm_from_eight_mini_beats_and_cleans_up(self):
        observed = {}

        def extract_patch_cqt(audio_path):
            observed["path"] = Path(audio_path)
            with wave.open(audio_path, "rb") as source:
                observed["wav"] = (source.getnchannels(), source.getsampwidth(),
                                   source.getframerate(), source.readframes(source.getnframes()))
            positions = [index / 16.0 for index in range(9)]
            return __import__("numpy").zeros((9, 120, 120), dtype="float32"), positions

        pcm = PCM(b"\x01\x00\xff\x7f", 22050, 1, 2, 2)
        result = factory.OmnizartFeatureProvider(extract_patch_cqt).extract(pcm)
        self.assertEqual(observed["wav"], (1, 2, 22050, pcm.data))
        self.assertAlmostEqual(result["bpm"], 120.0)
        self.assertEqual(result["origin_sample"], 0)
        self.assertEqual(result["features"].shape, (9, 120, 120))
        self.assertFalse(observed["path"].exists())

    def test_invalid_frontend_output_still_removes_temporary_wav(self):
        observed = {}

        def invalid_patch(audio_path):
            observed["path"] = Path(audio_path)
            return [], [index / 16.0 for index in range(9)]

        with self.assertRaisesRegex(factory.RuntimeFactoryError, "OMNIZART_FEATURES_INVALID"):
            factory.OmnizartFeatureProvider(invalid_patch).extract(
                PCM(b"\x00\x00", 22050, 1, 2, 1))
        self.assertFalse(observed["path"].exists())

    def test_make_builds_structural_composite_from_only_exact_pins(self):
        paths = {name: self.root / name for name in (factory.ENV_OMNIZART_SOURCE,
                                                      factory.ENV_OMNIZART_ONNX,
                                                      factory.ENV_UMXHQ_BASS,
                                                      factory.ENV_BASIC_PITCH_ONNX)}
        pipeline = types.SimpleNamespace(analyse=lambda pcm, origin: [], artifact_sha256="a" * 64)
        feature_provider = types.SimpleNamespace(extract=lambda pcm: None)
        with mock.patch.object(factory, "configured_paths", return_value=paths), \
             mock.patch.object(factory, "verify_omnizart_checkout", return_value=self.root) as checkout, \
             mock.patch.object(factory, "verify_artifact", return_value=factory.OMNIZART_DRUM_ONNX_SHA256) as drum_pin, \
             mock.patch.object(factory, "load_drum_onnx", return_value="drum-session") as drum_loader, \
             mock.patch.object(factory.OmnizartFeatureProvider, "from_checkout", return_value=feature_provider) as provider, \
             mock.patch.object(factory, "PinnedBassRuntime") as bass_runtime:
            bass_runtime.return_value.create.return_value = pipeline
            runtime = factory.make({})
        self.assertEqual(runtime.drum_session, "drum-session")
        self.assertIs(runtime.feature_provider, feature_provider)
        self.assertIs(runtime.bass_pipeline, pipeline)
        self.assertEqual(runtime.drum_gates, factory.PROVISIONAL_UNVALIDATED_DRUM_GATES)
        self.assertEqual(runtime.bass_gate, factory.PROVISIONAL_UNVALIDATED_BASS_ONSET_GATE)
        checkout.assert_called_once_with(paths[factory.ENV_OMNIZART_SOURCE])
        drum_pin.assert_called_once_with(paths[factory.ENV_OMNIZART_ONNX], factory.OMNIZART_DRUM_ONNX_SHA256)
        drum_loader.assert_called_once_with(paths[factory.ENV_OMNIZART_ONNX])
        provider.assert_called_once_with(self.root)
        args = bass_runtime.call_args.args
        self.assertEqual((args[0].sha256, args[1].sha256),
                         (factory.UMXHQ_BASS_SHA256, factory.BASIC_PITCH_ONNX_SHA256))
        self.assertIs(bass_runtime.call_args.kwargs["basic_pitch_loader"],
                      factory.load_provisional_basic_pitch)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
