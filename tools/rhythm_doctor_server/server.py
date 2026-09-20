"""HTTP front end for the Rhythm Doctor remote analysis server.

Runs on a PC on the player's own network. Mosaic posts a capture and gets back
the same analysis shape the local backend produces, with ten lanes instead of
three.

Standard library only at this layer. The heavy dependencies belong to the
models; the transport should not add more, and a server that fails to start
because a web framework is missing helps nobody.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import logging
import struct
import sys
import threading
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np

import lanes
import pipeline

PROTOCOL_VERSION = 1
MAX_CAPTURE_BYTES = 64 * 1024 * 1024
MAX_CAPTURE_SECONDS = 45
SR = 44100

log = logging.getLogger("rhythm-doctor-server")


def read_wav(raw: bytes) -> tuple[np.ndarray, int]:
    """Mono float32 and the sample rate, from PCM or float WAV bytes.

    softcut writes 24-bit PCM, which Python's wave module reads as frames but
    cannot convert, so the sample widths are handled explicitly.
    """
    with wave.open(io.BytesIO(raw), "rb") as handle:
        channels, width, rate = handle.getnchannels(), handle.getsampwidth(), handle.getframerate()
        frames = handle.readframes(handle.getnframes())
    if channels not in (1, 2) or rate <= 0:
        raise ValueError("unsupported channel count or sample rate")
    if width == 2:
        samples = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    elif width == 3:
        raw_bytes = np.frombuffer(frames, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        packed = raw_bytes[:, 0] | (raw_bytes[:, 1] << 8) | (raw_bytes[:, 2] << 16)
        packed = np.where(packed & 0x800000, packed - 0x1000000, packed)
        samples = packed.astype(np.float32) / 8388608.0
    elif width == 4:
        samples = np.frombuffer(frames, dtype="<f4").astype(np.float32)
    else:
        raise ValueError("unsupported sample width: %d bytes" % width)
    usable = (samples.size // channels) * channels
    samples = samples[:usable]
    if not np.isfinite(samples).all():
        raise ValueError("capture contains non-finite samples")
    mono = samples.reshape(-1, channels).mean(axis=1) if channels == 2 else samples
    return mono.astype(np.float32), int(rate)


class Service:
    """Model ownership and the one analysis lock.

    Separation is memory hungry and the norns sends one capture at a time, so
    requests are serialised rather than queued behind an unbounded thread pool
    that would run the machine out of memory.
    """

    def __init__(self, models: pipeline.Models | None, load_error: str | None = None) -> None:
        self.models, self.load_error = models, load_error
        self.lock = threading.Lock()

    def ready(self) -> bool:
        return self.models is not None

    def analyse(self, mono: np.ndarray, rate: int, alignment: dict | None) -> dict:
        if self.models is None:
            raise RuntimeError(self.load_error or "models are not loaded")
        with self.lock:
            return pipeline.analyse(mono, rate, self.models, alignment=alignment)


class Handler(BaseHTTPRequestHandler):
    server_version = "RhythmDoctor/1.0"
    service: Service = None                            # set by serve()

    def log_message(self, fmt, *args):                 # quieter default logging
        log.info("%s - %s", self.address_string(), fmt % args)

    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path.rstrip("/") != "/v1/health":
            self._send(404, {"error": "NOT_FOUND"})
            return
        self._send(200, {
            "protocol_version": PROTOCOL_VERSION,
            "ready": self.service.ready(),
            "error": None if self.service.ready() else self.service.load_error,
            "lanes": list(lanes.LANES),
            "lane_onset_gates": lanes.DEFAULT_GATE,
            "max_capture_seconds": MAX_CAPTURE_SECONDS,
            "detector": dict(self.service.models.identity) if self.service.ready() else {},
        })

    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/v1/analyse":
            self._send(404, {"error": "NOT_FOUND"})
            return
        if not self.service.ready():
            self._send(503, {"error": "MODELS_UNAVAILABLE", "detail": self.service.load_error})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send(400, {"error": "BAD_LENGTH"})
            return
        if length <= 0 or length > MAX_CAPTURE_BYTES:
            self._send(413, {"error": "CAPTURE_TOO_LARGE"})
            return
        raw = self.rfile.read(length)
        if len(raw) != length:
            self._send(400, {"error": "TRUNCATED"})
            return
        alignment = self.headers.get("X-Rhythm-Doctor-Alignment")
        try:
            alignment = json.loads(alignment) if alignment else None
        except json.JSONDecodeError:
            self._send(400, {"error": "BAD_ALIGNMENT"})
            return
        try:
            mono, rate = read_wav(raw)
        except (ValueError, wave.Error, EOFError, struct.error) as error:
            self._send(400, {"error": "BAD_CAPTURE", "detail": str(error)[:200]})
            return
        if mono.size > rate * MAX_CAPTURE_SECONDS:
            self._send(413, {"error": "CAPTURE_TOO_LONG"})
            return
        try:
            analysis = self.service.analyse(mono, rate, alignment)
        except Exception as error:                     # a model fault is a 500
            log.exception("analysis failed")
            self._send(500, {"error": "ANALYSIS_FAILED", "detail": str(error)[:200]})
            return
        analysis["capture_sha256"] = hashlib.sha256(raw).hexdigest()
        analysis["protocol_version"] = PROTOCOL_VERSION
        self._send(200, analysis)


def build_models() -> tuple[pipeline.Models | None, str | None]:
    import models as adapters
    try:
        separate, separator_identity = adapters.load_demucs()
        separate_drums, drum_identity = adapters.load_larsnet()
        track_beats, tracker_identity = adapters.load_beat_this()
    except adapters.ModelUnavailable as error:
        return None, str(error)
    identity = {"backend_id": "remote-htdemucs6s-larsnet-v1"}
    identity.update(separator_identity); identity.update(drum_identity); identity.update(tracker_identity)
    return pipeline.Models(separate=separate, separate_drums=separate_drums,
                           track_beats=track_beats, identity=identity), None


def serve(host: str, port: int, service: Service) -> None:
    Handler.service = service
    httpd = ThreadingHTTPServer((host, port), Handler)
    log.info("listening on http://%s:%d/ (ready=%s)", host, port, service.ready())
    httpd.serve_forever()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Rhythm Doctor remote analysis server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8420)
    parser.add_argument("--allow-missing-models", action="store_true",
                        help="start and report the fault on /v1/health instead of exiting")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    models, error = build_models()
    if models is None and not args.allow_missing_models:
        print("models unavailable: %s" % error, file=sys.stderr)
        return 2
    serve(args.host, args.port, Service(models, error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
