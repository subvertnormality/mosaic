#!/usr/bin/env python3
"""Read-only 45-second BabySlakh PCM scan for native tempo feasibility evidence."""
import argparse
import hashlib
import json
import pathlib
import struct
import subprocess
import tempfile
import wave


def tempo_events(path):
    """Extract tempo meta-event values by scanning standard MIDI event bytes."""
    data, marker, values, cursor = path.read_bytes(), b"\xff\x51\x03", [], 0
    while True:
        cursor = data.find(marker, cursor)
        if cursor < 0:
            return values
        values.append(60000000.0 / int.from_bytes(data[cursor + 3:cursor + 6], "big"))
        cursor += len(marker) + 3


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def analyse(binary, audio, midi):
    with wave.open(str(audio), "rb") as source:
        if (source.getnchannels(), source.getsampwidth()) != (1, 2):
            raise ValueError(f"{audio}: expected mono 16-bit PCM")
        rate = source.getframerate()
        pcm = source.readframes(min(source.getnframes(), rate * 45))
    samples = struct.unpack("<" + "h" * (len(pcm) // 2), pcm)
    raw = tempfile.NamedTemporaryFile(suffix=".f32", delete=False)
    try:
        raw.write(struct.pack("<" + "f" * len(samples), *(value / 32768.0 for value in samples)))
        raw.close()
        result = json.loads(subprocess.check_output(
            [str(binary), "--raw-f32", raw.name, str(rate), "onset-ac"], text=True))
    finally:
        pathlib.Path(raw.name).unlink(missing_ok=True)
    return {"track": audio.parent.name, "audio_sha256": digest(audio), "midi_sha256": digest(midi),
            "midi_tempos_bpm": tempo_events(midi),
            "reported_bpm": result["reported_bpm"], "candidate": result["candidate"],
            "onset_count": len(result["beats"])}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("binary", type=pathlib.Path)
    parser.add_argument("corpus_root", type=pathlib.Path)
    parser.add_argument("--evidence-output", type=pathlib.Path)
    parser.add_argument("--recorded-at", default="2026-09-19")
    args = parser.parse_args()
    results = []
    for audio in sorted(args.corpus_root.glob("Track*/mix.wav")):
        midi = audio.parent / "MIDI" / "S01.mid"
        if midi.is_file():
            result = analyse(args.binary, audio, midi)
            results.append(result)
            if not args.evidence_output:
                print(json.dumps(result, sort_keys=True))
    if args.evidence_output:
        source = pathlib.Path(__file__).with_name("rd_tempo.c")
        evidence = {
            "schema_version": 1,
            "recorded_at": args.recorded_at,
            "method": "onset-ac",
            "window_seconds": 45,
            "binary_sha256": digest(args.binary),
            "rd_tempo_c_sha256": digest(source),
            "scan_script_sha256": digest(pathlib.Path(__file__)),
            "tracks": results,
        }
        args.evidence_output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
