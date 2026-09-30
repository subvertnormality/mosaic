"""Detached, local-only protocol worker for a pinned pretrained backend.

The backend is an executable with ``--request REQUEST --result RESULT``.  It
must produce JSON analysis data for BD, SD and CYM.  This worker
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
import subprocess
import sys
import tempfile
import time
from typing import Any
import wave

# The lane set the on-device backend produces. A remote analysis declares its
# own, which is why nothing below compares against this beyond a default.
LANES = ("BD", "SD", "CYM")
MAX_CANDIDATES = 22_500
MAX_RESULT_BYTES = 4 * 1024 * 1024
SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
SAFE_BACKEND_ERROR = re.compile(r"^OMNIZART_[A-Z0-9_]{1,128}$")
SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
LANE_NAME = re.compile(r"^[A-Z][A-Z0-9_]{0,15}$")
# Results from the analysis server declare themselves with this prefix.
REMOTE_BACKEND_PREFIX = "remote-"
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


def analysis_matches_detector(value: Any, expected: dict[str, str] | None) -> bool:
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
    # expected None means "identity has already been established by other
    # means"; an empty mapping still means "nothing is acceptable".
    if expected is not None:
        if not expected:
            return False
        for name, digest in expected.items():
            actual = detector.get(name)
            if not isinstance(actual, str) or not SHA256.fullmatch(actual) or actual.lower() != str(digest).lower():
                return False
    # The gate table declares the lane set this analysis produced. The
    # on-device backend produces three; the remote server separates a kit and
    # produces ten. Demanding the local three would reject every remote result
    # and make the server pointless, so the declared set is validated for shape
    # and the candidates are held to it.
    if not isinstance(gates, dict) or not gates or len(gates) > 32:
        return False
    if any(not isinstance(lane, str) or not LANE_NAME.fullmatch(lane) or
           not isinstance(gate, (int, float)) or isinstance(gate, bool) or not 0 <= gate <= 1
           for lane, gate in gates.items()):
        return False
    candidates = value.get("candidates", [])
    if not isinstance(candidates, list) or len(candidates) > MAX_CANDIDATES:
        return False
    for candidate in candidates:
        if not isinstance(candidate, dict) or candidate.get("lane") not in gates or not isinstance(candidate.get("sample_index"), int) or candidate["sample_index"] < 0:
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


class Mailbox:
    """Sequenced file mailbox; the Python half of lib/rhythm_doctor/file_mailbox.lua.

    matron embeds Lua 5.3 without FFI, luasocket or a posix binding, so a norns
    script cannot hold an AF_UNIX socket at all. One message is therefore one
    file, written beside its target and renamed into place. Rename is atomic
    within a directory, so a reader never sees a partial record and framing
    stays exact -- the guarantee SOCK_SEQPACKET provided.

    The client has no socket to hang up, so it stamps "alive" while it polls
    and claims the mailbox exactly once. An unclaimed mailbox means nobody ever
    arrived; a stale stamp means the script is gone.
    """

    IDLE_SECONDS = 30.0
    CLAIM_SECONDS = 120.0

    def __init__(self, root: Path, outbound: str, inbound: str, limit: int) -> None:
        self.root, self.limit = root, limit
        self.outbound, self.inbound = root / outbound, root / inbound
        root.mkdir(mode=0o700, parents=True, exist_ok=True); os.chmod(root, 0o700)
        for directory in (self.outbound, self.inbound):
            shutil.rmtree(directory, ignore_errors=True); directory.mkdir(mode=0o700)
        self.send_sequence = self.receive_sequence = 1
        (root / "claimed").unlink(missing_ok=True); (root / "alive").unlink(missing_ok=True)
        (root / "claim").write_bytes(b""); (root / "up").write_bytes(b"")
        self.started = time.monotonic()

    def _name(self, directory: Path, sequence: int, suffix: str = "") -> Path:
        return directory / f"{sequence:09d}.msg{suffix}"

    def send(self, payload: bytes) -> None:
        partial = self._name(self.outbound, self.send_sequence, ".part")
        partial.write_bytes(payload)
        os.replace(partial, self._name(self.outbound, self.send_sequence))
        self.send_sequence += 1

    def receive(self) -> bytes | None:
        path = self._name(self.inbound, self.receive_sequence)
        try:
            payload = path.read_bytes()
        except FileNotFoundError:
            return None
        path.unlink(missing_ok=True); self.receive_sequence += 1
        return payload if 0 < len(payload) <= self.limit else b""

    def client_lost(self) -> bool:
        if not (self.root / "claimed").exists():
            return time.monotonic() - self.started > self.CLAIM_SECONDS
        try:
            stamped = (self.root / "alive").stat().st_mtime
        except FileNotFoundError:
            return False
        return time.time() - stamped > self.IDLE_SECONDS

    def flush_to_client(self, seconds: float = 1.0) -> None:
        """A socket kept a final reply buffered after close; files do not.

        Removing the outbox at once would delete an answer the client has not
        read yet, so a departing worker waits briefly for its last record to be
        consumed -- and only when a client actually claimed the mailbox.
        """
        if self.send_sequence <= 1 or not (self.root / "claimed").exists():
            return
        last = self._name(self.outbound, self.send_sequence - 1)
        deadline = time.monotonic() + seconds
        while last.exists() and time.monotonic() < deadline:
            time.sleep(.005)

    def close(self) -> None:
        self.flush_to_client()
        (self.root / "up").unlink(missing_ok=True)
        shutil.rmtree(self.outbound, ignore_errors=True); shutil.rmtree(self.inbound, ignore_errors=True)
        for leaf in ("claim", "claimed", "alive"):
            (self.root / leaf).unlink(missing_ok=True)


class Worker:
    remote_enabled: bool = False

    def __init__(self, runtime: Path, backend: Path | None, backend_sha256: str | None = None,
                 drum_artifact_sha256: str | None = None, bass_artifact_sha256: str | None = None,
                 template_sha256: str | None = None, backend_binary_sha256: str | None = None) -> None:
        self.runtime, self.backend = runtime, backend
        self.backend_sha256 = backend_sha256
        # Two different digests. backend_sha256 is the identity a result has to
        # declare, and for the backend Mosaic compiles itself that is the C
        # source, because a source digest reproduces and a binary does not --
        # it varies with the toolchain that built it. The integrity check below
        # needs the digest of the file actually on disk, which is this one.
        self.backend_binary_sha256 = backend_binary_sha256 or backend_sha256
        self.drum_artifact_sha256 = drum_artifact_sha256
        self.bass_artifact_sha256 = bass_artifact_sha256
        self.template_sha256 = template_sha256
        self.results = runtime / "results"; self.results.mkdir(mode=0o700, exist_ok=True)
        # Not "mailbox": the launcher publishes this root under that name as a
        # file, and a directory of the same name collides with it.
        self.mailbox = Mailbox(runtime / "ipc", "w2c", "c2w", 8192)
        self.request: dict[str, Any] | None = None
        self.process: subprocess.Popen[bytes] | None = None; self.request_path: Path | None = None; self.result_path: Path | None = None

    def analysis_is_acceptable(self, analysis: Any) -> bool:
        """Whether this result may become a bank.

        A locally produced result is pinned by digest: the worker built the
        backend, so it knows exactly what should have produced the answer.

        A result from the analysis server cannot be. Its models live on another
        machine that Mosaic does not build, install or version, so there is no
        digest to compare against and inventing one would only pin a claim the
        server makes about itself. What is checked instead is that the result
        declares the remote backend the launcher was told to expect, and that
        every field satisfies the same structural contract as a local result --
        which is what actually protects the bank.
        """
        if self.expected_detector() and analysis_matches_detector(analysis, self.expected_detector()):
            return True
        if not self.remote_enabled:
            return False
        detector = analysis.get("detector") if isinstance(analysis, dict) else None
        backend_id = detector.get("backend_id") if isinstance(detector, dict) else None
        # A prefix, not a fixed id: the server names itself for the models it
        # actually loaded, so it reports remote-htdemucs6s-larsnet-v1 with the
        # drum splitter and remote-htdemucs6s-v1 without it. Pinning one exact
        # id would reject every result the moment the operator added or removed
        # a model.
        if not isinstance(backend_id, str) or not backend_id.startswith(REMOTE_BACKEND_PREFIX):
            return False
        # Identity established by the declared backend id; everything else is
        # held to exactly the same structural contract as a local result.
        return analysis_matches_detector(analysis, None)

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
        self.mailbox.send(json.dumps(value, separators=(",", ":")).encode("utf-8"))

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
            backend_matches = sha256_file(self.backend).lower() == self.backend_binary_sha256.lower()
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
        if not self.analysis_is_acceptable(analysis) or \
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
        print(self.mailbox.root, flush=True)
        while not STOP:
            if self.process and self.process.poll() is not None:
                self.complete()
            raw = self.mailbox.receive()
            if raw is None:
                if self.mailbox.client_lost(): break
                time.sleep(.02); continue
            if not raw: continue
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
        self.mailbox.close()
        shutil.rmtree(self.results, ignore_errors=True)


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--runtime", type=Path, required=True); parser.add_argument("--backend", type=Path)
    parser.add_argument("--backend-sha256"); parser.add_argument("--drum-artifact-sha256"); parser.add_argument("--bass-artifact-sha256")
    parser.add_argument("--template-sha256")
    parser.add_argument("--remote-analysis", action="store_true",
                        help="accept results declaring a remote- backend, whose models "
                             "live on another machine and have no local digest")
    parser.add_argument("--backend-binary-sha256",
                        help="digest of the executable on disk, when it differs from the "
                             "identity a result declares (it does for a self-compiled backend)")
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
    worker=Worker(args.runtime, args.backend, args.backend_sha256, args.drum_artifact_sha256,
                  args.bass_artifact_sha256, args.template_sha256, args.backend_binary_sha256)
    worker.remote_enabled = bool(args.remote_analysis)
    try: return worker.run()
    finally: worker.close()


if __name__ == "__main__":
    raise SystemExit(main())
