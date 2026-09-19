#!/usr/bin/env python3
"""Frozen-parameter DEV BabySlakh tempo-method measurement; no detector tuning."""
import argparse
import hashlib
import json
import math
import pathlib
import statistics
import struct
import subprocess
import tempfile
import wave


METHODS = ("default", "energy", "specdiff", "onset-ac")
DEV_TRACKS = ("Track00003", "Track00004", "Track00005", "Track00007", "Track00010",
              "Track00012", "Track00013", "Track00017", "Track00018")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def variable_length(data, offset):
    value = 0
    while True:
        byte = data[offset]
        offset += 1
        value = (value << 7) | (byte & 0x7f)
        if not byte & 0x80:
            return value, offset


def midi_reference(path):
    """Read independent standard-MIDI tempo events and tick-zero phase."""
    data = path.read_bytes()
    if data[:4] != b"MThd" or len(data) < 14:
        raise ValueError(f"{path}: not a standard MIDI file")
    tracks, ticks_per_quarter = int.from_bytes(data[10:12], "big"), int.from_bytes(data[12:14], "big")
    if not ticks_per_quarter or ticks_per_quarter & 0x8000:
        raise ValueError(f"{path}: unsupported SMPTE MIDI division")
    position, events = 14, []
    for _ in range(tracks):
        if data[position:position + 4] != b"MTrk":
            raise ValueError(f"{path}: missing MIDI track")
        length = int.from_bytes(data[position + 4:position + 8], "big")
        end, position, tick, running = position + 8 + length, position + 8, 0, None
        while position < end:
            delta, position = variable_length(data, position)
            tick += delta
            status = data[position]
            if status & 0x80:
                position += 1
                if status < 0xf0:
                    running = status
            elif running is not None:
                status = running
            else:
                raise ValueError(f"{path}: running status without status")
            if status == 0xff:
                event_type = data[position]
                length, position = variable_length(data, position + 1)
                payload, position = data[position:position + length], position + length
                if event_type == 0x51 and len(payload) == 3:
                    events.append({"tick": tick, "bpm": 60000000.0 / int.from_bytes(payload, "big")})
            elif status in (0xf0, 0xf7):
                length, position = variable_length(data, position)
                position += length
            else:
                position += 1 if (status >> 4) in (0xc, 0xd) else 2
    if not events:
        raise ValueError(f"{path}: no set_tempo event")
    unique = []
    for event in events:
        if not unique or event != unique[-1]:
            unique.append(event)
    return {"ticks_per_quarter": ticks_per_quarter, "phase_origin_tick": 0,
            "tempo_events": unique}


def phase_metrics(beats, rate, reference):
    events = reference["tempo_events"]
    if len(events) != 1 or events[0]["tick"] != 0 or not beats:
        return {"kind": "not-single-constant-tempo", "beat_positions": len(beats)}
    period = rate * 60.0 / events[0]["bpm"]
    errors = [abs(beat["frame"] - round(beat["frame"] / period) * period) * 1000.0 / rate
              for beat in beats]
    return {"kind": "tick-zero-grid", "beat_positions": len(beats), "period_frames": period,
            "max_error_ms": max(errors), "median_error_ms": statistics.median(errors)}


def diagnostics(result, reference):
    beats, candidate = result["beats"], result["candidate"]
    bpms = [beat["bpm"] for beat in beats if beat["bpm"] > 0]
    confidence = [beat["confidence"] for beat in beats]
    first_tempo = reference["tempo_events"][0]["bpm"]
    reported = result["reported_bpm"]
    ratio = reported / first_tempo if first_tempo and reported else None
    return {
        "first_failure": candidate["reason"],
        "position_count": len(beats),
        "position_span_seconds": (beats[-1]["frame"] - beats[0]["frame"]) / result["sample_rate"] if len(beats) > 1 else 0,
        "reported_to_first_midi_tempo": ratio,
        "reported_octaves_from_first_midi": math.log2(ratio) if ratio else None,
        "callback_bpm_min": min(bpms) if bpms else None,
        "callback_bpm_max": max(bpms) if bpms else None,
        "callback_confidence_min": min(confidence) if confidence else None,
        "callback_confidence_max": max(confidence) if confidence else None,
        "retained_seconds": result["frames"] / result["sample_rate"],
        "retained_four_bars_at_first_midi_tempo": 16 * result["sample_rate"] * 60.0 / first_tempo <= result["frames"],
        "midi_phase": phase_metrics(beats, result["sample_rate"], reference),
    }


def measure_track(binary, corpus_root, track):
    audio, midi = corpus_root / track / "mix.wav", corpus_root / track / "MIDI" / "S01.mid"
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
        reference = midi_reference(midi)
        results = {}
        for method in METHODS:
            result = json.loads(subprocess.check_output(
                [str(binary), "--raw-f32", raw.name, str(rate), method], text=True))
            results[method] = {"raw": result, "diagnostic": diagnostics(result, reference)}
    finally:
        pathlib.Path(raw.name).unlink(missing_ok=True)
    return {"track": track, "audio_sha256": digest(audio), "midi_sha256": digest(midi),
            "midi_reference": reference, "methods": results}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("binary", type=pathlib.Path)
    parser.add_argument("corpus_root", type=pathlib.Path)
    parser.add_argument("evidence_output", type=pathlib.Path)
    parser.add_argument("--recorded-at", default="2026-09-19")
    args = parser.parse_args()
    missing = [track for track in DEV_TRACKS if not (args.corpus_root / track / "mix.wav").is_file()
               or not (args.corpus_root / track / "MIDI" / "S01.mid").is_file()]
    if missing:
        raise SystemExit(f"missing DEV tracks: {', '.join(missing)}")
    source = pathlib.Path(__file__).with_name("rd_tempo.c")
    evidence = {
        "schema_version": 1,
        "recorded_at": args.recorded_at,
        "scope": "development-only; frozen parameters; first 45 seconds; no held or v10 corpus",
        "methods": METHODS,
        "binary_sha256": digest(args.binary),
        "rd_tempo_c_sha256": digest(source),
        "scan_script_sha256": digest(pathlib.Path(__file__)),
        "tracks": [measure_track(args.binary, args.corpus_root, track) for track in DEV_TRACKS],
    }
    args.evidence_output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
