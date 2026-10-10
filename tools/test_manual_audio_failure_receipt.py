"""A failed lesson MIDI invariant exports only a small raw packet receipt."""
import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
import manual_audio

CANDIDATE = Path(__file__).resolve().parents[1] / ".github" / "scripts"
spec = importlib.util.spec_from_file_location("manual_artifact_under_test", CANDIDATE / "manual_artifact.py")
manual_artifact = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manual_artifact)

class FailureReceipt(unittest.TestCase):
    def fixture(self):
        status = 143 + manual_audio.WITNESS_CHANNEL_OFFSET + 1
        origin = 20_000_000_000
        step_ns = 1_000_000_000 / 6
        packets = [
            dict(index=1, port=1, monotonic_ns=origin, bytes=[status, 60, 80]),
            dict(index=2, port=1, monotonic_ns=int(origin + step_ns), bytes=[status - 16, 60, 80]),
            dict(index=3, port=1, monotonic_ns=int(origin + 4 * step_ns + 1_000_000),
                 bytes=[status, 60, 80, status + 1, 45, 80]),
            dict(index=4, port=1, monotonic_ns=int(origin + 5 * step_ns + 1_000_000), bytes=[status - 16, 60, 80]),
            dict(index=5, port=1, monotonic_ns=int(origin + 8 * step_ns), bytes=[status, 60, 80]),
        ]
        example = {"id":"voice-leading-revoice", "midi_contract":{
            "notes":[dict(port=1,status=status,note=60,velocity=80,step=0,length=1)],
            "invariants":[dict(kind="revoice",channel=1,reference_start_step=0,
                                revoiced_start_step=4,length_steps=1)]}}
        tracks = [dict(channel=1,voice="Doubledecker")]
        error = AssertionError(("Revoice changed the onset steps", [], []))
        identity = dict(source_sha256="a"*64,tool_sha256="b"*64,helper_sha256="c"*64)
        return example, tracks, packets, origin, error, identity, status

    def test_receipt_keeps_only_bounded_target_channel_window_and_exact_packet_bytes(self):
        example, tracks, packets, origin, error, identity, status = self.fixture()
        receipt = manual_audio.build_witness_failure_receipt(
            example, tracks, "MA-AUDIO-voice-leading-revoice", packets, origin,
            "real-time", error, identity)
        window = receipt["raw_packet_window"]
        self.assertEqual([v["index"] for v in window["packets"]], [1,2,3,4])
        self.assertEqual(window["packets"][2]["bytes"], [status,60,80,status+1,45,80])
        canonical = json.dumps(window["packets"], sort_keys=True, separators=(",",":")).encode()
        self.assertEqual(window["sha256"], hashlib.sha256(canonical).hexdigest())
        self.assertNotIn("wav", json.dumps(receipt).lower())
        self.assertNotIn("application", json.dumps(receipt).lower())
        bounded = manual_audio.build_witness_failure_receipt(example, tracks, "case", packets, origin, "real-time", AssertionError("x"*5000), identity)
        self.assertEqual(len(bounded["failure"]["message"]), 4096)
        self.assertTrue(bounded["failure"]["message_truncated"])

    def test_writer_is_opt_in_hash_pinned_and_refuses_overwrite(self):
        example, tracks, packets, origin, error, identity, _ = self.fixture()
        receipt = manual_audio.build_witness_failure_receipt(example, tracks, "case", packets,
                                                              origin, "real-time", error, identity)
        old = os.environ.get("MANUAL_AUDIO_FAILURE_RECEIPT")
        try:
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / "audio-failure-receipt.json"
                os.environ["MANUAL_AUDIO_FAILURE_RECEIPT"] = str(path)
                saved = manual_audio.write_witness_failure_receipt(receipt)
                self.assertEqual(saved["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
                self.assertEqual(json.loads(path.read_text()), receipt)
                with self.assertRaises(FileExistsError):
                    manual_audio.write_witness_failure_receipt(receipt)
        finally:
            if old is None:os.environ.pop("MANUAL_AUDIO_FAILURE_RECEIPT", None)
            else:os.environ["MANUAL_AUDIO_FAILURE_RECEIPT"] = old

    def test_existing_artifact_bundler_includes_only_explicit_receipt(self):
        example, tracks, packets, origin, error, identity, _ = self.fixture()
        receipt = manual_audio.build_witness_failure_receipt(example, tracks, "case", packets,
                                                              origin, "real-time", error, identity)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); source=root/"failure-receipt.json"
            source.write_text(json.dumps(receipt), encoding="utf-8")
            result=manual_artifact.make_evidence_bundle(None, root/"bundle", extra_references=[str(source)])
            self.assertFalse(result["build_directory_present"])
            self.assertEqual(len(result["files"]), 1)  # only the explicit receipt
            self.assertTrue(any(Path(name).name == "failure-receipt.json" for name in result["files"]))
            self.assertFalse(any(Path(name).suffix.lower() in (".wav", ".ogg", ".mp3") for name in result["files"]))

    def test_audio_finalizer_passes_opt_in_receipt_and_audio_command_receives_path(self):
        script=(CANDIDATE/"manual-build.sh").read_text(encoding="utf-8")
        self.assertIn('if [[ -f "$AUDIO_FAILURE_RECEIPT" ]]; then' + chr(10) + '    args+=(--extra-reference "$AUDIO_FAILURE_RECEIPT")' + chr(10) + '  fi',script)
        self.assertIn('MANUAL_AUDIO_FAILURE_RECEIPT="$AUDIO_FAILURE_RECEIPT" MONOME_EMULATOR=',script)

if __name__ == "__main__":
    unittest.main()
