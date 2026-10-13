"""Frozen-v11 ADTOF priority-lane transfer diagnostic; never production code.

The model is trained only on the two designated development kits.  A third,
disjoint development kit selects peak thresholds.  Held audio and annotations
are not opened until both model and thresholds are frozen.
"""
import argparse
import hashlib
import json
import random
import shutil
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT / "tests" / "rhythm_doctor"))
from quality import onset_score

LANES = ("BD", "SD", "HH")
OUTPUT_INDEX = {"BD": 0, "SD": 1, "HH": 3}
VALIDATION_KIT = "ar_modern_white_kit_full.nkm"
# Four seconds is no longer than the shortest (6.4 s) frozen development clip.
SEED, FPS, CHUNK, TOLERANCE = 20260919, 100, 400, .050


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def partition_development(clips):
    development = [clip for clip in clips if clip.get("split") == "development"]
    train = [clip for clip in development if clip.get("kit_id") != VALIDATION_KIT]
    validation = [clip for clip in development if clip.get("kit_id") == VALIDATION_KIT]
    if not train or not validation:
        raise ValueError("fixed development validation split is unavailable")
    if {clip["kit_id"] for clip in train} & {clip["kit_id"] for clip in validation}:
        raise ValueError("source-kit overlap in development partition")
    return train, validation


def upstream_import_root(path):
    path = Path(path)
    root = path if (path / "adtof_pytorch").is_dir() else path.parent
    if not (root / "adtof_pytorch" / "model.py").is_file():
        raise ValueError("pinned ADTOF package is unavailable")
    return root


def annotation(path):
    values = json.loads(Path(path).read_text(encoding="utf-8"))["events"]
    return {lane: [float(event["time_seconds"]) for event in values.get(lane, [])]
            for lane in LANES}


def targets(events, frames):
    values = np.zeros((frames, 5), dtype=np.float32)
    for lane, moments in events.items():
        for moment in moments:
            index = int(round(moment * FPS))
            values[max(0, index - 1):min(frames, index + 2), OUTPUT_INDEX[lane]] = 1.0
    return values


def stage(source, directory):
    source = Path(source)
    # Every corpus path ends in a clip-specific file today, but the hash prefix
    # makes accidental same-basename replacement fail closed if that changes.
    destination = directory / (sha256(source)[:16] + "-" + source.name)
    if not destination.exists():
        directory.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    if destination.stat().st_size != source.stat().st_size or sha256(destination) != sha256(source):
        raise ValueError("staged audio hash mismatch")
    return destination


