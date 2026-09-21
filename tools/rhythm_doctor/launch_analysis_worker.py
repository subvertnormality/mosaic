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
import shlex
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



def build_native(runtime: Path, source: Path, templates: Path) -> Path:
    """Compile the native analysis backend, reusing an identical earlier build.

    The data paths are baked in because the worker invokes a backend with only
    --request and --result. The backend re-hashes both at run time, so the
    identity it reports is its real source and template digest, not a claim the
    launcher makes on its behalf.
    """
    source, templates = source.resolve(), templates.resolve()
    if not source.is_file() or not templates.is_file():
        raise RuntimeError("native backend source or templates missing")
    output = runtime / "rd_analysis_backend"
    stamp = runtime / "rd_analysis_backend.identity"
    identity = "\t".join([sha256_file(source), sha256_file(templates), str(templates)])
    if output.is_file() and os.access(output, os.X_OK) and stamp.is_file() \
            and stamp.read_text().strip() == identity:
        return output
    candidate = output.with_name(output.name + ".new")
    candidate.unlink(missing_ok=True)
    common = ["gcc", "-std=c11", "-O3", "-ffast-math", "-funroll-loops",
              "-DRD_TEMPLATE_PATH=\"" + str(templates) + "\"",
              "-DRD_SOURCE_PATH=\"" + str(source) + "\"",
              str(source), "-o", str(candidate), "-lm"]
    # NEON and OpenMP are worth roughly three times on the device, but neither
    # is required; fall back rather than fail to build.
    for extra in (["-mfpu=neon-vfpv4", "-fopenmp"], ["-fopenmp"], []):
        done = subprocess.run(common[:1] + extra + common[1:], stdin=subprocess.DEVNULL,
                              stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                              text=True, timeout=300)
        if done.returncode == 0:
            break
    else:
        raise RuntimeError(done.stderr.strip().splitlines()[-1] if done.stderr else "compile failed")
    os.chmod(candidate, 0o700)
    os.replace(candidate, output)
    atomic_text(stamp, identity + "\n")
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--backend", type=Path)
    parser.add_argument("--backend-sha256")
    parser.add_argument("--drum-artifact-sha256")
    parser.add_argument("--bass-artifact-sha256")
    parser.add_argument("--template-sha256")
    parser.add_argument("--native-source", type=Path,
                        help="C analysis backend to build and use when no --backend is given")
    parser.add_argument("--remote-backend", type=Path,
                        help="rd_remote_backend.py, used when an endpoint is configured")
    parser.add_argument("--remote-endpoint", default="",
                        help="analysis server base URL; empty means local analysis only")
    parser.add_argument("--templates", type=Path,
                        help="template table the native backend reads")
    args = parser.parse_args()
    native_built = None
    native_binary_sha256 = None
    args.runtime.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(args.runtime, 0o700)
    for name in ("mailbox", "error", "pid"):
        (args.runtime / name).unlink(missing_ok=True)
    if (args.runtime / "cancel").exists():
        return 0
    # With no backend configured, build the native one that ships with Mosaic.
    # This is what lets a stock install analyse a capture: the alternative is a
    # Python backend that needs numpy, which a Norns does not have.
    if args.backend is None and args.native_source and args.templates:
        try:
            built = build_native(args.runtime, args.native_source, args.templates)
        except Exception as error:
            atomic_text(args.runtime / "error",
                        "native analysis backend build failed: " + str(error) + "\n")
            return 1
        args.backend = built
        native_built = built.resolve()
        # The identity a result declares is the source and the template table,
        # because those reproduce anywhere; the compiled binary does not, so it
        # is pinned separately for the worker's own integrity check.
        args.backend_sha256 = sha256_file(args.native_source)
        args.template_sha256 = sha256_file(args.templates)
        native_binary_sha256 = sha256_file(built)
    # Either a model-free DSP identity (source + templates) or a pretrained
    # identity (source + model artifacts). Exactly one, completely.
    supplied = (args.backend, args.backend_sha256, args.drum_artifact_sha256,
                args.bass_artifact_sha256, args.template_sha256)
    is_dsp = args.backend is not None and sha256(args.backend_sha256) and sha256(args.template_sha256) \
        and args.drum_artifact_sha256 is None and args.bass_artifact_sha256 is None
    is_pretrained = args.backend is not None and all(sha256(v) for v in (
        args.backend_sha256, args.drum_artifact_sha256, args.bass_artifact_sha256)) and args.template_sha256 is None
    if any(value is not None for value in supplied) and not (is_dsp or is_pretrained):
        atomic_text(args.runtime / "error", "incomplete analysis backend configuration\n")
        return 1
    backend = args.backend.resolve() if args.backend else None
    if backend:
        try:
            backend_valid = backend.is_file() and os.access(backend, os.X_OK) and (
                native_built == backend or sha256_file(backend).lower() == args.backend_sha256.lower())
        except OSError:
            backend_valid = False
        if not backend_valid:
            atomic_text(args.runtime / "error", "invalid analysis backend\n")
            return 1
    # With an endpoint configured, the worker talks to a wrapper that posts the
    # capture and falls back to the local backend on any failure. The wrapper is
    # generated rather than invoked directly because the worker runs exactly one
    # executable with --request/--result and checks its digest; a script pinned
    # to this runtime carries the endpoint without changing that contract.
    if args.remote_endpoint and args.remote_backend and backend is not None:
        wrapper = args.runtime / "remote-backend"
        wrapper.write_text(
            "#!/bin/sh\nexec %s %s --endpoint %s --fallback %s \"$@\"\n" % (
                shlex.quote(sys.executable), shlex.quote(str(args.remote_backend.resolve())),
                shlex.quote(args.remote_endpoint), shlex.quote(str(backend))),
            encoding="utf-8")
        wrapper.chmod(0o755)
        backend = wrapper.resolve()
        native_binary_sha256 = sha256_file(wrapper)

    try:
        worker = Path(__file__).with_name("rd_analysis_worker.py")
        process = subprocess.Popen(
            [sys.executable, str(worker), "--runtime", str(args.runtime)] +
            (["--remote-analysis"] if (args.remote_endpoint and args.remote_backend) else []) +
            (["--backend", str(backend), "--backend-sha256", args.backend_sha256] +
             (["--backend-binary-sha256", native_binary_sha256] if native_binary_sha256 else []) +
             (["--template-sha256", args.template_sha256] if is_dsp else
              ["--drum-artifact-sha256", args.drum_artifact_sha256,
               "--bass-artifact-sha256", args.bass_artifact_sha256]) if backend else []),
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        assert process.stdout is not None
        line = process.stdout.readline().decode("utf-8", "strict").strip()
        process.stdout.close()
        if (args.runtime / "cancel").exists():
            process.terminate(); return 0
        if process.poll() is not None or not line.startswith("/") or "\t" in line or "\n" in line:
            process.terminate(); raise RuntimeError("analysis worker did not publish a mailbox")
        atomic_text(args.runtime / "pid", str(process.pid) + "\n")
        atomic_text(args.runtime / "mailbox", line + "\n")
        return 0
    except Exception as error:
        atomic_text(args.runtime / "error", type(error).__name__ + ": " + str(error) + "\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
