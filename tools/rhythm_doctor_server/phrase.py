"""Phrase alignment from tracked beats and downbeats.

The remote path does not have to guess where the bar is: a downbeat tracker
states it. What remains is which of four bars opens the phrase, which is a
question about repetition rather than about accent, and the standard tool is
Foote's novelty over a self-similarity matrix (Foote, ICME 2000). It is applied
to BAR-synchronous features here, which is the arrangement compared against
beat-synchronous features in the barwise music structure analysis literature.

Where there is too little recording to see a four-bar period repeat, that is
reported as low confidence rather than papered over. Four bars of audio contain
no evidence about which of them is the first.
"""
from __future__ import annotations

import numpy as np

PHRASE_BARS = 4
CELLS_PER_BEAT = 4
BEATS_PER_BAR = 4
WINDOW_CELLS = PHRASE_BARS * BEATS_PER_BAR * CELLS_PER_BEAT


def tempo_from_beats(beats: list[int], sample_rate: int) -> tuple[float, bool]:
    """Median inter-beat interval, which is robust to a dropped beat."""
    if len(beats) < 3:
        return 120.0, False
    gaps = np.diff(np.asarray(beats, dtype=np.float64))
    gaps = gaps[gaps > 0]
    if gaps.size == 0:
        return 120.0, False
    bpm = 60.0 * sample_rate / float(np.median(gaps))
    if not (40.0 <= bpm <= 240.0):
        return 120.0, False
    return float(bpm), True


def phrase_offset(features: np.ndarray) -> tuple[int, float]:
    """Which bar of four opens the phrase, and how much to believe it.

    Foote novelty is the standard tool for finding structure in audio, and it
    is the wrong tool for this. It detects CHANGE across a boundary -- verse
    into chorus -- and a four-bar phrase that repeats identically has no change
    at its boundaries at all. Measured on exactly periodic material it returns
    the same value at every bar, and the winner is then decided by which
    candidates happened to include the uncomputed edges of the array. It
    reported an artefact of array shape with full confidence.

    What actually marks the boundary in homogeneous playing is the drummer: a
    fill closes the fourth bar and the first bar lands back on the pattern, so
    the largest bar-to-bar change in the whole phrase is the one INTO the
    downbeat. That is what is measured here: bars are averaged by their
    position within the phrase, and the position whose profile differs most
    from the position before it opens the phrase.
    """
    bars = features.shape[0]
    if bars < 2 * PHRASE_BARS:
        # Fewer than two phrases: nothing repeats yet, and any answer would be
        # an artefact of where the recording happened to start.
        return 0, 0.0
    profile = np.zeros((PHRASE_BARS, features.shape[1]))
    for residue in range(PHRASE_BARS):
        rows = features[residue::PHRASE_BARS]
        if rows.size:
            profile[residue] = rows.mean(axis=0)
    scale = np.linalg.norm(profile) + 1e-9
    change = [float(np.linalg.norm(profile[r] - profile[(r - 1) % PHRASE_BARS]) / scale)
              for r in range(PHRASE_BARS)]
    best = int(np.argmax(change))
    ordered = sorted(change, reverse=True)
    if ordered[0] <= 0:
        return 0, 0.0
    # How much the winning change stands out against the others. Uniform bars
    # give every position the same change and so no confidence, which is the
    # correct answer for material that carries no phrase information.
    margin = (ordered[0] - ordered[1]) / ordered[0]
    return best, float(min(1.0, max(0.0, margin)))


def bar_features(beats: list[int], downbeats: list[int], mono_length: int) -> np.ndarray:
    """A crude per-bar signature: where the downbeats fall inside each bar.

    Deliberately shape-only. The caller supplies richer features when it has
    them; with none, spacing alone still distinguishes a repeated four-bar
    grouping from an unstructured one.
    """
    if len(downbeats) < 2:
        return np.zeros((0, 1))
    gaps = np.diff(np.asarray(downbeats, dtype=np.float64))
    return gaps.reshape(-1, 1)


def align(beats: list[int], downbeats: list[int], sample_rate: int,
          capture_samples: int, alignment: dict | None = None,
          features: np.ndarray | None = None) -> dict:
    """Return the tempo and phrase fields of an analysis result."""
    bpm, detected = tempo_from_beats(beats, sample_rate)
    value = {"bpm": bpm, "tempo_detected": detected, "tempo_mode": "auto",
             "origin_sample": 0, "phrase_start_sample": 0, "phrase_confidence": 0.0,
             "beat_positions": [int(b) for b in beats]}
    if alignment:
        # A correction the player made outranks the tracker, and the origin
        # they chose IS the phrase start: saying where the phrase begins is
        # the entire purpose of the correction.
        origin = int(alignment["origin_sample"])
        value.update(bpm=float(alignment["bpm"]), tempo_detected=True, tempo_mode="manual",
                     origin_sample=origin, phrase_start_sample=origin, phrase_confidence=1.0,
                     beat_positions=sorted(set(value["beat_positions"]) | {origin}))
        return value
    if not detected or not downbeats:
        return value

    rows = features if features is not None else bar_features(beats, downbeats, capture_samples)
    offset, confidence = phrase_offset(rows) if rows.size else (0, 0.0)

    samples_per_cell = sample_rate * 15.0 / bpm
    window = WINDOW_CELLS * samples_per_cell
    # Take the first phrase downbeat that still has a whole window behind it.
    # Jumping to one with two bars of capture left shows a view clamped against
    # the end, which reads as a fault rather than as the end of the take.
    phrase_start = None
    for index in range(offset, len(downbeats), PHRASE_BARS):
        if downbeats[index] + window <= capture_samples:
            phrase_start = int(downbeats[index])
            break
    if phrase_start is None:
        return value

    cells_before = int(phrase_start // samples_per_cell)
    origin = int(round(phrase_start - cells_before * samples_per_cell))
    value.update(origin_sample=max(0, origin), phrase_start_sample=phrase_start,
                 phrase_confidence=float(confidence))
    return value
