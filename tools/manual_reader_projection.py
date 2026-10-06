"""Deterministic, source-bound chunks for the browser manual reader."""
from __future__ import annotations
import hashlib, json, re, base64, os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from manual_teaching import build_teaching_contracts
SCHEMA_VERSION = 1
_SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
class ProjectionError(ValueError):
    """The projection or one of its canonical sources is invalid."""
def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise ProjectionError(f"duplicate JSON key: {key}")
        result[key] = value
    return result
def _decode(raw: bytes, label: str) -> Any:
    try: return json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc: raise ProjectionError(f"{label} is not valid UTF-8 JSON") from exc
def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
def _sha(raw: bytes) -> str: return hashlib.sha256(raw).hexdigest()
def _read_source(value, label: str) -> tuple[dict, bytes]:
    if isinstance(value, bytes): raw, document = value, _decode(value, label)
    elif isinstance(value, (str, Path)):
        raw = Path(value).read_bytes(); document = _decode(raw, label)
    elif isinstance(value, Mapping): document = dict(value); raw = _canonical_bytes(document)
    else: raise TypeError(f"{label} must be a path, bytes, or mapping")
    if not isinstance(document, dict): raise ProjectionError(f"{label} must contain a JSON object")
    return document, raw
def _checked_id(value: Any, where: str) -> str:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value): raise ProjectionError(f"unsafe or invalid ID in {where}: {value!r}")
    return value
def _unique_rows(rows: Any, label: str) -> list[dict]:
    if not isinstance(rows, list): raise ProjectionError(f"{label} must be a list")
    seen, result = set(), []
    for row in rows:
        if not isinstance(row, dict): raise ProjectionError(f"{label} entries must be objects")
        item_id = _checked_id(row.get("id"), label)
        if item_id in seen: raise ProjectionError(f"duplicate {label} ID: {item_id}")
        seen.add(item_id); result.append(row)
    return result
def _scene_rows(book: Mapping[str, Any]) -> list[dict]:
    scenes = book.get("scenes")
    if not isinstance(scenes, dict): raise ProjectionError("book.scenes must be an object keyed by scene ID")
    rows = []
    for key, scene in scenes.items():
        key = _checked_id(key, "book.scenes key")
        if not isinstance(scene, dict) or scene.get("id") != key: raise ProjectionError(f"scene key/id mismatch: {key}")
        rows.append(scene)
    return rows
def _audio_document(audio: Mapping[str, Any]) -> tuple[list[dict], dict]:
    return _unique_rows(audio.get("examples"), "audio examples"), {k:v for k,v in audio.items() if k != "examples"}
def _chunk(path: str, value: dict) -> tuple[dict, bytes]:
    raw = _canonical_bytes(value); digest = _sha(raw)
    return {"path": path.format(id=value["id"], sha256=digest), "sha256": digest}, raw
def _project_root(book_value, supplied=None):
    if supplied is not None: return Path(supplied).resolve()
    if isinstance(book_value,(str,Path)):
        path=Path(book_value).resolve()
        if path.name=="book.json" and path.parent.name=="generated" and path.parent.parent.name=="manual":
            return path.parents[2]
    configured=os.environ.get("MOSAIC_REPO_ROOT")
    return Path(configured).resolve() if configured else None

