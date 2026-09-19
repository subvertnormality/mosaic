"""Validation of the external, independently referenced RD-02 corpus.

The corpus is deliberately outside the repository: a manifest identifies every
audio and annotation byte by SHA-256, and this module refuses to score a corpus
whose provenance or split is incomplete.  This is characterisation evidence for
the acceptance gates in docs/rhythm-doctor/PLAN.md, not Mosaic user behaviour.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path, PureWindowsPath
from typing import Any


LANES = ("BD", "SD", "HH", "TOM", "BASS")
FOUR_BAR_STRATA = ("isolated", "sparse", "full_mix")
REFERENCE_ORIGINS = ("independent_human", "independent_render_metadata")
REQUIRED_ACQUISITION_TAGS = {
    "random_record_phase", "silence_or_intro", "syncopation",
    "half_double_ambiguous", "changing_tempo", "uncertain_downbeat",
}
REQUIRED_ACQUISITION_BPM = {40, 60, 120, 180, 240}


class CorpusValidationError(ValueError):
    """The external corpus cannot establish the RD-02 acceptance premise."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_keys(value: dict[str, Any], expected: set[str], context: str) -> None:
    actual = set(value)
    missing, unexpected = expected - actual, actual - expected
    if missing or unexpected:
        raise CorpusValidationError(
            f"{context} schema mismatch; missing={sorted(missing)}, "
            f"unexpected={sorted(unexpected)}"
        )


def _relative_file(root: Path, descriptor: dict[str, Any], context: str) -> Path:
    _require_keys(descriptor, {"path", "sha256"}, context)
    rel, digest = descriptor["path"], descriptor["sha256"]
    if (not isinstance(rel, str) or not rel or Path(rel).is_absolute()
            or PureWindowsPath(rel).drive or ".." in Path(rel).parts
            or ".." in PureWindowsPath(rel).parts):
        raise CorpusValidationError(f"{context} path must be a non-empty relative path")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise CorpusValidationError(f"{context} sha256 must be lowercase hexadecimal")
    root = root.resolve()
    path = (root / rel).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise CorpusValidationError(f"{context} path escapes corpus root") from exc
    if not path.is_file():
        raise CorpusValidationError(f"{context} missing: {rel}")
    if _sha256(path) != digest:
        raise CorpusValidationError(f"{context} hash mismatch: {rel}")
    return path


