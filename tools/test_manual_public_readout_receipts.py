import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from manual_player_device_readout import validate_player_device_readout, PlayerDeviceReadoutError
from manual_panic_release_readout import (
    validate_panic_release_readout, PanicReleaseReadoutError, _validated_midi_60_release,
    is_retained_panic_source,
)

ROOT = Path(__file__).resolve().parents[1]
BOOK = json.loads((ROOT / "manual/generated/book.json").read_text(encoding="utf-8"))
PLAYER = BOOK["scenes"]["player-apply-polyperc"]
PANIC = BOOK["scenes"]["panic-stops-sounding-note"]
DEVICE = {"device": "Polyperc 1"}
PANIC_EVENT = [{"port": 1, "bytes": [128, 60, 0]}]

class PlayerDeviceReadoutTests(unittest.TestCase):
    def call_player(self, scene=None, wanted=DEVICE):
        return validate_player_device_readout(copy.deepcopy(scene or PLAYER), "polyperc-applied", wanted, ROOT)

    def test_retained_apply_frame_admits_exact_device(self):
        receipt = self.call_player()
        self.assertEqual(receipt["device_configuration"], DEVICE)
        self.assertEqual(receipt["observation_index"], 59)
        self.assertEqual(receipt["native"], True)
        self.assertEqual(receipt["adapter_source"], "tools/manual_player_device_readout.py")
        self.assertEqual(len(receipt["adapter_source_sha256"]), 64)

    def test_changed_field_value_is_rejected(self):
        with self.assertRaises(PlayerDeviceReadoutError):
            self.call_player(wanted={"device": "Other Device"})

    def test_wrong_assertion_is_rejected(self):
        scene = copy.deepcopy(PLAYER)
        step = next(row for row in scene["steps"] if row["id"] == "polyperc-applied")
        step["output"]["binding"]["assertion"]["value"] = "Other Device"
        with self.assertRaises(PlayerDeviceReadoutError):
            self.call_player(scene)

    def test_wrong_frame_digest_is_rejected(self):
        scene = copy.deepcopy(PLAYER)
        next(row for row in scene["steps"] if row["id"] == "polyperc-applied")["output"]["binding"]["sha256"] = "0" * 64
        with self.assertRaises(PlayerDeviceReadoutError):
            self.call_player(scene)

    def test_wrong_assertion_index_is_rejected(self):
        scene = copy.deepcopy(PLAYER)
        next(row for row in scene["steps"] if row["id"] == "polyperc-applied")["output"]["binding"]["assertion_index"] += 1
        with self.assertRaises(PlayerDeviceReadoutError):
            self.call_player(scene)

    def test_foreign_session_is_rejected(self):
        scene = copy.deepcopy(PLAYER)
        scene["evidence"]["session_context"]["session_id"] = "0" * 32
        with self.assertRaises(PlayerDeviceReadoutError):
            self.call_player(scene)

    def test_unverified_cleanup_is_rejected(self):
        scene = copy.deepcopy(PLAYER)
        scene["evidence"]["session_context"]["cleanup_verified"] = False
        with self.assertRaises(PlayerDeviceReadoutError):
            self.call_player(scene)

    def test_mutated_published_rle_is_rejected(self):
        scene = copy.deepcopy(PLAYER)
        step = next(row for row in scene["steps"] if row["id"] == "polyperc-applied")
        step["output"]["screen_rle"][0][0] = (step["output"]["screen_rle"][0][0] + 1) % 16
        with self.assertRaises(PlayerDeviceReadoutError):
            self.call_player(scene)

    def test_mutated_published_grid_is_rejected(self):
        scene = copy.deepcopy(PLAYER)
        next(row for row in scene["steps"] if row["id"] == "polyperc-applied")["output"]["grid"][0] ^= 1
        with self.assertRaises(PlayerDeviceReadoutError):
            self.call_player(scene)

    def test_restored_confirmation_footer_is_rejected_by_pixel_oracle(self):
        import manual_publication_verify
        with patch.object(manual_publication_verify, "verify_cached_ui", side_effect=ValueError("confirmation footer present")) as verify:
            with self.assertRaisesRegex(ValueError, "footer present"):
                self.call_player()
        expected = verify.call_args.args[1]
        self.assertEqual(expected["footer"], {"text": "Press K3 to confirm", "present": False})

