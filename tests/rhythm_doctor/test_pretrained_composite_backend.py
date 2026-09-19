"""Five-lane pretrained backend integration and bounded-work tests.

Characterisation outside README: deterministic session doubles exercise the
published raw-head/BASS adapter boundary; they contain no learned model.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import wave

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
EXECUTABLE = ROOT / "tools" / "rhythm_doctor" / "pretrained_composite_backend.py"
sys.path.insert(0, str(ROOT / "tools" / "rhythm_doctor"))
import pretrained_composite_backend as composite
from pretrained_bass_backend import BassPipeline, PCM, PinnedArtifact
import rd_analysis_worker


class Input(object):
    name = "patches"


class DrumSession(object):
    def __init__(self):
        self.calls = []

    def get_inputs(self):
        return [Input()]

    def run(self, names, feed):
        self.calls.append(feed["patches"])
        output = np.zeros((len(feed["patches"]), 13, 4, 1), dtype=np.float32)
        for head in (0, 1, 4, 6):
            output[0, head, 0, 0] = .9
        return [output]


class Features(object):
    def __init__(self):
        self.calls = []

    def extract(self, pcm):
        self.calls.append(pcm)
        return {"features": np.zeros((4, 120, 120), dtype=np.float32),
                "mini_beats": np.asarray((0., .1, .2, .3)), "bpm": 120., "origin_sample": 7}


class Separator(object):
    def __init__(self): self.calls = []
    def separate(self, pcm):
        self.calls.append(pcm)
        return PCM(b"\0\0" * pcm.frames, pcm.sample_rate, 1, 2, pcm.frames)


class Onsets(object):
    def __init__(self): self.calls = []
    def predict_onsets(self, pcm):
        self.calls.append(pcm)
        return [{"frame": 0, "midi_pitch": 36, "onset_confidence": .7, "attack_strength": .5}]


def pinned(path, value):
    path.write_bytes(value)
    return PinnedArtifact(path.name, path, hashlib.sha256(value).hexdigest())


class CompositeBackendTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="rd-composite-")
        self.root = Path(self.temporary.name)
        self.wav = self.root / "capture.wav"
        with wave.open(str(self.wav), "wb") as output:
            output.setnchannels(1); output.setsampwidth(2); output.setframerate(22050); output.writeframes(b"\0\0" * 22050)
        self.drum_model = self.root / "drum.onnx"; self.drum_model.write_bytes(b"drum")
        self.drum_sha = hashlib.sha256(self.drum_model.read_bytes()).hexdigest()
        self.drum = DrumSession(); self.features = Features(); self.separator = Separator(); self.onsets = Onsets()
        self.bass = BassPipeline(self.separator, self.onsets, pinned(self.root / "umxhq.pth", b"separator"),
                                 pinned(self.root / "basic-pitch.tflite", b"onsets"))
        self.runtime = composite.CompositeRuntime(self.drum, self.drum_model, self.features,
                                                  {"BD": .5, "SD": .5, "CHH": .5, "OHH": .5}, self.bass, .4)
        self.request = {"wav_path": str(self.wav), "pretrained": {"backend_sha256": "a" * 64,
                        "drum_artifact_sha256": self.drum_sha, "bass_artifact_sha256": self.bass.artifact_sha256}}

    def tearDown(self): self.temporary.cleanup()

    def test_composes_raw_drum_heads_and_pinned_bass_into_one_worker_valid_five_lane_result(self):
        value = composite.compose(self.request, self.runtime)
        self.assertEqual(set(value["lane_onset_gates"]), {"BD", "SD", "CHH", "OHH", "BASS"})
        self.assertEqual(value["detector"], {"backend_id": composite.BACKEND_ID, **self.request["pretrained"]})
        self.assertTrue(rd_analysis_worker.analysis_is_pretrained(value, **self.request["pretrained"]))
        self.assertEqual([candidate["lane"] for candidate in value["candidates"]], ["BD", "SD", "CHH", "OHH", "BASS"])
        self.assertTrue(all(candidate["sample_index"] == 7 for candidate in value["candidates"]))
        self.assertEqual(value["candidates"][-1], {"lane": "BASS", "sample_index": 7, "velocity": 64, "confidence": .7})

    def test_pin_mismatch_fails_closed_without_returning_a_four_lane_fallback(self):
        self.request["pretrained"]["bass_artifact_sha256"] = "0" * 64
        with self.assertRaisesRegex(composite.CompositeError, "BASS_PROFILE_MISMATCH"):
            composite.compose(self.request, self.runtime)

    def test_changed_drum_weight_fails_before_onnx_session_execution(self):
        self.drum_model.write_bytes(b"changed")
        with self.assertRaisesRegex(composite.CompositeError, "OMNIZART_ARTIFACT_SHA256_MISMATCH"):
            composite.compose(self.request, self.runtime)
        self.assertEqual(self.drum.calls, [])
        self.assertEqual(self.separator.calls, [])

    def test_fixed_four_frame_window_uses_one_drum_batch_and_one_bass_inference_each(self):
        composite.compose(self.request, self.runtime)
        self.assertEqual(len(self.features.calls), 1)
        self.assertEqual(len(self.drum.calls), 1)
        self.assertEqual(len(self.separator.calls), 1)
        self.assertEqual(len(self.onsets.calls), 1)
        self.assertEqual(self.drum.calls[0].shape, (32, 120, 120, 4))

    def test_executable_cli_writes_only_the_complete_result(self):
        request = self.root / "request.json"; result = self.root / "result.json"
        request.write_text(json.dumps(self.request), encoding="utf-8")
        with mock.patch.object(composite, "load_factory", return_value=self.runtime) as load:
            self.assertEqual(composite.main(["--request", str(request), "--result", str(result),
                                             "--runtime-factory", "unused.py:make",
                                             "--runtime-factory-sha256", "f" * 64]), 0)
        load.assert_called_once_with("unused.py:make", "f" * 64)
        value = json.loads(result.read_text(encoding="utf-8"))
        self.assertEqual(value["detector"]["bass_artifact_sha256"], self.bass.artifact_sha256)
        self.assertEqual(set(candidate["lane"] for candidate in value["candidates"]), set(composite.LANES))

    def test_subprocess_factory_is_the_same_request_result_abi_consumed_by_analysis_worker(self):
        request = self.root / "process-request.json"; result = self.root / "process-result.json"
        request.write_text(json.dumps(self.request), encoding="utf-8")
        factory = self.root / "pinned_factory.py"
        separator_sha = self.bass.separator_artifact.sha256
        onset_sha = self.bass.onset_artifact.sha256
        factory.write_text("""import numpy as np
