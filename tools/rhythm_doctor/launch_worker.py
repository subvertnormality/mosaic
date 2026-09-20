"""Build and detach Mosaic's owned Rhythm Doctor capture worker.

The norns Lua event thread starts this helper in the background and polls the
published mailbox pathname.  This process performs compilation and blocking
startup away from that event thread.  The worker removes its own mailbox and
capture directory once its client stops stamping liveness.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time


def digest(paths: list[Path]) -> str:
    value = hashlib.sha256()
    for path in paths:
        value.update(path.name.encode("utf-8") + b"\0")
        value.update(path.read_bytes())
    return value.hexdigest()


def atomic_text(path: Path, value: str) -> None:
    temporary = path.with_name(path.name + ".new")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def compile_worker(source: Path, output: Path, stamp: Path) -> None:
    inputs = [source / "rd_capture_worker.c", source / "rd_capture.c"]
    identity = digest(inputs)
    if output.is_file() and os.access(output, os.X_OK) and stamp.is_file() and stamp.read_text().strip() == identity:
        return
    candidate = output.with_name(output.name + ".new")
    candidate.unlink(missing_ok=True)
    subprocess.run([
        "gcc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
        str(inputs[0]), "-o", str(candidate), "-ljack",
    ], check=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
       stderr=subprocess.PIPE, text=True, timeout=60)
    os.chmod(candidate, 0o700)
    os.replace(candidate, output)
    atomic_text(stamp, identity + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--left", required=True)
    parser.add_argument("--right", required=True)
    args = parser.parse_args()
    args.runtime.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(args.runtime, 0o700)
    mailbox_file, error_file = args.runtime / "mailbox", args.runtime / "error"
    mailbox_file.unlink(missing_ok=True); error_file.unlink(missing_ok=True)
    try:
        binary = args.runtime / "rd-worker"
        compile_worker(args.source, binary, args.runtime / "rd-worker.sha256")
        if (args.runtime / "cancel").exists():
            return 0
        log = (args.runtime / "worker.log").open("ab", buffering=0)
        owned_template = f"/tmp/mosaic-rd-{os.getuid()}-XXXXXX"
        process = subprocess.Popen(
            [str(binary), owned_template, args.left, args.right],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=log,
            close_fds=True,
        )
        assert process.stdout is not None
        selector = selectors.DefaultSelector(); selector.register(process.stdout, selectors.EVENT_READ)
        ready = selector.select(timeout=5)
        line = process.stdout.readline().decode("utf-8", "strict").strip() if ready else ""
        selector.close(); process.stdout.close(); log.close()
        if (args.runtime / "cancel").exists():
            process.terminate()
            return 0
        if process.poll() is not None or not line.startswith("/") or "\n" in line or "\t" in line:
            process.terminate()
            raise RuntimeError("capture worker did not publish a mailbox")
        atomic_text(args.runtime / "pid", str(process.pid) + "\n")
        atomic_text(mailbox_file, line + "\n")
        return 0
    except Exception as error:
        atomic_text(error_file, type(error).__name__ + ": " + str(error) + "\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
