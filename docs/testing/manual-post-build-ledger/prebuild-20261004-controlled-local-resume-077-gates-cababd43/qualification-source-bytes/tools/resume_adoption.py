"""Fail-closed proof builder for controlled manual checkpoint adoption."""
import copy
import os
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SUPPORTED_PARENT_BUILDER_SHA256 = "cdf8b1cb1fdca9d6d2384e7e954acc7f992ddf6e4ca0d9e5a3b48d3cc8afd0cc"
QUALIFIED_RECONCILER_SHA256 = "c52cffddd8fd64a54b9f3043b2aaed0d96886a05d681dbb8dedc422aa168b404"
SCOPE = {"validation_scope": "controlled-manual-generation", "realtime_qualification": "pending-ci", "clock_mode": "controlled-experimental", "complete_regression_run": False}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read_json(path):
    return json.loads(Path(path).read_text())

def reconstruct_case_outputs(root, report):
    """Use the source-pinned reconciler to preserve typed/shared YAML semantics."""
    import yaml
    import_path = Path(root) / "tools/manual_reconcile_build.py"
    if not import_path.is_file() or sha(import_path) != QUALIFIED_RECONCILER_SHA256:
        raise ValueError("Qualified source-pinned YAML reconstructor changed")
    tools = str(Path(root) / "tools")
    for entry in (tools, str(import_path.parent)):
        if entry not in sys.path:
            sys.path.insert(0, entry)
    spec = importlib.util.spec_from_file_location("pinned_manual_reconciler", str(import_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = Path(root).resolve()
    raw = (json.dumps(report, indent=2) + chr(10)).encode()
    authored = yaml.safe_dump(module.reference_authoring(copy.deepcopy(report)), sort_keys=False).encode()
    return raw, authored

def verify_case_outputs(root, output, report):
    if not output.endswith("-scenes.json") or Path(output).name != output:
        raise ValueError("Unsupported controlled reference publication name")
    raw, authored = reconstruct_case_outputs(root, report)
    paths = [Path(root) / "manual/generated" / output,
             Path(root) / "manual/features" / ("scenes-" + output[:-5] + ".yaml")]
    if any(not p.is_file() for p in paths) or paths[0].read_bytes() != raw or paths[1].read_bytes() != authored:
        raise ValueError("Current publication is not an exact reconstruction for " + output)
    return {str(p.relative_to(root)): sha(p) for p in paths}

def verify_current_native_inputs(report, stage, root):
    """Compare recorded runtime/emulator identities to current pinned inputs."""
    command = stage["command"]
    if "--experimental-install" not in command or not stage.get("emulator"):
        raise ValueError("Native stage lacks exact runtime/emulator input paths")
    install_path = Path(command[command.index("--experimental-install") + 1]).resolve()
    install = read_json(install_path)
    emulator = Path(stage["emulator"]).resolve()
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(emulator), text=True).strip()
    except Exception as error:
        raise ValueError("Current emulator revision is unavailable") from error
    checked_emulator_files = set()
    scenes = report.get("scenes", [])
    if not scenes:
        raise ValueError("Native report has no scenes to bind runtime identity")
    for scene in scenes:
        native = Path(scene["evidence"]["path"]) / "native/identity.json"
        identity = read_json(native)
        runtime = identity.get("runtime_identity", {})
        for key, value in runtime.items():
            if install.get(key) != value:
                raise ValueError("Current runtime descriptor differs at " + key)
        for binary in install.get("binaries", {}).values():
            path = Path(binary["path"])
            if not path.is_file() or sha(path) != binary["sha256"]:
                raise ValueError("Current runtime binary differs")
        interpreted = runtime.get("interpreted_files", {})
        runtime_source = Path(install.get("source", "")).resolve()
        runtime_prefix = Path(install.get("prefix", "")).resolve()
        for relative, expected in interpreted.items():
            rel = Path(relative)
            if rel.is_absolute() or ".." in rel.parts:
                raise ValueError("Unsafe interpreted runtime path")
            candidates = (runtime_source / rel, runtime_prefix / rel)
            matches = [path for path in candidates if path.is_file() and sha(path) == expected]
            if len(matches) != 1:
                raise ValueError("Current interpreted runtime file differs: " + relative)
        emulator_identity = identity.get("emulator_identity", {})
        if emulator_identity.get("revision") != revision:
            raise ValueError("Current emulator revision differs")
        for item in emulator_identity.get("files", []):
            relative = Path(item["path"])
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("Unsafe emulator identity path")
            file = emulator / relative
            key = str(file)
            if key not in checked_emulator_files:
                if not file.is_file() or sha(file) != item["sha256"] or file.stat().st_size != item["size"]:
                    raise ValueError("Current emulator source differs: " + relative.as_posix())
                checked_emulator_files.add(key)

def verify_current_doctor_inputs(report_path,stage,root):
    command=stage.get('command',[])
    if '--audio-install' not in command or not stage.get('emulator'):
        raise ValueError('Doctor stage lacks exact installation/emulator inputs')
    install=read_json(command[command.index('--audio-install')+1])
    native=Path(report_path).parent/'native/identity.json'
    identity=read_json(native)
    runtime=identity.get('runtime_identity',{})
    for key,value in runtime.items():
        if install.get(key)!=value:raise ValueError('Current Doctor runtime descriptor differs at '+key)
    for binary in install.get('binaries',{}).values():
        path=Path(binary['path'])
        if not path.is_file() or sha(path)!=binary['sha256']:raise ValueError('Current Doctor runtime binary differs')
    interpreted=runtime.get('interpreted_files',{})
    source=Path(install.get('source','')).resolve();prefix=Path(install.get('prefix','')).resolve()
    for relative,expected in interpreted.items():
        rel=Path(relative)
        if rel.is_absolute() or '..' in rel.parts:raise ValueError('Unsafe Doctor interpreted runtime path')
        matches=[path for path in (source/rel,prefix/rel) if path.is_file() and sha(path)==expected]
        if len(matches)!=1:raise ValueError('Current Doctor interpreted runtime file differs: '+relative)
    emulator=Path(stage['emulator']).resolve()
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=str(emulator),text=True).strip()
    emulator_id=identity.get('emulator_identity',{})
    if emulator_id.get('revision')!=revision:raise ValueError('Current Doctor emulator revision differs')
    for item in emulator_id.get('files',[]):
        rel=Path(item['path'])
        if rel.is_absolute() or '..' in rel.parts:raise ValueError('Unsafe Doctor emulator source path')
        path=emulator/rel
        if not path.is_file() or sha(path)!=item['sha256'] or path.stat().st_size!=item['size']:
            raise ValueError('Current Doctor emulator file differs: '+rel.as_posix())

