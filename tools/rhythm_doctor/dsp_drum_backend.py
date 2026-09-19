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
LANES = ("BD", "SD", "CYM", "BASS")
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
DEFAULT_DELTA = {"BD": 0.40, "SD": 0.35, "CYM": 0.15, "BASS": 0.40}

# BASS is not detected independently. It reclassifies low-band onsets that hold
# a stable pitch after the attack, which is the one drum/instrument distinction
# that is physically reliable: a membrane vibrates in inharmonic Bessel ratios
# and decays fast, a string in integer ratios and sustains. The lanes are NOT
# exclusive, because a kick and a bass note routinely land together.
PITCH_CONFIDENCE_CUT = 0.15
PITCH_WINDOW_SECONDS = 0.080
BASS_F0_MIN, BASS_F0_MAX = 35.0, 300.0


def pitch_confidence(segment, sample_rate, f0_min=BASS_F0_MIN, f0_max=BASS_F0_MAX):
    """Normalised autocorrelation peak in the bass register.

    High for a sustained string tone, low for an inharmonic membrane strike.
    """
    seg = np.asarray(segment, dtype=np.float64)
    if seg.size < 64 or not np.any(seg):
        return 0.0
    seg = seg - seg.mean()
    ac = np.correlate(seg, seg, mode="full")[seg.size - 1:]
    if ac.size < 4 or ac[0] <= 0:
        return 0.0
    ac = ac / ac[0]
    lo, hi = int(sample_rate / f0_max), min(len(ac) - 1, int(sample_rate / f0_min))
    if hi <= lo:
        return 0.0
    return float(np.max(ac[lo:hi + 1]))


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
    out = {lane: [i / fps for i in pick_peaks(G_D[lanes.index(column[lane])], deltas[lane])]
           for lane in ("BD", "SD", "CYM")}
    out["BASS"] = _bass_from_low_onsets(x, out["BD"], sample_rate)
    return out


def _bass_from_low_onsets(mono, low_onsets, sample_rate):
    """Low-band onsets that hold a stable pitch are also BASS candidates."""
    span = int(PITCH_WINDOW_SECONDS * sample_rate)
    bass = []
    for t in low_onsets:
        start = int(t * sample_rate)
        if pitch_confidence(mono[start:start + span], sample_rate) >= PITCH_CONFIDENCE_CUT:
            bass.append(t)
    return bass


# --- capture WAV ------------------------------------------------------------

