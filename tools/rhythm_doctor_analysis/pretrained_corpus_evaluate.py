#!/usr/bin/env python3
"""Score the pinned pretrained chain against a validated schema-v2 corpus.

This is a quality-only measurement tool.  It never trains, fits, downloads, or
changes the pinned models.  Confidence gates are selected solely from cached
development predictions; held-out predictions are then scored once with those
fixed gates.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import wave


ROOT = Path(__file__).resolve().parents[2]
for directory in (ROOT / "tools" / "rhythm_doctor", ROOT / "tests" / "rhythm_doctor"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import pretrained_runtime_factory
from pretrained_composite_backend import DRUM_LANES, compose
from corpus import FOUR_BAR_STRATA, LANES, validate_manifest
from quality_report import evaluate as evaluate_quality


CACHE_SCHEMA_VERSION = 1
REPORT_SCHEMA_VERSION = 1
ONSET_TOLERANCE_SECONDS = 0.050
STRATA = FOUR_BAR_STRATA


class EvaluationError(ValueError):
    """The input, runtime, or resume cache cannot establish a score."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_hash(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _atomic_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".rd-evaluator-", suffix=".json", dir=str(path.parent))
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as target:
            json.dump(value, target, sort_keys=True, separators=(",", ":"))
            target.write("\n")
        temporary_path.replace(path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def force_candidate_floor(runtime) -> None:
    """Expose all decoder peaks before development-only gate selection."""
    gates = getattr(runtime, "drum_gates", None)
    if not isinstance(gates, dict) or set(gates) != set(DRUM_LANES):
        raise EvaluationError("pinned runtime does not expose four drum gates")
    runtime.drum_gates = dict.fromkeys(DRUM_LANES, 0.0)
    if not _number(getattr(runtime, "bass_gate", None)):
        raise EvaluationError("pinned runtime does not expose BASS gate")
    onset = getattr(getattr(runtime, "bass_pipeline", None), "onset", None)
    if not _number(getattr(onset, "threshold", None)):
        raise EvaluationError("pinned runtime does not expose Basic Pitch candidate floor")
    runtime.bass_gate = 0.0
    onset.threshold = 0.0


def runtime_model_hash() -> tuple[str, dict[str, str]]:
    """Identify the factory code and all immutable pretrained artifacts."""
    sources = {
        "runtime_factory_sha256": _sha256_file(ROOT / "tools" / "rhythm_doctor" / "pretrained_runtime_factory.py"),
        "composite_backend_sha256": _sha256_file(ROOT / "tools" / "rhythm_doctor" / "pretrained_composite_backend.py"),
        "omnizart_source_revision": pretrained_runtime_factory.OMNIZART_V042_HEAD,
        "omnizart_drum_onnx_sha256": pretrained_runtime_factory.OMNIZART_DRUM_ONNX_SHA256,
        "umxhq_bass_sha256": pretrained_runtime_factory.UMXHQ_BASS_SHA256,
        "basic_pitch_onnx_sha256": pretrained_runtime_factory.BASIC_PITCH_ONNX_SHA256,
    }
    return _canonical_hash(sources), sources


def _relative(root: Path, descriptor: dict, context: str) -> Path:
    path = descriptor.get("path") if isinstance(descriptor, dict) else None
    if not isinstance(path, str) or not path:
        raise EvaluationError("missing %s path" % context)
    candidate = (root / path).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as error:
        raise EvaluationError("%s path escapes corpus" % context) from error
    return candidate


def load_corpus(manifest_path: Path, corpus_root: Path) -> tuple[dict, list[dict], str, dict]:
    """Read annotations only after the independent validator re-hashes corpus bytes."""
    root = Path(corpus_root).resolve()
    validate_manifest(manifest_path, root)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise EvaluationError("validated manifest is unreadable") from error
    clips = []
    for source in manifest["clips"]:
        annotation_path = _relative(root, source["annotation"], "%s annotation" % source["id"])
        try:
            annotation = json.loads(annotation_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise EvaluationError("%s annotation is unreadable" % source["id"]) from error
        try:
            with wave.open(str(_relative(root, source["audio"], "%s audio" % source["id"])), "rb") as audio:
                sample_rate = audio.getframerate()
        except (OSError, wave.Error) as error:
            raise EvaluationError("%s audio is not PCM WAV" % source["id"]) from error
        if type(sample_rate) is not int or sample_rate <= 0:
            raise EvaluationError("%s sample rate is invalid" % source["id"])
        clip = dict(source)
        clip["events"] = annotation["events"]
        clip["sample_rate"] = sample_rate
        clip["audio_path"] = _relative(root, source["audio"], "%s audio" % source["id"])
        clips.append(clip)
    source_hashes = {
        "manifest_sha256": _sha256_file(manifest_path),
        "sources": [{"id": source["id"], "archive_sha256": source["archive"]["sha256"],
                     "license_evidence_sha256": source["license_evidence"]["sha256"]}
                    for source in manifest["sources"]],
        "clips": {clip["id"]: {
            "audio_sha256": clip["audio"]["sha256"], "annotation_sha256": clip["annotation"]["sha256"],
            "recipe_sha256": clip["render"]["recipe"]["sha256"],
            "timbre_evidence_sha256": clip["timbre_evidence"]["sha256"],
        } for clip in clips},
    }
    return manifest, clips, _canonical_hash(source_hashes), source_hashes


def _cache_path(cache_root: Path, model_hash: str, corpus_hash: str, clip_id: str) -> Path:
    if (not isinstance(clip_id, str) or not clip_id or clip_id in {".", ".."}
            or Path(clip_id).name != clip_id):
        raise EvaluationError("clip id is unsuitable for cache path")
    return cache_root / model_hash / corpus_hash / (clip_id + ".json")


def cached_prediction(cache_root: Path, model_hash: str, corpus_hash: str, clip: dict, infer) -> dict:
    """Resume only when model, corpus, and per-clip source bytes all agree."""
    path = _cache_path(cache_root, model_hash, corpus_hash, clip["id"])
    identity = {"id": clip["id"], "audio_sha256": clip["audio"]["sha256"],
                "annotation_sha256": clip["annotation"]["sha256"]}
    if path.is_file():
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise EvaluationError("cached prediction is corrupt: %s" % clip["id"]) from error
        if (cached.get("schema_version") == CACHE_SCHEMA_VERSION and cached.get("model_hash") == model_hash
                and cached.get("corpus_hash") == corpus_hash and cached.get("clip") == identity
                and isinstance(cached.get("prediction"), dict)):
            return cached["prediction"]
    prediction = infer(clip)
    if not isinstance(prediction, dict):
        raise EvaluationError("runtime returned invalid prediction for %s" % clip["id"])
    _atomic_json(path, {"schema_version": CACHE_SCHEMA_VERSION, "model_hash": model_hash,
                        "corpus_hash": corpus_hash, "clip": identity, "prediction": prediction})
    return prediction


def _candidates(prediction: dict, lane: str, threshold: float, sample_rate: int) -> list[dict]:
    if lane not in LANES or not _number(threshold) or not 0 <= threshold <= 1:
        raise EvaluationError("invalid lane threshold")
    candidates = prediction.get("candidates")
    if not isinstance(candidates, list):
        raise EvaluationError("prediction lacks candidates")
    selected = []
    for candidate in candidates:
        if not isinstance(candidate, dict) or candidate.get("lane") not in LANES:
            raise EvaluationError("invalid raw candidate")
        confidence, index, velocity = candidate.get("confidence"), candidate.get("sample_index"), candidate.get("velocity")
        if not _number(confidence) or not 0 <= confidence <= 1 or type(index) is not int or index < 0 or type(velocity) is not int or not 1 <= velocity <= 127:
            raise EvaluationError("invalid raw candidate")
        if candidate["lane"] == lane and confidence >= threshold:
            selected.append({"time_seconds": index / float(sample_rate), "velocity": velocity,
                             "confidence": float(confidence)})
    return sorted(selected, key=lambda item: item["time_seconds"])


def _match(reference: list[dict], predicted: list[dict]) -> tuple[int, int, int, list[tuple[int, int]]]:
    """The same chronological, one-to-one 50 ms rule used by quality.py."""
    reference = sorted(reference, key=lambda item: item["time_seconds"])
    predicted = sorted(predicted, key=lambda item: item["time_seconds"])
    left = right = tp = 0
    pairs = []
    while left < len(reference) and right < len(predicted):
        difference = predicted[right]["time_seconds"] - reference[left]["time_seconds"]
        if abs(difference) <= ONSET_TOLERANCE_SECONDS + 1e-12:
            tp += 1
            pairs.append((reference[left]["velocity"], predicted[right]["velocity"]))
            left += 1; right += 1
        elif difference < 0:
            right += 1
        else:
            left += 1
    return tp, len(predicted) - tp, len(reference) - tp, pairs


def _cell_counts(reference: list[dict], predicted: list[dict], bpm: float) -> tuple[int, int, int]:
    if not _number(bpm) or not 40 <= bpm <= 240:
        raise EvaluationError("clip bpm is invalid")
    duration = 60.0 / bpm / 4.0
    def cells(values):
        result = Counter()
        for event in values:
            cell = int(math.floor(event["time_seconds"] / duration + .5))
            if 0 <= cell < 64:
                result[cell] += 1
        return result
    reference_cells, predicted_cells = cells(reference), cells(predicted)
    tp = sum(min(reference_cells[cell], predicted_cells[cell]) for cell in reference_cells)
    return tp, sum(predicted_cells.values()) - tp, sum(reference_cells.values()) - tp


def select_development_thresholds(development: list[dict], sample_rate: int | None = None) -> dict[str, float]:
    """Pick one gate per lane by development onset F1, breaking ties upward."""
    if not development:
        raise EvaluationError("development split is empty")
    selected = {}
    for lane in LANES:
        possibilities = {0.0, 1.0}
        for clip in development:
            rate = clip.get("sample_rate", sample_rate)
            possibilities.update(candidate["confidence"] for candidate in _candidates(clip["prediction"], lane, 0.0, rate))
        best = None
        for threshold in sorted(possibilities):
            tp = fp = fn = 0
            for clip in development:
                rate = clip.get("sample_rate", sample_rate)
                counts = _match(clip["events"][lane], _candidates(clip["prediction"], lane, threshold, rate))
                tp += counts[0]; fp += counts[1]; fn += counts[2]
            f1 = 2 * tp / float(2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0
            # A higher threshold makes equal-F1 selections less permissive.
            candidate = (f1, threshold)
            if best is None or candidate > best:
                best = candidate
        selected[lane] = best[1]
    return selected


def _gain_ladder(clips: list[dict], predictions: dict[str, dict], gates: dict[str, float],
                 sample_rate: int | None = None) -> dict[str, dict]:
    evidence = {}
    for lane in LANES:
        pairs = []
        saw_ladder, complete, monotonic = False, True, True
        for clip in clips:
            if clip["stratum"] != "isolated" or "gain_ladder" not in clip.get("tags", ()) or not clip["events"][lane]:
                continue
            saw_ladder = True
            rate = clip.get("sample_rate", sample_rate)
            matched = _match(clip["events"][lane], _candidates(predictions[clip["id"]], lane, gates[lane], rate))
            pairs.extend(matched[3])
            complete = complete and matched[2] == 0 and bool(matched[3])
            monotonic = monotonic and all(b[1] >= a[1] for a, b in zip(matched[3], matched[3][1:]))
        errors = [abs(reference - predicted) for reference, predicted in pairs]
        evidence[lane] = {"velocity_absolute_errors": errors,
                          "velocity_monotonic": saw_ladder and complete and monotonic and bool(pairs)}
    return evidence


def held_out_rows(clips: list[dict], predictions: dict[str, dict], gates: dict[str, float], sample_rate: int | None = None) -> list[dict]:
    """Score held-out data once after gates have already been frozen."""
    held = [clip for clip in clips if clip["split"] == "held_out"]
    if not held or set(gates) != set(LANES):
        raise EvaluationError("held split or fixed lane gates are invalid")
    ladders = _gain_ladder(held, predictions, gates, sample_rate)
    rows = []
    for lane in LANES:
        for stratum in STRATA:
            aggregate = dict(onset_tp=0, onset_fp=0, onset_fn=0, cell_tp=0, cell_fp=0, cell_fn=0,
                             negative_control_painted_events=0, negative_control_clips=0)
            for clip in held:
                if clip["stratum"] != stratum:
                    continue
                rate = clip.get("sample_rate", sample_rate)
                if not isinstance(rate, int) or rate <= 0:
                    raise EvaluationError("clip sample rate is invalid")
                reference = clip["events"][lane]
                predicted = _candidates(predictions[clip["id"]], lane, gates[lane], rate)
                onset = _match(reference, predicted)
                cells = _cell_counts(reference, predicted, clip["bpm"])
                for field, value in zip(("onset_tp", "onset_fp", "onset_fn"), onset[:3]):
                    aggregate[field] += value
                for field, value in zip(("cell_tp", "cell_fp", "cell_fn"), cells):
                    aggregate[field] += value
                if not reference:
                    aggregate["negative_control_clips"] += 1
                    aggregate["negative_control_painted_events"] += len(predicted)
            velocity = ladders[lane] if stratum == "isolated" else {
                "velocity_absolute_errors": [], "velocity_monotonic": True,
            }
            row = {"lane": lane, "stratum": stratum, **aggregate, **velocity}
            rows.append(row)
    return rows


def run(manifest_path: Path, corpus_root: Path, cache_root: Path, report_path: Path) -> dict:
    manifest_path = Path(manifest_path).resolve()
    corpus_root = Path(corpus_root).resolve()
    _, clips, corpus_hash, source_hashes = load_corpus(manifest_path, corpus_root)
    model_hash, model_sources = runtime_model_hash()
    runtime = None
    profile = None

    def infer(clip):
        nonlocal runtime, profile
        # Construct at most one real pinned runtime, and only if an absent
        # cache record actually needs inference. A fully warm cache remains
        # auditable without requiring local model provisioning.
        if runtime is None:
            runtime = pretrained_runtime_factory.make()
            force_candidate_floor(runtime)
            profile = {"backend_sha256": model_sources["composite_backend_sha256"],
                       "drum_artifact_sha256": pretrained_runtime_factory.OMNIZART_DRUM_ONNX_SHA256,
                       "bass_artifact_sha256": runtime.bass_pipeline.artifact_sha256}
        return compose({"wav_path": str(clip["audio_path"]), "pretrained": profile}, runtime)

    predictions = {clip["id"]: cached_prediction(Path(cache_root), model_hash, corpus_hash, clip, infer)
                   for clip in clips if clip["split"] in {"development", "held_out"}}
    development = [dict(clip, prediction=predictions[clip["id"]]) for clip in clips if clip["split"] == "development"]
    gates = select_development_thresholds(development)
    # There is deliberately one held-out aggregation after development gates are fixed.
    rows = held_out_rows(clips, predictions, gates)
    quality = evaluate_quality(rows)
    report = {"schema_version": REPORT_SCHEMA_VERSION, "scope": "quality-only; corpus, provenance, and acceptance gates remain separate",
              "complete_rd02_acceptance": False, "manifest": str(manifest_path), "model_hash": model_hash,
              "corpus_hash": corpus_hash, "model_sources": model_sources, "source_hashes": source_hashes,
              "pinned_runtime_loaded": runtime is not None,
              "development_thresholds": gates, "held_out_rows": rows, "quality_report": quality}
    _atomic_json(Path(report_path), report)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True, help="validated schema-v2 external corpus manifest")
    parser.add_argument("--corpus-root", type=Path, required=True,
                        help="external corpus root to which manifest descriptors are relative")
    parser.add_argument("--cache-dir", type=Path, required=True, help="resume cache for raw floor-zero predictions")
    parser.add_argument("--report", type=Path, required=True, help="quality-only JSON report")
    args = parser.parse_args(argv)
    try:
        report = run(args.manifest, args.corpus_root, args.cache_dir, args.report)
    except (EvaluationError, OSError, ValueError) as error:
        print("pretrained corpus evaluation failed: %s" % error, file=sys.stderr)
        return 2
    print(json.dumps({"quality_passed": report["quality_report"]["passed"], "report": str(args.report)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