def build_projection(book_value, audio_value, prelude_admissions=None, project_root=None) -> tuple[dict, dict[str, bytes]]:
    """Return deterministic reader-index data and relative-path chunk bytes."""
    book, book_raw = _read_source(book_value, "book.json")
    audio, audio_raw = _read_source(audio_value, "audio-scenes.json")
    features = _unique_rows(book.get("features"), "book features")
    scenes = _scene_rows(book); examples, audio_metadata = _audio_document(audio)
    feature_ids = {f["id"] for f in features}; scene_ids = {s["id"] for s in scenes}
    for feature in features:
        refs = feature.get("scene_refs", [])
        if not isinstance(refs, list): raise ProjectionError(f"{feature['id']}.scene_refs must be a list")
        for ref in refs:
            sid = ref if isinstance(ref, str) else ref.get("id") if isinstance(ref, dict) else None
            if not isinstance(sid, str) or sid not in scene_ids: raise ProjectionError(f"feature {feature['id']} has unknown scene reference")
    for example in examples:
        ids = example.get("feature_ids", [])
        if not isinstance(ids, list) or any(fid not in feature_ids for fid in ids): raise ProjectionError(f"audio example {example['id']} has unknown feature")
    chunks, scene_index, scene_metadata = {}, {}, {}
    for scene in scenes:
        sid = scene["id"]; ref, raw = _chunk("reader-chunks/scenes/{id}-{sha256}.json", scene)
        scene_index[sid], chunks[ref["path"]] = ref, raw
        steps = scene.get("steps")
        if not isinstance(steps, list) or any(not isinstance(step, dict) for step in steps): raise ProjectionError(f"scene {sid}.steps must be a list of objects")
        scene_metadata[sid] = {k:scene.get(k) for k in ("id","title","behaviour_case","profile")}
        scene_metadata[sid]["steps"] = [{k:step.get(k) for k in ("id","title","caption")} for step in steps]
    audio_index, audio_refs = [], {}
    for example in examples:
        aid = example["id"]; ref, raw = _chunk("reader-chunks/audio/{id}-{sha256}.json", example)
        audio_refs[aid], chunks[ref["path"]] = ref, raw
        audio_index.append({k:example[k] for k in ("id","title","purpose","feature_ids","course","tracks") if k in example})
    prelude_admissions = prelude_admissions or {}
    prelude_index, normalized_preludes = {}, {}
    for alias, admission in sorted(prelude_admissions.items()):
        if alias != "getting-started-start" or not isinstance(admission, dict):
            raise ProjectionError("unexpected native prelude admission")
        summary = admission.get("admission_summary", {})
        snapshot = admission.get("display_snapshot", {})
        if summary.get("runtime_alias") != alias or summary.get("selector") != {"from_prelude_receipt_id": alias}:
            raise ProjectionError("native prelude admission selector mismatch")
        receipt_bytes = admission.get("receipt_bytes_base64")
        if not isinstance(receipt_bytes,str) or _sha(base64.b64decode(receipt_bytes,validate=True)) != admission.get("receipt_sha256"):
            raise ProjectionError("native prelude exact receipt bytes do not match the admission pin")
        payload = {"id": alias, "receipt_sha256": admission.get("receipt_sha256"),
            "receipt_bytes_base64": receipt_bytes,
            "admission_summary": summary, "display_snapshot": snapshot}
        raw = _canonical_bytes(payload); digest = _sha(raw)
        relative = "reader-chunks/preludes/{}-{}.json".format(alias, digest)
        chunks[relative] = raw
        normalized = dict(admission); normalized["chunk_sha256"] = digest
        normalized_preludes[alias] = normalized
        prelude_index[alias] = {"path": relative, "sha256": digest,
            "receipt_sha256": admission.get("receipt_sha256"),
            "scene_id": summary.get("scene_id"), "target_step_id": summary.get("target_step_id")}
    teaching_contracts = build_teaching_contracts(book, scene_index, normalized_preludes,
        project_root=_project_root(book_value,project_root))
    projected_features = []
    for feature in features:
        projected = dict(feature)
        lessons = []
        for lesson in feature.get("teaching_bindings", []):
            row = dict(lesson)
            contract_id = "feature:{}:{}".format(feature["id"], lesson["id"])
            receipt = teaching_contracts.get(contract_id)
            if receipt is not None:
                row.update(receipt)
            lessons.append(row)
        if "teaching_bindings" in feature:
            projected["teaching_bindings"] = lessons
        projected_features.append(projected)
    index = {
        "projection_schema": SCHEMA_VERSION,
        "canonical_inputs": {"book_json_sha256":_sha(book_raw),"audio_scenes_json_sha256":_sha(audio_raw)},
        **{k:book[k] for k in ("schema_version","edition","title","authoring_identity","source_sha256","legacy_source_sha256","complete_manual","validation_scope","realtime_qualification","complete_regression_run","aliases","navigation","course_title","course_summary","project","learning_path") if k in book},
        "features":projected_features,"scenes":scene_metadata,"scene_chunks":scene_index,"audio_metadata":audio_metadata,
        "audio_examples":audio_index,"audio_chunks":audio_refs,
        "teaching_contracts":teaching_contracts,"prelude_receipts":prelude_index,
        "inventory":{"feature_ids":[r["id"] for r in features],"scene_ids":[r["id"] for r in scenes],"audio_example_ids":[r["id"] for r in examples]},
    }
    return index, chunks
