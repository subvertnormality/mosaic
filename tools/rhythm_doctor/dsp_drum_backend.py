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

A BASS lane was carried through v1.3 and has been withdrawn. It never detected
bass independently: it reclassified the low-band onsets the BD lane had already
found, and on real captures the pitch test rejected none of them, so BASS was a
duplicate of BD wearing another name. No corpus with human-verified bass onsets
on real full-mix music exists to measure a replacement against (see CORPUS.md).
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


# --- phrase alignment -------------------------------------------------------
#
# A capture starts when the player hits Record, which is never the top of a
# bar. Until this existed the analysis returned origin_sample 0, so cell 0 was
# the moment of the keypress and every gate sat at an arbitrary offset from the
# beat. Three phases are recovered, in order, each conditioned on the last:
#
#   beat phase   -- where the beat grid sits inside the capture
#   bar phase    -- which of the four beats is "1"
#   phrase phase -- which of the four bars opens the phrase
#
# The first two are well determined by drum content. The third is not, and is
# reported with a confidence rather than asserted: see phrase_offset.

BEATS_PER_BAR = 4
PHRASE_BARS = 4
# Bar-phase margin at which the downbeat stops discounting the reported
# confidence. Four candidates scored as shares of their total start from a
# 0.25 share each, so a winner taking a tenth more than the runner-up is
# already a clear result; below that the vote is close and says so.
BAR_MARGIN_FULL = 0.10
CELLS_PER_BEAT = 4
WINDOW_CELLS = PHRASE_BARS * BEATS_PER_BAR * CELLS_PER_BEAT   # 64, == Bank.WINDOW_CELLS


def _accent(curve):
    """Positive deviation above the lane's median activation.

    Raw activation answers "is this lane busy here", which a steady hat pattern
    satisfies on every eighth and which therefore says nothing about where the
    bar starts. Accent answers "does this lane do something UNUSUAL here",
    which is what a crash on the downbeat or a kick against a sparse floor
    actually is. The median is the baseline rather than the mean because a few
    large accents would drag a mean up towards themselves and mask the very
    events being looked for.
    """
    curve = np.asarray(curve, dtype=np.float64)
    if not curve.size:
        return curve
    return np.maximum(curve - np.median(curve), 0.0)


def _combined_accent(accents):
    """All lanes' accents summed after each is scaled to its own peak.

    Used where the question is "did anything happen here", not "did this
    particular drum happen here".
    """
    total = None
    for curve in accents.values():
        scaled = curve / (curve.max() + EPS)
        total = scaled if total is None else total + scaled
    return total


def _pickup(combined, phase, beat, offset, size):
    """Activity in the three sixteenths immediately before each candidate downbeat.

    Drummers announce the bar line: a fill, a snare pickup, a kick run. That
    announcement sits in the sixteenths before beat 1 and nowhere else, which
    makes it the cue that separates beat 1 from beat 3 when the kick plays both
    and the snare answers on both backbeats. Beat-resolution scoring cannot see
    it at all, because it happens between the beats.
    """
    sixteenth = beat / CELLS_PER_BEAT
    total, count, bar_index = 0.0, 0, 0
    while True:
        downbeat_frame = phase + (offset + BEATS_PER_BAR * bar_index) * beat
        if downbeat_frame >= size:
            break
        for step in (1, 2, 3):
            frame = int(round(downbeat_frame - step * sixteenth))
            if 0 <= frame < size:
                total += combined[frame]
                count += 1
        bar_index += 1
    return total / count if count else 0.0


def _share(values):
    """Scale a set of candidate scores to fractions of their total."""
    total = float(sum(values))
    if total <= 0:
        return [0.0] * len(values)
    return [float(value) / total for value in values]


def _comb(curve, phase, spacing, first, stride, size):
    """Mean of `curve` sampled at first, first+stride, ... beats from `phase`.

    A mean rather than a sum so candidates that fit different numbers of beats
    into the capture stay comparable.
    """
    total, count, index = 0.0, 0, first
    while True:
        frame = int(round(phase + index * spacing))
        if frame >= size:
            break
        if frame >= 0:
            total += curve[frame]
            count += 1
        index += stride
    return total / count if count else 0.0


def beat_phase(envelope, fps, bpm):
    """Frame offset of the first beat: the comb phase collecting most energy.

    Searched at frame resolution, which at the shipped 512-sample hop is 11.6 ms
    -- finer than the onset envelope's own smearing, so a finer lattice would
    only fit noise.
    """
    env = np.asarray(envelope, dtype=np.float64)
    beat = 60.0 * fps / bpm
    if env.size < beat or not np.any(env > 0):
        return 0.0
    best, best_score = 0.0, -1.0
    for frame in range(max(1, int(round(beat)))):
        score = _comb(env, float(frame), beat, 0, 1, env.size)
        if score > best_score:
            best, best_score = float(frame), score
    return best


