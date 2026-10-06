"""Controller (CC) timing witness for the parameter-lock lesson.

README.md#trig-param-locks: a trig lock holds a parameter value for one step. With the
lock lead at 0 (README Lock lead time: 'Set it to 0 to send each value at its own step')
the value leaves at its step. A CC lock proves lock timing on a CC, not the voice parameter.
"""
import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import yaml

REPO = Path(os.environ.get("MOSAIC_MANUAL_ROOT", Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(REPO / "tools"))
import manual_audio

TICK = 1e9 / 6
CC = dict(port=1, status=176, controller=1, value=20, step=4)
NOTE = dict(port=1, status=144, note=48, velocity=70, step=4, length=0.5)
NOTE0, CC0 = dict(NOTE, step=0), dict(CC, step=0)


def at(step):
    return round(step * TICK)


def packet(index, data, step):
    return dict(index=index, port=1, bytes=data, logical_ns=at(step), monotonic_ns=at(step))


def stream(cc_step=4, value=20, cc_first=True):
    cc = packet(1, [176, 1, value], cc_step)
    on = packet(2 if cc_first else 0, [144, 48, 70], 4)
    off = packet(3, [128, 48, 70], 4.5)
    return [cc, on, off] if cc_first else [on, cc, off]


class VerifyControls(unittest.TestCase):
    def verify(self, packets, expected=(CC,), **kw):
        return manual_audio.verify_midi_controls(packets, list(expected), 0, "controlled-experimental", **kw)

    def test_exact_controller_at_its_step_before_the_note_passes(self):
        result = self.verify(stream())
        self.assertEqual((result["controls"], result["passed"]), (1, True))

    def test_wrong_value_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, "Literal controller output"):
            self.verify(stream(value=21))

    def test_wrong_time_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, "Controller onset"):
            self.verify(stream(cc_step=4 + 1 / 24))

    def test_missing_controller_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, "Literal controller output"):
            self.verify(stream()[1:])

    def test_unexpected_controller_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, "Literal controller output"):
            self.verify(stream(), expected=())

    def test_wrong_controller_number_or_channel_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, "Literal controller output"):
            self.verify(stream(), expected=[dict(CC, controller=2)])
        with self.assertRaisesRegex(AssertionError, "Literal controller output"):
            self.verify(stream(), expected=[dict(CC, status=177)])

    def test_controller_after_its_note_attack_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, "before the note"):
            self.verify(stream(cc_first=False))

    def test_controllers_at_or_after_the_closing_boundary_are_ignored(self):
        late = packet(9, [176, 1, 99], 64)
        self.assertTrue(self.verify(stream() + [late], boundary_index=9)["passed"])
        with self.assertRaisesRegex(AssertionError, "Literal controller output"):
            self.verify(stream() + [late])

    def test_simultaneous_packet_messages_are_split(self):
        both = dict(index=1, port=1, bytes=[176, 1, 20, 144, 48, 70], logical_ns=at(4), monotonic_ns=at(4))
        off = packet(2, [128, 48, 70], 4.5)
        self.assertTrue(self.verify([both, off])["passed"])

    def test_controller_without_a_note_on_its_step_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, "no note"):
            self.verify(stream()[:1])

    def test_real_time_lane_uses_monotonic_time_and_ten_ms(self):
        packets = stream()
        for p in packets:
            p["monotonic_ns"] += 5_000_000;p["logical_ns"] = 0
        self.assertTrue(manual_audio.verify_midi_controls(packets, [CC], 0, "real-time")["passed"])
        packets[0]["monotonic_ns"] += 20_000_000
        with self.assertRaisesRegex(AssertionError, "Controller onset"):
            manual_audio.verify_midi_controls(packets, [CC], 0, "real-time")


