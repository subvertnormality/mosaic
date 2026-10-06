"""Strict explicit adoption of one complete controlled-local standalone audio report.

The report itself is never rewritten. Adoption skips only the musical-audio-assets
producer; the normal raw and final publication audits still run.
"""
import hashlib
import json
from pathlib import Path

PROOF_NAME = "audio-report-adoption.json"
REPORT_RELATIVE = "manual/generated/audio-scenes.json"
SOURCE_PATHS = (
    "manual/audio-scenes.yaml",
    "manual/audio.schema.json",
    "tools/manual_audio.py",
    "tools/manual_capture.py",
    "tools/manual_audio_setups.py",
    "tools/manual_audio_resume.py",
    "tools/manual_audio_origin_audit.py",
    "tools/manual_publication_verify.py",
)

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def _source_hashes(root, report):
    paths = set(SOURCE_PATHS)
    for name in report.get("harness_sha256", {}):
        if Path(name).name != name or not name.endswith(".cjs"):
            raise ValueError("Unsafe audio harness identity")
        paths.add("tests/behaviour/" + name)
    return {name: digest(Path(root) / name) for name in sorted(paths)}

def prepare_audio_report_adoption(report_path, expected_sha256, root, evidence):
    """Run the strict existing full audio/session audits and create an immutable receipt."""
    root = Path(root).resolve()
    evidence = Path(evidence).resolve()
    report_path = Path(report_path).resolve()
    published = root / REPORT_RELATIVE
    if not report_path.is_file() or digest(report_path) != expected_sha256:
        raise ValueError("Audio adoption report SHA256 does not match the explicit pin")
    if not published.is_file() or digest(published) != expected_sha256 or report_path.read_bytes() != published.read_bytes():
        raise ValueError("Audio adoption report is not the exact current published report")
    import manual_audio
    import manual_publication_verify
    audit = manual_audio.audit_controlled_publication(report_path)
    session_audit = manual_publication_verify.audit_audio_session_integrity(
        report_path, controlled_local=True
    )
    report = json.loads(report_path.read_text())
    if report.get("passed") is not True or report.get("complete_regression_run") is not False:
        raise ValueError("Audio adoption requires a passed controlled report with complete_regression_run=false")
    if report.get("validation_scope") != "controlled-manual-generation" or report.get("realtime_qualification") != "pending-ci":
        raise ValueError("Audio adoption report has the wrong qualification scope")
    if report.get("clock_mode") != "controlled-experimental" or report.get("audio_capture_clock_mode") != "real-time":
        raise ValueError("Audio adoption report has the wrong clock identity")
    proof = {
        "schema_version": 1,
        "kind": "complete-controlled-audio-report-adoption",
        "report": {"path": str(report_path), "sha256": expected_sha256},
        "published_report": {"path": str(published.resolve()), "sha256": expected_sha256},
        "audit": audit,
        "session_audit": session_audit,
        "source_files": _source_hashes(root, report),
        "adoption_tool_sha256": digest(Path(__file__)),
        "builder_sha256": digest(root / "tools/manual_build.py"),
    }
    proof_path = evidence / PROOF_NAME
    with proof_path.open("x") as handle:
        json.dump(proof, handle, indent=2)
        handle.write("\n")
    if digest(report_path) != expected_sha256 or digest(published) != expected_sha256:
        raise ValueError("Audio adoption report changed during verification")
    return {
        "name": "musical-audio-assets",
        "passed": True,
        "returncode": 0,
        "execution_status": "adopted-verified",
        "native_report": {"path": str(report_path), "sha256": expected_sha256},
        "audio_adoption_proof": {"path": str(proof_path), "sha256": digest(proof_path)},
        "adopted_from": {
            "report_sha256": expected_sha256,
            "proof_sha256": digest(proof_path),
        },
    }

def audit_build_audio_adoption(build_evidence, manifest, root):
    """Recheck adoption lineage and the complete current audio publication at final audit."""
    build = Path(build_evidence).resolve()
    root = Path(root).resolve()
    stages = [row for row in manifest.get("stages", []) if row.get("name") == "musical-audio-assets"]
    audio_marker = manifest.get("audio_adoption")
    adopted = [row for row in stages if row.get("execution_status") == "adopted-verified"]
    if not audio_marker and not adopted:
        return None
    if len(stages) != 1 or len(adopted) != 1 or not isinstance(audio_marker, dict):
        raise ValueError("Audio adoption marker and stage receipt must be present exactly once")
    proof_path = (build / audio_marker.get("path", "")).resolve()
    if proof_path != build / PROOF_NAME or not proof_path.is_file() or digest(proof_path) != audio_marker.get("sha256"):
        raise ValueError("Audio adoption proof changed or is missing")
    proof = json.loads(proof_path.read_text())
    if proof.get("schema_version") != 1 or proof.get("kind") != "complete-controlled-audio-report-adoption":
        raise ValueError("Unsupported audio adoption proof")
    source_path = Path(proof["report"]["path"]).resolve()
    published = root / REPORT_RELATIVE
    sha = proof["report"]["sha256"]
    if proof.get("published_report") != {"path": str(published.resolve()), "sha256": sha}:
        raise ValueError("Adoption proof names a different published audio report")
    if digest(source_path) != sha or digest(published) != sha or source_path.read_bytes() != published.read_bytes():
        raise ValueError("Adopted audio report or current publication changed")
    record_path = build / "musical-audio-assets.json"
    if not record_path.is_file() or json.loads(record_path.read_text()) != stages[0]:
        raise ValueError("Adopted audio stage receipt changed")
    record = stages[0]
    if record.get("native_report") != {"path": str(source_path), "sha256": sha}:
        raise ValueError("Adopted audio report identity differs from stage receipt")
    if record.get("audio_adoption_proof") != {"path": str(proof_path), "sha256": digest(proof_path)}:
        raise ValueError("Adopted audio proof identity differs from stage receipt")
    import manual_audio
    import manual_publication_verify
    current_report = json.loads(source_path.read_text())
    if proof.get("source_files") != _source_hashes(root, current_report):
        raise ValueError("Audio adoption source identity changed after verification")
    if proof.get("adoption_tool_sha256") != digest(Path(__file__)) or proof.get("builder_sha256") != digest(root / "tools/manual_build.py"):
        raise ValueError("Audio adoption producer identity changed after verification")
    audit = manual_audio.audit_controlled_publication(source_path)
    session_audit = manual_publication_verify.audit_audio_session_integrity(
        source_path, controlled_local=True
    )
    if digest(source_path) != sha or digest(published) != sha or proof.get("source_files") != _source_hashes(root, current_report):
        raise ValueError("Audio report or source changed during final adoption audit")
    return {"audio": audit, "sessions": session_audit}
