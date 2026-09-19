"""Run on physical Norns: owned-port capture spike, never product acceptance.

RD-01 characterisation outside README. Injects PCM through owned JACK input ports;
this bypasses ADC/electrical ingress and never connects to audible output ports.
Existing JACK connections must be byte-for-byte unchanged after every capture.
"""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import resource
import struct
import subprocess
import tempfile
import time


def ports():
    return subprocess.check_output(["jack_lsp", "-c"], text=True)


def run(library, injector_binary, output):
    initial = ports()
    lib = ctypes.CDLL(str(library))
    for name in ("rd_capture_start", "rd_capture_stop", "rd_capture_state", "rd_capture_error"):
        function = getattr(lib, name)
        function.argtypes = [ctypes.c_void_p]
        function.restype = ctypes.c_int
    lib.rd_capture_preflight.argtypes = [ctypes.c_uint32]
    lib.rd_capture_preflight.restype = ctypes.c_void_p
    lib.rd_capture_destroy.argtypes = [ctypes.c_void_p]
    lib.rd_capture_pcm_locked.argtypes = [ctypes.c_void_p]
    lib.rd_capture_pcm_locked.restype = ctypes.c_int
    lib.rd_capture_input_port.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    lib.rd_capture_input_port.restype = ctypes.c_char_p
    lib.rd_capture_publish_wav.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lib.rd_capture_publish_wav.restype = ctypes.c_int
    for name in ("rd_capture_frames", "rd_capture_start_frame", "rd_capture_end_frame", "rd_capture_preflight_nanoseconds"):
        function = getattr(lib, name)
        function.argtypes = [ctypes.c_void_p]
        function.restype = ctypes.c_uint64
    results = []
    with tempfile.TemporaryDirectory(prefix="rd-hardware-capture-") as temporary:
        for trial in range(3):
            capture = None
            injector = None
            before = ports()
            record = {"trial": trial, "passed": False}
            try:
                started = time.monotonic_ns()
                capture = lib.rd_capture_preflight(45)
                record["preflight_ms"] = (time.monotonic_ns() - started) / 1e6
                if not capture:
                    raise RuntimeError("NOT READY")
                record["native_preflight_ms"] = lib.rd_capture_preflight_nanoseconds(capture) / 1e6
                record["pcm_locked"] = bool(lib.rd_capture_pcm_locked(capture))
                injector = subprocess.Popen([str(injector_binary)], stdout=subprocess.DEVNULL,
                                            stderr=subprocess.PIPE, text=True)
                deadline = time.monotonic() + 3
                while "rd-capture-injector:left" not in ports():
                    if injector.poll() is not None or time.monotonic() >= deadline:
                        raise RuntimeError("independent PCM source failed to start")
                    time.sleep(.01)
                for name, channel in (("left", 0), ("right", 1)):
                    subprocess.run(["jack_connect", "rd-capture-injector:" + name,
                                    lib.rd_capture_input_port(capture, channel).decode()], check=True)
                arm_time = time.monotonic_ns()
                if lib.rd_capture_start(capture) != 0:
                    raise RuntimeError("capture arm rejected")
                deadline = time.monotonic() + 1
                while not lib.rd_capture_frames(capture):
                    if lib.rd_capture_state(capture) == 6 or time.monotonic() >= deadline:
                        raise RuntimeError("no PCM arrived")
                    time.sleep(.0005)
                record["arm_to_first_observed_pcm_ms"] = (time.monotonic_ns() - arm_time) / 1e6
                # This is polling upper-bound latency, not grid-key-to-first-PCM latency.
                time.sleep(.25)
                if lib.rd_capture_stop(capture) != 0:
                    raise RuntimeError("capture stop rejected: error %d" % lib.rd_capture_error(capture))
                deadline = time.monotonic() + 1
                while lib.rd_capture_state(capture) != 4:
                    if lib.rd_capture_state(capture) == 6 or time.monotonic() >= deadline:
                        raise RuntimeError("capture did not complete")
                    time.sleep(.001)
                record["frames"] = lib.rd_capture_frames(capture)
                record["start_frame"] = lib.rd_capture_start_frame(capture)
                record["end_frame"] = lib.rd_capture_end_frame(capture)
                target = Path(temporary) / ("trial-%d.wav" % trial)
                if lib.rd_capture_publish_wav(capture, str(target).encode()) != 0:
                    raise RuntimeError("capture publication failed")
                payload = target.read_bytes()
                if payload[:4] + payload[8:12] != b"RIFFWAVE":
                    raise AssertionError("invalid WAV")
                values = struct.unpack("<" + "f" * ((len(payload) - 44) // 4), payload[44:])
                left, right = values[::2], values[1::2]
                if len(left) != record["frames"] or len(left) < 256:
                    raise AssertionError("wrong frame count")
                if not all(abs(l + r) < 1e-7 for l, r in zip(left, right)):
                    raise AssertionError("stereo polarity changed")
                if not all(round((b - a) * 1000) in (1, -999) for a, b in zip(left, left[1:])):
                    raise AssertionError("PCM discontinuity")
                if ((record["end_frame"] - record["start_frame"]) & 0xffffffff) != record["frames"]:
                    raise AssertionError("sample timestamp mismatch")
                record["wav_sha256"] = hashlib.sha256(payload).hexdigest()
                record["passed"] = True
            except Exception as error:
                record["failure"] = str(error)
            finally:
                if injector is not None:
                    injector.terminate()
                    try:
                        injector.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        injector.kill()
                        injector.wait(timeout=3)
                    record["injector_stderr"] = injector.stderr.read()
                    injector.stderr.close()
                if capture:
                    lib.rd_capture_destroy(capture)
                record["routing_restored"] = ports() == before
                record["passed"] = record["passed"] and record["routing_restored"]
                results.append(record)
            if not record["passed"]:
                break
    report = {"schema_version": 1, "scope": "RD-01 native capture spike only",
              "profile": "physical-norns-owned-JACK-injection", "physical_adc_tested": False,
              "grid_latency_tested": False, "analysis_performance_tested": False,
              "library_sha256": hashlib.sha256(Path(library).read_bytes()).hexdigest(),
              "injector_sha256": hashlib.sha256(Path(injector_binary).read_bytes()).hexdigest(),
              "architecture": os.uname().machine, "trials": results,
              "process_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              "routing_restored": ports() == initial,
              "passed": len(results) == 3 and all(r["passed"] for r in results) and ports() == initial}
    Path(output).write_text(json.dumps(report, indent=2) + "\n")
    return int(not report["passed"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--injector", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.library, args.injector, args.output))
