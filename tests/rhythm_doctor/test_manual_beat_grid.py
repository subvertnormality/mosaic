"""Manual Start Beat acceptance: confirmed timing yields addressable capture beats.

README rhythm-doctor alignment: Start Beat selects a beat, exact BPM and origin
remain player-owned. This is a new Manual-grid feature, not an inferred tempo.
"""
import json
from fractions import Fraction
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / 'tools/rhythm_doctor'
sys.path.insert(0, str(TOOLS))
import dsp_drum_backend as dsp


class ManualBeatGridTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory()
        cls.binary = Path(cls.work.name) / 'rd_analysis_backend'
        source = TOOLS / 'rd_analysis_backend.c'
        done = subprocess.run(['gcc', '-std=c11', '-O2', '-Wall', '-Wextra',
            '-DRD_TEMPLATE_PATH="' + str(TOOLS / 'data/nmf_drum_templates.bin') + '"',
            '-DRD_SOURCE_PATH="' + str(source) + '"', str(source),
            '-o', str(cls.binary), '-lm'], capture_output=True, text=True)
        if done.returncode: raise AssertionError(done.stderr)

    @classmethod
    def tearDownClass(cls): cls.work.cleanup()

    def _results(self, rate, frames, bpm, origin):
        wav = Path(self.work.name) / 'capture.wav'
        with wave.open(str(wav), 'wb') as out:
            out.setnchannels(1); out.setsampwidth(2); out.setframerate(rate)
            out.writeframes(b'\0\0' * frames)
        alignment = dict(bpm=bpm, origin_sample=origin)
        request = Path(self.work.name) / 'request.json'
        result = Path(self.work.name) / 'result.json'
        request.write_text(json.dumps(dict(wav_path=str(wav), alignment=alignment)))
        done = subprocess.run([str(self.binary), '--request', str(request),
                               '--result', str(result)], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        return [('native', json.loads(result.read_text())),
                ('python', dsp.analyse_request(str(wav), alignment=alignment))]

    def _check(self, rate, frames, bpm, origin, expected):
        for backend, value in self._results(rate, frames, bpm, origin):
            with self.subTest(backend=backend, rate=rate, bpm=bpm, origin=origin):
                self.assertEqual(value.get('beat_positions'), expected,
                                 'Manual Start Beat needs the confirmed capture beat grid')
                self.assertEqual(value['bpm'], bpm)
                self.assertEqual(value['origin_sample'], origin)
                self.assertEqual(value['phrase_start_sample'], origin)
                self.assertEqual(value['tempo_mode'], 'manual')
                self.assertEqual(value['candidates'], [])

    def test_manual_capture_start_has_more_than_one_addressable_beat(self):
        self._check(48000, 96000, 120, 0, [0, 24000, 48000, 72000])

    def test_a_corrected_origin_keeps_relevant_beats_before_it(self):
        self._check(48000, 96000, 120, 30000, [6000, 30000, 54000, 78000])

    def test_tempo_and_rate_boundaries_preserve_the_half_open_capture(self):
        for rate in (44100, 48000):
            for bpm in (40, 240):
                with self.subTest(rate=rate, bpm=bpm):
                    spacing = rate * 60 / bpm
                    frames = rate * 3
                    expected = [int(math.floor(k * spacing + .5))
                                for k in range(int(math.ceil(frames / spacing)))
                                if int(math.floor(k * spacing + .5)) < frames]
                    self._check(rate, frames, bpm, 0, expected)

    def test_exact_half_sample_ties_round_up_in_both_backends(self):
        for bpm in (64, 128):
            spacing = Fraction(44100 * 60, bpm)
            expected = []
            for k in range(20):
                sample = k * spacing
                rounded = (2 * sample.numerator + sample.denominator) // (2 * sample.denominator)
                if rounded < 300000: expected.append(rounded)
            self.assertIn(248063, expected, '248062.5 must round up rather than to even 248062')
            self._check(44100, 300000, bpm, 0, expected)

    def test_fractional_spacing_is_rounded_from_the_origin_without_drift(self):
        self._check(44100, 100000, 137, 12345,
                    [12345, 31659, 50973, 70287, 89600])


if __name__ == '__main__': unittest.main()
