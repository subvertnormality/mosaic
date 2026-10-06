"""Strict path/origin binding for resumed mixed-origin audio session audits."""
from pathlib import Path
import json
import os

class OriginAuditError(ValueError):
    pass

def resolve_capture_origins(session_refs, evidence_aliases, original_run, resumed_run):
    """Map each raw current-report path to precisely its verified old or fresh run."""
    old_run = Path(original_run).resolve(strict=True)
    new_run = Path(resumed_run).resolve(strict=True)
    if old_run == new_run:
        raise OriginAuditError("audio resume origins must be distinct")
    if not isinstance(evidence_aliases, dict) or not evidence_aliases:
        raise OriginAuditError("missing verified audio evidence aliases")
    resolved = []
    for raw_value, captured_path in session_refs:
        raw = Path(os.path.abspath(str(raw_value)))
        try:
            captured = Path(captured_path).resolve(strict=True)
        except OSError as error:
            raise OriginAuditError("missing audio session path") from error
        alias_source = evidence_aliases.get(str(raw))
        if alias_source is not None:
            source = Path(alias_source).resolve(strict=True)
            if source.parent != old_run or captured != source:
                raise OriginAuditError("reused session alias does not bind to its exact original capture")
            try:
                relative = raw.relative_to(new_run)
            except ValueError as error:
                raise OriginAuditError("reused session alias escapes the resumed run") from error
            if not relative.parts:
                raise OriginAuditError("reused session alias is not a capture directory")
            link = new_run / relative.parts[0]
            target = old_run / relative.parts[0]
            if not link.is_symlink() or link.resolve(strict=True) != target.resolve(strict=True):
                raise OriginAuditError("reused session alias link differs from its pinned origin")
            if raw.resolve(strict=True) != source:
                raise OriginAuditError("reused session alias resolves to a different original")
            resolved.append((captured, old_run, "reused"))
            continue
        if captured == old_run or old_run in captured.parents:
            raise OriginAuditError("historical audio session is missing its exact provenance alias")
        if raw.is_symlink() or raw.parent.resolve(strict=True) != new_run or captured.parent != new_run:
            raise OriginAuditError("fresh audio session escapes its declared resumed run")
        resolved.append((captured, new_run, "fresh"))
    if len({item[0] for item in resolved}) != len(resolved):
        raise OriginAuditError("audio session paths are duplicated across origins")
    return resolved

def rewrite_origin_paths(value, aliases):
    """Rewrite absolute path fields from a pinned old row to its verified alias."""
    reverse = {str(Path(source).resolve(strict=True)): alias for alias, source in aliases.items()}
    def visit(item):
        if isinstance(item, dict):
            result = {}
            for key, child in item.items():
                if key == "path" and isinstance(child, str) and os.path.isabs(child):
                    try:
                        source = str(Path(child).resolve(strict=True))
                    except OSError as error:
                        raise OriginAuditError("historical row path is absent from verified aliases") from error
                    if source not in reverse:
                        raise OriginAuditError("historical row path is absent from verified aliases")
                    result[key] = reverse[source]
                else:
                    result[key] = visit(child)
            return result
        if isinstance(item, list):
            return [visit(child) for child in item]
        return item
    return visit(value)