def downbeat_offset(curves, crash, fps, bpm, phase):
    """Which beat of four is "1", and how decided the vote was.

    Weights encode the two facts that hold across essentially all backbeat
    material: the kick marks the downbeat, and the snare marks 2 and 4. The
    crash contributes at half weight because it appears on some downbeats only.
    """
    beat = 60.0 * fps / bpm
    accents = {lane: _accent(curve) for lane, curve in curves.items()}
    combined = _combined_accent(accents)
    size = len(accents["BD"])
    offsets = range(BEATS_PER_BAR)
    kick = [_comb(accents["BD"], phase, beat, o, BEATS_PER_BAR, size) for o in offsets]
    back = [_comb(accents["SD"], phase, beat, o + 1, BEATS_PER_BAR, size)
            + _comb(accents["SD"], phase, beat, o + 3, BEATS_PER_BAR, size) for o in offsets]
    pickup = [_pickup(combined, phase, beat, o, size) for o in offsets]
    ring = [_comb(crash, phase, beat, o, BEATS_PER_BAR, size) for o in offsets]
    # Each lane votes on its own scale -- a kick activation is routinely two
    # orders of magnitude larger than a cymbal one -- so the votes are made
    # comparable before they are combined. Without this the kick decides alone,
    # and the kick cannot separate beat 1 from beat 3 in the commonest pattern
    # there is, where it plays both.
    #
    # The cymbal LANE deliberately does not vote. Its activation is highest
    # where a hat sounds UNMASKED by a kick or snare, which is the off-beat, so
    # scoring it at beat resolution votes confidently for the wrong answer. The
    # crash ring (crash_sustain) is a different measurement and does vote: it
    # is the only cue that survives when a pattern has no fill and the kick
    # plays 1 and 3, which is symmetric under a two-beat shift.
    kick_share, back_share = _share(kick), _share(back)
    pickup_share, ring_share = _share(pickup), _share(ring)
    scored = [kick_share[o] + back_share[o] + pickup_share[o] + ring_share[o] for o in offsets]
    best = max(offsets, key=lambda o: scored[o])
    ordered = sorted(scored, reverse=True)
    margin = 0.0 if ordered[0] <= 0 else (ordered[0] - ordered[1]) / ordered[0]
    return best, float(margin)


CRASH_BAND_HZ = 5000.0
CRASH_TAIL_SECONDS = 0.40


def crash_sustain(V, fps, sample_rate=SR):
    """How much high-band energy each frame LEAVES BEHIND it.

    A crash and a closed hat occupy the same band, so level cannot separate
    them; duration can. A crash rings for most of a second, a hat is gone in
    tens of milliseconds. This measures the mean high-band magnitude over the
    400 ms following each frame, so a hat scores near its own baseline and a
    crash scores far above it.

    Taken from the spectrogram rather than from the NMF lane on purpose. The
    lane's activation is suppressed wherever a kick or snare explains the same
    frame, which is exactly on the downbeats being looked for.
    """
    V = np.asarray(V, dtype=np.float64)
    if V.shape[1] == 0:
        return np.zeros(0)
    first = int(round(CRASH_BAND_HZ * NFFT / float(sample_rate)))
    if first >= V.shape[0]:
        return np.zeros(V.shape[1])
    band = V[first:].mean(axis=0)
    tail = max(1, int(round(CRASH_TAIL_SECONDS * fps)))
    padded = np.concatenate([band, np.zeros(tail)])
    window = np.convolve(padded, np.ones(tail) / tail, mode="full")[tail - 1:tail - 1 + band.size]
    return _accent(window)