def write_projection(book_path, audio_path, output_dir, prelude_admissions=None, project_root=None) -> dict:
    """Write projection files without deleting or replacing differing content."""
    output_dir=Path(output_dir); index,chunks=build_projection(book_path,audio_path,prelude_admissions,project_root); root=output_dir/"reader-chunks"
    expected=set(chunks)
    if root.exists():
        existing={p.relative_to(output_dir).as_posix() for p in root.rglob("*") if p.is_file()}
        if existing-expected: raise ProjectionError("stale or unreferenced files in reader-chunks")
    for relative,raw in chunks.items():
        dest=output_dir/relative; dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists() and dest.read_bytes()!=raw: raise ProjectionError(f"refusing to overwrite different chunk: {relative}")
        if not dest.exists(): dest.write_bytes(raw)
    ip=output_dir/"reader-index.json"; raw_index=_canonical_bytes(index)
    if ip.exists() and ip.read_bytes()!=raw_index: raise ProjectionError("refusing to overwrite a different reader index")
    if not ip.exists(): ip.write_bytes(raw_index)
    validate_projection(ip,root,book_path,audio_path,prelude_admissions,project_root); return index
def _safe_chunk_path(root: Path, relative: Any) -> Path:
    if not isinstance(relative,str) or "\\" in relative: raise ProjectionError("chunk path must be a safe relative POSIX path")
    parts=relative.split("/")
    if not parts or relative.startswith("/") or any(x in ("",".","..") for x in parts): raise ProjectionError("unsafe chunk path")
    if root.is_symlink(): raise ProjectionError("reader chunk root must not be a symlink")
    candidate=(root.parent/relative).resolve(); resolved_root=root.resolve()
    if resolved_root not in (candidate,*candidate.parents): raise ProjectionError("chunk path escapes its root")
    if candidate.is_symlink(): raise ProjectionError("reader chunk path must not be a symlink")
    return candidate
def validate_projection(index_path, chunk_root, book_value, audio_value, prelude_admissions=None, project_root=None) -> None:
    """Reject stale, altered, incomplete, unsafe, or source-mismatched projections."""
    expected_index,expected_chunks=build_projection(book_value,audio_value,prelude_admissions,project_root); ip=Path(index_path); raw_index=ip.read_bytes(); parsed=_decode(raw_index,"reader-index.json")
    if raw_index!=_canonical_bytes(expected_index) or parsed!=expected_index: raise ProjectionError("reader index is stale, altered, or does not match canonical inputs")
    root=Path(chunk_root)
    if root.is_symlink(): raise ProjectionError("reader chunk root must not be a symlink")
    if not root.exists() and expected_chunks: raise ProjectionError("reader chunk directory is missing")
    actual={p.relative_to(root.parent).as_posix() for p in root.rglob("*") if p.is_file()} if root.exists() else set()
    if actual!=set(expected_chunks): raise ProjectionError("reader chunk inventory differs from source-bound index")
    refs=[*parsed["scene_chunks"].values(),*parsed["audio_chunks"].values(),*parsed.get("prelude_receipts",{}).values()]; seen=set()
    for ref in refs:
        if not isinstance(ref,dict) or not {"path","sha256"}<=set(ref) or set(ref)-{"path","sha256","receipt_sha256","scene_id","target_step_id"}: raise ProjectionError("invalid chunk reference")
        path=_safe_chunk_path(root,ref["path"])
        if ref["path"] in seen: raise ProjectionError("duplicate chunk path")
        seen.add(ref["path"]); raw=path.read_bytes()
        if _sha(raw)!=ref["sha256"]: raise ProjectionError(f"chunk digest mismatch: {ref['path']}")
        _decode(raw,ref["path"])
        if raw!=expected_chunks.get(ref["path"]): raise ProjectionError(f"chunk does not match canonical source: {ref['path']}")
    index_digest=_sha(raw_index)
    chunk_rows=[{"path":path,"sha256":_sha(content)} for path,content in sorted(expected_chunks.items())]
    return {
        "passed": True,
        "reader_index_sha256": index_digest,
        "book_json_sha256": expected_index["canonical_inputs"]["book_json_sha256"],
        "audio_scenes_json_sha256": expected_index["canonical_inputs"]["audio_scenes_json_sha256"],
        "chunk_count": len(chunk_rows),
        "scene_count": len(expected_index["scene_chunks"]),
        "audio_example_count": len(expected_index["audio_chunks"]),
        "chunk_inventory_sha256": _sha(_canonical_bytes(chunk_rows)),
    }
