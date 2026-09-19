#!/usr/bin/env python3
"""Five-lane pinned pretrained backend for ``rd_analysis_worker``.

It composes the four raw Omnizart drum heads with the separately pinned
Open-Unmix -> Basic Pitch BASS path.  All sessions and the CQT/mini-beat
frontend are injected by an explicit local factory.  This file provides no
model downloader, trainer, fallback classifier, or implicit runtime.
"""
from __future__ import print_function

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import sys

from pretrained_bass_backend import BassPipeline, PCM, PipelineError, pinned_profile, read_pcm_wav
from rd_omnizart_onnx import BACKEND_ID as DRUM_BACKEND_ID
from rd_omnizart_onnx import TensorContractError, analyse_features, verify_artifact

if __name__ == "__main__":
    sys.modules.setdefault("pretrained_composite_backend", sys.modules[__name__])


DRUM_LANES = ("BD", "SD", "CHH", "OHH")
LANES = DRUM_LANES + ("BASS",)
LANE_ORDER = dict((lane, index) for index, lane in enumerate(LANES))
BACKEND_ID = "omnizart-onnx-raw-heads-v1+open-unmix-basic-pitch-v1"
# Digital silence carries no tempo. The composed result still has to satisfy
# the 40..240 bank contract, so publish this placeholder and record that it
# was not measured through ``drum_component["tempo_detected"]``.
SILENT_INPUT_BPM = 120.0
SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


class CompositeError(PipelineError):
    """The pinned five-lane result cannot be made safely."""


class CompositeRuntime(object):
    """Explicitly injected model sessions and fixed, previously selected gates."""

    def __init__(self, drum_session, drum_model_path, feature_provider, drum_gates,
                 bass_pipeline, bass_gate):
        if not callable(getattr(feature_provider, "extract", None)):
            raise ValueError("feature_provider.extract is required")
        # The concrete UMXHQ -> Basic Pitch session is intentionally not a
        # ``BassPipeline``: its PCM hand-off is 44.1 kHz stereo and its
        # published Basic Pitch decoder runs at 22.05 kHz. Keep the worker
        # boundary structural so it can accept that concrete session while
        # retaining the same pin and analysis contract as the legacy adapter.
        if (not callable(getattr(bass_pipeline, "analyse", None)) or
                not isinstance(getattr(bass_pipeline, "artifact_sha256", None), str) or
                not SHA256.fullmatch(bass_pipeline.artifact_sha256)):
            raise ValueError("pinned bass pipeline is required")
        self.drum_session = drum_session
        self.drum_model_path = Path(drum_model_path)
        self.feature_provider = feature_provider
        self.drum_gates = drum_gates
        self.bass_pipeline = bass_pipeline
        self.bass_gate = bass_gate

    def _silent_drum_component(self, profile):
        """Return an empty, pin-verified component for a digitally silent buffer.

        The pinned Omnizart frontend delegates beat tracking to madmom, whose
        tempo estimate degenerates on an all-zero buffer and raises
        ValueError("arange: cannot compute length"); that escaped as
        OMNIZART_FRONTEND_FAILED on held-out corpus clip v12-silence-0, leaving
        the RD-02 absent-lane controls unscorable. Digital silence has no
        attributable attack, so stop before the frontend exactly as the pinned
        BASS pipeline already does. The pinned weight is still verified here so
        a silent capture cannot become a route around the artifact pin.
        """
        if not isinstance(self.drum_gates, dict) or set(self.drum_gates) != set(DRUM_LANES):
            raise CompositeError("OMNIZART_GATES_INVALID")
        try:
            digest = verify_artifact(self.drum_model_path, profile["drum_artifact_sha256"])
        except (TensorContractError, ValueError) as error:
            raise CompositeError(str(error)) from error
        return {"bpm": SILENT_INPUT_BPM, "origin_sample": 0,
                "drum_component": {"backend_id": DRUM_BACKEND_ID, "drum_artifact_sha256": digest,
                                   "tempo_detected": False},
                "lane_onset_gates": dict(self.drum_gates), "candidates": []}

    def analyse_drums(self, pcm, profile):
        """Run the raw four-head adapter after validating its exact pinned weight."""
        # Only an exactly all-zero buffer takes this route, so no audible
        # capture can be suppressed by it.
        if pcm.data.count(0) == len(pcm.data):
            return self._silent_drum_component(profile)
        try:
            source = self.feature_provider.extract(pcm)
        except Exception as error:
            raise CompositeError("OMNIZART_FRONTEND_FAILED") from error
        if not isinstance(source, dict) or set(source) != {"features", "mini_beats", "bpm", "origin_sample"}:
            raise CompositeError("OMNIZART_FRONTEND_INVALID")
        try:
            return analyse_features(session=self.drum_session, model_path=self.drum_model_path,
                                    expected_sha256=profile["drum_artifact_sha256"], features=source["features"],
                                    mini_beats=source["mini_beats"], sample_rate=pcm.sample_rate,
                                    gates=self.drum_gates, bpm=source["bpm"], origin_sample=source["origin_sample"])
        except (TensorContractError, ValueError) as error:
            raise CompositeError(str(error)) from error


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _drum_component(value, profile):
    if not isinstance(value, dict) or set(value) != {"bpm", "origin_sample", "drum_component", "lane_onset_gates", "candidates"}:
        raise CompositeError("OMNIZART_COMPONENT_INVALID")
    if not _number(value["bpm"]) or not 40 <= value["bpm"] <= 240 or type(value["origin_sample"]) is not int or value["origin_sample"] < 0:
        raise CompositeError("OMNIZART_COMPONENT_INVALID")
    component = value["drum_component"]
    if not isinstance(component, dict) or component.get("backend_id") != "omnizart-onnx-raw-heads-v1" or component.get("drum_artifact_sha256", "").lower() != profile["drum_artifact_sha256"]:
        raise CompositeError("OMNIZART_ARTIFACT_MISMATCH")
    gates = value["lane_onset_gates"]
    if not isinstance(gates, dict) or set(gates) != set(DRUM_LANES) or any(not _number(gates[lane]) or not 0 <= gates[lane] <= 1 for lane in DRUM_LANES):
        raise CompositeError("OMNIZART_GATES_INVALID")
    candidates = value["candidates"]
    if not isinstance(candidates, list) or any(not isinstance(candidate, dict) or candidate.get("lane") not in DRUM_LANES for candidate in candidates):
        raise CompositeError("OMNIZART_CANDIDATES_INVALID")
    return value


