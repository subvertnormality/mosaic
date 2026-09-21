"""Remote analysis pipeline: separate, then detect, then align.

Order matters and is not arbitrary.

1. Downbeats are tracked on the MIX, before separation. Beat This! was trained
   on mixes, and separation is lossy -- running it on a drums stem throws away
   the harmonic motion that marks a bar line.
2. htdemucs_6s splits the mix into six stems.
3. LarsNet splits the drums stem into five pieces. This is the thing the local
   backend fundamentally cannot do: it guesses kit pieces from a full mix,
   where a kick and a bass note share a transient.
4. Every stem becomes onsets and velocity. No pitch anywhere: the bank stores
   a gate and a velocity per cell and has nowhere to put a note number.

Each model is injected rather than imported at module scope, so the contract
and the assembly can be tested without a GPU or several gigabytes of weights.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol

import numpy as np

import lanes
import onsets
import phrase

SR = 44100


class Separator(Protocol):
    def __call__(self, mono: np.ndarray, sample_rate: int) -> dict[str, np.ndarray]: ...


class DrumSeparator(Protocol):
    def __call__(self, drums: np.ndarray, sample_rate: int) -> dict[str, np.ndarray]: ...


class BeatTracker(Protocol):
    """Returns (beat_samples, downbeat_samples)."""
    def __call__(self, mono: np.ndarray, sample_rate: int) -> tuple[list[int], list[int]]: ...


@dataclass
class Models:
    separate: Separator
    track_beats: BeatTracker
    # Optional: LarsNet's checkpoints are CC BY-NC 4.0 and are a separate
    # download, so a server may legitimately run without them. Without it the
    # drums stem becomes one DRUMS lane instead of five.
    separate_drums: DrumSeparator | None = None
    identity: dict[str, str] = field(default_factory=dict)

    def lane_names(self) -> tuple[str, ...]:
        return lanes.lane_set(self.separate_drums is not None)


def bar_activity(candidates: list[dict], downbeats: list[int],
                 names: tuple[str, ...] = lanes.LANES) -> np.ndarray:
    """One row per bar: how much each lane played in it, weighted by velocity.

    Velocity rather than a plain count, because a bar where the kit is struck
    hard is a different musical event from one where it is brushed, and phrase
    boundaries tend to fall where that changes.
    """
    if len(downbeats) < 2:
        return np.zeros((0, len(names)))
    rows = np.zeros((len(downbeats) - 1, len(names)))
    index = {name: position for position, name in enumerate(names)}
    for candidate in candidates:
        at = int(candidate["sample_index"])
        for bar in range(len(downbeats) - 1):
            if downbeats[bar] <= at < downbeats[bar + 1]:
                rows[bar, index[candidate["lane"]]] += candidate["velocity"] / 127.0
                break
    return rows


def resample(mono: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
    """Bring a capture to the rate the models were trained at.

    A norns records at its hardware rate, which is not 44100, and every model
    here expects 44100: demucs refuses outright, and Beat This! would report a
    tempo scaled by the rate ratio without complaining at all. Uses torchaudio
    when it is present -- it is a demucs dependency, so in practice it always
    is -- and falls back to linear interpolation, which is poorer but honest
    and keeps the server working rather than failing the capture.
    """
    if source_rate == target_rate:
        return np.asarray(mono, dtype=np.float32)
    try:
        import torch
        import torchaudio
        wave = torch.tensor(np.asarray(mono, dtype=np.float32))[None]
        out = torchaudio.functional.resample(wave, source_rate, target_rate)
        return out[0].numpy().astype(np.float32)
    except Exception:
        count = int(round(len(mono) * target_rate / float(source_rate)))
        if count <= 0:
            return np.zeros(0, dtype=np.float32)
        source = np.arange(len(mono), dtype=np.float64)
        target = np.linspace(0, len(mono) - 1, count)
        return np.interp(target, source, np.asarray(mono, dtype=np.float64)).astype(np.float32)


def analyse(mono: np.ndarray, sample_rate: int, models: Models,
            gates: dict[str, float] | None = None,
            alignment: dict | None = None) -> dict:
    """One capture in, one worker-shaped analysis out."""
    names = models.lane_names()
    gates = dict(gates or lanes.gates_for(names))
    if set(gates) != set(names):
        raise ValueError("a gate is required for every lane, and only for lanes")
    mono = np.asarray(mono, dtype=np.float32)
    empty = {
        "bpm": 120.0, "tempo_detected": False, "origin_sample": 0,
        "phrase_start_sample": 0, "phrase_confidence": 0.0, "beat_positions": [],
        "tempo_mode": "auto", "lane_onset_gates": gates, "candidates": [],
        "detector": dict(models.identity),
    }
    if not mono.size or not np.any(mono):
        return empty

    # Everything below runs at the models' rate; positions are converted back
    # to the capture's own coordinates at the end, because the bank addresses
    # samples of the file the player recorded, not of our working copy.
    source_rate, source_samples = int(sample_rate), int(mono.size)
    analysis = resample(mono, source_rate, SR)
    if not analysis.size:
        return empty
    scale = source_rate / float(SR)

    beats, downbeats = models.track_beats(analysis, SR)
    beats = [int(b) for b in beats if 0 <= int(b) < analysis.size]
    downbeats = [int(b) for b in downbeats if 0 <= int(b) < analysis.size]

    stems = models.separate(analysis, SR)
    drums = stems.get("drums")
    candidates: list[dict] = []
    if drums is not None and models.separate_drums is not None:
        pieces = models.separate_drums(drums, SR)
        for lane in lanes.DRUM_LANES:
            piece = pieces.get(lane.lower())
            if piece is None:
                continue
            for found in onsets.analyse_stem(piece, SR, gates[lane]):
                candidates.append({"lane": lane, **found})
    elif drums is not None:
        for found in onsets.analyse_stem(drums, SR, gates["DRUMS"]):
            candidates.append({"lane": "DRUMS", **found})
    for lane in lanes.MELODIC_LANES:
        stem = stems.get(lanes.STEM_FOR_LANE[lane])
        if stem is None:
            continue
        for found in onsets.analyse_stem(stem, sample_rate, gates[lane]):
            candidates.append({"lane": lane, **found})

    order = {name: index for index, name in enumerate(names)}
    candidates.sort(key=lambda c: (c["sample_index"], order[c["lane"]]))

    # Per-bar lane activity is the feature the phrase boundary is found from.
    # A bar of a chorus and a bar of a verse differ in WHICH instruments play
    # and how often, which is exactly what a self-similarity matrix over these
    # rows measures -- and far more informative than downbeat spacing, which is
    # constant at a fixed tempo and so carries no structure at all.
    #
    # Still at the models' rate: the beat grid and the onsets have to agree
    # about what a sample is, and the tempo is derived from their spacing.
    aligned = phrase.align(beats, downbeats, SR, analysis.size, alignment,
                           features=bar_activity(candidates, downbeats, names))

    # Back to the capture's own coordinates. The bank addresses samples of the
    # file the player recorded, not of the server's resampled working copy.
    for candidate in candidates:
        candidate["sample_index"] = min(int(round(candidate["sample_index"] * scale)),
                                        source_samples - 1)
    aligned["beat_positions"] = [min(int(round(b * scale)), source_samples - 1)
                                 for b in aligned.get("beat_positions", [])]
    for key in ("origin_sample", "phrase_start_sample"):
        aligned[key] = min(int(round(aligned[key] * scale)), source_samples - 1)

    value = dict(empty)
    value.update(aligned)
    value["candidates"] = candidates
    return value