from pretrained_composite_backend import CompositeRuntime
from pretrained_bass_backend import BassPipeline, PCM, PinnedArtifact
class I: name = 'patches'
class D:
 def get_inputs(self): return [I()]
 def run(self, names, feed):
  result=np.zeros((len(feed['patches']),13,4,1),dtype=np.float32)
  for head in (0,1,4,6): result[0,head,0,0]=.9
  return [result]
class F:
 def extract(self, pcm): return {'features':np.zeros((4,120,120),dtype=np.float32),'mini_beats':np.asarray((0.,.1,.2,.3)),'bpm':120.,'origin_sample':7}
class S:
 def separate(self, pcm): return PCM(b'\\0\\0'*pcm.frames,pcm.sample_rate,1,2,pcm.frames)
class O:
 def predict_onsets(self, pcm): return [{'frame':0,'midi_pitch':36,'onset_confidence':.7,'attack_strength':.5}]
def make():
 return CompositeRuntime(D(),r'%s',F(),{'BD':.5,'SD':.5,'CHH':.5,'OHH':.5},BassPipeline(S(),O(),PinnedArtifact('umxhq',r'%s','%s'),PinnedArtifact('basic',r'%s','%s')),.4)
""" % (self.drum_model, self.bass.separator_artifact.path, separator_sha,
         self.bass.onset_artifact.path, onset_sha), encoding="utf-8")
        environment = dict(os.environ,
                           RHYTHM_DOCTOR_PRETRAINED_RUNTIME_FACTORY=str(factory) + ":make",
                           RHYTHM_DOCTOR_PRETRAINED_RUNTIME_FACTORY_SHA256=hashlib.sha256(factory.read_bytes()).hexdigest())
        # This is the exact argv used by rd_analysis_worker; runtime provisioning
        # is inherited as a separately pinned local deployment setting.
        process = subprocess.run([sys.executable, str(EXECUTABLE), "--request", str(request), "--result", str(result)],
                                 env=environment, text=True, capture_output=True, timeout=10)
        self.assertEqual(process.returncode, 0, process.stderr)
        value = json.loads(result.read_text(encoding="utf-8"))
        self.assertEqual(value["detector"], {"backend_id": composite.BACKEND_ID, **self.request["pretrained"]})
        self.assertEqual([candidate["lane"] for candidate in value["candidates"]], ["BD", "SD", "CHH", "OHH", "BASS"])


if __name__ == "__main__":
    unittest.main()
