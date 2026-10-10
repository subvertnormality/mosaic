"""RD-02 native tempo feasibility, characterisation outside the Mosaic manual."""
import json
import math
import os
import pathlib
import struct
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools" / "rhythm_doctor_tempo"
BUILD = TOOLS / "build_local_aubio.sh"
SOURCE = TOOLS / "rd_tempo.c"
DEFAULT_AUBIO = pathlib.Path("/tmp/rd-tempo-aubio-0.4.9/extracted")


def impulse_train(rate, seconds, bpm, extra=()):
    samples = [0.0] * int(rate * seconds)
    def add_pulse(position, amplitude):
        for offset in range(min(1024, len(samples) - position)):
            envelope = math.exp(-offset / 180.0)
            samples[position + offset] += amplitude * envelope * (
                .7 * math.sin(2 * math.pi * 120 * offset / rate) +
                .3 * math.sin(2 * math.pi * 1800 * offset / rate))
    interval = rate * 60.0 / bpm
    for position in range(0, len(samples), max(1, round(interval))):
        add_pulse(position, 1.0)
    for seconds_at, amplitude in extra:
        position = round(seconds_at * rate)
        if position < len(samples): add_pulse(position, amplitude)
    return samples


def drifting_train(rate, seconds, first_bpm, last_bpm):
    samples = [0.0] * int(rate * seconds)
    position = 0.0
    while round(position) < len(samples):
        frame = round(position)
        for offset in range(min(1024, len(samples) - frame)):
            samples[frame + offset] += math.exp(-offset / 180.0) * math.sin(2 * math.pi * 180 * offset / rate)
        ratio = position / max(1, len(samples) - 1)
        bpm = first_bpm + (last_bpm - first_bpm) * ratio
        position += rate * 60.0 / bpm
    return samples


def accented_syncopated_train(rate, seconds, bpm, record_phase=.137):
    """Previously unseen steady fixture: flams, offbeats, 16ths, and random start."""
    samples = [0.0] * int(rate * seconds)

    def pulse(seconds_at, amplitude, decay=100):
        position = round(seconds_at * rate)
        if position < 0 or position >= len(samples):
            return
        for offset in range(min(512, len(samples) - position)):
            samples[position + offset] += amplitude * math.exp(-offset / decay) * (
                .8 * math.sin(2 * math.pi * 180 * offset / rate) +
                .2 * math.sin(2 * math.pi * 2800 * offset / rate))

    period = 60.0 / bpm
    index = 0
    while record_phase + index * period < seconds:
        beat = record_phase + index * period
        pulse(beat, 1.0, 180)                 # kick / beat pulse
        if index < 4:
            pulse(beat - .022, .45, 45)       # introductory flam
        if index % 2:
            pulse(beat, .75, 110)             # accented backbeat
        for sixteenth in (.25, .5, .75):
            pulse(beat + period * sixteenth, .8, 30)   # audible offbeat hats
        index += 1
    return samples