def phrase_offset(crash, fps, bpm, phase, downbeat):
    """Which bar of four opens the phrase, and how much to believe it.

    Phrase position is normally recovered from repetition at a four-bar period.
    A Rhythm Doctor capture is a handful of bars, so there is often no second
    phrase to correlate against and the honest answer is "unknown". What
    survives on a short take is the crash a player lands on the top of the
    phrase, measured by its ring rather than its level (see crash_sustain).
    That cue is scored here, and the confidence is the margin between
    the best candidate and the runner-up, scaled down when too few phrases were
    observed for the margin to mean anything. It is NOT a probability; it is
    how much better the winner did than its nearest rival.
    """
    beat = 60.0 * fps / bpm
    bar = beat * BEATS_PER_BAR
    size = len(crash)
    bars_available = int(max(0.0, (size - phase - downbeat * beat)) // bar)
    if bars_available < PHRASE_BARS:
        return 0, 0.0
    origin = phase + downbeat * beat
    scores = [_comb(crash, origin, bar, candidate, PHRASE_BARS, size)
              for candidate in range(PHRASE_BARS)]
    best = max(range(PHRASE_BARS), key=lambda i: scores[i])
    ordered = sorted(scores, reverse=True)
    margin = 0.0 if ordered[0] <= 0 else (ordered[0] - ordered[1]) / ordered[0]
    # One phrase gives a margin with nothing to corroborate it; two or more let
    # the cue repeat. Below two observed phrases the margin is halved rather
    # than discarded, because a lone crash is still evidence.
    phrases = bars_available / float(PHRASE_BARS)
    scale = 1.0 if phrases >= 2.0 else 0.5
    return best, float(min(1.0, max(0.0, margin * scale)))


# --- tempo -----------------------------------------------------------------

BPM_MIN, BPM_MAX = 40.0, 240.0
DEFAULT_BPM = 120.0

# Tempo octave preference. Autocorrelation cannot tell a tempo from half or
# double it -- both are genuine periodicities of the same signal -- and for the
# commonest drum pattern there is, kick on 1 and 3, the two-beat period is the
# STRONGER one. A bare maximum therefore calls a 120 BPM rock groove 60 BPM,
# and the bars, the phrase alignment and every quantised gate inherit the
# error. The standard remedy is a log-normal preference over tempo; these are
# librosa's published defaults (start_bpm 120, std_bpm 1.0 octave) rather than
# values fitted to this project's material. The preference is gentle: a 60 BPM
# peak still wins if it is about 1.65x stronger than the 120 BPM one.
TEMPO_PRIOR_CENTRE = 120.0
TEMPO_PRIOR_OCTAVES = 1.0


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
    if window.max() <= 0.1:                       # no usable periodicity
        return DEFAULT_BPM, False
    lags = np.arange(lo, hi + 1, dtype=np.float64)
    prior = np.exp(-0.5 * (np.log2((60.0 * fps / lags) / TEMPO_PRIOR_CENTRE)
                           / TEMPO_PRIOR_OCTAVES) ** 2)
    # The prior reweights which periodicity is chosen; the 0.1 floor above is
    # still applied to the raw correlation, so preferring a tempo can never
    # manufacture a detection out of an unpulsed envelope.
    best = int(np.argmax(window * prior)) + lo
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


def confirmed_alignment(value):
    """A correction the player accepted, or None if it cannot be honoured.

    An alignment arrives only from a reanalysis the player asked for, so it
    outranks the automatic estimate. A malformed or out-of-range one is ignored
    rather than trusted: falling back to the estimate is wrong, but writing an
    unusable tempo into the bank is worse.
    """
    if not isinstance(value, dict):
        return None
    bpm, origin = value.get("bpm"), value.get("origin_sample", 0)
    if isinstance(bpm, bool) or not isinstance(bpm, (int, float)):
        return None
    bpm = float(bpm)
    if bpm != bpm or not (BPM_MIN <= bpm <= BPM_MAX):
        return None
    if isinstance(origin, bool) or not isinstance(origin, (int, float)):
        return None
    origin = int(round(float(origin)))
    if origin < 0:
        return None
    return {"bpm": bpm, "origin_sample": origin}


def analyse_request(wav_path, deltas=None, alignment=None):
    """Produce one worker-valid analysis result from a captured WAV."""
    mono, source_rate, _ = read_capture_wav(wav_path)
    deltas = dict(DEFAULT_DELTA if deltas is None else deltas)
    lanes, B_D, geom = load_templates()
    empty_gates = {lane: float(deltas[lane]) for lane in LANES}
    identity = {"backend_id": BACKEND_ID,
                "backend_sha256": _sha256_file(Path(__file__).resolve()),
                "template_sha256": _sha256_file(_TEMPLATES)}
    confirmed = confirmed_alignment(alignment)
    empty = {"bpm": DEFAULT_BPM, "tempo_detected": False, "origin_sample": 0,
             "phrase_start_sample": 0, "phrase_confidence": 0.0,
             "tempo_mode": "auto", "detector": identity,
             "lane_onset_gates": empty_gates, "candidates": []}
    if confirmed:
        empty.update({"bpm": confirmed["bpm"], "tempo_detected": True,
                      "origin_sample": confirmed["origin_sample"], "tempo_mode": "manual",
                      "phrase_start_sample": confirmed["origin_sample"],
                      "phrase_confidence": 1.0})
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

    def source_index(frame):
        """Frame -> sample index in the ORIGINAL capture's coordinates."""
        return int(round(frame * HOP * source_rate / float(SR)))

    for lane in LANES:
        row = G_D[lanes.index(column[lane])]
        envelope += row / (row.max() + EPS)
        frames = pick_peaks(row, deltas[lane])
        for frame, velocity in zip(frames, velocities(row, frames, fps)):
            candidates.append({"lane": lane, "sample_index": source_index(frame),
                               "velocity": int(velocity),
                               "confidence": float(min(1.0, row[frame] / (row.max() + EPS)))})
    candidates.sort(key=lambda c: (c["sample_index"], LANES.index(c["lane"])))
    bpm, detected = estimate_bpm(envelope, fps)
    origin, mode = 0, "auto"
    phrase_start, phrase_confidence, beats = 0, 0.0, []
    if detected:
        phrase_start, phrase_confidence, origin, beats = _align_to_phrase(
            {lane: G_D[lanes.index(column[lane])] for lane in LANES},
            crash_sustain(V, fps), envelope, fps, bpm, source_rate, mono.size, source_index)
    if confirmed:
        # The player corrected this capture and asked for it to be reanalysed;
        # their tempo and origin stand, and onset positions are absolute, so
        # they do not move. A corrected origin IS the phrase start they chose:
        # the whole point of the correction is to say where the phrase begins.
        bpm, detected, origin, mode = confirmed["bpm"], True, confirmed["origin_sample"], "manual"
        phrase_start, phrase_confidence = origin, 1.0
        # A corrected origin is a beat by definition, so it joins the grid the
        # player steps through rather than sitting between two of its entries.
        beats = sorted(set(beats) | {int(origin)})
    return {"bpm": float(bpm), "tempo_detected": bool(detected), "origin_sample": int(origin),
            "phrase_start_sample": int(phrase_start),
            "phrase_confidence": float(phrase_confidence),
            "beat_positions": [int(b) for b in beats],
            "tempo_mode": mode, "detector": identity, "lane_onset_gates": empty_gates,
            "candidates": candidates}


def _align_to_phrase(curves, crash, envelope, fps, bpm, source_rate, capture_samples, source_index):
    """Return (phrase_start_sample, confidence, origin_sample, beat_positions).

    All in the ORIGINAL capture's sample coordinates.

    The origin is rewound from the phrase start in whole cells, as far as the
    capture allows, for two reasons. It keeps the grid in phase with the music,
    so a gate detected on beat 1 quantises to a cell boundary rather than
    straddling one. And it keeps the audio recorded before the phrase began
    inside the timeline, so the player can scroll back behind the phrase start
    instead of losing it.
    """
    phase = beat_phase(envelope, fps, bpm)
    downbeat, bar_margin = downbeat_offset(curves, crash, fps, bpm, phase)
    offset, phrase_margin = phrase_offset(crash, fps, bpm, phase, downbeat)
    # A phrase position is only as trustworthy as the bar phase it is measured
    # against: naming the right bar of four is worthless if the downbeat inside
    # it is two beats out. Reporting the phrase margin alone told the player to
    # trust exactly that.
    confidence = phrase_margin * min(1.0, bar_margin / BAR_MARGIN_FULL)
    beat = 60.0 * fps / bpm
    bar = beat * BEATS_PER_BAR
    samples_per_cell = source_rate * 15.0 / bpm
    window = WINDOW_CELLS * samples_per_cell
    # Walk phrase candidates forward and take the first that still has a whole
    # window behind it. Jumping to a phrase start with two bars of capture left
    # would show a view clamped against the end, which reads as a detector
    # error rather than as the end of the recording.
    start_frame = phase + downbeat * beat + offset * bar
    phrase_start = None
    while True:
        candidate = source_index(start_frame)
        if candidate + window > capture_samples:
            break
        phrase_start = candidate
        if phrase_start >= 0:
            break
        start_frame += bar * PHRASE_BARS
    if phrase_start is None or phrase_start < 0:
        return 0, 0.0, 0, []
    cells_before = int(phrase_start // samples_per_cell)
    origin = int(round(phrase_start - cells_before * samples_per_cell))
    # The whole beat grid, anchored on the phrase start so that stepping away
    # from it and back is exact. Beats before the phrase start are included:
    # the player may decide the phrase begins earlier than the detector did,
    # and they cannot say so if those beats are missing from the list.
    samples_per_beat = source_rate * 60.0 / bpm
    first = phrase_start - samples_per_beat * int(phrase_start // samples_per_beat)
    beats, position = [], first
    while position < capture_samples:
        beats.append(int(round(position)))
        position += samples_per_beat
    return phrase_start, confidence, max(0, origin), beats


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
        args.result.write_text(
            json.dumps(analyse_request(wav, alignment=request.get("alignment")),
                       separators=(",", ":")), encoding="utf-8")
        return 0
    except Exception:
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
