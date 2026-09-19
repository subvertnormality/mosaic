"""Pinned Open-Unmix -> Basic Pitch BASS adapter for the analysis-worker ABI.

This is deliberately an adapter around *injected* model sessions.  It neither
imports a model framework nor installs, downloads, trains, or fine-tunes one.
The deployment profile supplies the two already-loaded sessions and their two
weight files.  Both files are hashed before a single inference call.  A failed
pin or malformed model result raises :class:`PipelineError`, so the enclosing
analysis worker can fail the request without publishing a partial analysis.

The runtime factory supplied to the command line owns the drum path.  It must
return an object with ``analyse_drums(request)``, ``bass_pipeline`` and
``bass_gate``.  ``analyse_drums`` supplies the four drum lanes and five gates;
this adapter refuses any BASS candidate from that path and replaces BASS only
with the separated, range-filtered Basic Pitch onsets.
"""
from __future__ import print_function

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys
import wave

# Factories normally import the adapter's public classes.  When this module is
# executed as the configured backend, make that import resolve to this live
# module rather than a second copy with incompatible PCM class identities.
if __name__ == "__main__":
    sys.modules.setdefault("pretrained_bass_backend", sys.modules[__name__])


LANES = ("BD", "SD", "CHH", "OHH", "BASS")
BASS_LOW_MIDI = 28
BASS_HIGH_MIDI = 60
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class PipelineError(RuntimeError):
    """The adapter cannot make a safe, fully attributable BASS result."""


class PinnedArtifact(object):
    """An explicitly provisioned immutable model artifact."""

    def __init__(self, name, path, sha256):
        self.name = name
        self.path = Path(path)
        self.sha256 = sha256.lower() if isinstance(sha256, str) else sha256
        if not isinstance(name, str) or not name or not SHA256.fullmatch(self.sha256 or ""):
            raise ValueError("artifact name and lowercase SHA-256 are required")

    def verify(self):
        try:
            digest = hashlib.sha256()
            with self.path.open("rb") as source:
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(block)
        except OSError as error:
            raise PipelineError("BASS_ARTIFACT_UNAVAILABLE") from error
        if digest.hexdigest() != self.sha256:
            raise PipelineError("BASS_ARTIFACT_SHA_MISMATCH")


class PCM(object):
    """Immutable interleaved PCM handed from capture to an injected session."""

    def __init__(self, data, sample_rate, channels, sample_width, frames):
        if not isinstance(data, bytes) or not isinstance(sample_rate, int) or sample_rate <= 0:
            raise ValueError("PCM data and positive sample rate are required")
        if channels not in (1, 2) or sample_width not in (1, 2, 3, 4) or not isinstance(frames, int) or frames < 0:
            raise ValueError("unsupported PCM layout")
        if len(data) != frames * channels * sample_width:
            raise ValueError("PCM byte count does not match its layout")
        self.data = data
        self.sample_rate = sample_rate
        self.channels = channels
        self.sample_width = sample_width
        self.frames = frames


def read_pcm_wav(path):
    """Read an immutable uncompressed mono/stereo WAV without downmixing it."""
    try:
        with wave.open(str(path), "rb") as source:
            if source.getcomptype() != "NONE":
                raise PipelineError("BASS_PCM_UNSUPPORTED")
            return PCM(source.readframes(source.getnframes()), source.getframerate(),
                       source.getnchannels(), source.getsampwidth(), source.getnframes())
    except PipelineError:
        raise
    except (OSError, EOFError, wave.Error, ValueError) as error:
        raise PipelineError("BASS_PCM_UNAVAILABLE") from error


