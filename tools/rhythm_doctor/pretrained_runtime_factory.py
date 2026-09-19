"""Fail-closed local factory for the pinned Rhythm Doctor pretrained chain.

This factory deliberately has no network, downloader, trainer, or heuristic
fallback.  Operators must provision the exact Omnizart v0.4.2 source checkout
and all three published/local model artifacts through its explicit environment
variables before the analysis worker may start.
"""
from __future__ import print_function

import importlib
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import wave

import numpy as np

from pretrained_bass_backend import PCM, PinnedArtifact
from pretrained_bass_runtime import PinnedBassRuntime, load_basic_pitch_onnx
from pretrained_composite_backend import CompositeRuntime
from rd_omnizart_onnx import verify_artifact, z_score_gate_to_confidence


OMNIZART_V042_HEAD = "0779fd5699be6605b9944ab3c5013af3c49f65df"
OMNIZART_DRUM_ONNX_SHA256 = "b6a2fd48850b3ef94fec3e2c97277ded6e3d366e7807a8ed2f0119b3da6e2d3f"
UMXHQ_BASS_SHA256 = "8d85a5bd3f996a8867fca0e8442e077e5a3f5ec747a6112742452a8f347b39c8"
BASIC_PITCH_ONNX_SHA256 = "2c3c1d144bfa61ad236e92e169c13535c880469a12a047d4e73451f2c059a0ec"

ENV_OMNIZART_SOURCE = "RHYTHM_DOCTOR_OMNIZART_SOURCE"
ENV_OMNIZART_ONNX = "RHYTHM_DOCTOR_OMNIZART_ONNX"
ENV_UMXHQ_BASS = "RHYTHM_DOCTOR_UMXHQ_BASS"
ENV_BASIC_PITCH_ONNX = "RHYTHM_DOCTOR_BASIC_PITCH_ONNX"

# These are fixed, intentionally provisional decoder gates.  They are kept in
# the factory, rather than inferred from an input, until the corpus gate work
# establishes production calibration for the selected recordings.
PROVISIONAL_UNVALIDATED_OMNIZART_Z_GATES = {
    "BD": 0.85, "SD": 1.20, "CHH": 0.17, "OHH": 0.17,
}
PROVISIONAL_UNVALIDATED_DRUM_GATES = {
    lane: z_score_gate_to_confidence(value)
    for lane, value in PROVISIONAL_UNVALIDATED_OMNIZART_Z_GATES.items()
}
PROVISIONAL_UNVALIDATED_BASS_ONSET_GATE = 0.20


class RuntimeFactoryError(RuntimeError):
    """The local provisioned pretrained chain is not exactly identifiable."""


def configured_paths(environment=None):
    """Read all paths explicitly; a partial configuration is never usable."""
    environment = os.environ if environment is None else environment
    names = (ENV_OMNIZART_SOURCE, ENV_OMNIZART_ONNX, ENV_UMXHQ_BASS,
             ENV_BASIC_PITCH_ONNX)
    values = {}
    for name in names:
        raw = environment.get(name)
        if not isinstance(raw, str) or not raw.strip():
            raise RuntimeFactoryError("RHYTHM_DOCTOR_RUNTIME_PATH_REQUIRED")
        values[name] = Path(raw).expanduser()
    return values


def verify_omnizart_checkout(source_root, runner=subprocess.run):
    """Require the exact source tree whose frontend made the feature patches."""
    root = Path(source_root).resolve()
    required = (root / "omnizart" / "feature" / "wrapper_func.py",
                root / "omnizart" / "feature" / "beat_for_drum.py")
    if not root.is_dir() or any(not path.is_file() for path in required):
        raise RuntimeFactoryError("OMNIZART_SOURCE_UNAVAILABLE")
    try:
        result = runner(["git", "-C", str(root), "rev-parse", "HEAD"],
                        check=False, capture_output=True, text=True)
    except (OSError, TypeError) as error:
        raise RuntimeFactoryError("OMNIZART_SOURCE_REVISION_UNAVAILABLE") from error
    actual = getattr(result, "stdout", "").strip().lower()
    if getattr(result, "returncode", 1) != 0 or actual != OMNIZART_V042_HEAD:
        raise RuntimeFactoryError("OMNIZART_SOURCE_REVISION_MISMATCH")
    return root


def _install_librosa_numpy_compatibility(numpy_module=np):
    """Permit Omnizart v0.4.2's librosa import under newer NumPy releases."""
    aliases = {"complex": "complex128", "float": "float64", "int": "int64"}
    for legacy, current in aliases.items():
        if not hasattr(numpy_module, legacy):
            setattr(numpy_module, legacy, getattr(numpy_module, current))


def _is_under(path, root):
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
        return True
    except (OSError, ValueError):
        return False


def _load_omnizart_frontend(source_root):
    """Import only the verified checkout's exact CQT and mini-beat functions."""
    _install_librosa_numpy_compatibility()
    root = Path(source_root).resolve()
    existing = sys.modules.get("omnizart")
    if existing is not None and not _is_under(getattr(existing, "__file__", ""), root):
        raise RuntimeFactoryError("OMNIZART_SOURCE_IMPORT_MISMATCH")
    sys.path.insert(0, str(root))
    try:
        audio_io = importlib.import_module("omnizart.io")
        # v0.4.2 intends to fall back to librosa when optional Spleeter is
        # absent, but evaluating ``adapter.SpleeterError`` re-imports Spleeter
        # inside the exception clause. Select that documented fallback before
        # the lazy CQT and beat modules bind their load_audio reference.
        audio_io.load_audio = audio_io.load_audio_with_librosa
        wrapper = importlib.import_module("omnizart.feature.wrapper_func")
    except Exception as error:
        raise RuntimeFactoryError("OMNIZART_FRONTEND_IMPORT_FAILED") from error
    finally:
        del sys.path[0]
    if not _is_under(getattr(wrapper, "__file__", ""), root):
        raise RuntimeFactoryError("OMNIZART_SOURCE_IMPORT_MISMATCH")
    extract_patch_cqt = getattr(wrapper, "extract_patch_cqt", None)
    if not callable(extract_patch_cqt):
        raise RuntimeFactoryError("OMNIZART_FRONTEND_UNAVAILABLE")
    return extract_patch_cqt


