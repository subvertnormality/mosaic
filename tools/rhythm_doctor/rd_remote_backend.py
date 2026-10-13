#!/usr/bin/env python3
"""Remote analysis backend: post the capture to a server, or fall back.

This is a drop-in backend for rd_analysis_worker: it takes --request and
--result like every other backend, so the worker's process model is unchanged.

It is deliberately the most pessimistic component in the chain. The server is
an advanced option on someone's home network; it will be switched off, moved,
upgraded mid-capture and asked to analyse while it is still loading models.
Every one of those has to end with the player getting gates, so any failure
falls through to the local backend rather than surfacing an error. A capture
the player waited for is not worth losing to a DNS timeout.

Standard library only: this runs on the norns.
"""
from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

PROTOCOL_VERSION = 1
# A norns capture is at most 45 seconds and separation is not fast. This is
# long enough for a CPU-only server to finish and short enough that a player
# does not sit watching ANALYSING with nothing happening.
DEFAULT_TIMEOUT = 180.0


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def post_capture(endpoint: str, wav: Path, alignment: Any, timeout: float) -> dict[str, Any] | None:
    """Return the server's analysis, or None if it could not supply one."""
    try:
        body = wav.read_bytes()
    except OSError:
        return None
    request = urllib.request.Request(
        endpoint.rstrip("/") + "/v1/analyse", data=body, method="POST",
        headers={"Content-Type": "audio/wav", "Content-Length": str(len(body))})
    if alignment is not None:
        request.add_header("X-Rhythm-Doctor-Alignment", json.dumps(alignment))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                return None
            value = json.loads(response.read())
    except (urllib.error.URLError, urllib.error.HTTPError, socket.timeout,
            OSError, json.JSONDecodeError, ValueError):
        return None
    if not isinstance(value, dict) or value.get("protocol_version") != PROTOCOL_VERSION:
        return None
    return value


def usable(value: dict[str, Any], frames: int) -> bool:
    """Reject anything that would poison the bank.

    The server is a separate program on a machine Mosaic does not control, so
    its output is checked the same way a backend's is rather than trusted
    because it answered.
    """
    if not isinstance(value.get("bpm"), (int, float)) or not 40 <= value["bpm"] <= 240:
        return False
    for key in ("origin_sample", "phrase_start_sample"):
        at = value.get(key)
        if not isinstance(at, int) or isinstance(at, bool) or at < 0 or at > frames:
            return False
    confidence = value.get("phrase_confidence", 0.0)
    if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        return False
    gates = value.get("lane_onset_gates")
    if not isinstance(gates, dict) or not gates:
        return False
    if any(not isinstance(gate, (int, float)) or not 0 <= gate <= 1 for gate in gates.values()):
        return False
    beats = value.get("beat_positions", [])
    if not isinstance(beats, list) or any(
            not isinstance(b, int) or isinstance(b, bool) or b < 0 or b > frames for b in beats):
        return False
    candidates = value.get("candidates")
    if not isinstance(candidates, list):
        return False
    for candidate in candidates:
        if not isinstance(candidate, dict) or candidate.get("lane") not in gates:
            return False
        at = candidate.get("sample_index")
        if not isinstance(at, int) or isinstance(at, bool) or not 0 <= at < frames:
            return False
        velocity, confidence = candidate.get("velocity"), candidate.get("confidence")
        if not isinstance(velocity, (int, float)) or not 1 <= velocity <= 127:
            return False
        if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            return False
    detector = value.get("detector")
    return isinstance(detector, dict) and isinstance(detector.get("backend_id"), str) \
        and bool(detector["backend_id"])


def run_fallback(fallback: Path, request_path: Path, result_path: Path) -> int:
    """Hand the job to the local backend and let its result stand."""
    try:
        done = subprocess.run(
            [str(fallback), "--request", str(request_path), "--result", str(result_path)],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=600)
    except (OSError, subprocess.TimeoutExpired):
        return 3
    return done.returncode


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Rhythm Doctor remote analysis backend")
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--endpoint", default="")
    parser.add_argument("--fallback", type=Path, default=None,
                        help="local backend to use when the server cannot answer")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    args = parser.parse_args(argv)

    request = read_json(args.request)
    if request is None:
        return 2
    wav_path = request.get("wav_path")
    frames = request.get("frames")
    if not isinstance(wav_path, str) or not isinstance(frames, int) or frames <= 0:
        return 2

    analysis = None
    if args.endpoint:
        analysis = post_capture(args.endpoint, Path(wav_path), request.get("alignment"), args.timeout)
        if analysis is not None and not usable(analysis, frames):
            analysis = None
    if analysis is None:
        if args.fallback is None:
            return 2
        return run_fallback(args.fallback, args.request, args.result)

    analysis.pop("protocol_version", None)
    analysis.pop("capture_sha256", None)
    args.result.write_text(json.dumps(analysis, separators=(",", ":")), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
