"""Fail-closed Omnizart ``drum_keras`` ONNX raw-head adapter.

This module deliberately contains no download, training, or output-head learning
path.  Its only supported model tensor contract is the one used by Omnizart's
published drum prediction code: CQT patches are batched as
``[batch, 120, 120, 4]`` and each inference result is
``[batch, 13, 4, 1]``.  The source Keras labels assign heads 0/1/4/6 to
BD/SD/CHH/OHH; deployment must separately establish Keras-to-ONNX activation
parity before this adapter is enabled.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
from typing import Any

import numpy as np


PATCH_SIZE = 120
MINI_BEATS_PER_SEGMENT = 4
RAW_HEADS = 13
DRUM_HEADS = {"BD": 0, "SD": 1, "CHH": 4, "OHH": 6}
DRUM_LANES = tuple(DRUM_HEADS)
BACKEND_ID = "omnizart-onnx-raw-heads-v1"


class ArtifactMismatch(ValueError):
    """The configured file is not the pinned ONNX artifact."""


class TensorContractError(ValueError):
    """The session did not implement Omnizart's documented tensor contract."""


def verify_artifact(path: Path, expected_sha256: str) -> str:
    """Return a verified digest, never accepting an inferred or missing pin."""
    if not isinstance(expected_sha256, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected_sha256):
        raise ArtifactMismatch("OMNIZART_ARTIFACT_SHA256_INVALID")
    if not path.is_file():
        raise ArtifactMismatch("OMNIZART_ARTIFACT_MISSING")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual.lower() != expected_sha256.lower():
        raise ArtifactMismatch("OMNIZART_ARTIFACT_SHA256_MISMATCH")
    return actual


def _batches(features: Any, batch_size: int) -> tuple[list[np.ndarray], int, int]:
    value = np.asarray(features, dtype=np.float32)
    if value.ndim != 3 or value.shape[1:] != (PATCH_SIZE, PATCH_SIZE):
        raise TensorContractError("OMNIZART_FEATURE_TENSOR_INVALID")
    source_frames = len(value)
    if source_frames < 1:
        raise TensorContractError("OMNIZART_FEATURE_TENSOR_INVALID")
    if not isinstance(batch_size, int) or batch_size < 1:
        raise TensorContractError("OMNIZART_BATCH_SIZE_INVALID")
    if len(value) < MINI_BEATS_PER_SEGMENT:
        value = np.concatenate((value, np.zeros((MINI_BEATS_PER_SEGMENT - len(value), PATCH_SIZE, PATCH_SIZE), dtype=np.float32)))
    hops = len(value) - MINI_BEATS_PER_SEGMENT + 1
    windows = [np.transpose(value[index:index + MINI_BEATS_PER_SEGMENT], (1, 2, 0)) for index in range(hops)]
    batches = [windows[index:index + batch_size] for index in range(0, len(windows), batch_size)]
    pad = batch_size - len(batches[-1])
    if pad:
        batches[-1].extend([np.zeros_like(windows[0]) for _ in range(pad)])
    return [np.asarray(batch, dtype=np.float32) for batch in batches], pad, source_frames


def _merge(batch_predictions: list[np.ndarray], pad: int, source_frames: int) -> np.ndarray:
    values = np.asarray(batch_predictions, dtype=np.float32)
    if values.ndim != 5 or values.shape[2:] != (RAW_HEADS, MINI_BEATS_PER_SEGMENT, 1):
        raise TensorContractError("OMNIZART_OUTPUT_TENSOR_INVALID")
    values = np.transpose(values, (0, 1, 3, 2, 4))
    batch_count, batch_size = values.shape[:2]
    merged = np.zeros((batch_count * batch_size + MINI_BEATS_PER_SEGMENT - 1, RAW_HEADS), dtype=np.float32)
    for batch_index, batch in enumerate(values):
        for step_index, step in enumerate(batch):
            start = batch_index * batch_size + step_index
            merged[start:start + MINI_BEATS_PER_SEGMENT] += step.squeeze(axis=-1)
    overlap = min(MINI_BEATS_PER_SEGMENT - 1, len(merged) - MINI_BEATS_PER_SEGMENT)
    if overlap > 0:
        merged[overlap:-overlap] /= overlap + 1
        for index in range(overlap):
            merged[index] /= index + 1
            merged[-1 - index] /= index + 1
    if pad:
        merged = merged[:-pad]
    return merged[:source_frames]