def doctor_evidence_files(report_path):
    run=Path(report_path).resolve().parent
    files={}
    for path in sorted(run.rglob('*')):
        if path.is_symlink():
            files[str(path.relative_to(run))]={'symlink':os.readlink(path)}
        elif path.is_file():
            files[str(path.relative_to(run))]=sha(path)
    if 'report.json' not in files or 'native/identity.json' not in files:
        raise ValueError('Doctor evidence tree lacks immutable report or native identity')
    return files

def verify_adopted_doctor_stage(evidence,name,record,current_root):
    evidence=Path(evidence).resolve();current_root=Path(current_root).resolve()
    proof=read_json(evidence/'resume-adoption.json')
    item=next((x for x in proof.get('adopted',[]) if x.get('name')==name),None)
    if not item or item.get('kind')!='doctor-capture':raise ValueError('Doctor reuse lacks explicit adoption proof')
    parent_manifest=Path(proof['parent_manifest'])
    if not parent_manifest.is_file() or sha(parent_manifest)!=proof.get('parent_manifest_sha256'):
        raise ValueError('Doctor parent manifest changed')
    parent=read_json(parent_manifest)
    if parent.get("passed") is not False or parent.get("build_complete") is not False or parent.get("controlled_local") is not True or parent.get("tool_sha256") != SUPPORTED_PARENT_BUILDER_SHA256 or any(parent.get(key) != value for key,value in SCOPE.items()):
        raise ValueError("Doctor parent manifest is not the pinned failed controlled build")
    parent_row=next((x for x in parent.get('stages',[]) if x.get('name')==name),None)
    receipt=parent_manifest.parent/(name+'.json');log=parent_manifest.parent/(name+'.log')
    if not parent_row or parent_row.get("passed") is not True or parent_row.get("returncode") != 0 or not receipt.is_file() or not log.is_file() or read_json(receipt)!=parent_row:
        raise ValueError('Doctor parent receipt/log missing or changed')
    if sha(receipt)!=item.get('parent_stage_receipt_sha256') or sha(log)!=item.get('parent_log_sha256') or sha(log)!=parent_row.get('log_sha256'):
        raise ValueError('Doctor parent receipt/log hash changed')
    report_ref=parent_row.get('native_report',{})
    report_path=Path(report_ref.get('path',''))
    if not report_path.is_file() or sha(report_path)!=report_ref.get('sha256') or record.get('native_report')!=report_ref:
        raise ValueError('Doctor parent report changed')
    tree=doctor_evidence_files(report_path)
    if tree!=item.get('doctor_evidence_files') or hashlib.sha256(json.dumps(tree,sort_keys=True).encode()).hexdigest()!=item.get('doctor_evidence_tree_sha256'):
        raise ValueError('Doctor parent evidence tree changed')
    from manual_publication_verify import audit_doctor
    audit_doctor(report_path)
    verify_current_doctor_inputs(report_path,record,current_root)
    return str(report_path)

