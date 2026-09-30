"""Concrete local-runtime adapter for pinned UMXHQ BASS and Basic Pitch.

This module is intentionally a thin, dependency-injected runtime boundary.  A
deployment provides already-installed Open-Unmix and ONNX Runtime session loaders and
two local, SHA-pinned artifacts.  It never downloads weights, trains a model,
or substitutes another separator/onset model.  The pure PCM conversion and
decoder below make the hand-off contract reviewable without importing Torch or
TensorFlow Lite in the norns process.
"""
from __future__ import print_function

import math
import ast
import hashlib
import json
from pathlib import Path

from pretrained_bass_backend import (BASS_HIGH_MIDI, BASS_LOW_MIDI, PCM,
                                     PinnedArtifact, PipelineError,
                                     attack_velocity, basic_pitch_frame_time)


UMX_SAMPLE_RATE = 44100
BASIC_PITCH_SAMPLE_RATE = 22050
BASIC_PITCH_MIDI_OFFSET = 21
MAX_CANDIDATES = 22500


class RuntimeError(PipelineError):
    """A pinned local inference runtime cannot make a complete BASS result."""


class FloatPCM(object):
    """Finite interleaved float PCM passed to an injected inference session."""

    def __init__(self, samples, sample_rate, channels):
        if not isinstance(sample_rate, int) or sample_rate <= 0 or channels not in (1, 2):
            raise ValueError("invalid float PCM layout")
        if not isinstance(samples, (tuple, list)) or len(samples) % channels:
            raise ValueError("invalid float PCM data")
        values = tuple(float(value) for value in samples)
        # Polyphase filtering and inverse STFT can ring just beyond unit gain;
        # preserve that waveform rather than clipping it before either model.
        if any(not math.isfinite(value) for value in values):
            raise ValueError("float PCM must be finite")
        self.samples, self.sample_rate, self.channels = values, sample_rate, channels
        self.frames = len(values) // channels

    def channel(self, index):
        if type(index) is not int or not 0 <= index < self.channels:
            raise ValueError("channel index out of range")
        return tuple(self.samples[index::self.channels])


def _integer_sample(data, width, offset):
    raw = data[offset:offset + width]
    if len(raw) != width:
        raise RuntimeError("BASS_PCM_INVALID")
    if width == 1:
        return (raw[0] - 128) / 128.0
    value = int.from_bytes(raw, byteorder="little", signed=True)
    return value / float(1 << (8 * width - 1))


