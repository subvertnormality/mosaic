"""Unit and protocol integration coverage for the injected pretrained BASS path.

Characterisation outside README: the adapter consumes Basic Pitch's frozen
frame coordinate and maps its separately reported attack strength to velocity.
No fake session is a classifier; it only records the exact PCM contract.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import wave


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "tools" / "rhythm_doctor" / "pretrained_bass_backend.py"
sys.path.insert(0, str(BACKEND.parent))
from pretrained_bass_backend import (BassPipeline, PCM, PipelineError, PinnedArtifact,
                                     basic_pitch_frame_time, run_request)


LANES = ("BD", "SD", "CHH", "OHH", "BASS")


class Separator(object):
    def __init__(self):
        self.calls = []

    def separate(self, pcm):
        self.calls.append(pcm)
        return PCM(b"\0\0" * pcm.frames, pcm.sample_rate, 1, 2, pcm.frames)


class Onsets(object):
    def __init__(self, values):
        self.values = values
        self.calls = []

    def predict_onsets(self, pcm):
        self.calls.append(pcm)
        return self.values


class Runtime(object):
    def __init__(self, pipeline, base, gate=.35):
        self.bass_pipeline = pipeline
        self.base = base
        self.bass_gate = gate

    def analyse_drums(self, request):
        self.request = request
        return self.base


def artifact(path, name):
    path.write_bytes(name.encode("ascii"))
    return PinnedArtifact(name, path, hashlib.sha256(path.read_bytes()).hexdigest())


def base_analysis(origin=100):
    return {"bpm": 120, "origin_sample": origin,
            "detector": {"backend_id": "omnizart-raw-heads", "drum_artifact_sha256": "b" * 64},
            "lane_onset_gates": dict((lane, .5) for lane in LANES),
            "candidates": [{"lane": "BD", "sample_index": origin, "velocity": 80, "confidence": .8}]}


def pinned_request(wav, pipeline):
    return {"wav_path": str(wav), "pretrained": {"backend_sha256": "d" * 64,
            "drum_artifact_sha256": "b" * 64, "bass_artifact_sha256": pipeline.artifact_sha256}}


class PretrainedBassPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="rd-pretrained-bass-")
        self.root = Path(self.temporary.name)
        self.separator = Separator()
        self.onsets = Onsets([
            {"frame": 172, "midi_pitch": 40, "onset_confidence": .9, "attack_strength": .25},
            {"frame": 0, "midi_pitch": 61, "onset_confidence": .8, "attack_strength": .99},
        ])
        self.pipeline = BassPipeline(self.separator, self.onsets,
                                     artifact(self.root / "umxhq.pth", "umxhq"),
                                     artifact(self.root / "basic-pitch.tflite", "basic-pitch"))

    def tearDown(self):
        self.temporary.cleanup()

    def test_separation_pcm_then_basic_pitch_frame_produces_bass_only_candidate(self):
        source = PCM(b"\0\0\0\0" * 50000, 22050, 2, 2, 50000)
        candidates = self.pipeline.analyse(source, 100)
        self.assertEqual(self.separator.calls, [source])
        self.assertEqual(len(self.onsets.calls), 1)
        self.assertEqual(candidates, [{"lane": "BASS",
                                       "sample_index": 100 + int(basic_pitch_frame_time(172) * 22050 + .5),
                                       "velocity": 33, "confidence": .9}])

    def test_pitch_filter_does_not_turn_non_bass_basic_pitch_notes_into_hits(self):
        self.onsets.values = [{"frame": 0, "midi_pitch": 27, "onset_confidence": 1., "attack_strength": 1.},
                              {"frame": 1, "midi_pitch": 61, "onset_confidence": 1., "attack_strength": 1.}]
        self.assertEqual(self.pipeline.analyse(PCM(b"\0\0", 22050, 1, 2, 1), 0), [])

    def test_artifact_mismatch_fails_closed_before_either_inference_session_runs(self):
        self.pipeline.separator_artifact.path.write_bytes(b"replaced")
        with self.assertRaisesRegex(PipelineError, "BASS_ARTIFACT_SHA_MISMATCH"):
            self.pipeline.analyse(PCM(b"\0\0", 22050, 1, 2, 1), 0)
        self.assertEqual(self.separator.calls, [])
        self.assertEqual(self.onsets.calls, [])

    def test_malformed_bass_onset_rejects_the_whole_result_instead_of_publishing_a_partial_lane(self):
        self.onsets.values.append({"frame": 2, "midi_pitch": 40, "onset_confidence": .5, "attack_strength": 2.})
        with self.assertRaisesRegex(PipelineError, "BASS_ATTACK_INVALID"):
            self.pipeline.analyse(PCM(b"\0\0", 22050, 1, 2, 1), 0)

    def test_merge_requires_drum_path_to_have_no_bass_fallback_and_keeps_velocity_separate_from_confidence(self):
        wav = self.root / "capture.wav"
        with wave.open(str(wav), "wb") as output:
            output.setnchannels(1); output.setsampwidth(2); output.setframerate(22050); output.writeframes(b"\0\0" * 22050)
        analysis = run_request(pinned_request(wav, self.pipeline), Runtime(self.pipeline, base_analysis()))
        self.assertEqual(analysis["lane_onset_gates"]["BASS"], .35)
        self.assertEqual(analysis["candidates"][-1]["velocity"], 33)
        self.assertEqual(analysis["candidates"][-1]["confidence"], .9)
        self.assertEqual(analysis["detector"]["bass_artifact_sha256"], self.pipeline.artifact_sha256)
        forbidden = base_analysis(); forbidden["candidates"].append({"lane": "BASS"})
        with self.assertRaisesRegex(PipelineError, "DRUM_BASS_FALLBACK_FORBIDDEN"):
            run_request(pinned_request(wav, self.pipeline), Runtime(self.pipeline, forbidden))


class PretrainedBassBackendProtocolTests(unittest.TestCase):
    def test_cli_factory_creates_a_generic_worker_compatible_five_lane_result_without_model_download(self):
        with tempfile.TemporaryDirectory(prefix="rd-pretrained-bass-cli-") as temporary:
            root = Path(temporary)
            separator, onset = root / "umxhq.pth", root / "basic.tflite"
            separator.write_bytes(b"sep"); onset.write_bytes(b"onset")
            wav = root / "capture.wav"
            with wave.open(str(wav), "wb") as output:
                output.setnchannels(1); output.setsampwidth(2); output.setframerate(22050); output.writeframes(b"\0\0" * 22050)
            factory = root / "injected_runtime.py"
            sep_sha = hashlib.sha256(separator.read_bytes()).hexdigest()
            onset_sha = hashlib.sha256(onset.read_bytes()).hexdigest()
            bass_sha = hashlib.sha256(json.dumps({"adapter": "open-unmix-basic-pitch-v1", "basic_pitch": onset_sha,
                                                   "open_unmix": sep_sha}, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
            factory.write_text("""from pretrained_bass_backend import BassPipeline, PCM, PinnedArtifact