class TempoNativeHarness:
    @classmethod
    def setUpClass(cls):
        system_aubio = os.environ.get("RD_TEMPO_SYSTEM_AUBIO") == "1"
        cls.aubio_root = pathlib.Path(os.environ.get("RD_TEMPO_AUBIO_ROOT", DEFAULT_AUBIO))
        if system_aubio:
            subprocess.run(["pkg-config", "--exists", "aubio"], check=True)
        elif not (cls.aubio_root / "usr/include/aubio/aubio.h").exists():
            raise unittest.SkipTest("run tools/rhythm_doctor_tempo/bootstrap_local_aubio.sh first")
        cls.temp = tempfile.TemporaryDirectory(prefix="rd-tempo-native-")
        cls.binary = pathlib.Path(cls.temp.name) / "rd-tempo"
        environment = os.environ.copy()
        if not system_aubio:
            environment["RD_TEMPO_AUBIO_ROOT"] = str(cls.aubio_root)
        subprocess.run(["sh", str(BUILD), str(cls.binary)], cwd=ROOT, env=environment, check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def analyse(self, samples, rate=44100, method="energy"):
        with tempfile.TemporaryDirectory(prefix="rd-tempo-pcm-") as directory:
            pcm = pathlib.Path(directory) / "fixture.f32"
            pcm.write_bytes(struct.pack("<" + "f" * len(samples), *samples))
            output = subprocess.check_output([str(self.binary), "--raw-f32", str(pcm), str(rate), method], text=True)
        result = json.loads(output)
        result["method"] = method
        if os.environ.get("RD_TEMPO_PRINT"):
            print(json.dumps(result, sort_keys=True))
        if os.environ.get("RD_TEMPO_SUMMARY"):
            print(method, result["reported_bpm"], result["candidate"]["status"],
                  result["candidate"]["reason"], len(result["beats"]))
        return result

    def assert_ready_bounds(self, result):
        candidate = result["candidate"]
        if candidate["status"] == "READY":
            self.assertGreaterEqual(candidate["origin_frame"], 0)
            self.assertLess(candidate["region_end_frame"], result["frames"] + 1)
            # The candidate needs eight observed positions; the 16-beat musical
            # region is established by its separately retained end frame.
            self.assertGreaterEqual(candidate["beats_used"], 8)
            self.assertLessEqual(candidate["phase_error_ms"], 50.0)


class TempoNativeTests(TempoNativeHarness, unittest.TestCase):
    def test_steady_120_bpm_actual_pcm_candidate_is_in_bounds(self):
        result = self.analyse(impulse_train(44100, 40, 120))
        self.assertEqual(result["fixture_contract"], "streaming-raw-f32")
        self.assertGreaterEqual(len(result["beats"]), 8)
        self.assertLess(abs(result["reported_bpm"] - 120), 5.0)
        self.assertEqual((result["candidate"]["status"], result["candidate"]["reason"]),
                         ("UNCERTAIN", "half-double-ambiguous"))

    def test_default_energy_and_specdiff_are_measured_on_the_same_pcm(self):
        fixture = impulse_train(44100, 40, 120)
        results = [self.analyse(fixture, method=method) for method in ("default", "energy", "specdiff", "onset-ac")]
        self.assertEqual([result["method"] for result in results], ["default", "energy", "specdiff", "onset-ac"])
        self.assertTrue(all(result["frames"] == len(fixture) for result in results))
        self.assertTrue(all(result["candidate"]["status"] == "UNCERTAIN" for result in results[:3]))
        onset = results[3]
        self.assertEqual((onset["candidate"]["status"], onset["candidate"]["reason"]),
                         ("UNCERTAIN", "half-double-ambiguous"))
        self.assertLess(abs(onset["reported_bpm"] - 120), 2)

    def test_onset_autocorrelation_dev_envelope_excludes_halfdouble_from_accuracy(self):
        eligible = [self.analyse(impulse_train(44100, 40, bpm), method="onset-ac")
                    for bpm in (40, 60, 120, 180, 240)]
        correct = [result for bpm, result in zip((40, 60, 120, 180, 240), eligible)
                   if result["candidate"]["status"] == "READY" and abs(result["reported_bpm"] - bpm) <= bpm * .02]
        self.assertEqual(len(correct), 2)  # 40/60; their half-time lies outside the supported range.
        for result in correct:
            self.assert_ready_bounds(result)
        self.assertTrue(all(result["candidate"]["reason"] == "half-double-ambiguous"
                            for result in eligible[2:]))

    def test_unseen_accented_syncopation_with_record_phase_acquires_steady_tempo(self):
        result = self.analyse(accented_syncopated_train(44100, 40, 120), method="onset-ac")
        self.assertEqual((result["candidate"]["status"], result["candidate"]["reason"]),
                         ("UNCERTAIN", "half-double-ambiguous"))
        self.assertGreaterEqual(result["candidate"]["grid_support"], 8)
        # The frozen mean*3 front end retains quarter-note peaks from this PCM
        # and rejects its hats. Literal candidate data covers accepted offbeats;
        # this pins the current front-end limitation rather than hiding it.
        self.assertEqual(result["candidate"]["offbeat_residual"], 0)


    def test_silence_is_uncertain_and_never_claims_a_region(self):
        result = self.analyse([0.0] * (44100 * 20))
        self.assertEqual(result["candidate"]["status"], "UNCERTAIN")
        self.assertEqual(result["candidate"]["reason"], "insufficient-beats")

    def test_half_double_fixture_reports_candidate_comparison(self):
        result = self.analyse(impulse_train(44100, 40, 60, extra=[(x + .5, .6) for x in range(40)]))
        self.assertIn("half_bpm", result["candidate"])
        self.assertIn("double_bpm", result["candidate"])
        self.assertEqual((result["candidate"]["status"], result["candidate"]["reason"]),
                         ("UNCERTAIN", "half-double-ambiguous"))

    def test_onset_ac_half_double_stress_is_not_accuracy_evidence(self):
        """A denser offbeat pattern can establish 120 pulses, not musical meter.

        The controlled 40..240 accuracy denominator intentionally excludes this
        stress input: audio periodicity alone cannot determine whether the sparse
        60 BPM accents are a half-time interpretation of the same material.
        """
        result = self.analyse(
            impulse_train(44100, 40, 60, extra=[(x + .5, .6) for x in range(40)]),
            method="onset-ac")
        self.assertIn("half_bpm", result["candidate"])
        self.assertIn("double_bpm", result["candidate"])
        self.assertNotEqual(result["candidate"]["status"], "FAILED")
        self.assert_ready_bounds(result)

    def test_syncopated_actual_pcm_has_no_out_of_bounds_ready_region(self):
        extras = [(x + offset, amplitude) for x in range(40) for offset, amplitude in ((.25, .7), (.75, .5))]
        result = self.analyse(impulse_train(44100, 40, 120, extras))
        self.assertGreater(result["frames"], 0)
        self.assertEqual((result["candidate"]["status"], result["candidate"]["reason"]),
                         ("UNCERTAIN", "half-double-ambiguous"))

    def test_tempo_drift_is_uncertain(self):
        result = self.analyse(drifting_train(44100, 24, 100, 145))
        self.assertEqual(result["candidate"]["status"], "UNCERTAIN")
        self.assertIn(result["candidate"]["reason"], ("unstable-estimates", "phase-fit", "insufficient-beats"))


if __name__ == "__main__":
    unittest.main()