def decode_pcm(pcm):
    """Decode norns WAV PCM exactly, preserving channel phase and amplitude."""
    if not isinstance(pcm, PCM):
        raise RuntimeError("BASS_PCM_INVALID")
    stride = pcm.channels * pcm.sample_width
    if len(pcm.data) != pcm.frames * stride:
        raise RuntimeError("BASS_PCM_INVALID")
    if pcm.sample_width in (1, 2, 4):
        try:
            import numpy as np
            if pcm.sample_width == 1:
                values = (np.frombuffer(pcm.data, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
            else:
                values = np.frombuffer(pcm.data, dtype="<i%d" % pcm.sample_width).astype(np.float32)
                values /= float(1 << (8 * pcm.sample_width - 1))
            return FloatPCM(values.tolist(), pcm.sample_rate, pcm.channels)
        except ImportError:
            pass
    values = []
    for frame in range(pcm.frames):
        offset = frame * stride
        for channel in range(pcm.channels):
            values.append(_integer_sample(pcm.data, pcm.sample_width,
                                          offset + channel * pcm.sample_width))
    return FloatPCM(values, pcm.sample_rate, pcm.channels)


def to_stereo_44100(pcm):
    """Duplicate mono or preserve stereo, then use SciPy's polyphase resampler."""
    source = decode_pcm(pcm) if isinstance(pcm, PCM) else pcm
    if not isinstance(source, FloatPCM):
        raise RuntimeError("BASS_PCM_INVALID")
    frames = []
    for index in range(source.frames):
        left = source.samples[index * source.channels]
        right = left if source.channels == 1 else source.samples[index * 2 + 1]
        frames.append((left, right))
    if not frames:
        return FloatPCM((), UMX_SAMPLE_RATE, 2)
    try:
        import numpy as np
        from scipy.signal import resample_poly
        values = np.asarray(frames, dtype=np.float32).T
        if source.sample_rate != UMX_SAMPLE_RATE:
            divisor = math.gcd(UMX_SAMPLE_RATE, source.sample_rate)
            values = resample_poly(values, UMX_SAMPLE_RATE // divisor,
                                   source.sample_rate // divisor, axis=1).astype(np.float32)
    except ImportError as error:
        raise RuntimeError("BASS_RESAMPLER_UNAVAILABLE") from error
    return FloatPCM(tuple(values.T.reshape(-1).tolist()), UMX_SAMPLE_RATE, 2)


def basic_pitch_mono(separated):
    """Match Basic Pitch's actual mono frontend after UMXHQ has separated stereo.

    The UMXHQ output is preserved as stereo until this point.  Basic Pitch's
    published frontend averages the separated channels, then resamples through
    ``scipy.signal.resample_poly``; it never receives mixed-source stereo.
    """
    if not isinstance(separated, FloatPCM) or separated.channels != 2 or separated.sample_rate != UMX_SAMPLE_RATE:
        raise RuntimeError("BASS_SEPARATOR_INVALID")
    try:
        import numpy as np
        from scipy.signal import resample_poly
        stereo = np.asarray(separated.samples, dtype=np.float32).reshape(-1, 2)
        mono = np.mean(stereo, axis=1)
        return resample_poly(mono, 1, 2).astype(np.float32)
    except ImportError as error:
        raise RuntimeError("BASS_RESAMPLER_UNAVAILABLE") from error


def _prediction(value, source_rate, origin_sample):
    if not isinstance(value, dict):
        raise RuntimeError("BASS_ONSET_INVALID")
    pitch = value.get("midi_pitch")
    if type(pitch) is not int or not 21 <= pitch <= 108:
        raise RuntimeError("BASS_PITCH_INVALID")
    if not BASS_LOW_MIDI <= pitch <= BASS_HIGH_MIDI:
        return None
    frame = value.get("frame")
    time_seconds = basic_pitch_frame_time(frame)
    confidence = value.get("onset_confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
        raise RuntimeError("BASS_CONFIDENCE_INVALID")
    return {"lane": "BASS", "sample_index": origin_sample + int(math.floor(time_seconds * source_rate + .5)),
            "velocity": attack_velocity(value.get("attack_strength")), "confidence": float(confidence),
            "_frame": frame}


def merge_channel_onsets(predictions, source_rate, origin_sample):
    """Filter BASS range and merge two channel onsets within one model frame."""
    if not isinstance(predictions, (tuple, list)) or len(predictions) != 2:
        raise RuntimeError("BASS_ONSET_INVALID")
    values = []
    for channel in predictions:
        if not isinstance(channel, (tuple, list)):
            raise RuntimeError("BASS_ONSET_INVALID")
        for item in channel:
            candidate = _prediction(item, source_rate, origin_sample)
            if candidate is not None:
                values.append(candidate)
    values.sort(key=lambda value: (value["_frame"], -value["confidence"], -value["velocity"]))
    merged = []
    for candidate in values:
        if merged and candidate["_frame"] - merged[-1]["_frame"] <= 1:
            continue
        merged.append(candidate)
    if len(merged) > MAX_CANDIDATES:
        raise RuntimeError("BASS_CANDIDATE_LIMIT")
    for candidate in merged:
        del candidate["_frame"]
    return merged


class TorchUMXHQSession(object):
    """The pilot's centered-Hann STFT, magnitude mask, mixture phase and iSTFT."""

    def __init__(self, model):
        self.model = model

    def separate(self, pcm):
        if not isinstance(pcm, FloatPCM) or pcm.sample_rate != UMX_SAMPLE_RATE or pcm.channels != 2:
            raise RuntimeError("BASS_SEPARATOR_INPUT_INVALID")
        try:
            import torch
            waveform = torch.tensor(pcm.samples, dtype=torch.float32).reshape(-1, 2).transpose(0, 1).unsqueeze(0)
            window = torch.hann_window(4096)
            complex_mix = torch.stft(waveform.reshape(-1, waveform.shape[-1]), n_fft=4096,
                                     hop_length=1024, window=window, center=True,
                                     normalized=False, onesided=True, return_complex=False)
            complex_mix = complex_mix.reshape(1, 2, *complex_mix.shape[-3:])
            mix_magnitude = torch.linalg.vector_norm(complex_mix, dim=-1)
            with torch.no_grad():
                bass_magnitude = self.model(mix_magnitude)
            estimated = complex_mix * (bass_magnitude.unsqueeze(-1) / (mix_magnitude.unsqueeze(-1) + 1e-10))
            waveform = torch.istft(estimated.reshape(-1, estimated.shape[-3], estimated.shape[-2], estimated.shape[-1]),
                                   n_fft=4096, hop_length=1024, window=window, center=True,
                                   normalized=False, onesided=True, length=pcm.frames)
            data = waveform.reshape(1, 2, -1).squeeze(0).transpose(0, 1).reshape(-1).cpu().numpy().tolist()
            return FloatPCM(data, UMX_SAMPLE_RATE, 2)
        except RuntimeError:
            raise
        except Exception as error:
            raise RuntimeError("BASS_SEPARATOR_FAILED") from error


def load_open_unmix_pilot(path):
    """Load the exact local UMXHQ state dict using the pilot's OpenUnmix class."""
    try:
        import torch
        import torch.nn as nn
        import torch.nn.functional as functional
        source = Path(path).parent / "model.py"
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        core = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "OpenUnmix")
        namespace = {"torch": torch, "nn": nn, "F": functional, "Tensor": torch.Tensor,
                     "LSTM": nn.LSTM, "BatchNorm1d": nn.BatchNorm1d, "Linear": nn.Linear,
                     "Parameter": nn.Parameter}
        exec(compile(ast.Module(body=[core], type_ignores=[]), str(source), "exec"), namespace)
        state = torch.load(str(path), map_location="cpu")
        core_class = namespace["OpenUnmix"]
        bins, max_bin = int(state["output_mean"].shape[0]), int(state["input_mean"].shape[0])
        channels = int(state["fc1.weight"].shape[1] // max_bin)
        model = core_class(nb_bins=bins, nb_channels=channels,
                           hidden_size=int(state["fc1.weight"].shape[0]), max_bin=max_bin)
        model.load_state_dict(state, strict=False)
        model.freeze()
        return TorchUMXHQSession(model)
    except RuntimeError:
        raise
    except Exception as error:
        raise RuntimeError("BASS_UMXHQ_LOAD_FAILED") from error


class BasicPitchOnnxSession(object):
    """Exact overlapping ONNX windows and fixed peak decoder from the pilot."""

    def __init__(self, session, threshold=.2, gap_frames=8):
        if not 0 <= threshold <= 1 or type(gap_frames) is not int or gap_frames < 1:
            raise ValueError("fixed Basic Pitch decoder settings are required")
        self.session, self.threshold, self.gap_frames = session, float(threshold), gap_frames

    def predict_onsets(self, mono):
        try:
            import numpy as np
        except ImportError as error:
            raise RuntimeError("BASS_ONNX_RUNTIME_UNAVAILABLE") from error
        value = np.asarray(mono, dtype=np.float32)
        if value.ndim != 1 or not np.isfinite(value).all():
            raise RuntimeError("BASS_ONSET_INPUT_INVALID")
        hop, overlap = 256, 30
        window, window_hop = BASIC_PITCH_SAMPLE_RATE * 2 - hop, BASIC_PITCH_SAMPLE_RATE * 2 - hop - overlap * hop
        padded = np.concatenate((np.zeros(overlap * hop // 2, dtype=np.float32), value))
        outputs = []
        for index in range(0, len(padded), window_hop):
            chunk = padded[index:index + window]
            if len(chunk) < window:
                chunk = np.pad(chunk, (0, window - len(chunk)))
            try:
                raw = self.session.run(["StatefulPartitionedCall:1", "StatefulPartitionedCall:2"],
                                       {"serving_default_input_2:0": chunk[None, :, None]})
            except Exception as error:
                raise RuntimeError("BASS_ONNX_INFERENCE_FAILED") from error
            if not isinstance(raw, (list, tuple)) or len(raw) != 2:
                raise RuntimeError("BASS_ONNX_OUTPUT_INVALID")
            outputs.append(np.asarray(raw[1], dtype=np.float32))
        onset = np.concatenate(outputs)[:, overlap // 2:-overlap // 2, :].reshape(-1, 88)
        onset = onset[:int(len(value) * (BASIC_PITCH_SAMPLE_RATE // hop) / BASIC_PITCH_SAMPLE_RATE)]
        if onset.size and (not np.isfinite(onset).all() or onset.shape[1] != 88):
            raise RuntimeError("BASS_ONNX_OUTPUT_INVALID")
        # Basic Pitch's 88 output columns are MIDI 21..108, never raw MIDI
        # numbers.  Keep this offset explicit so the BASS reduction cannot
        # silently shift seven semitones upward.
        first = BASS_LOW_MIDI - BASIC_PITCH_MIDI_OFFSET
        last = BASS_HIGH_MIDI - BASIC_PITCH_MIDI_OFFSET + 1
        curve = onset[:, first:last].max(axis=1) if len(onset) else np.asarray(())
        candidates = [index for index in range(1, len(curve) - 1)
                      if curve[index] >= self.threshold and curve[index] >= curve[index - 1] and curve[index] > curve[index + 1]]
        selected = []
        for index in sorted(candidates, key=lambda item: curve[item], reverse=True):
            if all(abs(index - other) >= self.gap_frames for other in selected):
                selected.append(index)
        return [{"frame": int(index), "midi_pitch": int(BASIC_PITCH_MIDI_OFFSET + first + onset[index, first:last].argmax()),
                 "onset_confidence": float(curve[index]), "attack_strength": float(curve[index])}
                for index in sorted(selected)]


def load_basic_pitch_onnx(path, threshold=.2):
    try:
        import onnxruntime
        return BasicPitchOnnxSession(onnxruntime.InferenceSession(str(path), providers=["CPUExecutionProvider"]),
                                     threshold=threshold)
    except Exception as error:
        raise RuntimeError("BASS_ONNX_LOAD_FAILED") from error


class PinnedBassRuntime(object):
    """Factory shape for one explicitly provisioned UMXHQ + Basic Pitch pair.

    ``open_unmix_loader(path)`` must return an object with
    ``separate(FloatPCM) -> FloatPCM(44.1 kHz stereo)``.  ``basic_pitch_loader``
    must return an object with ``predict_onsets(mono_22050) -> list[dict]``.
    Both loaders are called only after the two local artifact digests match.
    """

    def __init__(self, open_unmix_artifact, basic_pitch_artifact,
                 open_unmix_loader=load_open_unmix_pilot, basic_pitch_loader=load_basic_pitch_onnx):
        if not isinstance(open_unmix_artifact, PinnedArtifact) or not isinstance(basic_pitch_artifact, PinnedArtifact):
            raise ValueError("both local pinned artifacts are required")
        if not callable(open_unmix_loader) or not callable(basic_pitch_loader):
            raise ValueError("both local runtime loaders are required")
        self.open_unmix_artifact = open_unmix_artifact
        self.basic_pitch_artifact = basic_pitch_artifact
        self.open_unmix_loader = open_unmix_loader
        self.basic_pitch_loader = basic_pitch_loader

    def create(self):
        try:
            self.open_unmix_artifact.verify()
            self.basic_pitch_artifact.verify()
        except PipelineError as error:
            raise RuntimeError(str(error)) from error
        try:
            separator = self.open_unmix_loader(self.open_unmix_artifact.path)
            onset = self.basic_pitch_loader(self.basic_pitch_artifact.path)
        except Exception as error:
            raise RuntimeError("BASS_RUNTIME_LOAD_FAILED") from error
        if not callable(getattr(separator, "separate", None)) or not callable(getattr(onset, "predict_onsets", None)):
            raise RuntimeError("BASS_RUNTIME_CONTRACT_INVALID")
        manifest = {"adapter": "open-unmix-basic-pitch-v1",
                    "basic_pitch": self.basic_pitch_artifact.sha256,
                    "open_unmix": self.open_unmix_artifact.sha256}
        identity = hashlib.sha256(json.dumps(manifest, sort_keys=True,
                                             separators=(",", ":")).encode("utf-8")).hexdigest()
        return PinnedBassSession(separator, onset, identity)


class PinnedBassSession(object):
    def __init__(self, separator, onset, artifact_sha256):
        if (not isinstance(artifact_sha256, str) or len(artifact_sha256) != 64 or
                any(character not in "0123456789abcdef" for character in artifact_sha256)):
            raise ValueError("pinned BASS artifact identity is required")
        self.separator, self.onset = separator, onset
        self.artifact_sha256 = artifact_sha256

    def analyse(self, pcm, origin_sample):
        if not isinstance(pcm, PCM) or type(origin_sample) is not int or origin_sample < 0:
            raise RuntimeError("BASS_INPUT_INVALID")
        stereo = to_stereo_44100(pcm)
        # The published Basic Pitch graph can emit a padding-edge onset for
        # all-zero input. Digital silence has no attributable attack, so stop
        # before either model rather than inventing a BASS candidate.
        if not any(abs(sample) > 1e-8 for sample in stereo.samples):
            return []
        try:
            separated = self.separator.separate(stereo)
            predictions = self.onset.predict_onsets(basic_pitch_mono(separated))
        except RuntimeError:
            raise
        except Exception as error:
            raise RuntimeError("BASS_RUNTIME_FAILED") from error
        return merge_channel_onsets((predictions, ()), pcm.sample_rate, origin_sample)