def compose(request, runtime):
    """Create one worker-valid, deterministic five-lane result from local PCM."""
    if not isinstance(request, dict) or not isinstance(request.get("wav_path"), str) or not isinstance(runtime, CompositeRuntime):
        raise CompositeError("COMPOSITE_REQUEST_INVALID")
    profile = pinned_profile(request)
    pcm = read_pcm_wav(request["wav_path"])
    drum = _drum_component(runtime.analyse_drums(pcm, profile), profile)
    origin = drum["origin_sample"]
    bass = runtime.bass_pipeline.analyse(pcm, origin)
    if runtime.bass_pipeline.artifact_sha256 != profile["bass_artifact_sha256"]:
        raise CompositeError("BASS_PROFILE_MISMATCH")
    if not _number(runtime.bass_gate) or not 0 <= runtime.bass_gate <= 1:
        raise CompositeError("BASS_GATE_INVALID")
    candidates = []
    for candidate in drum["candidates"]:
        copied = dict(candidate)
        if type(copied.get("sample_index")) is not int or copied["sample_index"] < 0:
            raise CompositeError("OMNIZART_CANDIDATES_INVALID")
        copied["sample_index"] += origin
        candidates.append(copied)
    candidates.extend(bass)
    if len(candidates) > 22500:
        raise CompositeError("COMPOSITE_CANDIDATE_LIMIT")
    candidates.sort(key=lambda candidate: (candidate["sample_index"], LANE_ORDER[candidate["lane"]],
                                            -candidate["confidence"], -candidate["velocity"]))
    gates = dict(drum["lane_onset_gates"])
    gates["BASS"] = float(runtime.bass_gate)
    return {"bpm": float(drum["bpm"]), "origin_sample": origin,
            "detector": {"backend_id": BACKEND_ID, "backend_sha256": profile["backend_sha256"],
                         "drum_artifact_sha256": profile["drum_artifact_sha256"],
                         "bass_artifact_sha256": profile["bass_artifact_sha256"]},
            "lane_onset_gates": gates, "candidates": candidates}


def _sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_factory(spec, expected_sha256):
    if not isinstance(spec, str) or ":" not in spec:
        raise CompositeError("RUNTIME_FACTORY_REQUIRED")
    location, name = spec.rsplit(":", 1)
    path = Path(location)
    if (not path.is_file() or not name.isidentifier() or
            not isinstance(expected_sha256, str) or not SHA256.fullmatch(expected_sha256) or
            _sha256_file(path).lower() != expected_sha256.lower()):
        raise CompositeError("RUNTIME_FACTORY_INVALID")
    module_spec = importlib.util.spec_from_file_location("rhythm_doctor_composite_runtime", str(path))
    if module_spec is None or module_spec.loader is None:
        raise CompositeError("RUNTIME_FACTORY_INVALID")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    factory = getattr(module, name, None)
    runtime = factory() if callable(factory) else None
    if not isinstance(runtime, CompositeRuntime):
        raise CompositeError("RUNTIME_FACTORY_INVALID")
    return runtime


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--runtime-factory", default=os.environ.get("RHYTHM_DOCTOR_PRETRAINED_RUNTIME_FACTORY"))
    parser.add_argument("--runtime-factory-sha256", default=os.environ.get("RHYTHM_DOCTOR_PRETRAINED_RUNTIME_FACTORY_SHA256"))
    args = parser.parse_args(argv)
    try:
        request = json.loads(args.request.read_text(encoding="utf-8"))
        runtime = load_factory(args.runtime_factory, args.runtime_factory_sha256)
        args.result.write_text(json.dumps(compose(request, runtime), separators=(",", ":")), encoding="utf-8")
        return 0
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, PipelineError, ValueError):
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
