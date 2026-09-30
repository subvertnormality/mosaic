"""The remote server's HTTP contract, over a real socket.

The models are stubbed. What is under test is the transport, the capture
decoding and the shape of the result -- the parts Mosaic depends on and the
parts that do not need a GPU to be wrong.
"""
import io
import json
import struct
import sys
import threading
import unittest
import urllib.error
import urllib.request
import wave
from http.server import ThreadingHTTPServer
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "rhythm_doctor_server"))
import lanes
import pipeline
import server

SR = 44100
BPM = 120.0


def groove(bars=12, sr=SR, bpm=BPM, lead=0.75):
    beat = 60.0 / bpm
    length = int((lead + bars * 4 * beat + 1.0) * sr)
    x = np.zeros(length, dtype=np.float32)
    span = int(0.08 * sr)
    env = np.exp(-np.linspace(0, 10, span)).astype(np.float32)
    for bar in range(bars):
        for index in range(4):
            at = int((lead + (bar * 4 + index) * beat) * sr)
            amp = 1.0 if index == 0 else 0.5
            tone = np.sin(2 * np.pi * 90 * np.arange(span) / sr).astype(np.float32)
            seg = (tone * env * amp)[:max(0, length - at)]
            x[at:at + len(seg)] += seg
    return x / (np.abs(x).max() + 1e-9)


def wav_bytes(mono, sr=SR, width=2, channels=1):
    """Encode as the device would. width=3 is what softcut actually writes."""
    if width == 2:
        payload = (np.clip(mono, -1, 1) * 32767).astype("<i2").tobytes()
    elif width == 3:
        scaled = (np.clip(mono, -1, 1) * 8388607).astype(np.int32)
        payload = np.stack([scaled & 0xFF, (scaled >> 8) & 0xFF,
                            (scaled >> 16) & 0xFF], axis=1).astype(np.uint8).tobytes()
    else:
        payload = np.asarray(mono, dtype="<f4").tobytes()
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as out:
        out.setnchannels(channels); out.setsampwidth(width); out.setframerate(sr)
        out.writeframes(payload)
    return buffer.getvalue()