def score(references, predictions):
    result = {}
    for lane in LANES:
        rows = [onset_score(reference[lane], predicted[lane], TOLERANCE)
                for reference, predicted in zip(references, predictions)]
        tp, fp, fn = (sum(row[key] for row in rows) for key in ("tp", "fp", "fn"))
        result[lane] = {"tp": tp, "fp": fp, "fn": fn,
                        "precision": tp / (tp + fp) if tp + fp else 0.0,
                        "recall": tp / (tp + fn) if tp + fn else 0.0,
                        "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 1.0}
    return result


def choose_thresholds(activations, references, picker):
    thresholds = {}
    for lane in LANES:
        column = OUTPUT_INDEX[lane]
        values = np.concatenate([activation[:, column] for activation in activations])
        best = None
        for threshold in np.unique(np.quantile(values, np.linspace(.05, .995, 48))):
            guesses = [[float(moment) for moment, _ in picker(float(threshold), fps=FPS).process(row[:, column])]
                       for row in activations]
            rows = [onset_score(reference[lane], guess, TOLERANCE)
                    for reference, guess in zip(references, guesses)]
            tp, fp, fn = (sum(row[key] for row in rows) for key in ("tp", "fp", "fn"))
            candidate = (2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 1.0,
                         -float(threshold), float(threshold))
            if best is None or candidate > best:
                best = candidate
        thresholds[lane] = best[2]
    return thresholds


def extract(activation, thresholds, picker):
    return {lane: [float(moment) for moment, _ in picker(thresholds[lane], fps=FPS).process(
        activation[:, OUTPUT_INDEX[lane]])] for lane in LANES}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--cache-root", type=Path, required=True)
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--pretrained-state", type=Path,
                        help="optional frozen state dict: calibrate only, without a v11 training pass")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--time-cap-seconds", type=float, default=600.0)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit("fresh output directory required")
    manifest_path = args.corpus / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    train_clips, validation_clips = partition_development(manifest["clips"])
    held_clips = [clip for clip in manifest["clips"]
                  if clip.get("split") == "held_out" and clip["id"].startswith("v11-")]
    if len(held_clips) != 66:
        raise ValueError("expected 66 frozen v11 held clips")
    random.seed(SEED); np.random.seed(SEED)
    import torch
    import torch.nn.functional as functional
    torch.manual_seed(SEED); torch.set_num_threads(1)
    upstream_root = upstream_import_root(args.upstream)
    sys.path.insert(0, str(upstream_root))
    from adtof_pytorch import create_frame_rnn_model, calculate_n_bins, load_audio_for_model, load_pytorch_weights
    from adtof_pytorch.post_processing import NotePeakPickingProcessor
    model = create_frame_rnn_model(calculate_n_bins())
    load_pytorch_weights(model, str(args.weights), strict=True)
    if args.pretrained_state:
        model.load_state_dict(torch.load(args.pretrained_state, map_location="cpu"))
    for parameter in model.parameters():
        parameter.requires_grad = True
    staged = args.out / "staged-development-audio"
    train_features, train_targets, train_refs, intervals = {}, {}, {}, []
    class_weight = torch.ones(5); losses = []; frontend_seconds = training_seconds = 0.0
    if not args.pretrained_state:
        frontend_started = time.perf_counter()
        for clip in train_clips:
            audio = stage(args.cache_root / clip["audio"]["path"], staged)
            matrix = load_audio_for_model(str(audio))[0]
            refs = annotation(args.cache_root / clip["annotation"]["path"])
            train_features[clip["id"]] = matrix
            train_targets[clip["id"]] = torch.from_numpy(targets(refs, matrix.shape[0]))
            train_refs[clip["id"]] = refs
            for begin in range(0, matrix.shape[0] - CHUNK + 1, CHUNK):
                intervals.append((clip["id"], begin, begin + CHUNK))
        if not intervals:
            raise ValueError("development clips are shorter than one training interval")
        frontend_seconds = time.perf_counter() - frontend_started
        random.Random(SEED).shuffle(intervals)
        positives = torch.stack([value.sum(dim=0) for value in train_targets.values()]).sum(dim=0)
        total_frames = sum(value.shape[0] for value in train_targets.values())
        for lane, index in OUTPUT_INDEX.items():
            class_weight[index] = min(100.0, float((total_frames - positives[index]) / max(positives[index], 1)))
        optimiser = torch.optim.Adam(model.parameters(), lr=.0001)
        model.train(); started = time.perf_counter()
        for clip_id, begin, end in intervals:
            if time.perf_counter() - started >= args.time_cap_seconds:
                raise RuntimeError("training cap reached before the fixed one epoch completed")
            value = model(train_features[clip_id][begin:end].unsqueeze(0))
            target = train_targets[clip_id][begin:begin + value.shape[1]].unsqueeze(0)
            weight = torch.zeros_like(target)
            for lane, index in OUTPUT_INDEX.items():
                weight[:, :, index] = torch.where(target[:, :, index] > 0,
                    class_weight[index].to(dtype=target.dtype), torch.ones_like(target[:, :, index]))
            loss = functional.binary_cross_entropy(value, target, weight=weight)
            optimiser.zero_grad(); loss.backward(); optimiser.step(); losses.append(float(loss))
        training_seconds = time.perf_counter() - started
    model.eval()
    def infer(clip):
        path = stage(args.cache_root / clip["audio"]["path"], staged)
        with torch.no_grad():
            return model(load_audio_for_model(str(path))).cpu().numpy()[0]
    # Validation is the sole threshold-selection input; held paths are not opened yet.
    validation_activations = [infer(clip) for clip in validation_clips]
    validation_refs = [annotation(args.cache_root / clip["annotation"]["path"]) for clip in validation_clips]
    thresholds = choose_thresholds(validation_activations, validation_refs, NotePeakPickingProcessor)
    validation_predictions = [extract(value, thresholds, NotePeakPickingProcessor)
                              for value in validation_activations]
    torch.save(model.state_dict(), args.out / "model.pt")
    # The frozen model and validation-only thresholds precede every held source read.
    held_activations = [infer(clip) for clip in held_clips]
    held_refs = [annotation(args.cache_root / clip["annotation"]["path"]) for clip in held_clips]
    held_predictions = [extract(value, thresholds, NotePeakPickingProcessor) for value in held_activations]
    absent = {lane: {"clips": 0, "false_positives": 0} for lane in LANES}
    for refs, predicted in zip(held_refs, held_predictions):
        for lane in LANES:
            if not refs[lane]:
                absent[lane]["clips"] += 1
                absent[lane]["false_positives"] += onset_score([], predicted[lane], TOLERANCE)["fp"]
    predictions = {clip["id"]: value for clip, value in zip(held_clips, held_predictions)}
    (args.out / "predictions.json").write_text(json.dumps(predictions, indent=2), encoding="utf-8")
    report = {
        "kind": ("frozen_adtof_v11_validation_only_calibration" if args.pretrained_state else
                 "one_epoch_adtof_v11_development_kit_disjoint_priority_transfer"),
        "acceptance_claimed": False,
        "scope": "Diagnostic only. ADTOF redistribution licensing remains unresolved; no runtime or acceptance claim.",
        "seed": SEED,
        "manifest_sha256": sha256(manifest_path),
        "train_ids": [clip["id"] for clip in train_clips],
        "validation_ids": [clip["id"] for clip in validation_clips],
        "held_ids": [clip["id"] for clip in held_clips],
        "validation_kit": VALIDATION_KIT,
        "held_kits": sorted({clip["kit_id"] for clip in held_clips}),
        "training": {"epoch": 1, "learning_rate": .0001, "intervals": len(intervals),
            "chunk_frames": CHUNK, "frontend_seconds": frontend_seconds,
            "compute_seconds": training_seconds, "time_cap_seconds": args.time_cap_seconds,
            "mean_loss": float(np.mean(losses)) if losses else None, "positive_weights": class_weight.tolist(),
            "loss": ("none; frozen pretrained state, validation-only threshold calibration" if args.pretrained_state else
                     "class-balanced BCE on BD, SD, HH only; TOM and cymbal are zero-weighted")},
        "thresholds_validation_only": thresholds,
        "validation_per_class": score(validation_refs, validation_predictions),
        "held_per_class": score(held_refs, held_predictions),
        "held_absent_lane_false_positives": absent,
        "source_hashes": {"script": sha256(__file__), "manifest": sha256(manifest_path),
            "upstream_model": sha256(upstream_root / "adtof_pytorch" / "model.py"),
            "base_weight": sha256(args.weights), "pretrained_state": sha256(args.pretrained_state) if args.pretrained_state else None,
            "fine_tuned_model": sha256(args.out / "model.pt"),
            "predictions": sha256(args.out / "predictions.json")},
        "limitations": ["Held Hydrogen source kits are disjoint from development source kits.",
            "Metrics use independent 50 ms one-to-one onset scoring; no held labels, audio, or thresholds entered training or selection.",
            "This omits BASS, TOM, grid scoring, ARM measurements, device behavior, and a redistribution decision."]}
    (args.out / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