def _annotation(path: Path, clip_id: str) -> dict[str, list[dict[str, Any]]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CorpusValidationError(f"{clip_id} annotation is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise CorpusValidationError(f"{clip_id} annotation must be an object")
    _require_keys(value, {"reference_origin", "annotator_id", "events"}, f"{clip_id} annotation")
    if value["reference_origin"] not in REFERENCE_ORIGINS:
        raise CorpusValidationError(f"{clip_id} annotation is not independent reference evidence")
    if not isinstance(value["annotator_id"], str) or not value["annotator_id"]:
        raise CorpusValidationError(f"{clip_id} annotation lacks an annotator identity")
    events = value["events"]
    if not isinstance(events, dict) or set(events) != set(LANES):
        raise CorpusValidationError(f"{clip_id} annotation must have exactly the five lanes")
    for lane, lane_events in events.items():
        if not isinstance(lane_events, list):
            raise CorpusValidationError(f"{clip_id} {lane} events must be a list")
        previous = -1.0
        for event in lane_events:
            if not isinstance(event, dict):
                raise CorpusValidationError(f"{clip_id} {lane} event must be an object")
            _require_keys(event, {"time_seconds", "velocity"}, f"{clip_id} {lane} event")
            time, velocity = event["time_seconds"], event["velocity"]
            if isinstance(time, bool) or not isinstance(time, (int, float)) or not math.isfinite(time) or time < 0:
                raise CorpusValidationError(f"{clip_id} {lane} has an invalid onset time")
            if type(velocity) is not int or not 1 <= velocity <= 127:
                raise CorpusValidationError(f"{clip_id} {lane} has an invalid MIDI velocity")
            if time < previous:
                raise CorpusValidationError(f"{clip_id} {lane} events must be ordered")
            previous = time
    return events


def _timbre_evidence(path: Path, clip_id: str, timbres: dict[str, str]) -> None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CorpusValidationError(f"{clip_id} timbre evidence is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise CorpusValidationError(f"{clip_id} timbre evidence must be an object")
    _require_keys(value, {"lanes"}, f"{clip_id} timbre evidence")
    lanes = value["lanes"]
    if not isinstance(lanes, dict) or set(lanes) != set(LANES):
        raise CorpusValidationError(f"{clip_id} timbre evidence must cover exactly the five lanes")
    for lane, evidence in lanes.items():
        if not isinstance(evidence, dict):
            raise CorpusValidationError(f"{clip_id} {lane} timbre evidence must be an object")
        _require_keys(evidence, {"timbre", "basis", "source"}, f"{clip_id} {lane} timbre evidence")
        if evidence["timbre"] != timbres[lane] or evidence["basis"] not in {"source_patch_metadata", "source_render_spec", "independent_audition"} or not isinstance(evidence["source"], str) or not evidence["source"]:
            raise CorpusValidationError(f"{clip_id} {lane} timbre label lacks matching source-backed evidence")


def _clip(value: dict[str, Any], root: Path) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    expected = {
        "id", "split", "source_id", "source_song_id", "kit_id", "source_start_seconds", "render", "audio", "annotation", "timbre_evidence",
        "duration_seconds", "bpm", "stratum", "timbres", "tags",
    }
    actual = set(value)
    missing, unexpected = expected - actual, actual - expected - {"additional_source_ids"}
    if missing or unexpected:
        raise CorpusValidationError(
            f"clip schema mismatch; missing={sorted(missing)}, unexpected={sorted(unexpected)}"
        )
    clip_id = value["id"]
    if not isinstance(clip_id, str) or not clip_id:
        raise CorpusValidationError("clip id must be a non-empty string")
    if value["split"] not in {"development", "held_out", "acquisition"}:
        raise CorpusValidationError(f"{clip_id} has an invalid split")
    for field in ("source_id", "source_song_id", "kit_id"):
        if not isinstance(value[field], str) or not value[field]:
            raise CorpusValidationError(f"{clip_id} lacks {field}")
    additional = value.get("additional_source_ids", [])
    if (not isinstance(additional, list) or any(not isinstance(item, str) or not item for item in additional)
            or len(set(additional)) != len(additional) or value["source_id"] in additional):
        raise CorpusValidationError(f"{clip_id} has invalid additional_source_ids")
    source_start = value["source_start_seconds"]
    if isinstance(source_start, bool) or not isinstance(source_start, (int, float)) or not math.isfinite(source_start) or source_start < 0:
        raise CorpusValidationError(f"{clip_id} has invalid source_start_seconds")
    duration, bpm = value["duration_seconds"], value["bpm"]
    if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0:
        raise CorpusValidationError(f"{clip_id} has invalid duration_seconds")
    if isinstance(bpm, bool) or not isinstance(bpm, (int, float)) or not math.isfinite(bpm) or not 40 <= bpm <= 240:
        raise CorpusValidationError(f"{clip_id} has invalid bpm")
    if value["split"] == "acquisition":
        if duration > 45:
            raise CorpusValidationError(f"{clip_id} acquisition fixture exceeds 45 seconds")
    else:
        if value["stratum"] not in FOUR_BAR_STRATA:
            raise CorpusValidationError(f"{clip_id} has invalid four-bar stratum")
        expected_duration = 960 / bpm
        if abs(duration - expected_duration) > 0.005:
            raise CorpusValidationError(f"{clip_id} is not an exact four-bar fixture")
    timbres = value["timbres"]
    if not isinstance(timbres, dict) or set(timbres) != set(LANES) or any(v not in {"acoustic", "electronic", "unverified"} for v in timbres.values()):
        raise CorpusValidationError(f"{clip_id} must declare acoustic/electronic/unverified timbre for every lane")
    _timbre_evidence(_relative_file(root, value["timbre_evidence"], f"{clip_id} timbre evidence"), clip_id, timbres)
    render = value["render"]
    if not isinstance(render, dict) or set(render) != {"kind", "recipe"} or render["kind"] not in {"source_mix", "frozen_submix", "isolated_stem"}:
        raise CorpusValidationError(f"{clip_id} must declare its frozen render kind and recipe")
    _relative_file(root, render["recipe"], f"{clip_id} render recipe")
    if not isinstance(value["tags"], list) or any(not isinstance(tag, str) for tag in value["tags"]):
        raise CorpusValidationError(f"{clip_id} tags must be strings")
    _relative_file(root, value["audio"], f"{clip_id} audio")
    annotation = _annotation(_relative_file(root, value["annotation"], f"{clip_id} annotation"), clip_id)
    if any(event["time_seconds"] >= duration for events in annotation.values() for event in events):
        raise CorpusValidationError(f"{clip_id} annotation exceeds clip duration")
    return value, annotation


def validate_manifest(manifest_path: str | Path, corpus_root: str | Path | None = None) -> dict[str, Any]:
    """Validate an external corpus manifest and return audited aggregate counts.

    ``corpus_root`` defaults to the directory containing the manifest.  Every
    referenced byte must live below that root; no copied audio is expected in git.
    """
    manifest_path = Path(manifest_path)
    root = Path(corpus_root) if corpus_root is not None else manifest_path.parent
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CorpusValidationError("manifest is not valid UTF-8 JSON") from exc
    if not isinstance(manifest, dict):
        raise CorpusValidationError("manifest must be an object")
    _require_keys(manifest, {"schema_version", "corpus_id", "sources", "clips"}, "manifest")
    if manifest["schema_version"] != 1 or not isinstance(manifest["corpus_id"], str) or not manifest["corpus_id"]:
        raise CorpusValidationError("unsupported or anonymous corpus manifest")
    if not isinstance(manifest["sources"], list) or not manifest["sources"]:
        raise CorpusValidationError("manifest needs at least one licensed source")
    source_ids = set()
    for source in manifest["sources"]:
        if not isinstance(source, dict):
            raise CorpusValidationError("source must be an object")
        _require_keys(source, {"id", "record_url", "license", "archive", "license_evidence", "domain"}, "source")
        if not isinstance(source["id"], str) or not source["id"] or source["id"] in source_ids:
            raise CorpusValidationError("source ids must be unique non-empty strings")
        source_ids.add(source["id"])
        if source["domain"] not in {"rendered", "recorded"}:
            raise CorpusValidationError(f"{source['id']} must declare recorded or rendered source domain")
        if not isinstance(source["record_url"], str) or not source["record_url"].startswith("https://"):
            raise CorpusValidationError(f"{source['id']} lacks an immutable HTTPS source record")
        license_ = source["license"]
        if (not isinstance(license_, dict) or license_.get("spdx") not in {"CC-BY-4.0", "CC0-1.0", "GPL-2.0"}
                or not isinstance(license_.get("url"), str)):
            raise CorpusValidationError(f"{source['id']} must declare an approved pinned license with a URL")
        _relative_file(root, source["archive"], f"{source['id']} archive")
        _relative_file(root, source["license_evidence"], f"{source['id']} license evidence")
    if not isinstance(manifest["clips"], list):
        raise CorpusValidationError("manifest clips must be a list")
    clips, annotations, clip_ids = [], {}, set()
    for raw in manifest["clips"]:
        if not isinstance(raw, dict):
            raise CorpusValidationError("clip must be an object")
        clip, annotation = _clip(raw, root)
        if clip["id"] in clip_ids:
            raise CorpusValidationError(f"duplicate clip id: {clip['id']}")
        if clip["source_id"] not in source_ids:
            raise CorpusValidationError(f"{clip['id']} references an unknown source")
        for source_id in clip.get("additional_source_ids", []):
            if source_id not in source_ids:
                raise CorpusValidationError(f"{clip['id']} references an unknown additional source")
        clip_ids.add(clip["id"]); clips.append(clip); annotations[clip["id"]] = annotation
    partitions = {split: [clip for clip in clips if clip["split"] == split] for split in ("development", "held_out", "acquisition")}
    if len(partitions["development"]) < 40 or len(partitions["held_out"]) < 40:
        raise CorpusValidationError("need at least 40 development and 40 held-out four-bar clips")
    dev_songs = {clip["source_song_id"] for clip in partitions["development"]}
    held_songs = {clip["source_song_id"] for clip in partitions["held_out"]}
    dev_kits = {clip["kit_id"] for clip in partitions["development"]}
    held_kits = {clip["kit_id"] for clip in partitions["held_out"]}
    if dev_songs & held_songs:
        raise CorpusValidationError("development and held-out source songs overlap")
    if dev_kits & held_kits:
        raise CorpusValidationError("development and held-out kits overlap")
    for song, song_clips in defaultdict(list, {
        song: [clip for clip in clips if clip["source_song_id"] == song]
        for song in {clip["source_song_id"] for clip in clips}
    }).items():
        intervals = sorted((clip["source_start_seconds"], clip["duration_seconds"], clip["id"]) for clip in song_clips)
        for (start, duration, clip_id), (next_start, next_duration, next_id) in zip(intervals, intervals[1:]):
            # A frozen stem/submix may intentionally derive from the exact same
            # source span as its full mix.  It is one unique base span, not a
            # neighbouring segment or extra development/held-out provenance.
            if abs(next_start - start) <= 0.005 and abs(next_duration - duration) <= 0.005:
                continue
            if next_start - (start + duration) <= 0.005:
                raise CorpusValidationError(
                    f"{song} contains overlapping or adjacent source clips: {clip_id}, {next_id}"
                )
    tags = Counter(tag for clip in clips for tag in clip["tags"])
    if any(tags[tag] == 0 for tag in ("clipping", "phase_inverted_stereo", "kick_bass_unison")):
        raise CorpusValidationError("missing declared clipping, phase-inverted stereo, or kick+bass-unison control")
    silence = [clip for clip in clips if "silence" in clip["tags"]]
    if len(silence) < 3 or any(any(annotations[clip["id"]][lane] for lane in LANES) for clip in silence):
        raise CorpusValidationError("need three annotated silence clips")
    held = partitions["held_out"]
    # Distinct held source-song identities must bring distinct PCM evidence.
    # Silence controls are an explicit exception: their shared all-zero bytes
    # are not musical examples and never count toward the 40 base clips.
    held_audio = defaultdict(list)
    for clip in held:
        if "silence" not in clip["tags"]:
            held_audio[clip["audio"]["sha256"]].append(clip["id"])
    repeated_audio = [ids for ids in held_audio.values() if len(ids) > 1]
    if repeated_audio:
        raise CorpusValidationError(
            f"held-out non-silence PCM is duplicated: {repeated_audio[0]}"
        )
    for lane in LANES:
        positives = [clip for clip in held if annotations[clip["id"]][lane]]
        if len(positives) < 10:
            raise CorpusValidationError(f"held-out {lane} has fewer than 10 positive clips")
        if sum(len(annotations[clip["id"]][lane]) for clip in positives) < 50:
            raise CorpusValidationError(f"held-out {lane} has fewer than 50 reference events")
        by_stratum = Counter(clip["stratum"] for clip in positives)
        if by_stratum["full_mix"] < 5 or by_stratum["sparse"] < 2 or by_stratum["isolated"] < 2:
            raise CorpusValidationError(f"held-out {lane} lacks required full/sparse/isolated strata")
        if not {"acoustic", "electronic"} <= {clip["timbres"][lane] for clip in positives}:
            raise CorpusValidationError(f"held-out {lane} lacks acoustic or electronic timbre")
        if sum(not annotations[clip["id"]][lane] for clip in held) < 5:
            raise CorpusValidationError(f"held-out {lane} has fewer than five absent-lane negatives")
    acquisition_tags = {tag for clip in partitions["acquisition"] for tag in clip["tags"]}
    acquisition_bpms = {clip["bpm"] for clip in partitions["acquisition"]}
    if not REQUIRED_ACQUISITION_TAGS <= acquisition_tags:
        raise CorpusValidationError("acquisition fixtures miss required scenario tags")
    if not REQUIRED_ACQUISITION_BPM <= acquisition_bpms:
        raise CorpusValidationError("acquisition fixtures miss required BPM envelope")
    return {
        "development_clips": len(partitions["development"]),
        "held_out_clips": len(partitions["held_out"]),
        "acquisition_clips": len(partitions["acquisition"]),
        "held_out_positive_clips": {lane: sum(bool(annotations[clip["id"]][lane]) for clip in held) for lane in LANES},
        "held_out_events": {lane: sum(len(annotations[clip["id"]][lane]) for clip in held) for lane in LANES},
    }