def audit_resumed_audio_sessions(module, report, authored, sessions, session_examples, run, resume_audit):
    """Audit every session against its pinned old or fresh origin root.

    The caller must run manual_audio_resume.audit_resume_provenance first. That
    validator binds the durable marker, original report, exact alias map, reused
    rows, and the reviewed old/current helper transition.
    """
    if not isinstance(resume_audit, dict) or resume_audit.get("passed") is not True:
        raise OriginAuditError("strict audio resume provenance audit was not completed")
    provenance = report.get("resume_provenance")
    if not isinstance(provenance, dict) or provenance.get("kind") not in ("strict-partial-audio-resume", "strict-same-lineage-audio-resume"):
        raise OriginAuditError("mixed-origin audit requires approved strict resume provenance")
    new_run = Path(run).resolve(strict=True)
    old_run = Path(provenance["original_run"]).resolve(strict=True)
    aliases = provenance.get("evidence_aliases")
    refs = []
    examples = report.get("examples", [])
    by_authored = {item["id"]: item for item in authored.get("examples", [])}
    if len(by_authored) != len(authored.get("examples", [])) or {row.get("id") for row in examples} != set(by_authored):
        raise OriginAuditError("resumed audio inventory does not match authored inventory")
    for example in examples:
        source = by_authored[example["id"]]
        tracks = source["tracks"]
        records = [(example, tracks)] + [
            (solo, [next(track for track in tracks if track["channel"] == solo["channel"])])
            for solo in example.get("solo_contributions", [])
        ]
        for record, selected in records:
            refs.append((example["id"], record["evidence"]["path"], Path(record["evidence"]["path"]).resolve(strict=True), "real-time", True))
        if source.get("purpose") == "lesson-comparison":
            for lane in example.get("musical_evidence", []):
                refs.append((example["id"], lane["path"], Path(lane["path"]).resolve(strict=True), lane["clock_mode"], False))
    if len(refs) != len(sessions) or any(
        refs[index][2] != sessions[index][0] or refs[index][3:] != sessions[index][1:]
        for index in range(len(refs))
    ):
        raise OriginAuditError("report session paths differ from the strict authored session inventory")
    reused_ids = set(provenance.get("reused_ids", []))
    if not reused_ids or not reused_ids <= set(by_authored):
        raise OriginAuditError("invalid resumed reused-id declaration")
    origins = resolve_capture_origins(
        [(raw, resolved) for _, raw, resolved, _, _ in refs],
        aliases,
        old_run,
        new_run,
    )
    for ref, origin in zip(refs, origins):
        expected_kind = "reused" if ref[0] in reused_ids else "fresh"
        if origin[2] != expected_kind:
            raise OriginAuditError("capture origin relabels reused/fresh example: " + ref[0])
    original_report_path = Path(provenance["original_report"]).resolve(strict=True)
    original_report = json.loads(original_report_path.read_text())
    original_rows = {row["id"]: row for row in original_report.get("examples", [])}
    fresh_baseline_path = new_run / "audio-scenes.json"
    if not fresh_baseline_path.is_file():
        raise OriginAuditError("fresh resumed run has no immutable native report baseline")
    fresh_baseline = json.loads(fresh_baseline_path.read_text())
    if fresh_baseline.get("passed") is not True or fresh_baseline.get("source_sha256") != report.get("source_sha256"):
        raise OriginAuditError("fresh native audio baseline is not a passed same-source report")
    fresh_rows = {row["id"]: row for row in fresh_baseline.get("examples", [])}
    current_rows = {row["id"]: row for row in examples}
    if len(current_rows) != len(examples):
        raise OriginAuditError("duplicate audio report example id")
    fields = ("musical_evidence", "midi_witness", "phase_observations", "lesson_pcm", "course_before_after")
    for ident, current in current_rows.items():
        baseline_rows = original_rows if ident in reused_ids else fresh_rows
        baseline = baseline_rows.get(ident)
        if baseline is None:
            raise OriginAuditError("missing per-origin immutable audio baseline: " + ident)
        if ident in reused_ids:
            baseline = rewrite_origin_paths(baseline, aliases)
        for field in fields:
            if (field in current) != (field in baseline) or current.get(field) != baseline.get(field):
                raise OriginAuditError("musical evidence differs from its immutable origin row: " + ident + "." + field)
    fresh_origins = [origin for origin in origins if origin[2] == "fresh"]
    if fresh_origins:
        from manual_publication_verify import digest
        for name, key, current_path in (
            ("capture-tool.py", "tool_sha256", module.ROOT / "tools/manual_audio.py"),
            ("capture-helpers.py", "helper_sha256", module.ROOT / "tools/manual_capture.py"),
            ("capture-setups.py", "setups_sha256", module.ROOT / "tools/manual_audio_setups.py"),
        ):
            frozen = new_run / name
            if not frozen.is_file() or digest(current_path) != report.get(key) or digest(frozen) != report.get(key):
                raise OriginAuditError("fresh audio origin has stale frozen source: " + key)
    for (out, clock, voices), (_, origin, kind) in zip(sessions, origins):
        module.check_audio_native_session(out, clock, voices)
        identity = json.loads((out / "native/identity.json").read_text())
        application = identity["application_identity"]
        code_root = Path(application["code_root"])
        expected_application = (origin / "application").resolve(strict=True)
        if module.capture_application_root(out) != expected_application:
            raise OriginAuditError("audio participant application root differs from its declared origin")
        for item in application["files"]:
            relative = Path(item["path"])
            if relative.parts[0] == "mosaic" and (code_root / relative).resolve() != expected_application.joinpath(*relative.parts[1:]).resolve():
                raise OriginAuditError("audio participant source escapes its declared origin")
        results = json.loads((out / "results.json").read_text())
        observations = json.loads((out / "observations.json").read_text())
        example = session_examples[out]
        for phase in module.audio_scale_phase_rows(example, results):
            module.check_scale_phase_frame(phase, results, observations)
            binding = phase["output"]["binding"]
            state = next(value["state"] for value in observations
                if value["state"]["frame"]["sha256"] == binding["sha256"]
                and value["state"]["grid"] == phase["output"]["grid"])
            module.verify_cached_ui(
                state,
                dict(literal_header=["SCALE", "SLOT 02", "vertical_list"],
                     field=dict(layout="vertical_list", label="Root", value="D")),
                out,
            )
    full_audio_inventory = (
        len(by_authored) == 21
        and sum(len(row["tracks"]) + 1 for row in by_authored.values()) == 54
        and len(current_rows) == 21
    )
    return {
        "passed": True,
        "complete_regression_run": False,
        "all_audio_inventory_captured": full_audio_inventory,
        "observed_examples": len(current_rows),
        "expected_examples": len(by_authored),
        "origin_sessions": {
            "reused": sum(kind == "reused" for _, _, kind in origins),
            "fresh": sum(kind == "fresh" for _, _, kind in origins),
        },
        "dsp_sessions": sum(voices for _, clock, voices in sessions),
        "midi_sessions": sum(not voices for _, clock, voices in sessions),
        "hardware_timing_verified": False,
    }
