"""Read-only TOM mapping/time audit for one frozen ADTOF pilot artifact."""
import argparse
import json
import re
import shutil
from pathlib import Path

import mido
import numpy as np
import soundfile as sf

HELD = (1, 2, 6, 8, 9, 11, 14, 15, 16, 19, 20)
TOM_NOTES = (41, 43, 45, 47, 48, 50)


def drum_stem(metadata):
    current, found = None, []
    for line in Path(metadata).read_text(encoding="utf-8").splitlines():
        match = re.match(r"^  (S\d+):", line)
        if match:
            current = match.group(1)
        if current and "is_drum: true" in line:
            found.append(current)
    if len(found) != 1:
        raise ValueError("missing unique drum stem: " + str(metadata))
    return found[0]


def drum_events(path, seconds):
    elapsed, output = 0.0, []
    for message in mido.MidiFile(path):
        elapsed += message.time
        if elapsed >= seconds:
            break
        if message.type == "note_on" and message.velocity and message.note in TOM_NOTES:
            output.append((float(elapsed), int(message.note)))
    return output


def all_drum_onsets(path, seconds):
    elapsed, output = 0.0, []
    for message in mido.MidiFile(path):
        elapsed += message.time
        if elapsed >= seconds:
            break
        if message.type == "note_on" and message.velocity:
            output.append((float(elapsed), int(message.note)))
    return output


def stage(source, directory):
    source = Path(source)
    destination = directory / (source.parents[1].name + "-" + source.name)
    if not destination.exists() or destination.stat().st_size != source.stat().st_size:
        directory.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return destination


def rms(audio, start, end, rate):
    left, right = max(0, int(start * rate)), max(0, int(end * rate))
    part = audio[left:right]
    return float(np.sqrt(np.mean(np.square(part)))) if len(part) else 0.0


def nearest_summary(events, predicted):
    distances = [min((abs(event - value) for value in predicted), default=None) for event, _ in events]
    finite = [value for value in distances if value is not None]
    return {"per_event_seconds": distances,
            "median_seconds": float(np.median(finite)) if finite else None,
            "p95_seconds": float(np.quantile(finite, .95)) if finite else None,
            "within_50ms": sum(value <= .05 for value in finite),
            "within_100ms": sum(value <= .10 for value in finite),
            "within_250ms": sum(value <= .25 for value in finite),
            "no_predicted_tom": len(distances) - len(finite)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--selected", type=Path, required=True)
    parser.add_argument("--meta", type=Path, required=True)
    parser.add_argument("--stems", type=Path, required=True)
    parser.add_argument("--pilot", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=60.0)
    args = parser.parse_args()
    report = json.loads((args.pilot / "report.json").read_text(encoding="utf-8"))
    predictions = json.loads((args.pilot / "predictions.json").read_text(encoding="utf-8"))["held"]
    config = (args.pilot / "upstream" / "adtof_pytorch" / "post_processing.py").read_text(encoding="utf-8")
    labels = [int(value) for value in re.search(r"LABELS_5\s*=\s*\[([^]]+)\]", config).group(1).split(",")]
    stage_dir = args.pilot / "tom-audit-staged"
    by_track, total_by_note, transient_rows = {}, {str(note): 0 for note in TOM_NOTES}, []
    for number, prediction in zip(HELD, predictions):
        track = f"Track{number:05d}"
        stem = drum_stem(args.meta / track / "metadata.yaml")
        midi = args.selected / track / "MIDI" / (stem + ".mid")
        toms = drum_events(midi, args.seconds)
        all_onsets = all_drum_onsets(midi, args.seconds)
        audio_path = stage(args.stems / track / "stems" / (stem + ".wav"), stage_dir)
        audio, rate = sf.read(audio_path, always_2d=True)
        audio = audio.mean(axis=1, dtype=np.float64)
        event_rows = []
        for moment, note in toms:
            total_by_note[str(note)] += 1
            before, after = rms(audio, moment - .030, moment, rate), rms(audio, moment, moment + .030, rate)
            simultaneous = [other_note for other_moment, other_note in all_onsets
                            if other_note != note and abs(other_moment - moment) <= .050]
            row = {"time_seconds": moment, "midi_note": note, "pre_rms": before, "post_rms": after,
                   "post_over_pre": after / max(before, 1e-12), "simultaneous_other_drum_notes": simultaneous}
            event_rows.append(row); transient_rows.append(row)
        by_track[track] = {"tom_events": len(toms), "tom_notes": {str(note): sum(item[1] == note for item in toms) for note in TOM_NOTES},
                           "predicted_tom_events": len(prediction["TOM"]),
                           "nearest_predicted_tom": nearest_summary(toms, prediction["TOM"]), "transients": event_rows}
    dev = report["development_metrics"]["TOM"]
    tp, fp, fn = dev["tp"], dev["fp"], dev["fn"]
    output = {"kind": "adtof_tom_mapping_time_audit", "acceptance_claimed": False,
              "pilot_weight_sha256": report["source"]["weight_sha256"],
              "upstream_labels_5": labels, "mapping_verified": {"47": "TOM", "42": "HH", "49": "cymbal_not_scored"},
              "held_tom_events_by_midi_note": total_by_note, "held_by_track": by_track,
              "transient_energy": {"window_seconds": .030,
                 "events": len(transient_rows),
                 "median_post_over_pre": float(np.median([row["post_over_pre"] for row in transient_rows])) if transient_rows else None,
                 "simultaneous_or_nearby_other_drum_events": sum(bool(row["simultaneous_other_drum_notes"]) for row in transient_rows)},
              "development_tom_frozen_threshold": {"tp": tp, "fp": fp, "fn": fn,
                  "precision": tp / (tp + fp) if tp + fp else 0.0, "recall": tp / (tp + fn) if tp + fn else 0.0},
              "limitations": ["Energy is a supporting check on the original aggregate DRUM stem, not an independent human annotation.",
                              "Near-simultaneous drum hits can obscure an individual TOM transient.",
                              "No held threshold/model tuning occurred."]}
    (args.pilot / "tom-audit.json").write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
