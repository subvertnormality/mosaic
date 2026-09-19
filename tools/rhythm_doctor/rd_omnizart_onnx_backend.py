#!/usr/bin/env python3
"""Executable adapter for the owned analysis-worker protocol.

This is deliberately a partial component: Omnizart supplies four drum lanes,
whereas the worker protocol requires a separate BASS result.  Until a pinned
BASS component and a five-lane merger are configured, it reports that exact
blocker rather than publishing an incomplete bank.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
from typing import Any

from rd_omnizart_onnx import ArtifactMismatch, verify_artifact


SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


def _write(path: Path, value: dict[str, Any]) -> int:
    path.write_text(json.dumps(value, separators=(",", ":")), encoding="utf-8")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    model, digest = os.environ.get("RD_OMNIZART_ONNX_MODEL"), os.environ.get("RD_OMNIZART_ONNX_SHA256")
    try:
        if not model or not digest:
            return _write(args.result, {"backend_error": "OMNIZART_ARTIFACT_NOT_CONFIGURED"})
        actual_digest = verify_artifact(Path(model), digest)
    except ArtifactMismatch as error:
        return _write(args.result, {"backend_error": str(error)})
    try:
        request = json.loads(args.request.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return _write(args.result, {"backend_error": "OMNIZART_REQUEST_INVALID"})
    pins = request.get("pretrained") if isinstance(request, dict) else None
    if not isinstance(pins, dict) or set(pins) != {
        "backend_sha256", "drum_artifact_sha256", "bass_artifact_sha256"
    } or any(not isinstance(pin, str) or not SHA256.fullmatch(pin) for pin in pins.values()):
        return _write(args.result, {"backend_error": "OMNIZART_REQUEST_INVALID"})
    if pins["drum_artifact_sha256"].lower() != actual_digest:
        return _write(args.result, {"backend_error": "OMNIZART_REQUEST_ARTIFACT_MISMATCH"})
    # Omnizart's published model has no BASS head.  Do not invoke a four-lane
    # result through the five-lane worker as though it were a paintable bank.
    return _write(args.result, {"backend_error": "OMNIZART_BASS_BACKEND_REQUIRED"})


if __name__ == "__main__":
    raise SystemExit(main())
