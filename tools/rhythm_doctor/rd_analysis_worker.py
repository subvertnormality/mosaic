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

LANES = ("BD", "SD", "CHH", "OHH", "BASS")
MAX_CANDIDATES = 22_500
MAX_RESULT_BYTES = 4 * 1024 * 1024
SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
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


def asset_is_exact(request: dict[str, Any]) -> bool:
    path = request.get("wav_path")
    digest = request.get("wav_sha256")
    if not isinstance(path, str) or not path.startswith("/") or "\x00" in path or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
        return False
    try:
        with wave.open(path, "rb") as source:
            frames, rate = source.getnframes(), source.getframerate()
        h = hashlib.sha256()
        with open(path, "rb") as source:
            for chunk in iter(lambda: source.read(1 << 20), b""):
                h.update(chunk)
        return frames == request.get("frames") and rate == request.get("sample_rate") and h.hexdigest().lower() == digest.lower()
    except (OSError, wave.Error):
        return False


def analysis_is_pretrained(value: Any) -> bool:
    if not isinstance(value, dict) or not isinstance(value.get("bpm"), (int, float)) or not 40 <= value["bpm"] <= 240:
        return False
    if not isinstance(value.get("origin_sample"), int) or value["origin_sample"] < 0:
        return False
    detector, gates = value.get("detector"), value.get("lane_onset_gates")
    if not isinstance(detector, dict) or not isinstance(detector.get("backend_id"), str) or not detector["backend_id"]:
        return False
    if not isinstance(detector.get("artifact_sha256"), str) or not re.fullmatch(r"[0-9a-fA-F]{64}", detector["artifact_sha256"]):
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


class Worker:
    def __init__(self, runtime: Path, backend: Path | None) -> None:
        self.runtime, self.backend = runtime, backend
        self.results = runtime / "results"; self.results.mkdir(mode=0o700, exist_ok=True)
        self.socket_path = runtime / "analysis.sock"; self.socket_path.unlink(missing_ok=True)
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.server.bind(str(self.socket_path)); os.chmod(self.socket_path, 0o600); self.server.listen(1)
        self.peer: socket.socket | None = None; self.request: dict[str, Any] | None = None
        self.process: subprocess.Popen[bytes] | None = None; self.request_path: Path | None = None; self.result_path: Path | None = None

    def send(self, value: dict[str, Any]) -> None:
        assert self.peer is not None
        self.peer.send(json.dumps(value, separators=(",", ":")).encode("utf-8"))

    def clear_job(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
        self.process = None; self.request = None; self.request_path = None; self.result_path = None

    def start(self, request: dict[str, Any]) -> None:
        if self.request is not None:
            self.send(failed(request, "ANALYSIS_BUSY")); return
        if not asset_is_exact(request):
            self.send(failed(request, "ANALYSIS_ASSET_MISMATCH")); return
        if self.backend is None:
            self.send(failed(request, "ANALYSIS_BACKEND_UNAVAILABLE")); return
        token = request["job_id"]
        self.request_path = self.results / (token + ".request.json")
        self.result_path = self.results / (token + ".json")
        self.request_path.write_text(json.dumps(request, separators=(",", ":")), encoding="utf-8")
        self.result_path.unlink(missing_ok=True)
        self.request = request
        self.process = subprocess.Popen([str(self.backend), "--request", str(self.request_path), "--result", str(self.result_path)],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)

    def complete(self) -> None:
        assert self.request is not None and self.process is not None and self.result_path is not None
        request, process, path = self.request, self.process, self.result_path
        if process.returncode != 0 or not path.is_file() or path.stat().st_size > MAX_RESULT_BYTES:
            self.send(failed(request, "ANALYSIS_BACKEND_FAILED")); self.clear_job(); return
        try:
            analysis = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            self.send(failed(request, "ANALYSIS_BACKEND_INVALID")); self.clear_job(); return
        if not analysis_is_pretrained(analysis):
            self.send(failed(request, "ANALYSIS_BACKEND_INVALID")); self.clear_job(); return
        stored = response(request, "COMPLETED", wav_path=request["wav_path"], wav_sha256=request["wav_sha256"],
            frames=request["frames"], sample_rate=request["sample_rate"], analysis=analysis)
        temporary = path.with_suffix(".published")
        with temporary.open("w", encoding="utf-8") as output:
            json.dump(stored, output, separators=(",", ":")); output.flush(); os.fsync(output.fileno())
        os.replace(temporary, path)
        self.send(response(request, "COMPLETED", result_path=str(path)))
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
                    self.clear_job(); self.send(response(message, "CANCELLED", command="CANCEL"))
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
    args=parser.parse_args(); args.runtime.mkdir(mode=0o700, parents=True, exist_ok=True)
    signal.signal(signal.SIGTERM, stop)
    if hasattr(signal, "SIGHUP"): signal.signal(signal.SIGHUP, stop)
    signal.signal(signal.SIGINT, stop)
    worker=Worker(args.runtime, args.backend)
    try: return worker.run()
    finally: worker.close()


if __name__ == "__main__":
    raise SystemExit(main())
