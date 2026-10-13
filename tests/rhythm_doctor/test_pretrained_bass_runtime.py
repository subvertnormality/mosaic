"""Pure local-runtime tests for pinned UMXHQ -> Basic Pitch BASS inference."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "rhythm_doctor"))
from pretrained_bass_backend import PCM, PinnedArtifact
from pretrained_bass_runtime import (BASIC_PITCH_SAMPLE_RATE, FloatPCM,
                                     BasicPitchOnnxSession, PinnedBassRuntime, RuntimeError,
                                     basic_pitch_mono, decode_pcm, merge_channel_onsets,
                                     to_stereo_44100)

try:
    import numpy  # noqa: F401
    import scipy  # noqa: F401
    HAS_ARRAY_RUNTIME = True
except ImportError:
    HAS_ARRAY_RUNTIME = False


def pcm16(frames, rate=22050, channels=2):
    data = b"".join(int(value).to_bytes(2, "little", signed=True) for frame in frames for value in frame)
    return PCM(data, rate, channels, 2, len(frames))


def artifact(path, data):
    path.write_bytes(data)
    return PinnedArtifact(path.name, path, hashlib.sha256(data).hexdigest())


class Separator(object):
    def __init__(self): self.calls = []
    def separate(self, pcm):
        self.calls.append(pcm)
        return pcm


class Onset(object):
    def __init__(self): self.calls = []
    def predict_onsets(self, mono):
        self.calls.append(mono)
        return ([{"frame": 0, "midi_pitch": 36, "onset_confidence": .6, "attack_strength": .2},
                 {"frame": 172, "midi_pitch": 64, "onset_confidence": .99, "attack_strength": 1.}]
                if len(self.calls) == 1 else
                [{"frame": 1, "midi_pitch": 40, "onset_confidence": .9, "attack_strength": .8}])


class FakeOnnx(object):
    def __init__(self): self.calls = []
    def run(self, outputs, feeds):
        self.calls.append((outputs, feeds))
        note = __import__("numpy").zeros((1, 172, 88), dtype="float32")
        onset = note.copy(); onset[0, 30, 15] = .8
        return [note, onset]


class BoundaryOnnx(object):
    def run(self, outputs, feeds):
        numpy = __import__("numpy")
        note = numpy.zeros((1, 172, 88), dtype="float32")
        onset = note.copy()
        onset[0, 30, 7] = .8   # MIDI 28: included first BASS column.
        onset[0, 50, 39] = .9  # MIDI 60: included last BASS column.
        onset[0, 70, 6] = 1.0  # MIDI 27: must be excluded.
        onset[0, 90, 40] = 1.0 # MIDI 61: must be excluded.
        return [note, onset]


class PinnedBassRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="rd-bass-runtime-")
        self.root = Path(self.temporary.name)

    def tearDown(self): self.temporary.cleanup()

    @unittest.skipUnless(HAS_ARRAY_RUNTIME, "requires local NumPy and SciPy model runtime")
    def test_pcm_preprocessing_preserves_stereo_phase_and_uses_polyphase_resampling(self):
        source = pcm16([(-32768, 32767), (0, 0)], 22050)
        value = to_stereo_44100(source)
        self.assertEqual((value.sample_rate, value.channels, value.frames), (44100, 2, 4))
        self.assertLess(value.samples[0], -.9)
        self.assertGreater(value.samples[1], .9)
        self.assertLess(value.samples[2], 0.)
        self.assertGreater(value.samples[3], 0.)

    @unittest.skipUnless(HAS_ARRAY_RUNTIME, "requires local NumPy and SciPy model runtime")
    def test_basic_pitch_receives_actual_mono_frontend_after_stereo_umx(self):
        separated = FloatPCM((1., -1., .5, -.5, 0., 0., -.5, .5), 44100, 2)
        mono = basic_pitch_mono(separated)
        self.assertEqual(len(mono), 2)
        self.assertTrue(all(abs(float(value)) < .1 for value in mono))
        self.assertEqual(BASIC_PITCH_SAMPLE_RATE, 22050)

    def test_factory_verifies_both_artifacts_before_loading_any_runtime(self):
        umx = artifact(self.root / "umxhq.pth", b"umx")
        pitch = artifact(self.root / "nmp.onnx", b"pitch")
        calls = []
        runtime = PinnedBassRuntime(umx, pitch, lambda path: calls.append(path), lambda path: calls.append(path))
        umx.path.write_bytes(b"replaced")
        with self.assertRaisesRegex(RuntimeError, "BASS_ARTIFACT_SHA_MISMATCH"):
            runtime.create()
        self.assertEqual(calls, [])

    def test_concrete_session_records_the_same_two_artifact_identity_as_the_worker_profile(self):
        umx = artifact(self.root / "umxhq.pth", b"umx")
        pitch = artifact(self.root / "nmp.onnx", b"pitch")
        session = PinnedBassRuntime(umx, pitch, lambda path: Separator(), lambda path: Onset()).create()
        self.assertEqual(session.artifact_sha256,
                         "08c29eb27008e31fcefb150311d873c5ff5c2f17789574767fbb068c6496ad99")

    def test_pcm_decoder_handles_unsigned_8_bit_and_signed_24_bit_boundaries(self):
        eight = PCM(bytes((0, 128, 255)), 8000, 1, 1, 3)
        self.assertEqual(decode_pcm(eight).samples, (-1.0, 0.0, 127 / 128.0))
        raw = (-8388608).to_bytes(3, "little", signed=True) + (8388607).to_bytes(3, "little", signed=True)
        twenty_four = PCM(raw, 8000, 1, 3, 2)
        self.assertEqual(decode_pcm(twenty_four).samples, (-1.0, 8388607 / 8388608.0))

    @unittest.skipUnless(HAS_ARRAY_RUNTIME, "requires local NumPy and SciPy model runtime")
    def test_two_channel_runtime_filters_pitch_merges_nearby_stereo_onsets_and_keeps_attack_velocity_separate(self):
        umx = artifact(self.root / "umxhq.pth", b"umx")
        pitch = artifact(self.root / "nmp.onnx", b"pitch")
        separator, onset = Separator(), Onset()
        session = PinnedBassRuntime(umx, pitch, lambda path: separator, lambda path: onset).create()
        result = session.analyse(pcm16([(1, -1)] * 96000, 48000), 9)
        self.assertEqual(len(separator.calls), 1)
        self.assertEqual(separator.calls[0].sample_rate, 44100)
        self.assertEqual(len(onset.calls), 1)
        self.assertEqual(result, [{"lane": "BASS", "sample_index": 9, "velocity": 26, "confidence": .6}])

    @unittest.skipUnless(HAS_ARRAY_RUNTIME, "requires local NumPy and SciPy model runtime")
    def test_runtime_rejects_non_float_or_wrong_rate_separator_output_without_fallback(self):
        umx = artifact(self.root / "umxhq.pth", b"umx")
        pitch = artifact(self.root / "nmp.onnx", b"pitch")
        class BadSeparator(object):
            def separate(self, pcm): return FloatPCM((0.,), 22050, 1)
        class NeverOnset(object):
            def predict_onsets(self, mono): raise AssertionError("must not be called")
        session = PinnedBassRuntime(umx, pitch, lambda path: BadSeparator(), lambda path: NeverOnset()).create()
        with self.assertRaisesRegex(RuntimeError, "BASS_SEPARATOR_INVALID"):
            session.analyse(pcm16([(1, -1)]), 0)

    @unittest.skipUnless(HAS_ARRAY_RUNTIME, "requires local NumPy and SciPy model runtime")
    def test_fixed_input_invokes_one_separator_and_one_basic_pitch_call(self):
        umx = artifact(self.root / "umxhq.pth", b"umx")
        pitch = artifact(self.root / "nmp.onnx", b"pitch")
        separator, onset = Separator(), Onset()
        session = PinnedBassRuntime(umx, pitch, lambda path: separator, lambda path: onset).create()
        session.analyse(pcm16([(1, -1)] * 32), 0)
        self.assertEqual(len(separator.calls), 1)
        self.assertEqual(len(onset.calls), 1)

    @unittest.skipUnless(HAS_ARRAY_RUNTIME, "requires local NumPy and SciPy model runtime")
    def test_digital_silence_returns_no_bass_without_invoking_models(self):
        umx = artifact(self.root / "umxhq.pth", b"umx")
        pitch = artifact(self.root / "nmp.onnx", b"pitch")
        separator, onset = Separator(), Onset()
        session = PinnedBassRuntime(umx, pitch, lambda path: separator, lambda path: onset).create()
        self.assertEqual(session.analyse(pcm16([(0, 0)] * 32), 0), [])
        self.assertEqual(separator.calls, [])
        self.assertEqual(onset.calls, [])

    def test_postprocessor_refuses_malformed_records_instead_of_emitting_partial_candidates(self):
        with self.assertRaisesRegex(RuntimeError, "BASS_CONFIDENCE_INVALID"):
            merge_channel_onsets(([{"frame": 0, "midi_pitch": 36, "onset_confidence": .5, "attack_strength": .5}],
                                 [{"frame": 1, "midi_pitch": 36, "onset_confidence": 2., "attack_strength": .5}]), 22050, 0)

    @unittest.skipUnless(HAS_ARRAY_RUNTIME, "requires local NumPy and SciPy model runtime")
    def test_onnx_adapter_uses_published_window_and_output_names(self):
        onnx = FakeOnnx()
        records = BasicPitchOnnxSession(onnx, threshold=.5, gap_frames=8).predict_onsets(__import__("numpy").zeros(22050, dtype="float32"))
        self.assertEqual(len(onnx.calls), 1)
        outputs, feeds = onnx.calls[0]
        self.assertEqual(outputs, ["StatefulPartitionedCall:1", "StatefulPartitionedCall:2"])
        self.assertEqual(feeds["serving_default_input_2:0"].shape, (1, 43844, 1))
        self.assertEqual(records[0]["frame"], 15)
        self.assertEqual(records[0]["midi_pitch"], 36)
        self.assertAlmostEqual(records[0]["onset_confidence"], .8, places=6)
        self.assertAlmostEqual(records[0]["attack_strength"], .8, places=6)

    @unittest.skipUnless(HAS_ARRAY_RUNTIME, "requires local NumPy and SciPy model runtime")
    def test_basic_pitch_88_column_offset_includes_midi_28_to_60_and_excludes_adjacent_columns(self):
        records = BasicPitchOnnxSession(BoundaryOnnx(), threshold=.5, gap_frames=8).predict_onsets(__import__("numpy").zeros(22050, dtype="float32"))
        self.assertEqual([(record["frame"], record["midi_pitch"]) for record in records], [(15, 28), (35, 60)])

if __name__ == "__main__": unittest.main()
