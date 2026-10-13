"""Development-only low-frequency calibration features for BASS candidates.

The source detector stores three 66-column context frames.  This module reads the
middle (current) frame without duplicating the detector's FFT implementation.
"""
from __future__ import annotations

import numpy as np

BAND_COUNT = 32
BASE_WIDTH = BAND_COUNT * 2 + 2
CURRENT_FRAME_OFFSET = BASE_WIDTH
BAND_EDGES_HZ = np.geomspace(25.0, 7500.0, BAND_COUNT + 1)
LOW_BAND_INDICES = np.flatnonzero(BAND_EDGES_HZ[1:] <= 250.0)
MID_BAND_INDICES = np.flatnonzero(
    (BAND_EDGES_HZ[:-1] >= 250.0) & (BAND_EDGES_HZ[1:] <= 2000.0)
)


def low_frequency_gate(feature_rows):
    """Return positive low-band flux share and low-to-mid current-frame energy.

    Values are derived solely from the RF's existing analysis features, so the
    calibration cannot introduce timing or source-separation differences.
    """
    rows = np.asarray(feature_rows, dtype=float)
    required = CURRENT_FRAME_OFFSET + BASE_WIDTH
    if rows.ndim != 2 or rows.shape[1] < required:
        raise ValueError("expected detector context features")
    current = rows[:, CURRENT_FRAME_OFFSET:required]
    energy = current[:, : BAND_COUNT * 2 : 2]
    delta = current[:, 1 : BAND_COUNT * 2 : 2]
    positive_delta = np.maximum(delta, 0.0)
    total_delta = positive_delta.sum(axis=1)
    low_delta = positive_delta[:, LOW_BAND_INDICES].sum(axis=1)
    low_delta_share = low_delta / (total_delta + 1e-9)
    low_energy = energy[:, LOW_BAND_INDICES].sum(axis=1)
    mid_energy = energy[:, MID_BAND_INDICES].sum(axis=1)
    return low_delta_share, low_energy / (mid_energy + 1e-9)


def fuse_probability(probability, low_delta_share, low_to_mid, rf_weight,
                     delta_scale, ratio_scale):
    """Attenuate RF confidence by a bounded low-frequency/harmonic prior."""
    probability = np.asarray(probability, dtype=float)
    low_delta_share = np.asarray(low_delta_share, dtype=float)
    low_to_mid = np.asarray(low_to_mid, dtype=float)
    if not (probability.shape == low_delta_share.shape == low_to_mid.shape):
        raise ValueError("calibration inputs must have equal shapes")
    if not 0.0 <= rf_weight <= 1.0:
        raise ValueError("rf_weight must be in [0, 1]")
    if delta_scale <= 0.0 or ratio_scale <= 0.0:
        raise ValueError("calibration scales must be positive")
    prior = 0.5 * (
        np.clip(low_delta_share / delta_scale, 0.0, 1.0)
        + np.clip(low_to_mid / ratio_scale, 0.0, 1.0)
    )
    return probability * (rf_weight + (1.0 - rf_weight) * prior)


def apply_gate(probability, low_delta_share, low_to_mid, min_delta_share,
               min_low_to_mid):
    """Zero candidates that fail either independently selected gate."""
    probability = np.asarray(probability, dtype=float)
    keep = (
        (np.asarray(low_delta_share, dtype=float) >= min_delta_share)
        & (np.asarray(low_to_mid, dtype=float) >= min_low_to_mid)
    )
    if probability.shape != keep.shape:
        raise ValueError("calibration inputs must have equal shapes")
    return np.where(keep, probability, 0.0)