def basic_pitch_frame_time(frame):
    """Pinned Basic Pitch 0.4.0 frame coordinate, including window correction."""
    if type(frame) is not int or frame < 0:
        raise PipelineError("BASS_ONSET_FRAME_INVALID")
    rate, hop, annotation_frames = 22050.0, 256.0, 172
    audio_samples = rate * 2 - hop
    offset = (hop / rate) * (annotation_frames - audio_samples / hop) + .0018
    return frame * hop / rate - (frame // annotation_frames) * offset


def attack_velocity(value):
    """Versioned attack-energy mapping; onset confidence is never velocity."""
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise PipelineError("BASS_ATTACK_INVALID")
    return max(1, min(127, int(math.floor(value * 126.0 + 1.5))))


class BassPipeline(object):
    """Run injected Open-Unmix-style separation then injected Basic Pitch onsets."""

    def __init__(self, separator_session, onset_session, separator_artifact, onset_artifact):
        if not callable(getattr(separator_session, "separate", None)):
            raise ValueError("separator_session.separate is required")
        if not callable(getattr(onset_session, "predict_onsets", None)):
            raise ValueError("onset_session.predict_onsets is required")
        if not isinstance(separator_artifact, PinnedArtifact) or not isinstance(onset_artifact, PinnedArtifact):
            raise ValueError("both pinned artifacts are required")
        self.separator_session = separator_session
        self.onset_session = onset_session
        self.separator_artifact = separator_artifact
        self.onset_artifact = onset_artifact

    @property
    def artifact_sha256(self):
        """Digest of the exact two-artifact manifest recorded in the result."""
        manifest = {"adapter": "open-unmix-basic-pitch-v1", "basic_pitch": self.onset_artifact.sha256,
                    "open_unmix": self.separator_artifact.sha256}
        return hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()

    def analyse(self, pcm, origin_sample):
        if not isinstance(pcm, PCM) or type(origin_sample) is not int or origin_sample < 0:
            raise PipelineError("BASS_INPUT_INVALID")
        self.separator_artifact.verify()
        self.onset_artifact.verify()
        try:
            separated = self.separator_session.separate(pcm)
            if not isinstance(separated, PCM) or separated.sample_rate != pcm.sample_rate:
                raise PipelineError("BASS_SEPARATOR_INVALID")
            predictions = self.onset_session.predict_onsets(separated)
        except PipelineError:
            raise
        except Exception as error:
            raise PipelineError("BASS_RUNTIME_FAILED") from error
        if not isinstance(predictions, (list, tuple)):
            raise PipelineError("BASS_ONSET_INVALID")
        candidates = []
        for prediction in predictions:
            candidate = self._candidate(prediction, pcm.sample_rate, origin_sample)
            if candidate is not None:
                candidates.append(candidate)
        if len(candidates) > 22500:
            raise PipelineError("BASS_CANDIDATE_LIMIT")
        candidates.sort(key=lambda value: (value["sample_index"], -value["confidence"], -value["velocity"]))
        return candidates

    def _candidate(self, prediction, sample_rate, origin_sample):
        if not isinstance(prediction, dict):
            raise PipelineError("BASS_ONSET_INVALID")
        pitch = prediction.get("midi_pitch")
        if type(pitch) is not int or not 21 <= pitch <= 108:
            raise PipelineError("BASS_PITCH_INVALID")
        if not BASS_LOW_MIDI <= pitch <= BASS_HIGH_MIDI:
            return None
        time_seconds = basic_pitch_frame_time(prediction.get("frame"))
        confidence = prediction.get("onset_confidence")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
            raise PipelineError("BASS_CONFIDENCE_INVALID")
        return {"lane": "BASS", "sample_index": origin_sample + int(math.floor(time_seconds * sample_rate + .5)),
                "velocity": attack_velocity(prediction.get("attack_strength")), "confidence": float(confidence)}


def pinned_profile(request):
    """The existing worker transports these identity pins unchanged to a backend."""
    value = request.get("pretrained") if isinstance(request, dict) else None
    if not isinstance(value, dict) or set(value) != {"backend_sha256", "drum_artifact_sha256", "bass_artifact_sha256"}:
        raise PipelineError("PRETRAINED_PROFILE_REQUIRED")
    if any(not isinstance(value[key], str) or not SHA256.fullmatch(value[key].lower()) for key in value):
        raise PipelineError("PRETRAINED_PROFILE_INVALID")
    return dict((key, value[key].lower()) for key in value)


def merge_bass(base_analysis, candidates, bass_gate, profile, pipeline_bass_sha256):
    """Replace only BASS, preserving the four pinned drum lanes and their gates."""
    if not isinstance(base_analysis, dict) or not isinstance(base_analysis.get("detector"), dict):
        raise PipelineError("DRUM_ANALYSIS_INVALID")
    gates = base_analysis.get("lane_onset_gates")
    if not isinstance(gates, dict) or set(gates) != set(LANES):
        raise PipelineError("DRUM_GATES_INVALID")
    if not isinstance(bass_gate, (int, float)) or isinstance(bass_gate, bool) or not math.isfinite(bass_gate) or not 0 <= bass_gate <= 1:
        raise PipelineError("BASS_GATE_INVALID")
    original = base_analysis.get("candidates", [])
    if not isinstance(original, list) or any(isinstance(row, dict) and row.get("lane") == "BASS" for row in original):
        raise PipelineError("DRUM_BASS_FALLBACK_FORBIDDEN")
    detector = dict(base_analysis["detector"])
    backend_id = detector.get("backend_id")
    if not isinstance(backend_id, str) or not backend_id:
        raise PipelineError("DRUM_DETECTOR_INVALID")
    # The drum adapter must identify the same frozen drum asset the profile
    # pinned.  The BASS profile hash is a canonical manifest of both injected
    # Open-Unmix and Basic Pitch assets, independently verified above.
    if detector.get("drum_artifact_sha256", detector.get("artifact_sha256")) != profile["drum_artifact_sha256"]:
        raise PipelineError("DRUM_ARTIFACT_MISMATCH")
    if pipeline_bass_sha256 != profile["bass_artifact_sha256"]:
        raise PipelineError("BASS_PROFILE_MISMATCH")
    detector = {"backend_id": backend_id + "+open-unmix-basic-pitch-v1",
                "backend_sha256": profile["backend_sha256"],
                "drum_artifact_sha256": profile["drum_artifact_sha256"],
                "bass_artifact_sha256": profile["bass_artifact_sha256"]}
    merged = dict(base_analysis)
    merged["detector"] = detector
    merged["lane_onset_gates"] = dict(gates)
    merged["lane_onset_gates"]["BASS"] = float(bass_gate)
    merged["candidates"] = list(original) + list(candidates)
    return merged


def run_request(request, runtime):
    """The concrete backend command's operation, separated for integration tests."""
    if not isinstance(request, dict) or not isinstance(request.get("wav_path"), str):
        raise PipelineError("REQUEST_INVALID")
    pipeline = getattr(runtime, "bass_pipeline", None)
    analyser = getattr(runtime, "analyse_drums", None)
    # A command-line factory may import this module by name while this file is
    # running as ``__main__``.  Structural validation keeps that harmless and
    # still requires the narrow adapter ABI; an unrelated object cannot enter
    # the worker merely by sharing a class name.
    if not callable(getattr(pipeline, "analyse", None)) or not isinstance(getattr(pipeline, "artifact_sha256", None), str) or not callable(analyser):
        raise PipelineError("BASS_RUNTIME_UNAVAILABLE")
    profile = pinned_profile(request)
    base = analyser(request)
    pcm = read_pcm_wav(request["wav_path"])
    return merge_bass(base, pipeline.analyse(pcm, base.get("origin_sample")), getattr(runtime, "bass_gate", None),
                      profile, pipeline.artifact_sha256)


def load_factory(spec):
    """Load an explicitly named local factory; there is no implicit runtime."""
    if not isinstance(spec, str) or ":" not in spec:
        raise PipelineError("RUNTIME_FACTORY_REQUIRED")
    location, name = spec.rsplit(":", 1)
    path = Path(location)
    if not path.is_file() or not name.isidentifier():
        raise PipelineError("RUNTIME_FACTORY_INVALID")
    module_spec = importlib.util.spec_from_file_location("rhythm_doctor_injected_runtime", str(path))
    if module_spec is None or module_spec.loader is None:
        raise PipelineError("RUNTIME_FACTORY_INVALID")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    factory = getattr(module, name, None)
    if not callable(factory):
        raise PipelineError("RUNTIME_FACTORY_INVALID")
    return factory()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--runtime-factory", required=True,
                        help="absolute local factory.py:callable; it injects already-loaded sessions and pinned artifacts")
    args = parser.parse_args(argv)
    try:
        request = json.loads(args.request.read_text(encoding="utf-8"))
        result = run_request(request, load_factory(args.runtime_factory))
        args.result.write_text(json.dumps(result, separators=(",", ":")), encoding="utf-8")
        return 0
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, PipelineError, ValueError):
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