@dataclass
class Projection:
    """Audited projection for deterministic test/replay access."""
    index:dict
    chunk_root:Path
    def _load(self,refs:Mapping[str,dict],item_id:str)->dict:
        item_id=_checked_id(item_id,"chunk lookup")
        if item_id not in refs: raise KeyError(item_id)
        ref=refs[item_id]; path=_safe_chunk_path(self.chunk_root,ref["path"]); raw=path.read_bytes()
        if _sha(raw)!=ref["sha256"]: raise ProjectionError(f"chunk digest mismatch: {ref['path']}")
        value=_decode(raw,ref["path"])
        if not isinstance(value,dict) or value.get("id")!=item_id: raise ProjectionError(f"chunk identity mismatch: {ref['path']}")
        return value
    def load_scene(self,scene_id:str)->dict: return self._load(self.index["scene_chunks"],scene_id)
    def load_audio(self,audio_id:str)->dict: return self._load(self.index["audio_chunks"],audio_id)
    def load_prelude(self,receipt_id:str)->dict: return self._load(self.index["prelude_receipts"],receipt_id)
def load_projection(index_path,canonical_book_path,canonical_audio_path,prelude_admissions=None)->Projection:
    ip=Path(index_path); root=ip.parent/"reader-chunks"
    validate_projection(ip,root,canonical_book_path,canonical_audio_path,prelude_admissions)
    return Projection(_decode(ip.read_bytes(),"reader-index.json"),root)

def admit_reader_prelude(package_dir, *, verify_cached_ui):
    from manual_native_prelude_admission import admit_native_prelude
    admission = admit_native_prelude(
        package_dir=package_dir,
        expected_manifest_sha256="897f26ea1252f9bf65ff95fca7abf84654f89d9342db5d1ce5d306c90e223dd6",
        expected_receipt_sha256="4c70e182a3a21c03abe5c4aec4d0555ec3373e9fbd73970d8f035a5967eec8af",
        verify_cached_ui=verify_cached_ui,
    )
    raw_receipt = (Path(package_dir) / "derived-native-prelude-receipt.json").read_bytes()
    if _sha(raw_receipt) != admission["receipt_sha256"]:
        raise ProjectionError("native prelude receipt bytes changed after admission")
    admission["receipt_bytes_base64"] = base64.b64encode(raw_receipt).decode("ascii")
    return admission

def main(argv=None):
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book",required=True)
    parser.add_argument("--audio",required=True)
    parser.add_argument("--output-dir",required=True)
    parser.add_argument("--prelude-package")
    parser.add_argument("--project-root")
    args=parser.parse_args(argv)
    prelude_admissions={"getting-started-start":admit_reader_prelude(args.prelude_package)} if args.prelude_package else None
    write_projection(args.book,args.audio,args.output_dir,prelude_admissions,args.project_root)
    report=validate_projection(Path(args.output_dir)/"reader-index.json",
        Path(args.output_dir)/"reader-chunks",args.book,args.audio,prelude_admissions,args.project_root)
    report["producer_sha256"]=_sha(Path(__file__).read_bytes())
    print(json.dumps(report,sort_keys=True,separators=(",",":")))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