class LaneWiring(unittest.TestCase):
    """midi_acceptance records the controller proof and audit_lesson_midi re-derives it."""

    def lesson(self):
        value = copy.deepcopy(next(v for v in yaml.safe_load((REPO / "manual/audio-scenes.yaml").read_text())["examples"]
                                   if v["id"] == "ghost-note-comparison"))
        value["midi_contract"] = dict(cycle_steps=64, notes=[dict(NOTE0)], controls=[dict(CC0)])
        return value

    def packets(self, value=20):
        return [packet(1, [176, 1, value], 0), packet(2, [144, 48, 70], 0), packet(3, [128, 48, 70], 0.5),
                packet(5, [144, 48, 70], 64), packet(6, [128, 48, 70], 64.5)]

    def test_midi_acceptance_verifies_and_records_controls(self):
        from test_manual_audio_cycle import FakeDriver
        example = self.lesson();packets = self.packets()
        driver = FakeDriver(packets)
        options = SimpleNamespace(midi_controlled_install="/controlled", midi_real_install=None, app_root="/app")
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(manual_audio, "tracked_driver", return_value=driver), \
             patch.object(manual_audio, "configure"), patch.object(manual_audio, "close"), \
             patch.object(manual_audio, "digest", return_value="sha"), \
             patch.object(manual_audio, "verify_midi_controls", wraps=manual_audio.verify_midi_controls) as verify:
            manual_audio.midi_acceptance(example, Path(directory), options, "controlled-experimental")
        self.assertEqual(verify.call_args.args[1], [dict(CC0)])
        self.assertEqual(verify.call_args.kwargs.get("boundary_index"), 5)
        row = next(v for v in driver.results if v["kind"] == "manual-audio-lesson-midi")
        self.assertEqual(row["controls"], 1)

    def audit(self, packets, recorded):
        example = self.lesson()
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory);(out / "native").mkdir()
            proof = manual_audio.verify_midi_packets(packets, [NOTE0], 0,
                                                     "controlled-experimental", allow_boundary=True)
            row = dict(kind="manual-audio-lesson-midi", passed=True, midi_start_index=0, midi_end_index=6, origin_ns=0,
                       boundary_index=5, phases=[], controls=recorded, **{k: v for k, v in proof.items() if k != "passed"})
            (out / "results.json").write_text(json.dumps([row]))
            (out / "native/cleanup.json").write_text(json.dumps([dict(returncode=0)]))
            lane = dict(clock_mode="controlled-experimental", path=str(out), results_sha256="r", identity_sha256="i")
            with patch.object(manual_audio, "digest", side_effect=lambda path: "r" if path.name == "results.json" else "i"), \
                 patch.object(manual_audio, "native_midi_packets", return_value=packets), \
                 patch.object(manual_audio, "audit_phases", return_value=True), \
                 patch.object(manual_audio, "mapped_score", return_value=[NOTE0]):
                return manual_audio.audit_lesson_midi(example, [lane], controlled_local=True)

    def test_audit_accepts_the_recorded_controller_proof(self):
        self.assertTrue(self.audit(self.packets(), 1))

    def test_audit_rejects_a_changed_controller_stream_or_record(self):
        late = self.packets(value=21)
        with self.assertRaisesRegex(AssertionError, "Literal controller output"):
            self.audit(late, 1)
        with self.assertRaisesRegex(ValueError, "controller"):
            self.audit(self.packets(), 2)


def authored():
    return yaml.safe_load((REPO / "manual/audio-scenes.yaml").read_text())


class AuthoredControls(unittest.TestCase):
    def lesson(self):
        return copy.deepcopy(next(v for v in authored()["examples"] if v["id"] == "harmony-strum-arp"))

    def test_witness_mapping_moves_status_by_fourteen_channels(self):
        example = self.lesson()
        example["midi_contract"]["controls"] = [dict(CC, status=176)]
        self.assertEqual(manual_audio.mapped_controls(example, example["tracks"]), [dict(CC, status=176)])
        self.assertEqual(manual_audio.mapped_controls(example, example["tracks"], witness=True), [dict(CC, status=190)])

    def test_no_controls_map_to_none(self):
        example = self.lesson()
        self.assertEqual(manual_audio.mapped_controls(example, example["tracks"]), [])

    def test_contract_controls_are_validated_like_notes(self):
        example = self.lesson()
        example["midi_contract"]["controls"] = [dict(CC, step=64)]
        with self.assertRaisesRegex(ValueError, "control"):
            manual_audio.validate_contract(example)
        example["midi_contract"]["controls"] = [dict(CC, step=4.001)]
        with self.assertRaisesRegex(ValueError, "control"):
            manual_audio.validate_contract(example)

    def test_schema_accepts_controls_and_rejects_malformed_ones(self):
        data = authored()
        lesson = next(v for v in data["examples"] if v["id"] == "harmony-strum-arp")
        lesson["midi_contract"]["controls"] = [dict(CC)]
        manual_audio.validate(data)
        lesson["midi_contract"]["controls"] = [dict(CC, value=128)]
        with self.assertRaises(ValueError):
            manual_audio.validate(data)
        lesson["midi_contract"]["controls"] = [dict(CC, status=144)]
        with self.assertRaises(ValueError):
            manual_audio.validate(data)


if __name__ == "__main__":
    unittest.main()