def prepare_resume(parent, root, planned_stages, *, expected_parent_manifest_sha256, current_builder_sha, producer_hashes, audit_native, proof_path, audit_doctor=None):
    """Validate current reusable stages. Caller reruns all absent/rejected stages."""
    parent, root = Path(parent).resolve(), Path(root).resolve()
    manifest_path = parent / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError("Parent run lacks terminal manifest")
    if not expected_parent_manifest_sha256 or sha(manifest_path) != expected_parent_manifest_sha256:
        raise ValueError("Parent terminal manifest does not match caller-pinned SHA256")
    manifest = read_json(manifest_path)
    if manifest.get("passed") is not False or manifest.get("build_complete") is not False:
        raise ValueError("Parent must be a terminal failed build")
    if manifest.get("controlled_local") is not True or any(manifest.get(k) != v for k, v in SCOPE.items()):
        raise ValueError("Parent is not controlled-only evidence")
    if manifest.get("tool_sha256") != SUPPORTED_PARENT_BUILDER_SHA256 or current_builder_sha == SUPPORTED_PARENT_BUILDER_SHA256:
        raise ValueError("Unsupported parent/current builder lineage")
    current_builder = root / "tools/manual_build.py"
    if not current_builder.is_file() or sha(current_builder) != current_builder_sha:
        raise ValueError("Current builder hash does not match resume process")
    reconciler = root / "tools/manual_reconcile_build.py"
    if not reconciler.is_file() or sha(reconciler) != QUALIFIED_RECONCILER_SHA256:
        raise ValueError("Qualified source-pinned YAML reconstructor changed")
    if producer_hashes.get("tools/manual_reconcile_build.py") != QUALIFIED_RECONCILER_SHA256:
        raise ValueError("Resume proof omits exact qualified reconstruction helper pin")
    if "tools/resume_adoption.py" not in producer_hashes:
        raise ValueError("Resume proof omits its own adoption-validator source pin")
    required = {str(path.relative_to(root)) for path in (root / "tools").glob("manual_*.py")}
    required.update(("tools/resume_adoption.py", "tools/manual_reconcile_build.py"))
    if set(producer_hashes) != required:
        raise ValueError("Resume producer source map is not the exact required tool inventory")
    for relative, expected in producer_hashes.items():
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts or not (root / path).is_file() or sha(root / path) != expected:
            raise ValueError("Resume producer source map is stale or forged: " + relative)
    archived = parent / "authoring-before"
    if not archived.is_dir():
        raise ValueError("Parent authoring-before snapshot missing")
    old_sources = {str(p.relative_to(archived)): sha(p) for p in sorted(archived.rglob("*.yaml"))}
    if old_sources != manifest.get("source_files_before"):
        raise ValueError("Parent source archive differs from original start snapshot")
    old_plans = {k: v for k, v in old_sources.items() if k.startswith("manual/scene-plans")}
    current_plans = {str(p.relative_to(root)): sha(p) for p in sorted((root / "manual").glob("scene-plans*.yaml"))}
    if old_plans != current_plans:
        raise ValueError("Current authored plan inventory/hash differs from parent")
    if not producer_hashes or any(not isinstance(v, str) or len(v) != 64 for v in producer_hashes.values()):
        raise ValueError("Producer/runtime source identity map incomplete")
    planned = {s["name"]: s for s in planned_stages}
    rows = manifest.get("stages", [])
    parent_rows = {r.get("name"): r for r in rows}
    if len(parent_rows) != len(rows):
        raise ValueError("Duplicate stage names in parent manifest")
    adopted, rejected, proof_rows = {}, {}, []
    doctor_names={"doctor-manual-real","doctor-auto-real"}
    for name, stage in planned.items():
        is_reference=name.startswith("reference-controlled-")
        is_doctor=name in doctor_names
        if not (is_reference or is_doctor):
            continue
        try:
            row = parent_rows[name]
            if row.get("passed") is not True or row.get("returncode") != 0:
                raise ValueError("stage did not pass")
            old_receipt, old_log = parent / (name + ".json"), parent / (name + ".log")
            if not old_receipt.is_file() or not old_log.is_file() or sha(old_log) != row.get("log_sha256"):
                raise ValueError("stage receipt/log missing or changed")
            if read_json(old_receipt) != row:
                raise ValueError("stage receipt differs from immutable parent manifest")
            if row.get("command") != stage.get("command"):
                raise ValueError("canonical command changed")
            if is_reference and row.get("executed_command") != stage.get("command"):
                raise ValueError("canonical executed command changed")
            if is_doctor:
                expected_executed=[str(part).replace("{evidence}",str(parent)) for part in stage.get("command",[])]
                if row.get("executed_command") != expected_executed:
                    raise ValueError("Doctor executed capture command changed")
            if row.get("emulator") != stage.get("emulator") or row.get("exclusive_lock") != stage.get("exclusive_lock"):
                raise ValueError("emulator/lock command identity changed")
            report_ref = row.get("native_report", {})
            report_path = Path(report_ref.get("path", ""))
            if not report_path.is_file() or sha(report_path) != report_ref.get("sha256"):
                raise ValueError("native report missing or changed")
            report = read_json(report_path)
            if is_doctor:
                if audit_doctor is None:raise ValueError("Doctor adoption requires the current strict Doctor auditor")
                audit_doctor(report_path)
                verify_current_doctor_inputs(report_path,row,root)
                doctor_files=doctor_evidence_files(report_path)
                output_proof={}
            else:
                if any(report.get(k) != v for k, v in SCOPE.items()) or "manual_generation_complete" in report:
                    raise ValueError("native report scope changed")
                source = report.get("source", {})
                for collection in ("plan_files", "case_sources", "capture_sources", "fixture_sources"):
                    for relative, expected_hash in source.get(collection, {}).items():
                        if not (root / relative).is_file() or sha(root / relative) != expected_hash:
                            raise ValueError("current producer/source hash differs: " + relative)
                audit_native(report)
                verify_current_native_inputs(report, stage, root)
                command = stage["command"]
                if "--output" not in command:
                    raise ValueError("Controlled reference command lacks exact output name")
                output_proof = verify_case_outputs(root, command[command.index("--output") + 1], report)
                doctor_files=None
            receipt_sha, log_sha = sha(old_receipt), sha(old_log)
            adopted[name] = dict(stage, passed=True, returncode=0, executed_command=row.get("executed_command"),
                native_report=report_ref, execution_status="adopted-verified",
                adopted_from={"parent_manifest_sha256": sha(manifest_path),
                              "parent_stage_receipt_sha256": receipt_sha, "parent_log_sha256": log_sha})
            proof_row=dict(name=name, parent_stage_receipt_sha256=receipt_sha,
                parent_log_sha256=log_sha, native_report=report_ref, current_outputs=output_proof,
                producer_hashes=dict(sorted(producer_hashes.items())), audit_result="passed-current-strict-audit")
            if is_doctor:
                proof_row.update(kind="doctor-capture",doctor_evidence_files=doctor_files,
                    doctor_evidence_tree_sha256=hashlib.sha256(json.dumps(doctor_files,sort_keys=True).encode()).hexdigest())
            else:
                proof_row["kind"]="controlled-reference"
            proof_rows.append(proof_row)
        except Exception as error:
            rejected[name] = str(error)
    if not adopted:
        raise ValueError("No parent stage passed current adoption proof: " + json.dumps(rejected, sort_keys=True))
    proof = {"schema_version": 1, "adoption_scope": "controlled-stage-checkpoint-reuse",
        "parent_manifest": str(manifest_path), "parent_manifest_sha256": sha(manifest_path),
        "parent_builder_sha256": manifest["tool_sha256"], "resume_builder_sha256": current_builder_sha,
        "old_source_start_sha256": hashlib.sha256(json.dumps(old_sources, sort_keys=True).encode()).hexdigest(),
        "resume_source_start_sha256": None, "producer_hashes": dict(sorted(producer_hashes.items())),
        "adopted": proof_rows, "rejected": rejected,
        "stage_inventory": [s["name"] for s in planned_stages], "scope": dict(SCOPE)}
    if Path(proof_path).exists():
        raise ValueError("Adoption proof destination already exists")
    Path(proof_path).write_text(json.dumps(proof, indent=2) + "\n")
    return adopted, proof