class OmnizartFeatureProvider(object):
    """CQT patch provider using Omnizart's exact audio-path frontend."""

    def __init__(self, extract_patch_cqt):
        if not callable(extract_patch_cqt):
            raise ValueError("exact Omnizart frontend function is required")
        self.extract_patch_cqt = extract_patch_cqt

    @classmethod
    def from_checkout(cls, source_root):
        return cls(_load_omnizart_frontend(source_root))

    @staticmethod
    def _write_pcm_wav(pcm, path):
        if not isinstance(pcm, PCM):
            raise RuntimeFactoryError("OMNIZART_PCM_INVALID")
        with wave.open(str(path), "wb") as target:
            target.setnchannels(pcm.channels)
            target.setsampwidth(pcm.sample_width)
            target.setframerate(pcm.sample_rate)
            target.writeframes(pcm.data)

    @staticmethod
    def _bpm_from_eight_mini_beats(mini_beats):
        positions = np.asarray(mini_beats, dtype=np.float64)
        if positions.ndim != 1 or len(positions) < 9 or not np.isfinite(positions).all():
            raise RuntimeFactoryError("OMNIZART_MINI_BEATS_INVALID")
        intervals = positions[8:] - positions[:-8]
        if not np.isfinite(intervals).all() or np.any(intervals <= 0):
            raise RuntimeFactoryError("OMNIZART_MINI_BEATS_INVALID")
        bpm = 60.0 / float(np.median(intervals))
        if not math.isfinite(bpm) or not 40.0 <= bpm <= 240.0:
            raise RuntimeFactoryError("OMNIZART_BPM_INVALID")
        return bpm

    def extract(self, pcm):
        descriptor, raw_path = tempfile.mkstemp(prefix="rhythm-doctor-omnizart-", suffix=".wav")
        os.close(descriptor)
        path = Path(raw_path)
        try:
            self._write_pcm_wav(pcm, path)
            extracted = self.extract_patch_cqt(str(path))
            if not isinstance(extracted, (tuple, list)) or len(extracted) != 2:
                raise RuntimeFactoryError("OMNIZART_FEATURES_INVALID")
            features = np.asarray(extracted[0], dtype=np.float32)
            mini_beats = np.asarray(extracted[1], dtype=np.float64)
            if (features.ndim != 3 or features.shape[1:] != (120, 120) or
                    len(features) != len(mini_beats) or not np.isfinite(features).all()):
                raise RuntimeFactoryError("OMNIZART_FEATURES_INVALID")
            return {"features": features, "mini_beats": mini_beats,
                    "bpm": self._bpm_from_eight_mini_beats(mini_beats),
                    "origin_sample": 0}
        finally:
            try:
                path.unlink()
            except FileNotFoundError:
                pass


def load_drum_onnx(path):
    """Create a bounded, sequential CPU session for the verified drum graph."""
    try:
        import onnxruntime
        options = onnxruntime.SessionOptions()
        options.enable_cpu_mem_arena = False
        options.enable_mem_pattern = False
        options.execution_mode = onnxruntime.ExecutionMode.ORT_SEQUENTIAL
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        return onnxruntime.InferenceSession(str(path), sess_options=options,
                                            providers=["CPUExecutionProvider"])
    except Exception as error:
        raise RuntimeFactoryError("OMNIZART_ONNX_RUNTIME_UNAVAILABLE") from error


def load_provisional_basic_pitch(path):
    """Use the named provisional gate for the published Basic Pitch decoder."""
    return load_basic_pitch_onnx(path, threshold=PROVISIONAL_UNVALIDATED_BASS_ONSET_GATE)


def make(environment=None):
    """Construct the fully pinned five-lane runtime from local artifacts only."""
    paths = configured_paths(environment)
    source_root = verify_omnizart_checkout(paths[ENV_OMNIZART_SOURCE])
    drum_path = paths[ENV_OMNIZART_ONNX]
    try:
        verify_artifact(drum_path, OMNIZART_DRUM_ONNX_SHA256)
    except Exception as error:
        raise RuntimeFactoryError("OMNIZART_DRUM_ARTIFACT_INVALID") from error
    umxhq = PinnedArtifact("umxhq-bass", paths[ENV_UMXHQ_BASS], UMXHQ_BASS_SHA256)
    basic_pitch = PinnedArtifact("basic-pitch-nmp", paths[ENV_BASIC_PITCH_ONNX],
                                 BASIC_PITCH_ONNX_SHA256)
    try:
        bass_pipeline = PinnedBassRuntime(umxhq, basic_pitch,
                                           basic_pitch_loader=load_provisional_basic_pitch).create()
    except Exception as error:
        raise RuntimeFactoryError("BASS_RUNTIME_UNAVAILABLE") from error
    return CompositeRuntime(load_drum_onnx(drum_path), drum_path,
                            OmnizartFeatureProvider.from_checkout(source_root),
                            dict(PROVISIONAL_UNVALIDATED_DRUM_GATES), bass_pipeline,
                            PROVISIONAL_UNVALIDATED_BASS_ONSET_GATE)