def read_capture_wav(path):
    """Read a capture as (mono float32, sample_rate, frames).

    The native recorder publishes WAVE_FORMAT_IEEE_FLOAT (tag 3), 32-bit,
    stereo. Python's `wave` module rejects tag 3 outright, so parsing the RIFF
    chunks directly is what lets a real capture be analysed at all. Integer PCM
    is accepted too, because fixtures and imported material use it.
    """
    raw = Path(path).read_bytes()
    if len(raw) < 12 or raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
        raise ValueError("not a RIFF/WAVE file")
    import struct
    pos, fmt, data = 12, None, None
    while pos + 8 <= len(raw):
        cid, size = raw[pos:pos+4], struct.unpack_from("<I", raw, pos+4)[0]
        body = raw[pos+8:pos+8+size]
        if cid == b"fmt " and len(body) >= 16:
            tag, channels, rate, _, _, bits = struct.unpack_from("<HHIIHH", body, 0)
            fmt = (tag, channels, rate, bits)
        elif cid == b"data":
            data = body
        pos += 8 + size + (size & 1)
    if fmt is None or data is None:
        raise ValueError("missing fmt or data chunk")
    tag, channels, rate, bits = fmt
    if channels not in (1, 2) or rate <= 0:
        raise ValueError("unsupported channel count or sample rate")
    if tag == 3 and bits == 32:
        samples = np.frombuffer(data, dtype="<f4").astype(np.float32)
    elif tag == 1 and bits == 16:
        samples = np.frombuffer(data, dtype="<i2").astype(np.float32) / 32768.0
    elif tag == 1 and bits == 32:
        samples = np.frombuffer(data, dtype="<i4").astype(np.float32) / 2147483648.0
    else:
        raise ValueError("unsupported WAV encoding: tag %d, %d bits" % (tag, bits))
    usable = (samples.size // channels) * channels
    samples = samples[:usable]
    if not np.isfinite(samples).all():
        raise ValueError("capture contains non-finite samples")
    mono = samples.reshape(-1, channels).mean(axis=1) if channels == 2 else samples
    return mono.astype(np.float32), int(rate), int(mono.size)


# --- tempo -----------------------------------------------------------------

BPM_MIN, BPM_MAX = 40.0, 240.0
DEFAULT_BPM = 120.0


def estimate_bpm(onset_envelope, fps, bpm_min=BPM_MIN, bpm_max=BPM_MAX):
    """Autocorrelation tempo estimate over the summed onset envelope.

    Returns (bpm, detected). When no periodicity is found the caller still
    needs a value inside the bank's 40..240 contract, so a placeholder is
    returned with detected False rather than presenting a guess as measured.
    The player can correct it through the existing alignment controls.
    """
    env = np.asarray(onset_envelope, dtype=np.float64)
    if env.size < 8 or not np.any(env > 0):
        return DEFAULT_BPM, False
    env = env - env.mean()
    ac = np.correlate(env, env, mode="full")[len(env) - 1:]
    if ac.size < 4 or ac[0] <= 0:
        return DEFAULT_BPM, False
    ac = ac / ac[0]
    lo = max(1, int(round(60.0 * fps / bpm_max)))
    hi = min(len(ac) - 1, int(round(60.0 * fps / bpm_min)))
    if hi <= lo:
        return DEFAULT_BPM, False
    window = ac[lo:hi + 1]
    best = int(np.argmax(window)) + lo
    if window.max() <= 0.1:                       # no usable periodicity
        return DEFAULT_BPM, False
    bpm = 60.0 * fps / best
    while bpm < bpm_min: bpm *= 2.0
    while bpm > bpm_max: bpm /= 2.0
    if not (bpm_min <= bpm <= bpm_max):
        return DEFAULT_BPM, False
    return float(bpm), True


# --- velocity --------------------------------------------------------------

def velocities(activation, frames, fps, window_seconds=0.025):
    """Peak activation in a window around each onset, scaled to MIDI 1..127.

    Normalised within the capture, so a quiet recording is not flattened to
    nothing and a loud one is not clipped to uniform 127.
    """
    if not frames:
        return []
    half = max(1, int(round(window_seconds * fps)))
    peaks = []
    for i in frames:
        lo, hi = max(0, i - half), min(len(activation), i + half + 1)
        peaks.append(float(activation[lo:hi].max()) if hi > lo else 0.0)
    top = max(peaks)
    if top <= 0:
        return [64] * len(frames)
    return [int(min(127, max(1, round(1 + 126 * (p / top))))) for p in peaks]


# --- worker backend --------------------------------------------------------

BACKEND_ID = "nmf-pfnmf-drums-v1"


def _sha256_file(path):
    import hashlib
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def analyse_request(wav_path, deltas=None):
    """Produce one worker-valid analysis result from a captured WAV."""
    mono, source_rate, _ = read_capture_wav(wav_path)
    deltas = dict(DEFAULT_DELTA if deltas is None else deltas)
    lanes, B_D, geom = load_templates()
    empty_gates = {lane: float(deltas[lane]) for lane in LANES}
    identity = {"backend_id": BACKEND_ID,
                "backend_sha256": _sha256_file(Path(__file__).resolve()),
                "template_sha256": _sha256_file(_TEMPLATES)}
    empty = {"bpm": DEFAULT_BPM, "tempo_detected": False, "origin_sample": 0,
             "detector": identity, "lane_onset_gates": empty_gates, "candidates": []}
    if not mono.size or not np.any(mono):
        return empty
    analysis = mono if source_rate == SR else _resample(mono, source_rate, SR)
    V = stft_magnitude(analysis)
    if V.shape[1] < 5:
        return empty
    G_D = pfnmf(V, B_D)
    # Frames are produced from the RESAMPLED signal, so frame timing is in
    # analysis-rate terms. Using the source rate here would read a 48 kHz
    # capture about 8.8% fast and corrupt both tempo and quantisation.
    fps = SR / float(HOP)
    column = {"BD": "BD", "SD": "SD", "CYM": "CHH"}
    candidates, envelope = [], np.zeros(G_D.shape[1], dtype=np.float64)
    low_frames, low_row = [], None

    def source_index(frame):
        """Frame -> sample index in the ORIGINAL capture's coordinates."""
        return int(round(frame * HOP * source_rate / float(SR)))

    for lane in ("BD", "SD", "CYM"):
        row = G_D[lanes.index(column[lane])]
        envelope += row / (row.max() + EPS)
        frames = pick_peaks(row, deltas[lane])
        if lane == "BD":
            low_frames, low_row = list(frames), row
        for frame, velocity in zip(frames, velocities(row, frames, fps)):
            candidates.append({"lane": lane, "sample_index": source_index(frame),
                               "velocity": int(velocity),
                               "confidence": float(min(1.0, row[frame] / (row.max() + EPS)))})
    span = int(PITCH_WINDOW_SECONDS * source_rate)
    bass_frames = [f for f in low_frames
                   if pitch_confidence(mono[source_index(f):source_index(f) + span],
                                       source_rate) >= PITCH_CONFIDENCE_CUT]
    if low_row is not None:
        for frame, velocity in zip(bass_frames, velocities(low_row, bass_frames, fps)):
            candidates.append({"lane": "BASS", "sample_index": source_index(frame),
                               "velocity": int(velocity),
                               "confidence": float(min(1.0, low_row[frame] / (low_row.max() + EPS)))})
    candidates.sort(key=lambda c: (c["sample_index"], LANES.index(c["lane"])))
    bpm, detected = estimate_bpm(envelope, fps)
    return {"bpm": float(bpm), "tempo_detected": bool(detected), "origin_sample": 0,
            "detector": identity, "lane_onset_gates": empty_gates, "candidates": candidates}


def _mono_float(pcm):
    width, channels = pcm.sample_width, pcm.channels
    if width != 2:
        raise ValueError("only 16-bit PCM is supported by this backend")
    x = np.frombuffer(pcm.data, dtype="<i2").astype(np.float32) / 32768.0
    return x.reshape(-1, channels).mean(axis=1) if channels == 2 else x


def _resample(x, src, dst):
    if src == dst:
        return x
    index = np.linspace(0, len(x) - 1, int(round(len(x) * dst / float(src))))
    return np.interp(index, np.arange(len(x)), x).astype(np.float32)


def main(argv=None):
    import argparse, json
    parser = argparse.ArgumentParser(description="classical-DSP drum backend")
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        request = json.loads(args.request.read_text(encoding="utf-8"))
        wav = request.get("wav_path")
        if not isinstance(wav, str) or not wav:
            raise ValueError("wav_path is required")
        args.result.write_text(json.dumps(analyse_request(wav), separators=(",", ":")),
                               encoding="utf-8")
        return 0
    except Exception:
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