class PanicReleaseReadoutTests(unittest.TestCase):
    def test_actual_midi_60_cutoff_is_admitted_from_full_source(self):
        receipt = validate_panic_release_readout(copy.deepcopy(PANIC), "panic-released", PANIC_EVENT, ROOT)
        self.assertEqual(receipt["events"], PANIC_EVENT)
        self.assertEqual(receipt["note_on_event_index"], 18)
        self.assertEqual(receipt["native_event_index"], 2927)
        self.assertEqual(receipt["release_seconds_after_note_on"], 1.260002156)
        self.assertEqual(receipt["adapter_source"], "tools/manual_panic_release_readout.py")

    def test_generic_sweep_packet_cannot_substitute_for_sounding_note(self):
        with self.assertRaises(PanicReleaseReadoutError):
            validate_panic_release_readout(copy.deepcopy(PANIC), "panic-released",
                                           [{"port": 1, "bytes": [134, 44, 0]}], ROOT)

    def test_failed_early_release_assertion_is_rejected(self):
        scene = copy.deepcopy(PANIC)
        next(row for row in scene["steps"] if row["id"] == "panic-released")["output"]["binding"]["assertion"]["released_early"] = False
        with self.assertRaises(PanicReleaseReadoutError):
            validate_panic_release_readout(scene, "panic-released", PANIC_EVENT, ROOT)

    def test_panic_published_rle_must_match_native_frame(self):
        scene = copy.deepcopy(PANIC)
        step = next(row for row in scene["steps"] if row["id"] == "panic-released")
        step["output"]["screen_rle"][0][0] = (step["output"]["screen_rle"][0][0] + 1) % 16
        with self.assertRaises(PanicReleaseReadoutError):
            validate_panic_release_readout(scene, "panic-released", PANIC_EVENT, ROOT)

    def test_foreign_panic_session_is_rejected(self):
        scene = copy.deepcopy(PANIC)
        scene["evidence"]["session_context"]["session_id"] = "0" * 32
        with self.assertRaises(PanicReleaseReadoutError):
            validate_panic_release_readout(scene, "panic-released", PANIC_EVENT, ROOT)

    def test_missing_actual_onset_is_rejected(self):
        rows = [json.loads(line) for line in (Path(PANIC["evidence"]["path"]) / "native/native-events.jsonl").read_text().splitlines() if line.strip()]
        midi = [row for row in rows if row.get("kind") in (3, 11) and row.get("index") != 18]
        with self.assertRaises(PanicReleaseReadoutError):
            _validated_midi_60_release(midi, next(row for row in results_rows() if row.get("kind") == "panic-releases-sounding-note"))

    def test_missing_actual_cutoff_is_rejected(self):
        rows = [json.loads(line) for line in (Path(PANIC["evidence"]["path"]) / "native/native-events.jsonl").read_text().splitlines() if line.strip()]
        midi = [row for row in rows if row.get("kind") in (3, 11) and row.get("index") != 2927]
        with self.assertRaises(PanicReleaseReadoutError):
            _validated_midi_60_release(midi, next(row for row in results_rows() if row.get("kind") == "panic-releases-sounding-note"))

    def test_misordered_native_journal_is_rejected(self):
        rows = [json.loads(line) for line in (Path(PANIC["evidence"]["path"]) / "native/native-events.jsonl").read_text().splitlines() if line.strip()]
        midi = [row for row in rows if row.get("kind") in (3, 11)]
        midi[17], midi[18] = midi[18], midi[17]
        with self.assertRaises(PanicReleaseReadoutError):
            _validated_midi_60_release(midi, next(row for row in results_rows() if row.get("kind") == "panic-releases-sounding-note"))

    def test_actual_cutoff_before_onset_is_rejected(self):
        rows = [json.loads(line) for line in (Path(PANIC["evidence"]["path"]) / "native/native-events.jsonl").read_text().splitlines() if line.strip()]
        midi = [row for row in rows if row.get("kind") in (3, 11)]
        onset = next(row for row in midi if row.get("index") == 18)
        cutoff = next(row for row in midi if row.get("index") == 2927)
        onset["bytes"], cutoff["bytes"] = cutoff["bytes"], onset["bytes"]
        assertion = next(row for row in results_rows() if row.get("kind") == "panic-releases-sounding-note")
        with self.assertRaises(PanicReleaseReadoutError):
            _validated_midi_60_release(midi, assertion)

    def test_fresh_complete_midi_uses_generic_packet_check(self):
        from manual_teaching_v8 import _validate_output
        requirement = {"midi_events_at_target": PANIC_EVENT}
        native = {"to_step": {"output": {"midi": {"truncated": False, "events": PANIC_EVENT}}}}
        _validate_output(native, requirement)
        fresh = copy.deepcopy(PANIC)
        fresh["evidence"]["session_context"]["session_id"] = "1" * 32
        self.assertFalse(is_retained_panic_source(fresh))
        _validate_output(native, requirement)

def results_rows():
    return json.loads((Path(PANIC["evidence"]["path"]) / "results.json").read_text(encoding="utf-8"))

if __name__ == "__main__":
    unittest.main()