def predict_raw_heads(session: Any, features: Any, batch_size: int = 32) -> np.ndarray:
    """Run one already-constructed session with strict upstream input/output shapes."""
    try:
        inputs = session.get_inputs()
        if len(inputs) != 1 or not isinstance(inputs[0].name, str) or not inputs[0].name:
            raise TensorContractError("OMNIZART_SESSION_INPUT_INVALID")
        input_name = inputs[0].name
    except AttributeError as error:
        raise TensorContractError("OMNIZART_SESSION_INPUT_INVALID") from error
    batches, pad, source_frames = _batches(features, batch_size)
    outputs: list[np.ndarray] = []
    for batch in batches:
        result = session.run(None, {input_name: batch})
        if not isinstance(result, (list, tuple)) or len(result) != 1:
            raise TensorContractError("OMNIZART_SESSION_OUTPUT_INVALID")
        output = np.asarray(result[0], dtype=np.float32)
        if output.shape != (len(batch), RAW_HEADS, MINI_BEATS_PER_SEGMENT, 1):
            raise TensorContractError("OMNIZART_OUTPUT_TENSOR_INVALID")
        if not np.isfinite(output).all():
            raise TensorContractError("OMNIZART_OUTPUT_TENSOR_INVALID")
        outputs.append(output)
    return _merge(outputs, pad, source_frames)


def _validate_gates(gates: Any) -> dict[str, float]:
    if not isinstance(gates, dict) or set(gates) != set(DRUM_LANES):
        raise TensorContractError("OMNIZART_DRUM_GATES_INVALID")
    result = {lane: float(gates[lane]) for lane in DRUM_LANES}
    if any(not np.isfinite(value) or value < 0 or value > 1 for value in result.values()):
        raise TensorContractError("OMNIZART_DRUM_GATES_INVALID")
    return result


def decode_drum_heads(raw: Any, mini_beats: Any, sample_rate: int, gates: Any) -> list[dict[str, Any]]:
    """Peak-decode four independent raw heads; CHH and OHH are never combined."""
    activations = np.asarray(raw, dtype=np.float32)
    positions = np.asarray(mini_beats, dtype=np.float64)
    selected_gates = _validate_gates(gates)
    if activations.ndim != 2 or activations.shape[1] != RAW_HEADS or len(activations) != len(positions):
        raise TensorContractError("OMNIZART_DECODE_TENSOR_INVALID")
    if not isinstance(sample_rate, int) or sample_rate < 8000 or not np.isfinite(positions).all() or np.any(positions < 0):
        raise TensorContractError("OMNIZART_DECODE_TIMING_INVALID")
    candidates: list[dict[str, Any]] = []
    for lane, head in DRUM_HEADS.items():
        values = activations[:, head]
        for index, confidence in enumerate(values):
            before = values[index - 1] if index else -np.inf
            after = values[index + 1] if index + 1 < len(values) else -np.inf
            if confidence >= selected_gates[lane] and confidence >= before and confidence > after:
                candidates.append({"lane": lane, "sample_index": int(round(float(positions[index]) * sample_rate)),
                                   "velocity": int(round(1 + 126 * float(confidence))), "confidence": float(confidence)})
    return sorted(candidates, key=lambda candidate: (candidate["sample_index"], candidate["lane"]))


def analyse_features(*, session: Any, model_path: Path, expected_sha256: str, features: Any,
                     mini_beats: Any, sample_rate: int, gates: Any, bpm: float,
                     origin_sample: int) -> dict[str, Any]:
    """Return a verified four-lane component result for a later five-lane merger."""
    digest = verify_artifact(model_path, expected_sha256)
    if not isinstance(bpm, (int, float)) or not np.isfinite(bpm) or not 40 <= bpm <= 240:
        raise TensorContractError("OMNIZART_BPM_INVALID")
    if not isinstance(origin_sample, int) or origin_sample < 0:
        raise TensorContractError("OMNIZART_ORIGIN_INVALID")
    raw = predict_raw_heads(session, features)
    return {"bpm": float(bpm), "origin_sample": origin_sample,
            "drum_component": {"backend_id": BACKEND_ID, "drum_artifact_sha256": digest},
            "lane_onset_gates": _validate_gates(gates),
            "candidates": decode_drum_heads(raw, mini_beats, sample_rate, gates)}
