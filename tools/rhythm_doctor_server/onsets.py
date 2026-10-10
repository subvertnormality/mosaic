"""Onsets and velocity from a separated stem.

Once a stem has been isolated the hard part is over: what is left is finding
where it is struck and how hard. Spectral flux with an adaptive threshold does
that, and needs no model and no training.

Velocity is normalised PER STEM, against that stem's own loudest attack in the
capture. A guitar stem's absolute level says nothing about how hard the guitar
was played relative to the kick, and a shared scale would make every quiet stem
produce uniformly weak gates.
"""
from __future__ import annotations

import numpy as np

NFFT, HOP = 2048, 512

# Boeck, Krebs & Schedl (ISMIR 2012) offline peak-picking windows, in frames,
# as used by the local backend so the two agree on what an onset is.
W1, W2, W3, W4, W5 = 3, 3, 8, 1, 2


def spectral_flux(mono: np.ndarray, sample_rate: int) -> np.ndarray:
    """Half-wave rectified difference of successive log-magnitude spectra.

    The transform is CENTRED: the signal is padded by half a window so that
    frame i is centred on sample i * HOP. Without that, frame i covers
    [i*HOP, i*HOP+NFFT) and an onset it detects is reported up to a whole
    window early -- far enough that the velocity window, looking 25ms either
    side of the reported position, misses the attack completely and every
    stem comes back at velocity 1.
    """
    x = np.asarray(mono, dtype=np.float32)
    if x.size < NFFT:
        return np.zeros(0, dtype=np.float64)
    x = np.pad(x, NFFT // 2, mode="constant")
    window = np.hanning(NFFT).astype(np.float32)
    frames = 1 + (x.size - NFFT) // HOP
    spectra = np.empty((frames, NFFT // 2 + 1), dtype=np.float64)
    for index in range(frames):
        start = index * HOP
        spectra[index] = np.abs(np.fft.rfft(x[start:start + NFFT] * window))
    spectra = np.log1p(spectra)
    flux = np.diff(spectra, axis=0)
    np.maximum(flux, 0.0, out=flux)
    return np.concatenate([[0.0], flux.sum(axis=1)])


def pick_peaks(curve: np.ndarray, delta: float) -> list[int]:
    """Boeck's three conditions over a curve normalised to its own maximum."""
    curve = np.asarray(curve, dtype=np.float64)
    if curve.size < 5:
        return []
    top = curve.max()
    if top <= 0:
        return []
    curve = curve / top
    picked, last = [], -(10 ** 9)
    for index in range(curve.size):
        lo = max(0, index - W1)
        if curve[index] < curve[lo:index + W2 + 1].max():
            continue
        mean_lo = max(0, index - W3)
        if curve[index] < curve[mean_lo:index + W4 + 1].mean() + delta:
            continue
        if index - last <= W5:
            continue
        picked.append(index)
        last = index
    return picked


def velocities(mono: np.ndarray, frames: list[int], sample_rate: int,
               window_seconds: float = 0.025) -> list[int]:
    """Peak absolute amplitude around each onset, scaled 1..127 per stem.

    Scaled against the loudest attack in THIS stem, so the lane spans the full
    velocity range whatever the stem's absolute level. A stem whose loudest
    attack is silence yields no velocities, because there are no onsets in it.
    """
    x = np.abs(np.asarray(mono, dtype=np.float32))
    span = max(1, int(window_seconds * sample_rate))
    peaks = []
    for frame in frames:
        start = frame * HOP
        peaks.append(float(x[max(0, start - span):start + span].max()) if x.size else 0.0)
    if not peaks:
        return []
    top = max(peaks)
    if top <= 0:
        return [1] * len(peaks)
    return [int(max(1, min(127, round(1 + 126 * (peak / top))))) for peak in peaks]


def refine(mono: np.ndarray, sample_index: int, back: int = HOP // 2,
           forward: int = 2 * HOP) -> int:
    """Snap a frame-resolution onset to the energy rise it was detected from.

    A frame's window sees an attack before the frame's centre reaches it, so a
    flux peak lands about one hop early and every gate inherits that bias. The
    beat grid comes from a separate model, so a systematic offset between the
    two shows up as gates sitting consistently ahead of the beat.

    The search runs over a block ENVELOPE, not the waveform. An 80Hz kick's
    rectified waveform rises and falls 160 times a second, so differencing it
    directly finds the loudest part of a carrier cycle rather than the attack,
    and moves the onset somewhere arbitrary within a period.

    It is also asymmetric. The bias only ever runs early, and a symmetric
    window of one hop stops just short of the attack it is looking for -- which
    left every first onset exactly one hop adrift. Searching further forward
    than back follows the direction the error is known to take.
    """
    x = np.abs(np.asarray(mono, dtype=np.float32))
    block = 64
    lo = max(0, sample_index - back)
    hi = min(x.size, sample_index + forward + 1)
    if hi - lo < 3 * block:
        return sample_index
    usable = ((hi - lo) // block) * block
    envelope = x[lo:lo + usable].reshape(-1, block).max(axis=1)
    if envelope.size < 3:
        return sample_index
    rise = np.diff(envelope)
    if not rise.size or rise.max() <= 0:
        return sample_index
    return int(lo + (int(np.argmax(rise)) + 1) * block)


def analyse_stem(mono: np.ndarray, sample_rate: int, delta: float) -> list[dict]:
    """Onset candidates for one stem, in that stem's own sample coordinates."""
    flux = spectral_flux(mono, sample_rate)
    if flux.size == 0:
        return []
    frames = pick_peaks(flux, delta)
    if not frames:
        return []
    loudness = velocities(mono, frames, sample_rate)
    top = flux.max() or 1.0
    return [{"sample_index": refine(mono, int(frame * HOP)),
             "velocity": int(velocity),
             "confidence": float(min(1.0, flux[frame] / top))}
            for frame, velocity in zip(frames, loudness)]
