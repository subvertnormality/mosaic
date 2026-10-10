"""Characterisation: authorized Manual Start Beat sample-grid/provenance.

Pure oracle guards supplement, and never replace, public native acceptance.
No fabricated bank is passed to Mosaic; no emulator is launched.
"""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tests/behaviour'))
from contract.rhythm_doctor_start_beat import regular_grid, correction


def envelope(origin=0, revision=1):
    return dict(status='COMPLETED', command='ANALYSE', frames=100001,
                sample_rate=48000, wav_sha256='actual-wave-identity',
                project_id='actual-project', generation=1,
                job_id='analysis-' + str(revision), analysis_revision=revision,
                analysis=dict(tempo_mode='manual', bpm=120,
                              origin_sample=origin, phrase_start_sample=origin,
                              beat_positions=[0,24000,48000,72000,96000],
                              candidates=[dict(sample=32001, strength=.5)],
                              detector='recorded-detector'))


class ManualStartBeatGuards(unittest.TestCase):
    def test_old_singleton_cannot_qualify_regular_capture_grid(self):
        old = envelope()
        old['analysis']['beat_positions'] = [0]
        with self.assertRaisesRegex(AssertionError, 'whole actual capture'):
            regular_grid(old)

    def test_origin_second_beat_retains_absolute_first_beat(self):
        self.assertEqual(regular_grid(envelope(24000), origin=24000),
                         [0,24000,48000,72000,96000])
        self.assertEqual(regular_grid(envelope()), [0,24000,48000,72000,96000])

    def test_apply_and_restore_bind_same_wave_exact_revisions(self):
        original = envelope()
        advanced = envelope(24000,2)
        restored = envelope(0,3)
        self.assertIs(correction(original,advanced,24000), advanced)
        self.assertIs(correction(advanced,restored,0), restored)

    def test_recording_or_candidate_mutation_refuses_correction(self):
        previous = envelope()
        candidate = envelope(24000,2)
        for key, value in [('wav_sha256','other-wave'), ('frames',100002),
                           ('sample_rate',44100), ('generation',2),
                           ('project_id','other-project'), ('analysis_revision',3),
                           ('job_id',previous['job_id'])]:
            changed = copy.deepcopy(candidate)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(AssertionError):
                correction(previous,changed,24000)
        changed = copy.deepcopy(candidate)
        changed['analysis']['candidates'][0]['sample'] += 24000
        with self.assertRaisesRegex(AssertionError, 'absolute sample'):
            correction(previous,changed,24000)

    def test_wrong_phase_or_partial_capture_grid_refused(self):
        for positions in ([24000,48000,72000,96000], [0,24001,48000,72000,96000],
                          [0,24000,48000,72000,96000,120000]):
            changed = envelope(24000)
            changed['analysis']['beat_positions'] = positions
            with self.subTest(positions=positions), self.assertRaises(AssertionError):
                regular_grid(changed,origin=24000)