def stub_models():
    """Stand-ins that keep the assembly honest without the real weights."""
    beat = int(SR * 60 / BPM)
    def track(mono, sample_rate):
        beats = list(range(int(0.75 * SR), int(mono.size), beat))
        return beats, beats[::4]
    def separate(mono, sample_rate):
        stems = {name: np.zeros_like(mono) for name in lanes.DEMUCS_STEMS}
        stems["drums"] = mono
        stems["bass"] = mono * 0.5
        return stems
    def separate_drums(drums, sample_rate):
        return {"kick": drums, "snare": drums * 0.0, "toms": drums * 0.0,
                "hihat": drums * 0.0, "cymbals": drums * 0.0}
    return pipeline.Models(separate=separate, separate_drums=separate_drums,
                           track_beats=track,
                           identity={"backend_id": "remote-test", "separator": "stub"})


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        server.Handler.service = server.Service(stub_models())
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown(); cls.httpd.server_close(); cls.thread.join(timeout=5)

    def url(self, path):
        return "http://127.0.0.1:%d%s" % (self.port, path)

    def post(self, body, alignment=None):
        request = urllib.request.Request(self.url("/v1/analyse"), data=body, method="POST")
        if alignment is not None:
            request.add_header("X-Rhythm-Doctor-Alignment", json.dumps(alignment))
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, json.loads(response.read())

    def test_health_advertises_the_lane_set_before_any_capture(self):
        """Mosaic needs the lane list to lay out the grid, and needs it without
        having recorded anything yet."""
        with urllib.request.urlopen(self.url("/v1/health"), timeout=10) as response:
            value = json.loads(response.read())
        self.assertTrue(value["ready"])
        self.assertEqual(value["lanes"], list(lanes.LANES))
        self.assertGreater(len(value["lanes"]), 3, "the point is more lanes than DSP")
        self.assertEqual(set(value["lane_onset_gates"]), set(lanes.LANES))

    def test_a_capture_comes_back_in_the_shape_the_worker_accepts(self):
        status, value = self.post(wav_bytes(groove()))
        self.assertEqual(status, 200)
        for key in ("bpm", "tempo_detected", "origin_sample", "tempo_mode",
                    "phrase_start_sample", "phrase_confidence", "beat_positions",
                    "lane_onset_gates", "candidates", "detector"):
            self.assertIn(key, value)
        self.assertTrue(40 <= value["bpm"] <= 240)
        self.assertEqual(set(value["lane_onset_gates"]), set(lanes.LANES))
        self.assertTrue(value["candidates"], "a groove must produce gates")
        for candidate in value["candidates"]:
            self.assertIn(candidate["lane"], lanes.LANES)
            self.assertTrue(1 <= candidate["velocity"] <= 127)
            self.assertTrue(0 <= candidate["confidence"] <= 1)
            self.assertGreaterEqual(candidate["sample_index"], 0)

    def test_no_candidate_carries_a_note(self):
        """Velocity yes, pitch no: the bank has nowhere to put a note number,
        so transcribing one would be work whose result is discarded."""
        _, value = self.post(wav_bytes(groove()))
        for candidate in value["candidates"]:
            for forbidden in ("note", "pitch", "midi_note", "frequency"):
                self.assertNotIn(forbidden, candidate)

    def test_it_reads_the_24_bit_wav_softcut_actually_writes(self):
        """The device records through softcut, which writes 24-bit PCM. Python's
        wave module reads those frames but will not convert them."""
        status, value = self.post(wav_bytes(groove(), width=3))
        self.assertEqual(status, 200)
        self.assertTrue(value["candidates"])

    def test_it_reads_a_stereo_capture(self):
        mono = groove()
        stereo = np.repeat(mono[:, None], 2, axis=1).ravel()
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as out:
            out.setnchannels(2); out.setsampwidth(2); out.setframerate(SR)
            out.writeframes((np.clip(stereo, -1, 1) * 32767).astype("<i2").tobytes())
        status, value = self.post(buffer.getvalue())
        self.assertEqual(status, 200)
        self.assertTrue(value["candidates"])

    def test_the_phrase_start_is_reported_and_is_a_tracked_downbeat(self):
        _, value = self.post(wav_bytes(groove()))
        self.assertGreater(value["phrase_start_sample"], 0)
        self.assertIn(value["phrase_start_sample"], value["beat_positions"])
        cell = SR * 15 / value["bpm"]
        offset = (value["phrase_start_sample"] - value["origin_sample"]) / cell
        self.assertLess(abs(offset - round(offset)), 0.01)

    def test_a_player_correction_is_honoured(self):
        _, value = self.post(wav_bytes(groove()), alignment={"bpm": 96.0, "origin_sample": 4410})
        self.assertEqual(value["tempo_mode"], "manual")
        self.assertEqual(value["origin_sample"], 4410)
        self.assertEqual(value["bpm"], 96.0)

    def test_silence_is_a_valid_empty_result(self):
        status, value = self.post(wav_bytes(np.zeros(SR * 2, dtype=np.float32)))
        self.assertEqual(status, 200)
        self.assertEqual(value["candidates"], [])
        self.assertFalse(value["tempo_detected"])

    def test_the_capture_digest_is_returned_so_the_client_can_match_it(self):
        body = wav_bytes(groove())
        import hashlib
        _, value = self.post(body)
        self.assertEqual(value["capture_sha256"], hashlib.sha256(body).hexdigest())

    def test_rubbish_is_refused_rather_than_analysed(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.post(b"this is not a wav file at all")
        self.assertEqual(caught.exception.code, 400)

    def test_an_over_long_capture_is_refused(self):
        long = np.zeros(SR * (server.MAX_CAPTURE_SECONDS + 5), dtype=np.float32)
        long[::1000] = 0.5
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.post(wav_bytes(long))
        self.assertEqual(caught.exception.code, 413)

    def test_an_unknown_path_is_not_served(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(self.url("/v1/everything"), timeout=10)
        self.assertEqual(caught.exception.code, 404)


class CaptureRateTests(unittest.TestCase):
    """A norns does not record at 44100.

    Every other test here uses 44100, which is why a capture at the device's
    real rate reached the server and was refused outright: demucs raises on a
    rate it was not trained at. Beat This! would have been worse -- it accepts
    any rate and reports a tempo scaled by the ratio, so the capture would have
    come back plausible and wrong.
    """

    @classmethod
    def setUpClass(cls):
        server.Handler.service = server.Service(stub_models())
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown(); cls.httpd.server_close(); cls.thread.join(timeout=5)

    def post(self, body):
        request = urllib.request.Request(
            "http://127.0.0.1:%d/v1/analyse" % self.port, data=body, method="POST")
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read())

    def test_a_48k_capture_is_analysed_rather_than_refused(self):
        rate = 48000
        value = self.post(wav_bytes(groove(sr=rate), sr=rate, width=3))
        self.assertTrue(value["candidates"], "a 48kHz capture must produce gates")
        self.assertTrue(40 <= value["bpm"] <= 240)

    def test_positions_come_back_in_the_captures_own_coordinates(self):
        """The bank addresses samples of the file the player recorded, not of
        the server's resampled working copy. Reporting analysis-rate indices
        would place every gate about 9% early on a 48kHz capture."""
        rate = 48000
        mono = groove(sr=rate)
        value = self.post(wav_bytes(mono, sr=rate, width=3))
        for candidate in value["candidates"]:
            self.assertLess(candidate["sample_index"], mono.size,
                            "an onset past the end of the capture is out of coordinates")
        for beat in value["beat_positions"]:
            self.assertLess(beat, mono.size)
        self.assertLess(value["phrase_start_sample"], mono.size)
        self.assertLess(value["origin_sample"], mono.size)

    def test_the_tempo_is_not_scaled_by_the_rate_ratio(self):
        """The stub tracker places beats on a real grid, so a mishandled rate
        shows up as a tempo off by exactly 48000/44100."""
        at_44 = self.post(wav_bytes(groove(sr=44100), sr=44100))
        at_48 = self.post(wav_bytes(groove(sr=48000), sr=48000, width=3))
        self.assertAlmostEqual(at_44["bpm"], at_48["bpm"], delta=2.0,
                               msg="%.2f vs %.2f" % (at_44["bpm"], at_48["bpm"]))

    def test_resampling_preserves_length_within_a_sample(self):
        mono = np.zeros(48000, dtype=np.float32)
        out = pipeline.resample(mono, 48000, 44100)
        self.assertAlmostEqual(len(out), 44100, delta=1)
        self.assertIs(pipeline.resample(mono, 44100, 44100).dtype.type, np.float32)


class UnreadyServerTests(unittest.TestCase):
    """A server whose models failed to load must say so, not pretend."""

    def test_health_reports_the_fault_and_analysis_is_refused(self):
        service = server.Service(None, "demucs is not installed")
        self.assertFalse(service.ready())
        with self.assertRaises(RuntimeError):
            service.analyse(np.zeros(10, dtype=np.float32), SR, None)


if __name__ == "__main__":
    unittest.main()
