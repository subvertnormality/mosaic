"""Launch the owned Rhythm Doctor pretrained-analysis protocol worker.

This launcher deliberately does not install, train, or download a model.  The
configured backend must already be an executable pinned by Mosaic's deployment
profile; otherwise the worker stays available and fails each request closed.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys


def atomic_text(path: Path, value: str) -> None:
    temporary = path.with_name(path.name + ".new")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(value); handle.flush(); os.fsync(handle.fileno())
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--backend", type=Path)
    args = parser.parse_args()
    args.runtime.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(args.runtime, 0o700)
    for name in ("socket", "error", "pid"):
        (args.runtime / name).unlink(missing_ok=True)
    if (args.runtime / "cancel").exists():
        return 0
    backend = args.backend.resolve() if args.backend else None
    if backend and (not backend.is_file() or not os.access(backend, os.X_OK)):
        atomic_text(args.runtime / "error", "invalid pretrained analysis backend\n")
        return 1
    try:
        worker = Path(__file__).with_name("rd_analysis_worker.py")
        process = subprocess.Popen(
            [sys.executable, str(worker), "--runtime", str(args.runtime)] +
            (["--backend", str(backend)] if backend else []),
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
