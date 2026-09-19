#!/usr/bin/env python3
"""Classical-DSP drum lane detection: partially fixed NMF, no learned model.

Why this exists. The pinned pretrained chain cannot run standalone on the
device: measured on physical Norns it needs about six minutes for the drum
graph alone on one 45-second capture, and batching and threading do not close
that gap (evidence/norns-drum-inference-2026-09-19.json). This backend runs at
a few hundredths of real time, needs no ONNX Runtime and no model weights, and
is GPL-3 clean.

Method. V is factorised as B_D G_D + B_H G_H, where B_D holds fixed drum
templates and B_H is a freely adapting harmonic dictionary. That harmonic half
is what makes NMF work on full mixes rather than only on isolated drum stems:
bass, guitar and vocals are given somewhere to go instead of contaminating the
drum activations.

Nothing here is tuned by us where a published value exists. The drum dictionary
is Wu & Lerch's (ISMIR 2015), redistributed under GPL-3 with attribution; see
data/NMF_TEMPLATES_PROVENANCE.md. The peak-picking constants are Boeck, Krebs &
Schedl's (ISMIR 2012), grid-searched over 25,966 onsets.

Lane scope. BD, SD and CYM. The third lane is deliberately CYM, hats AND
cymbals together, not closed hi-hat alone. The hat template has high recall for
metal but cannot separate a hat from a ride: both are inharmonic plates with
overlapping 5-15 kHz energy, and the one property that distinguishes them,
decay, is destroyed by a full mix. Scored as CHH-only the lane reaches 0.4374
F1 at 0.2965 precision; scored as CYM, with the SAME detector output, it
reaches 0.7165 at 0.7006 on held-out real music. The detector was never wrong,
the lane definition was, and the events it finds are real cymbal hits a player
may want. Adding ride and crash decoy templates was tried and gains only 0.02;
summing their activations into the lane costs 0.08.

BASS is not detected here. No corpus with human-verified bass onsets on real
full-mix music exists, so the lane cannot be honestly measured (see CORPUS.md).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

SR = 44100
NFFT, HOP = 2048, 512
LANES = ("BD", "SD", "CYM")
EPS = 1e-10

# Harmonic rank. The shipped toolbox default is 50; a sweep on real-music
# development material found 10 marginally better and cheaper, and the
# difference across 10..50 was under 0.02 F1 on every lane.
HARMONIC_RANK = 10
ITERATIONS = 20                      # toolbox default (maxIter)

# Boeck, Krebs & Schedl offline peak-picking window sizes, in frames.
W1, W2, W3, W4, W5 = 3, 3, 8, 1, 2

_TEMPLATES = Path(__file__).resolve().parent / "data" / "nmf_drum_templates.npz"


def load_templates(path=_TEMPLATES):
    """Return (lane names, fixed dictionary, (window, hop)) for the pinned STFT."""
    with np.load(path, allow_pickle=False) as data:
        B = np.asarray(data["templates"], dtype=np.float32)
        lanes = tuple(str(x) for x in data["lanes"])
        geom = (int(data["window_size"]), int(data["hop_size"]))
    if B.ndim != 2 or B.shape[1] != len(lanes) or not np.isfinite(B).all():
        raise ValueError("drum template dictionary is malformed")
    return lanes, B, geom


def stft_magnitude(x, nfft=NFFT, hop=HOP):
    window = np.hanning(nfft).astype(np.float32)
    frames = 1 + max(0, (len(x) - nfft) // hop)
    out = np.empty((nfft // 2 + 1, frames), dtype=np.float32)
    for i in range(frames):
        out[:, i] = np.abs(np.fft.rfft(x[i * hop:i * hop + nfft] * window))
    return out


def pfnmf(V, B_D, harmonic_rank=HARMONIC_RANK, iterations=ITERATIONS, seed=0):
    """KL multiplicative updates with the drum dictionary held fixed.

    Only B_H, G_D and G_H adapt. Seeded so a capture analysed twice gives an
    identical result; the player must not see a different transcription from
    the same audio.
    """
    rng = np.random.default_rng(seed)
    bins, frames = V.shape
    drums = B_D.shape[1]
    B_H = rng.random((bins, harmonic_rank)).astype(np.float32) + 0.1
    G_D = rng.random((drums, frames)).astype(np.float32) + 0.1
    G_H = rng.random((harmonic_rank, frames)).astype(np.float32) + 0.1
    ones = np.ones((bins, frames), dtype=np.float32)
    for _ in range(iterations):
        B = np.concatenate([B_D, B_H], axis=1)
        G = np.concatenate([G_D, G_H], axis=0)
        ratio = V / (B @ G + EPS)
        G = G * (B.T @ ratio) / (B.T @ ones + EPS)
        G_D, G_H = G[:drums], G[drums:]
        B = np.concatenate([B_D, B_H], axis=1)
        ratio = V / (B @ G + EPS)
        B_H = B_H * (ratio @ G_H.T) / (ones @ G_H.T + EPS)
        B_H = B_H / (np.linalg.norm(B_H, axis=0, keepdims=True) + EPS)
    return G_D


def pick_peaks(curve, delta, w1=W1, w2=W2, w3=W3, w4=W4, w5=W5):
    """Boeck's three-condition picker over a robustly normalised curve.

    Normalising by a high percentile rather than the maximum matters: with a
    maximum-normalised curve one loud fill raises the bar for a whole track and
    silently caps recall.
    """
    curve = np.asarray(curve, dtype=np.float32)
    if curve.size < 5:
        return []
    positive = curve[curve > 0]
    scale = float(np.percentile(positive, 95)) if positive.size else 1.0
    a = curve / (scale + EPS)
    n = len(a)
    cumulative = np.concatenate([[0.0], np.cumsum(a, dtype=np.float64)])
    picked, last = [], -(10 ** 9)
    for i in range(n):
        lo, hi = max(0, i - w1), min(n, i + w2 + 1)
        if a[i] < a[lo:hi].max():
            continue                                   # not a local maximum
        lo3, hi3 = max(0, i - w3), min(n, i + w4 + 1)
        mean = (cumulative[hi3] - cumulative[lo3]) / max(1, hi3 - lo3)
        if a[i] < mean + delta:
            continue                                   # not above local mean
        if i - last <= w5:
            continue                                   # too close to the last
        picked.append(i)
        last = i
    return picked


# Selected on the development half of the real-music corpus only.
DEFAULT_DELTA = {"BD": 0.40, "SD": 0.35, "CYM": 0.15}


def analyse(mono, deltas=None, sample_rate=SR):
    """Return onset times in seconds per drum lane for mono float PCM."""
    x = np.asarray(mono, dtype=np.float32)
    if x.ndim != 1:
        raise ValueError("mono float PCM is required")
    if x.size and not np.isfinite(x).all():
        raise ValueError("PCM contains non-finite samples")
    deltas = dict(DEFAULT_DELTA if deltas is None else deltas)
    if set(deltas) != set(LANES):
        raise ValueError("a threshold is required for every lane")
    empty = {lane: [] for lane in LANES}
    # Digital silence has no attributable attack, and the KL updates are not
    # defined on an all-zero spectrogram.
    if not x.size or not np.any(x):
        return empty
    lanes, B_D, geom = load_templates()
    if geom != (NFFT, HOP):
        raise ValueError("template STFT geometry does not match this backend")
    V = stft_magnitude(x)
    if V.shape[1] < 5:
        return empty
    G_D = pfnmf(V, B_D)
    fps = sample_rate / float(HOP)
    # The dictionary's third column is a closed-hat template, but the lane it
    # feeds is CYM: see the lane-scope note in the module docstring.
    column = {"BD": "BD", "SD": "SD", "CYM": "CHH"}
    return {lane: [i / fps for i in pick_peaks(G_D[lanes.index(column[lane])], deltas[lane])]
            for lane in LANES}
