"""Launch the owned Rhythm Doctor pretrained-analysis protocol worker.

This launcher deliberately does not install, train, or download a model.  The
configured backend must already be an executable pinned by Mosaic's deployment
profile; otherwise the worker stays available and fails each request closed.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys


def atomic_text(path: Path, value: str) -> None:
    temporary = path.with_name(path.name + ".new")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(value); handle.flush(); os.fsync(handle.fileno())
    os.replace(temporary, path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256(value: str | None) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdefABCDEF" for character in value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--backend", type=Path)
    parser.add_argument("--backend-sha256")
    parser.add_argument("--drum-artifact-sha256")
    parser.add_argument("--bass-artifact-sha256")
    args = parser.parse_args()
    args.runtime.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(args.runtime, 0o700)
    for name in ("socket", "error", "pid"):
        (args.runtime / name).unlink(missing_ok=True)
    if (args.runtime / "cancel").exists():
        return 0
    configured = (args.backend, args.backend_sha256, args.drum_artifact_sha256, args.bass_artifact_sha256)
    if any(value is not None for value in configured) and (args.backend is None or not all(sha256(value) for value in configured[1:])):
        atomic_text(args.runtime / "error", "incomplete pretrained analysis backend configuration\n")
        return 1
    backend = args.backend.resolve() if args.backend else None
    if backend:
        try:
            backend_valid = backend.is_file() and os.access(backend, os.X_OK) and sha256_file(backend).lower() == args.backend_sha256.lower()
        except OSError:
            backend_valid = False
        if not backend_valid:
            atomic_text(args.runtime / "error", "invalid pretrained analysis backend\n")
            return 1
    try:
        worker = Path(__file__).with_name("rd_analysis_worker.py")
        process = subprocess.Popen(
            [sys.executable, str(worker), "--runtime", str(args.runtime)] +
            (["--backend", str(backend), "--backend-sha256", args.backend_sha256,
              "--drum-artifact-sha256", args.drum_artifact_sha256,
              "--bass-artifact-sha256", args.bass_artifact_sha256] if backend else []),
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        assert process.stdout is not None
        line = process.stdout.readline().decode("utf-8", "strict").strip()
        process.stdout.close()
        if (args.runtime / "cancel").exists():
            process.terminate(); return 0
        if process.poll() is not None or not line.startswith("/") or "\t" in line or "\n" in line:
            process.terminate(); raise RuntimeError("analysis worker did not publish a socket")
        atomic_text(args.runtime / "pid", str(process.pid) + "\n")
        atomic_text(args.runtime / "socket", line + "\n")
        return 0
    except Exception as error:
        atomic_text(args.runtime / "error", type(error).__name__ + ": " + str(error) + "\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
