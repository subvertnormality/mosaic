"""RD-02 ADTOF diagnostic scorer; never a shipping classifier integration.

It invokes a frozen copy of the upstream ADTOF-PyTorch frontend/model, derives
references from independent source MIDI, and scores only its four applicable
drum labels.  It deliberately has no BASS result.
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
import time
from pathlib import Path

import mido
import numpy as np

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "AGENTS.md").exists())
sys.path.insert(0, str(ROOT / "tests" / "rhythm_doctor"))
from quality import onset_score

DEV = (3, 4, 5, 7, 10, 12, 13, 17, 18)
HELD = (1, 2, 6, 8, 9, 11, 14, 15, 16, 19, 20)
ADTOF_LABEL_TO_LANE = {35: "BD", 38: "SD", 47: "TOM", 42: "HH", 49: None}
ADTOF_LANE_INDEX = {lane: index for index, label in enumerate((35, 38, 47, 42, 49))
                    for lane in (ADTOF_LABEL_TO_LANE[label],) if lane is not None}
SOURCE_NOTES = {"BD": (35, 36), "SD": (37, 38, 40), "HH": (42, 44, 46),
                "TOM": (41, 43, 45, 47, 48, 50)}
TOLERANCE = .050


def scored_lanes():
    return ("BD", "SD", "HH", "TOM")


def roles(path):
    drum, current = [], None
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        match = re.match(r"^  (S\d+):", line)
        if match:
            current = match.group(1)
        if current and "is_drum: true" in line:
            drum.append(current)
    if len(drum) != 1:
        raise ValueError("missing unique source DRUM stem: " + str(path))
    return drum[0]


def references(selected, meta, number, seconds):
    track = f"Track{number:05d}"
    stem = roles(meta / track / "metadata.yaml")
    source = {lane: [] for lane in scored_lanes()}
    elapsed = 0.0
    for message in mido.MidiFile(selected / track / "MIDI" / (stem + ".mid")):
        elapsed += message.time
        if elapsed >= seconds:
            break
        if message.type == "note_on" and message.velocity:
            lane = next((name for name, notes in SOURCE_NOTES.items() if message.note in notes), None)
            if lane in source:
                source[lane].append(float(elapsed))
    return source


def local_audio(source, stage):
    source = Path(source)
    target = stage / (source.parent.name + "-" + source.name)
    if not target.exists() or target.stat().st_size != source.stat().st_size:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return target


def aggregate(reference_sets, predictions):
    output = {}
    for lane in scored_lanes():
        values = [onset_score(ref[lane], prediction[lane], TOLERANCE)
                  for ref, prediction in zip(reference_sets, predictions)]
        tp, fp, fn = (sum(value[key] for value in values) for key in ("tp", "fp", "fn"))
        output[lane] = {"tp": tp, "fp": fp, "fn": fn,
                        "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 1.0}
    return output


def thresholds_from_development(activations, refs, picker):
    chosen, diagnostics = {}, {}
    for lane in scored_lanes():
        index = ADTOF_LANE_INDEX[lane]
        values = np.concatenate([row[:, index] for row in activations])
        best = None
        for threshold in np.unique(np.quantile(values, np.linspace(.05, .995, 48))):
            # Upstream processor holds its threshold at construction, so recreate it here.
            predicted = [picker(threshold=float(threshold), fps=100).process(row[:, index])
                         for row in activations]
            times = [[time for time, _ in result] for result in predicted]
            scores = [onset_score(reference[lane], prediction, TOLERANCE)
                      for reference, prediction in zip(refs, times)]
            tp, fp, fn = (sum(score[key] for score in scores) for key in ("tp", "fp", "fn"))
            metric = {"tp": tp, "fp": fp, "fn": fn,
                      "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 1.0}
            if best is None or (metric["f1"], -float(threshold)) > (best[1]["f1"], -best[0]):
                best = (float(threshold), metric)
        chosen[lane], diagnostics[lane] = best
    return chosen, diagnostics


def prediction_from_activations(activation, thresholds, picker):
    result = {}
    for lane in scored_lanes():
        index = ADTOF_LANE_INDEX[lane]
        peaks = picker(threshold=float(thresholds[lane]), fps=100).process(activation[:, index])
        result[lane] = [float(moment) for moment, _ in peaks]
    return result


def source_hashes(path):
    return {file.name: hashlib.sha256(file.read_bytes()).hexdigest()
            for file in sorted(Path(path).glob("*.py"))}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--selected", type=Path, required=True)
    parser.add_argument("--meta", type=Path, required=True)
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=60.0)
    args = parser.parse_args()
    if args.seconds <= 0:
        raise ValueError("seconds must be positive")
    args.out.mkdir(parents=True, exist_ok=True)
    stage = args.out / "staged-audio"
    sys.path.insert(0, str(args.upstream.parent))
    from adtof_pytorch import create_frame_rnn_model, calculate_n_bins, load_audio_for_model, load_pytorch_weights
    from adtof_pytorch.post_processing import NotePeakPickingProcessor
    import torch

    torch.set_num_threads(1)
    source = {"adapter_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "upstream_python_sha256": source_hashes(args.upstream),
              "weight_sha256": hashlib.sha256(args.weights.read_bytes()).hexdigest()}
    model = create_frame_rnn_model(calculate_n_bins())
    model = load_pytorch_weights(model, str(args.weights), strict=True)
    model.eval().to("cpu")

    def activation(number):
        audio = local_audio(args.selected / f"Track{number:05d}" / "mix.wav", stage)
        # The upstream frontend accepts a file, so trim only after full extraction.
        tensor = load_audio_for_model(str(audio))
        with torch.no_grad():
            value = model(tensor).cpu().numpy()[0]
        return value[:int(args.seconds * 100)]

    started = time.perf_counter()
    dev_activation = [activation(number) for number in DEV]
    dev_refs = [references(args.selected, args.meta, number, args.seconds) for number in DEV]
    thresholds, dev_metrics = thresholds_from_development(dev_activation, dev_refs, NotePeakPickingProcessor)
    dev_predictions = [prediction_from_activations(row, thresholds, NotePeakPickingProcessor) for row in dev_activation]
    held_activation = [activation(number) for number in HELD]
    held_refs = [references(args.selected, args.meta, number, args.seconds) for number in HELD]
    held_predictions = [prediction_from_activations(row, thresholds, NotePeakPickingProcessor) for row in held_activation]
    (args.out / "predictions.json").write_text(json.dumps({"development": dev_predictions, "held": held_predictions}, indent=2), encoding="utf-8")
    np.savez_compressed(args.out / "activations.npz", **{f"dev_{number}": row for number, row in zip(DEV, dev_activation)},
                        **{f"held_{number}": row for number, row in zip(HELD, held_activation)})
    report = {"kind": "adtof_pytorch_old_babyslakh_diagnostic", "acceptance_claimed": False,
              "source": source, "runtime": {"torch": torch.__version__, "device": "cpu", "threads": 1},
              "development_tracks": list(DEV), "held_tracks": list(HELD), "seconds": args.seconds,
              "scored_lanes": list(scored_lanes()), "not_scored": ["BASS", "cymbal"],
              "thresholds_development_only": thresholds, "development_metrics": aggregate(dev_refs, dev_predictions),
              "development_threshold_metrics": dev_metrics, "held_metrics": aggregate(held_refs, held_predictions),
              "wall_seconds": time.perf_counter() - started,
              "limitations": ["Old BabySlakh diagnostic only; not the clean acceptance corpus.",
                              "Upstream port/license and weight redistribution remain unresolved.",
                              "No BASS lane or grid F1 is claimed."]}
    (args.out / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
