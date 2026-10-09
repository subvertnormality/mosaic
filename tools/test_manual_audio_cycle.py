"""The closing MIDI boundary follows the authored cycle length; setups run after
routing (characterisation of the manual audio harness, outside README.md)."""
import copy
import json
import os
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import yaml

REPO = Path(os.environ.get("MOSAIC_MANUAL_ROOT", Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(REPO / "tools"))
import manual_audio
import manual_audio_setups

TICK = 1e9 / 6
ROW = dict(port=1, status=144, note=60, velocity=80, step=0, length=0.5)


def onset_and_release(index, step, length=0.5):
    on = dict(index=index, port=1, bytes=[144, 60, 80], logical_ns=round(step * TICK), monotonic_ns=round(step * TICK))
    off = dict(on, index=index + 1, bytes=[128, 60, 80], logical_ns=round((step + length) * TICK), monotonic_ns=round((step + length) * TICK))
    return [on, off]


def lesson(cycle_steps):
    value = copy.deepcopy(next(v for v in yaml.safe_load((REPO / "manual/audio-scenes.yaml").read_text())["examples"]
                               if v["id"] == "ghost-note-comparison"))
    value["midi_contract"] = dict(cycle_steps=cycle_steps, notes=[dict(ROW)])
    return value


class ClosingBoundary(unittest.TestCase):
    def test_default_keeps_the_sixty_four_step_boundary(self):
        packets = onset_and_release(1, 0) + onset_and_release(3, 64)
        manual_audio.verify_midi_packets(packets, [ROW], 0, "controlled-experimental", allow_boundary=True)
        late = onset_and_release(1, 0) + onset_and_release(3, 128)
        with self.assertRaisesRegex(AssertionError, "64-step boundary"):
            manual_audio.verify_midi_packets(late, [ROW], 0, "controlled-experimental", allow_boundary=True)

    def test_eight_bar_cycle_closes_at_step_one_hundred_twenty_eight(self):
        packets = onset_and_release(1, 0) + onset_and_release(3, 128)
        result = manual_audio.verify_midi_packets(packets, [ROW], 0, "controlled-experimental", allow_boundary=True, cycle_steps=128)
        self.assertTrue(result["passed"])
        early = onset_and_release(1, 0) + onset_and_release(3, 64)
        with self.assertRaisesRegex(AssertionError, "128-step boundary"):
            manual_audio.verify_midi_packets(early, [ROW], 0, "controlled-experimental", allow_boundary=True, cycle_steps=128)

    def test_fractional_swing_onset_keeps_the_controlled_tolerance(self):
        row = dict(ROW, step=4.25, length=0.25)
        packets = onset_and_release(1, 4.25, 0.25)
        manual_audio.verify_midi_packets(packets, [row], 0, "controlled-experimental")
        shifted = onset_and_release(1, 4.25 + 1 / 24, 0.25)
        with self.assertRaisesRegex(AssertionError, "Musical onset"):
            manual_audio.verify_midi_packets(shifted, [row], 0, "controlled-experimental")


class FakeDriver:
    def __init__(self, packets):
        self.packets = packets;self.logical_ns = 0;self.results = [];self.playing = False
        self.ui = SimpleNamespace(play=lambda: setattr(self, "playing", True), stop=lambda: None)

    def snapshot(self):
        midi = self.packets if self.playing else []
        return dict(midi=midi, midi_count=max([0] + [p["index"] for p in midi]), midi_capture=dict(outstanding=[]))

    def wait(self, predicate, timeout=None):
        state = self.snapshot();assert predicate(state);return state

    def elapse(self, seconds):
        self.logical_ns += round(seconds * 1e9)


class LaneAcceptance(unittest.TestCase):
    def test_midi_acceptance_verifies_the_authored_cycle(self):
        example = lesson(128)
        driver = FakeDriver(onset_and_release(1, 0) + onset_and_release(3, 128))
        options = SimpleNamespace(midi_controlled_install="/controlled", midi_real_install=None, app_root="/app")
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(manual_audio, "tracked_driver", return_value=driver), \
             patch.object(manual_audio, "configure"), patch.object(manual_audio, "close"), \
             patch.object(manual_audio, "digest", return_value="sha"), \
             patch.object(manual_audio, "verify_midi_packets", wraps=manual_audio.verify_midi_packets) as verify:
            manual_audio.midi_acceptance(example, Path(directory), options, "controlled-experimental")
        self.assertEqual(verify.call_args.kwargs.get("cycle_steps"), 128)

    def test_lane_audit_verifies_the_authored_cycle(self):
        example = lesson(128)
        packets = onset_and_release(1, 0) + onset_and_release(3, 128)
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory);(out / "native").mkdir()
            proof = manual_audio.verify_midi_packets(packets, [ROW], 0, "controlled-experimental", allow_boundary=True, cycle_steps=128)
            row = dict(kind="manual-audio-lesson-midi", passed=True, midi_start_index=0, midi_end_index=4, origin_ns=0,
                       boundary_index=3, phases=[], **{k: v for k, v in proof.items() if k != "passed"})
            (out / "results.json").write_text(json.dumps([row]))
            (out / "native/cleanup.json").write_text(json.dumps([dict(returncode=0)]))
            lane = dict(clock_mode="controlled-experimental", path=str(out), results_sha256="r", identity_sha256="i")
            with patch.object(manual_audio, "digest", side_effect=lambda path: "r" if path.name == "results.json" else "i"), \
                 patch.object(manual_audio, "native_midi_packets", return_value=packets), \
                 patch.object(manual_audio, "audit_phases", return_value=True), \
                 patch.object(manual_audio, "verify_midi_packets", wraps=manual_audio.verify_midi_packets) as verify:
                self.assertTrue(manual_audio.audit_lesson_midi(example, [lane], controlled_local=True))
        self.assertEqual(verify.call_args.kwargs.get("cycle_steps"), 128)