import hashlib
class S:
 def separate(self, pcm): return PCM(b'\\0\\0' * pcm.frames, pcm.sample_rate, 1, 2, pcm.frames)
class O:
 def predict_onsets(self, pcm): return [{'frame': 0, 'midi_pitch': 36, 'onset_confidence': .75, 'attack_strength': .5}]
class R:
 bass_gate=.4
 def __init__(self):
  self.bass_pipeline=BassPipeline(S(),O(),PinnedArtifact('umxhq',r'%s','%s'),PinnedArtifact('basic-pitch',r'%s','%s'))
 def analyse_drums(self, request):
  return {'bpm':120,'origin_sample':7,'detector':{'backend_id':'omnizart','drum_artifact_sha256':'b'*64},'lane_onset_gates':dict.fromkeys(('BD','SD','CHH','OHH','BASS'),.5),'candidates':[]}
def make(): return R()
""" % (separator, sep_sha, onset, onset_sha), encoding="utf-8")
            request = root / "request.json"; result = root / "result.json"
            request.write_text(json.dumps({"wav_path": str(wav), "pretrained": {"backend_sha256": "d" * 64,
                                           "drum_artifact_sha256": "b" * 64, "bass_artifact_sha256": bass_sha}}), encoding="utf-8")
            process = subprocess.run([sys.executable, str(BACKEND), "--request", str(request), "--result", str(result),
                                      "--runtime-factory", str(factory) + ":make"], text=True, capture_output=True, timeout=10)
            self.assertEqual(process.returncode, 0, process.stderr)
            value = json.loads(result.read_text(encoding="utf-8"))
            self.assertEqual(set(value["lane_onset_gates"]), set(LANES))
            self.assertEqual(value["candidates"], [{"lane": "BASS", "sample_index": 7, "velocity": 64, "confidence": .75}])
            self.assertEqual(value["detector"]["backend_sha256"], "d" * 64)
            self.assertEqual(value["detector"]["drum_artifact_sha256"], "b" * 64)
            self.assertEqual(value["detector"]["bass_artifact_sha256"], bass_sha)


if __name__ == "__main__":
    unittest.main()
