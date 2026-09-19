"""Detached, local-only protocol worker for a pinned pretrained backend.

The backend is an executable with ``--request REQUEST --result RESULT``.  It
must produce JSON analysis data for BD, SD, CHH, OHH, and BASS.  This worker
checks WAV identity before invocation and keeps model execution off the norns
Lua event thread.  There is deliberately no fallback classifier or training
path: a missing/invalid backend reports a terminal error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
from typing import Any
import wave

LANES = ("BD", "SD", "CYM", "BASS")
MAX_CANDIDATES = 22_500
MAX_RESULT_BYTES = 4 * 1024 * 1024
SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
SAFE_BACKEND_ERROR = re.compile(r"^OMNIZART_[A-Z0-9_]{1,128}$")
SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
STOP = False


def stop(_: int, __: Any) -> None:
    global STOP
    STOP = True


def identity(value: Any) -> bool:
    return isinstance(value, dict) and value.get("protocol_version") == 1 and all(
        SAFE_ID.fullmatch(value.get(key, "")) for key in ("job_id", "project_id")
    ) and all(isinstance(value.get(key), int) and 0 <= value[key] <= 0xFFFFFFFF
              for key in ("generation", "analysis_revision"))


def same_identity(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return identity(left) and identity(right) and all(left[key] == right[key] for key in
        ("protocol_version", "job_id", "project_id", "generation", "analysis_revision"))


def response(request: dict[str, Any], status: str, **extra: Any) -> dict[str, Any]:
    value = {key: request[key] for key in ("protocol_version", "job_id", "project_id", "generation", "analysis_revision")}
    value.update(command="ANALYSE", status=status)
    value.update(extra)
    return value


def failed(request: dict[str, Any], code: str) -> dict[str, Any]:
    return response(request, "FAILED", analysis_error=code[:160])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def capture_is_bounded(request: dict[str, Any]) -> bool:
    frames, rate = request.get("frames"), request.get("sample_rate")
    return type(frames) is int and type(rate) is int and 8000 <= rate <= 192000 and 0 <= frames <= 45 * rate


def wav_geometry(path: str) -> tuple[int, int]:
    """Return (frames, sample_rate) for a capture WAV.

    The native recorder publishes WAVE_FORMAT_IEEE_FLOAT (tag 3), which
    Python's `wave` module refuses, so the RIFF chunks are parsed directly.
    Integer PCM still goes through `wave`, which validates it more strictly.
    """
    with open(path, "rb") as source:
        head = source.read(12)
        if len(head) < 12 or head[:4] != b"RIFF" or head[8:12] != b"WAVE":
            raise wave.Error("not a RIFF/WAVE file")
        fmt = None
        data_bytes = None
        while True:
            header = source.read(8)
            if len(header) < 8:
                break
            cid, size = header[:4], int.from_bytes(header[4:8], "little")
            if cid == b"fmt ":
                body = source.read(size)
                if len(body) < 16:
                    raise wave.Error("short fmt chunk")
                tag = int.from_bytes(body[0:2], "little")
                channels = int.from_bytes(body[2:4], "little")
                rate = int.from_bytes(body[4:8], "little")
                bits = int.from_bytes(body[14:16], "little")
                fmt = (tag, channels, rate, bits)
            elif cid == b"data":
                data_bytes = size
                source.seek(size + (size & 1), 1)
            else:
                source.seek(size + (size & 1), 1)
    if fmt is None or data_bytes is None:
        raise wave.Error("missing fmt or data chunk")
    tag, channels, rate, bits = fmt
    if channels not in (1, 2) or rate <= 0 or bits % 8 or bits == 0:
        raise wave.Error("unsupported WAV geometry")
    if tag not in (1, 3):
        raise wave.Error("unsupported WAV encoding")
    block = channels * (bits // 8)
    if block <= 0:
        raise wave.Error("unsupported WAV block alignment")
    return data_bytes // block, rate


def asset_is_exact(request: dict[str, Any]) -> bool:
    path = request.get("wav_path")
    digest = request.get("wav_sha256")
    if not isinstance(path, str) or not path.startswith("/") or "\x00" in path or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
        return False
    try:
        frames, rate = wav_geometry(path)
        h = hashlib.sha256()
        with open(path, "rb") as source:
            for chunk in iter(lambda: source.read(1 << 20), b""):
                h.update(chunk)
        return frames == request.get("frames") and rate == request.get("sample_rate") and h.hexdigest().lower() == digest.lower()
    except (OSError, wave.Error):
        return False


def analysis_matches_detector(value: Any, expected: dict[str, str]) -> bool:
    """Validate a backend result against an explicit detector identity.

    The identity fields differ by backend: a pretrained chain pins its model
    artifacts, a model-free DSP backend pins its own source and template table.
    Requiring a fixed set of field names would force one backend to invent
    digests it does not have, so the expected identity is supplied instead and
    every one of its entries must match exactly.
    """
    if not isinstance(value, dict) or not isinstance(value.get("bpm"), (int, float)) or not 40 <= value["bpm"] <= 240:
        return False
    if not isinstance(value.get("origin_sample"), int) or value["origin_sample"] < 0:
        return False
    detector, gates = value.get("detector"), value.get("lane_onset_gates")
    if not isinstance(detector, dict) or not isinstance(detector.get("backend_id"), str) or not detector["backend_id"]:
        return False
    if not expected:
        return False
    for name, digest in expected.items():
        actual = detector.get(name)
        if not isinstance(actual, str) or not SHA256.fullmatch(actual) or actual.lower() != str(digest).lower():
            return False
    if not isinstance(gates, dict) or set(gates) != set(LANES) or any(not isinstance(gates[lane], (int, float)) or not 0 <= gates[lane] <= 1 for lane in LANES):
        return False
    candidates = value.get("candidates", [])
    if not isinstance(candidates, list) or len(candidates) > MAX_CANDIDATES:
        return False
    for candidate in candidates:
        if not isinstance(candidate, dict) or candidate.get("lane") not in LANES or not isinstance(candidate.get("sample_index"), int) or candidate["sample_index"] < 0:
            return False
        if not isinstance(candidate.get("velocity"), (int, float)) or not 1 <= candidate["velocity"] <= 127 or not isinstance(candidate.get("confidence"), (int, float)) or not 0 <= candidate["confidence"] <= 1:
            return False
    return True


def analysis_is_pretrained(value: Any, backend_sha256: str, drum_artifact_sha256: str, bass_artifact_sha256: str) -> bool:
    """Pretrained-chain identity, expressed through the generic validator."""
    return analysis_matches_detector(value, {"backend_sha256": backend_sha256,
                                             "drum_artifact_sha256": drum_artifact_sha256,
                                             "bass_artifact_sha256": bass_artifact_sha256})


def analysis_is_dsp(value: Any, backend_sha256: str, template_sha256: str) -> bool:
    """Model-free DSP backend identity: its own source plus its template table."""
    return analysis_matches_detector(value, {"backend_sha256": backend_sha256,
                                             "template_sha256": template_sha256})


class Worker:
    def __init__(self, runtime: Path, backend: Path | None, backend_sha256: str | None = None,
                 drum_artifact_sha256: str | None = None, bass_artifact_sha256: str | None = None,
                 template_sha256: str | None = None) -> None:
        self.runtime, self.backend = runtime, backend
        self.backend_sha256 = backend_sha256
        self.drum_artifact_sha256 = drum_artifact_sha256
        self.bass_artifact_sha256 = bass_artifact_sha256
        self.template_sha256 = template_sha256
        self.results = runtime / "results"; self.results.mkdir(mode=0o700, exist_ok=True)
        self.socket_path = runtime / "analysis.sock"; self.socket_path.unlink(missing_ok=True)
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.server.bind(str(self.socket_path)); os.chmod(self.socket_path, 0o600); self.server.listen(1)
        self.peer: socket.socket | None = None; self.request: dict[str, Any] | None = None
        self.process: subprocess.Popen[bytes] | None = None; self.request_path: Path | None = None; self.result_path: Path | None = None

    def expected_detector(self) -> dict[str, str]:
        """The identity this worker will accept, keyed by how it was configured.

        A model-free backend pins its source and templates; a pretrained chain
        pins its model artifacts. Configuring neither accepts nothing.
        """
        identity: dict[str, str] = {}
        if self.backend_sha256:
            identity["backend_sha256"] = self.backend_sha256
        if self.template_sha256:
            identity["template_sha256"] = self.template_sha256
        if self.drum_artifact_sha256:
            identity["drum_artifact_sha256"] = self.drum_artifact_sha256
        if self.bass_artifact_sha256:
            identity["bass_artifact_sha256"] = self.bass_artifact_sha256
        return identity

    def send(self, value: dict[str, Any]) -> None:
        assert self.peer is not None
        self.peer.send(json.dumps(value, separators=(",", ":")).encode("utf-8"))

    def clear_job(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.process.kill(); self.process.wait(timeout=1)
        self.process = None; self.request = None; self.request_path = None; self.result_path = None

    def remove_job_files(self, remove_result: bool) -> None:
        for path in (self.request_path, self.result_path if remove_result else None):
            if path is not None:
                path.unlink(missing_ok=True)

    def start(self, request: dict[str, Any]) -> None:
        if self.request is not None:
            self.send(failed(request, "ANALYSIS_BUSY")); return
        if not asset_is_exact(request):
            self.send(failed(request, "ANALYSIS_ASSET_MISMATCH")); return
        if not capture_is_bounded(request):
            self.send(failed(request, "ANALYSIS_CAPTURE_BOUNDS")); return
        if self.backend is None:
            self.send(failed(request, "ANALYSIS_BACKEND_UNAVAILABLE")); return
        try:
            backend_matches = sha256_file(self.backend).lower() == self.backend_sha256.lower()
        except OSError:
            backend_matches = False
        if not backend_matches:
            self.send(failed(request, "ANALYSIS_BACKEND_MISMATCH")); return
        token = request["job_id"]
        self.request_path = self.results / (token + ".request.json")
        self.result_path = self.results / (token + ".json")
        backend_request = dict(request)
        backend_request["pretrained"] = {"backend_sha256": self.backend_sha256,
                                         "drum_artifact_sha256": self.drum_artifact_sha256,
                                         "bass_artifact_sha256": self.bass_artifact_sha256}
        self.request_path.write_text(json.dumps(backend_request, separators=(",", ":")), encoding="utf-8")
        self.result_path.unlink(missing_ok=True)
        self.request = request
        self.process = subprocess.Popen([str(self.backend), "--request", str(self.request_path), "--result", str(self.result_path)],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)

    def complete(self) -> None:
        assert self.request is not None and self.process is not None and self.result_path is not None
        request, process, path = self.request, self.process, self.result_path
        if process.returncode != 0 or not path.is_file() or path.stat().st_size > MAX_RESULT_BYTES:
            self.remove_job_files(True); self.clear_job(); self.send(failed(request, "ANALYSIS_BACKEND_FAILED")); return
        try:
            analysis = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            self.remove_job_files(True); self.clear_job(); self.send(failed(request, "ANALYSIS_BACKEND_INVALID")); return
        if isinstance(analysis, dict) and set(analysis) == {"backend_error"} and isinstance(analysis["backend_error"], str) and SAFE_BACKEND_ERROR.fullmatch(analysis["backend_error"]):
            self.remove_job_files(True); self.clear_job(); self.send(failed(request, analysis["backend_error"])); return
        if not analysis_matches_detector(analysis, self.expected_detector()) or \
                any(candidate["sample_index"] >= request["frames"] for candidate in analysis["candidates"]):
            self.remove_job_files(True); self.clear_job(); self.send(failed(request, "ANALYSIS_BACKEND_INVALID")); return
        stored = response(request, "COMPLETED", wav_path=request["wav_path"], wav_sha256=request["wav_sha256"],
            frames=request["frames"], sample_rate=request["sample_rate"], analysis=analysis)
        temporary = path.with_suffix(".published")
        with temporary.open("w", encoding="utf-8") as output:
            json.dump(stored, output, separators=(",", ":")); output.flush(); os.fsync(output.fileno())
        os.replace(temporary, path)
        self.send(response(request, "COMPLETED", result_path=str(path)))
        self.remove_job_files(False)
        self.clear_job()

    def run(self) -> int:
        print(self.socket_path, flush=True)
        self.peer, _ = self.server.accept(); self.peer.settimeout(.02)
        while not STOP:
            if self.process and self.process.poll() is not None:
                self.complete()
            try:
                raw = self.peer.recv(8192)
            except socket.timeout:
                continue
            if not raw: break
            try: message = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError): continue
            if not identity(message): continue
            if message.get("command") == "CANCEL":
                if self.request and same_identity(self.request, message):
                    self.remove_job_files(True); self.clear_job(); self.send(response(message, "CANCELLED", command="CANCEL"))
                else: self.send(failed(message, "ANALYSIS_STALE_CANCEL"))
            elif message.get("command") == "ANALYSE": self.start(message)
            else: self.send(failed(message, "ANALYSIS_PROTOCOL_ERROR"))
        self.clear_job(); return 0

    def close(self) -> None:
        if self.peer: self.peer.close()
        self.server.close(); self.socket_path.unlink(missing_ok=True)
        shutil.rmtree(self.results, ignore_errors=True)


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--runtime", type=Path, required=True); parser.add_argument("--backend", type=Path)
    parser.add_argument("--backend-sha256"); parser.add_argument("--drum-artifact-sha256"); parser.add_argument("--bass-artifact-sha256")
    parser.add_argument("--template-sha256")
    args=parser.parse_args(); args.runtime.mkdir(mode=0o700, parents=True, exist_ok=True)
    # Two identity shapes are supported, and a backend must supply exactly one
    # of them completely. A model-free DSP backend pins its source and template
    # table; a pretrained chain pins its model artifacts. Half a set is a
    # configuration error rather than a weaker pin.
    supplied = (args.backend, args.backend_sha256, args.drum_artifact_sha256,
                args.bass_artifact_sha256, args.template_sha256)
    def pinned(*values):
        return all(isinstance(v, str) and SHA256.fullmatch(v) for v in values)
    if any(value is not None for value in supplied):
        dsp = args.backend is not None and pinned(args.backend_sha256, args.template_sha256) \
            and args.drum_artifact_sha256 is None and args.bass_artifact_sha256 is None
        pretrained = args.backend is not None and pinned(args.backend_sha256, args.drum_artifact_sha256,
                                                         args.bass_artifact_sha256) and args.template_sha256 is None
        if not (dsp or pretrained):
            parser.error("configure a backend with either --template-sha256 or both model artifact digests, "
                         "alongside --backend and --backend-sha256")
    if args.backend and (not args.backend.is_file() or not os.access(args.backend, os.X_OK)):
        parser.error("backend must be an executable local file")
    signal.signal(signal.SIGTERM, stop)
    if hasattr(signal, "SIGHUP"): signal.signal(signal.SIGHUP, stop)
    signal.signal(signal.SIGINT, stop)
    worker=Worker(args.runtime, args.backend, args.backend_sha256, args.drum_artifact_sha256, args.bass_artifact_sha256)
    try: return worker.run()
    finally: worker.close()


if __name__ == "__main__":
    raise SystemExit(main())
