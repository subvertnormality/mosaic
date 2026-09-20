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
    separate_drums: DrumSeparator
    track_beats: BeatTracker
    identity: dict[str, str] = field(default_factory=dict)


def bar_activity(candidates: list[dict], downbeats: list[int]) -> np.ndarray:
    """One row per bar: how much each lane played in it, weighted by velocity.

    Velocity rather than a plain count, because a bar where the kit is struck
    hard is a different musical event from one where it is brushed, and phrase
    boundaries tend to fall where that changes.
    """
    if len(downbeats) < 2:
        return np.zeros((0, len(lanes.LANES)))
    rows = np.zeros((len(downbeats) - 1, len(lanes.LANES)))
    index = {name: position for position, name in enumerate(lanes.LANES)}
    for candidate in candidates:
        at = int(candidate["sample_index"])
        for bar in range(len(downbeats) - 1):
            if downbeats[bar] <= at < downbeats[bar + 1]:
                rows[bar, index[candidate["lane"]]] += candidate["velocity"] / 127.0
                break
    return rows


def analyse(mono: np.ndarray, sample_rate: int, models: Models,
            gates: dict[str, float] | None = None,
            alignment: dict | None = None) -> dict:
    """One capture in, one worker-shaped analysis out."""
    gates = dict(gates or lanes.DEFAULT_GATE)
    if set(gates) != set(lanes.LANES):
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

    beats, downbeats = models.track_beats(mono, sample_rate)
    beats = [int(b) for b in beats if 0 <= int(b) < mono.size]
    downbeats = [int(b) for b in downbeats if 0 <= int(b) < mono.size]

    stems = models.separate(mono, sample_rate)
    drums = stems.get("drums")
    pieces = models.separate_drums(drums, sample_rate) if drums is not None else {}

    candidates: list[dict] = []
    for lane in lanes.DRUM_LANES:
        piece = pieces.get(lane.lower())
        if piece is None:
            continue
        for found in onsets.analyse_stem(piece, sample_rate, gates[lane]):
            candidates.append({"lane": lane, **found})
    for lane in lanes.MELODIC_LANES:
        stem = stems.get(lanes.STEM_FOR_LANE[lane])
        if stem is None:
            continue
        for found in onsets.analyse_stem(stem, sample_rate, gates[lane]):
            candidates.append({"lane": lane, **found})

    order = {name: index for index, name in enumerate(lanes.LANES)}
    candidates.sort(key=lambda c: (c["sample_index"], order[c["lane"]]))
    for candidate in candidates:
        candidate["sample_index"] = min(int(candidate["sample_index"]), int(mono.size) - 1)

    # Per-bar lane activity is the feature the phrase boundary is found from.
    # A bar of a chorus and a bar of a verse differ in WHICH instruments play
    # and how often, which is exactly what a self-similarity matrix over these
    # rows measures -- and far more informative than downbeat spacing, which is
    # constant at a fixed tempo and so carries no structure at all.
    aligned = phrase.align(beats, downbeats, sample_rate, mono.size, alignment,
                           features=bar_activity(candidates, downbeats))
    value = dict(empty)
    value.update(aligned)
    value["candidates"] = candidates
    return value