def finalize_resume_source_start(proof_path, resumed_evidence):
    """Bind proof to the distinct actual snapshot taken at resumed-run start."""
    proof_path = Path(proof_path)
    proof = read_json(proof_path)
    archive = Path(resumed_evidence) / "authoring-before"
    if not archive.is_dir():
        raise ValueError("Resumed physical source-start archive missing")
    current = {str(p.relative_to(archive)): sha(p) for p in sorted(archive.rglob("*.yaml"))}
    proof["resume_source_start_sha256"] = hashlib.sha256(json.dumps(current, sort_keys=True).encode()).hexdigest()
    proof["resume_source_start_files"] = current
    proof_path.write_text(json.dumps(proof, indent=2) + chr(10))
    return proof

def audit_resume_lineage(build, manifest, current_root):
    """Additional final-audit check; existing raw/native checks remain required."""
    build = Path(build).resolve()
    current_root = Path(current_root).resolve()
    lineage = manifest.get("resume_lineage")
    adopted_rows = [row for row in manifest.get("stages", []) if row.get("execution_status") == "adopted-verified"]
    if not lineage:
        if adopted_rows:
            raise ValueError("Adopted stages have no resume lineage proof")
        return None
    proof_path = (build / lineage.get("path", "")).resolve()
    if proof_path != (build / "resume-adoption.json").resolve() or not proof_path.is_file() or sha(proof_path) != lineage.get("sha256"):
        raise ValueError("Resume lineage proof missing or changed")
    proof = read_json(proof_path)
    if proof.get("schema_version") != 1 or proof.get("scope") != SCOPE:
        raise ValueError("Resume lineage proof scope/schema changed")
    manifest_stage_names = [row.get("name") for row in manifest.get("stages", [])]
    if proof.get("stage_inventory") != manifest_stage_names:
        raise ValueError("Resume stage inventory differs from finalized manifest")
    required_producers = {str(path.relative_to(current_root)) for path in (current_root / "tools").glob("manual_*.py")}
    required_producers.update(("tools/resume_adoption.py", "tools/manual_reconcile_build.py"))
    producer_map = proof.get("producer_hashes", {})
    if set(producer_map) != required_producers:
        raise ValueError("Resume lineage producer map is incomplete or unexpected")
    for relative, expected in producer_map.items():
        source = current_root / relative
        if not source.is_file() or sha(source) != expected:
            raise ValueError("Resume lineage producer source changed: " + relative)
    parent_manifest = Path(proof.get("parent_manifest", ""))
    if not parent_manifest.is_file() or sha(parent_manifest) != proof.get("parent_manifest_sha256"):
        raise ValueError("Original failed parent manifest changed")
    parent = read_json(parent_manifest)
    if parent.get("passed") is not False or parent.get("build_complete") is not False or parent.get("controlled_local") is not True or any(parent.get(key) != value for key,value in SCOPE.items()) or parent.get("tool_sha256") != proof.get("parent_builder_sha256") or proof.get("parent_builder_sha256") != SUPPORTED_PARENT_BUILDER_SHA256:
        raise ValueError("Resume parent identity or failed scope changed")
    if manifest.get("tool_sha256") != proof.get("resume_builder_sha256") or proof.get("resume_source_start_sha256") is None:
        raise ValueError("Resume builder or actual new source-start identity missing")
    current_builder = current_root / "tools/manual_build.py"
    if not current_builder.is_file() or sha(current_builder) != proof.get("resume_builder_sha256"):
        raise ValueError("Current builder bytes differ from resumed build identity")
    old_archive = parent_manifest.parent / "authoring-before"
    old_sources = {str(p.relative_to(old_archive)): sha(p) for p in sorted(old_archive.rglob("*.yaml"))}
    if old_sources != parent.get("source_files_before") or hashlib.sha256(json.dumps(old_sources, sort_keys=True).encode()).hexdigest() != proof.get("old_source_start_sha256"):
        raise ValueError("Original parent physical source-start snapshot changed")
    archive = build / "authoring-before"
    actual = {str(p.relative_to(archive)): sha(p) for p in sorted(archive.rglob("*.yaml"))}
    if actual != proof.get("resume_source_start_files") or hashlib.sha256(json.dumps(actual, sort_keys=True).encode()).hexdigest() != proof.get("resume_source_start_sha256"):
        raise ValueError("Resume source-start snapshot is not the actual new-run archive")
    proof_rows = {row["name"]: row for row in proof.get("adopted", [])}
    if len(proof_rows) != len(proof.get("adopted", [])) or set(proof_rows) != {row.get("name") for row in adopted_rows}:
        raise ValueError("Manifest adopted-stage inventory differs from lineage proof")
    parent_rows = {row.get("name"): row for row in parent.get("stages", [])}
    for row in adopted_rows:
        item = proof_rows[row["name"]]
        origin = row.get("adopted_from", {})
        parent_row = parent_rows.get(row["name"])
        parent_receipt = parent_manifest.parent / (row["name"] + ".json")
        parent_log = parent_manifest.parent / (row["name"] + ".log")
        if parent_row is None or not parent_receipt.is_file() or not parent_log.is_file():
            raise ValueError("Parent adopted-stage receipt/log missing")
        if read_json(parent_receipt) != parent_row or sha(parent_receipt) != item.get("parent_stage_receipt_sha256") or sha(parent_log) != item.get("parent_log_sha256") or sha(parent_log) != parent_row.get("log_sha256"):
            raise ValueError("Parent adopted-stage receipt/log changed")
        if row.get("command") != parent_row.get("command") or row.get("executed_command") != parent_row.get("executed_command") or row.get("emulator") != parent_row.get("emulator") or row.get("exclusive_lock") != parent_row.get("exclusive_lock"):
            raise ValueError("Adopted stage command identity differs from parent")
        if row.get("native_report") != parent_row.get("native_report") or item.get("native_report") != parent_row.get("native_report"):
            raise ValueError("Adopted native report identity differs from parent")
        report_path = Path(parent_row["native_report"]["path"])
        if not report_path.is_file() or sha(report_path) != parent_row["native_report"].get("sha256"):
            raise ValueError("Adopted native report changed after preparation")
        report = read_json(report_path)
        if item.get("kind") == "doctor-capture":
            if row.get("name") not in ("doctor-manual-real", "doctor-auto-real") or item.get("current_outputs") != {}:
                raise ValueError("Unexpected Doctor adoption scope or output claim")
            if doctor_evidence_files(report_path) != item.get("doctor_evidence_files"):
                raise ValueError("Doctor evidence tree changed after adoption")
            from manual_publication_verify import audit_doctor
            audit_doctor(report_path)
            verify_current_doctor_inputs(report_path,row,current_root)
        else:
            if item.get("kind") != "controlled-reference":
                raise ValueError("Unknown adopted stage type")
            verify_current_native_inputs(report, row, current_root)
        if origin.get("parent_manifest_sha256") != proof["parent_manifest_sha256"] or origin.get("parent_stage_receipt_sha256") != item["parent_stage_receipt_sha256"] or origin.get("parent_log_sha256") != item["parent_log_sha256"]:
            raise ValueError("Adopted stage lineage fields forged or changed")
        if item.get("audit_result") != "passed-current-strict-audit" or not item.get("producer_hashes"):
            raise ValueError("Adopted stage lacks current reconstruction proof")
        if item.get("kind") == "controlled-reference" and not item.get("current_outputs"):
            raise ValueError("Adopted reference lacks exact current output hashes")
        if item.get("kind") == "doctor-capture" and not item.get("doctor_evidence_files"):
            raise ValueError("Adopted Doctor stage lacks immutable evidence-tree hashes")
        if item.get("producer_hashes") != proof.get("producer_hashes"):
            raise ValueError("Per-stage producer hashes differ from proof header")
        required_for_stage = set(required_producers)
        if set(item.get("producer_hashes", {})) != required_for_stage:
            raise ValueError("Adopted-stage producer source map is incomplete")
        for rel, expected in item["current_outputs"].items():
            path = Path(rel)
            if path.is_absolute() or ".." in path.parts or not (current_root / path).is_file() or sha(current_root / path) != expected:
                raise ValueError("Adopted current publication bytes changed: " + rel)
        for rel, expected in item["producer_hashes"].items():
            path = Path(rel)
            if path.is_absolute() or ".." in path.parts or not (current_root / path).is_file() or sha(current_root / path) != expected:
                raise ValueError("Adopted producer/source pin changed: " + rel)
    if manifest.get("source_files_before") != proof.get("resume_source_start_files"):
        raise ValueError("Manifest does not preserve the actual resumed-run source-start snapshot")
    return {"passed": True, "adopted_stages": sorted(proof_rows), "parent_manifest_sha256": proof["parent_manifest_sha256"]}
