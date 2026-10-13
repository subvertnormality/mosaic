"""Fail-closed Rhythm Doctor device performance acceptance.

This validates measurement reports, not the authenticity of their observations.
Callers must retain the hashed raw device evidence and bind it to deployed source.
"""
import math
import re

NUMBERS = ("analysis_tail_ms", "peak_incremental_rss_bytes", "ui_response_ms",
           "scroll_response_ms", "capture_start_ms", "xruns", "duration_seconds", "bpm")
FLAGS = ("routing_changed", "transport_start_delayed", "playback_regressed",
         "all_five_lanes_ready")
HASH = re.compile(r"[0-9a-fA-F]{64}\Z")


def evaluate(measurements):
    rows = list(measurements)
    errors = []
    identities = set()
    revisions = set()
    devices = set()
    backend_hashes = set()
    drum_hashes = set()
    bass_hashes = set()
    groups = {"warm": [], "cold": []}
    for index, row in enumerate(rows):
        prefix = "measurement %d: " % index
        if not isinstance(row, dict):
            errors.append(prefix + "invalid record")
            continue
        invalid = False
        for name in NUMBERS:
            value = row.get(name)
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                errors.append(prefix + "missing/invalid " + name)
                invalid = True
        for name in FLAGS:
            if type(row.get(name)) is not bool:
                errors.append(prefix + "missing/invalid " + name)
                invalid = True
        for name in ("source_sha256", "raw_evidence_sha256", "backend_sha256", "drum_artifact_sha256", "bass_artifact_sha256"):
            if not isinstance(row.get(name), str) or not HASH.fullmatch(row[name]):
                errors.append(prefix + "missing/invalid " + name)
                invalid = True
        if row.get("profile") != "norns" or not isinstance(row.get("device_id"), str) or not row["device_id"]:
            errors.append(prefix + "matching physical Norns evidence required")
        if row.get("temperature") not in groups:
            errors.append(prefix + "cold/warm classification required")
            invalid = True
        if invalid:
            continue
        identity = row["raw_evidence_sha256"].lower()
        if identity in identities:
            errors.append(prefix + "duplicate evidence")
        identities.add(identity)
        revisions.add(row["source_sha256"].lower())
        backend_hashes.add(row["backend_sha256"].lower())
        drum_hashes.add(row["drum_artifact_sha256"].lower())
        bass_hashes.add(row["bass_artifact_sha256"].lower())
        devices.add(row.get("device_id"))
        if not 40 <= row["bpm"] <= 240 or not 960 / row["bpm"] <= row["duration_seconds"] <= 45:
            errors.append(prefix + "unsupported capture envelope")
        if row["xruns"] != 0 or any(row[name] for name in FLAGS[:3]) or not row["all_five_lanes_ready"]:
            errors.append(prefix + "unconditional audio/transport/readiness blocker")
        if row["peak_incremental_rss_bytes"] > 256 * 1024 * 1024:
            errors.append(prefix + "incremental RSS exceeds 256 MiB")
        # Capture origin is a per-press bound, not a percentile that can hide a shifted first beat.
        if row["capture_start_ms"] > 10:
            errors.append(prefix + "capture start exceeds 10 ms target")
        full = row["duration_seconds"] == 45
        limit = (5000 if full else 2000) if row["temperature"] == "warm" else (10000 if full else 5000)
        groups[row["temperature"]].append((row, row["analysis_tail_ms"] / limit))
    if len(revisions) != 1 or len(devices) != 1 or len(backend_hashes) != 1 or len(drum_hashes) != 1 or len(bass_hashes) != 1:
        errors.append("measurement source, device, backend and pretrained artifacts must each have one identity")
    for temperature, minimum in (("warm", 30), ("cold", 5)):
        group = groups[temperature]
        if len(group) < minimum:
            errors.append("need at least %d %s acquisitions" % (minimum, temperature))
        if not group:
            continue
        # Four-bar and full-buffer measurements have separate latency targets;
        # pooling ratios can conceal a failing duration class in a larger class.
        for full in (False, True):
            ratios = sorted(ratio for row, ratio in group
                            if (row["duration_seconds"] == 45) == full)
            if not ratios:
                errors.append(temperature + (" full-buffer" if full else " shorter-buffer") + " measurements missing")
                continue
            ratio = ratios[math.ceil(len(ratios) * .95) - 1] if temperature == "warm" else ratios[-1]
            if ratio > 1:
                errors.append(temperature + (" full-buffer" if full else " shorter-buffer")
                              + " analysis tail exceeds declared limit")
    for field in ("ui_response_ms", "scroll_response_ms"):
        samples = sorted(row[field] for group in groups.values() for row, _ in group)
        if not samples or samples[math.ceil(len(samples) * .95) - 1] > 100:
            errors.append(field + " p95 exceeds 100 ms or has no observations")
    bpms = {row["bpm"] for group in groups.values() for row, _ in group}
    if not {40, 60, 120, 180, 240}.issubset(bpms):
        errors.append("missing BPM envelope coverage")
    return {"passed": not errors, "errors": errors, "measurement_count": len(rows),
            "hardware_evidence_authenticated": False, "metrics_gate_passed": not errors, "limits_version": "rhythm-doctor-plan-2026-09-18"}