class PublicUi:
    def __init__(self, calls):
        self.calls = calls

    def __getattr__(self, name):
        if name == "hold_step":
            @contextmanager
            def hold_step(*args):
                yield
            return hold_step
        return lambda *args, **kwargs: self.calls.append(name)


class SetupDispatch(unittest.TestCase):
    def configure(self, example, **kwargs):
        calls = []
        driver = SimpleNamespace(ui=PublicUi(calls), results=[], enc=lambda *args: calls.append("enc"))
        with patch.object(manual_audio, "set_tempo"), patch.object(manual_audio, "route_track"), \
             patch.object(manual_audio, "set_mask_field", side_effect=lambda *args: calls.append("mask")):
            manual_audio.configure(driver, example, example["tracks"], **kwargs)
        return driver, calls

    def test_named_setup_runs_after_routing_and_masks(self):
        example = lesson(64);example["setup"] = "probe";seen = []
        def probe(c, authored, tracks, witnesses, midi_only):
            seen.append((c, authored, tracks, witnesses, midi_only, list(calls_ref[0])))
        calls_ref = [[]]
        with patch.dict(manual_audio_setups.SETUPS, {"probe": probe}):
            calls = []
            calls_ref[0] = calls
            driver = SimpleNamespace(ui=PublicUi(calls), results=[], enc=lambda *args: calls.append("enc"))
            with patch.object(manual_audio, "set_tempo"), patch.object(manual_audio, "route_track"), \
                 patch.object(manual_audio, "set_mask_field", side_effect=lambda *args: calls.append("mask")):
                manual_audio.configure(driver, example, example["tracks"], midi_only=True, witnesses=False)
        self.assertEqual(len(seen), 1)
        c, authored, tracks, witnesses, midi_only, before = seen[0]
        self.assertIs(c, driver);self.assertIs(authored, example);self.assertIs(tracks, example["tracks"])
        self.assertEqual((witnesses, midi_only), (False, True))
        self.assertEqual(before, calls, "setup must be the last configuration step")
        self.assertIn("mask", before)

    def test_examples_without_setup_are_configured_as_before(self):
        example = lesson(64)
        with patch.dict(manual_audio_setups.SETUPS, {}, clear=True):
            driver, calls = self.configure(example, midi_only=True)
        self.assertEqual(calls[-2:], ["select_channel", "channel_page"])


if __name__ == "__main__":
    unittest.main()
