"""Build a traceable inventory from manual sections, requirements and Lua sources."""
import copy
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tests/behaviour"))


def slug(title):
    title=re.sub(r"<[^>]*>|[*_`]", "", title)
    return re.sub(r"[^a-z0-9]+","-",title.lower()).strip("-")


def merge_audit(fresh, previous, root=ROOT):
    """Retain reviewed evidence verbatim; flag drift instead of rewriting its identity."""
    result=copy.deepcopy(fresh)
    if not previous or not previous.get("source_review"):
        return result
    for field in ("controls","feedback","edge_cases","interactions","code_candidates",
                  "audit_status","source_review","review","details","recipes"):
        if field in previous: result[field]=copy.deepcopy(previous[field])
    drift=[]
    before=previous.get("readme",{}).get("sha256")
    after=fresh.get("readme",{}).get("sha256")
    if before and after and before!=after: drift.append("readme")
    for owner in previous.get("code_candidates",[]):
        path=root/owner["path"]
        if owner.get("sha256") and path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()!=owner["sha256"]:
            drift.append(owner["path"])
    if drift:
        result["audit_status"]="source-review-stale"
        result["review_drift"]=drift
    elif previous.get("review_drift"):
        result["review_drift"]=copy.deepcopy(previous["review_drift"])
    return result

def current_reference_review(feature, captures):
    """Current scoped native evidence, separate from the frozen source review."""
    refs=[value if isinstance(value,str) else value["id"] for value in feature.get("scene_refs",[])]
    replayed=[];missing=[];cases=[];lanes=[]
    for name in refs:
        scene=captures.get(name,{})
        bindings=[step.get("output",{}).get("binding",{}) for step in scene.get("steps",[])]
        valid=bool(bindings) and scene.get("behaviour_case") and all(
            b.get("passed") is True and b.get("semantic_assertions",0)>0 and b.get("sha256")
            and b.get("grid_sha256") for b in bindings)
        if valid:
            replayed.append(name);cases.append(scene["behaviour_case"])
            if scene.get("clock_mode"):lanes.append(scene["clock_mode"])
        else:missing.append(name)
    review=feature["review"]
    result=dict(declared_review_status=review["status"],
        applicability=review.get("applicability","native-ui"),
        native_replayed=bool(replayed),scene_refs=refs,replayed_scene_refs=replayed,
        missing_scene_refs=missing,all_referenced_scenes_bound=bool(refs) and not missing,
        behaviour_cases=sorted(set(cases)),clock_modes=sorted(set(lanes)),
        scope=review.get("rationale") or review.get("native_gap") or review.get("note",""),
        complete_regression_run=False)
    if result["applicability"] in ("documentation-only","external-hardware") and result["scope"] and not refs:
        status="source-reviewed-native-not-applicable"
    elif replayed:
        status="source-reviewed-with-partial-native-reference-evidence" if missing else "source-reviewed-with-native-reference-evidence"
    else:status="source-reviewed-native-reference-evidence-missing"
    return result,status

def native_catalogue(root=ROOT):
    """Read actual publication bindings and keep their clock lane visible."""
    result={}
    for path in sorted((root/"manual/generated").glob("*.json")):
        if path.name in ("book.json","reader-index.json"):continue
        document=json.loads(path.read_text())
        lane=document.get("clock_mode") or document.get("validation",{}).get("clock_mode")
        for scene in document.get("scenes",[]):
            if scene["id"] in result:raise ValueError("Duplicate native scene ID: "+scene["id"])
            result[scene["id"]]=dict(scene,clock_mode=lane)
    return result

def book_entry(feature, baseline, root=ROOT, captures=None):
    """Overlay authored references while keeping frozen native/source evidence."""
    result=copy.deepcopy(baseline)
    result.update({key:copy.deepcopy(feature[key]) for key in
        ("id","title","level","parent","category","controls","details","recipes","review") if key in feature})
    result["authoring_source"]=feature["sources"]["readme"]
    result["interactions"]=copy.deepcopy(feature["related"])
    if not baseline:
        result.update(readme=dict(path=feature["sources"]["readme"],start_line=None,end_line=None,
            section_ids=[],sha256=None,excerpt=feature.get("prose","")),
            requirements=[],behaviour_cases=[],feedback=[],edge_cases=[],
            cheat_sheet=dict(path="cheat_sheet.html",lines=[]),code_candidates=[],
            audit_status="cross-referenced-awaiting-semantic-review")
    reviewed=feature["review"].get("source_status")=="code-and-case-reviewed"
    if reviewed:
        if not result.get("source_review"):
            result["source_review"]=dict(native_replayed=False,
                note=feature["review"].get("note","Source and case definitions reviewed; native replay pending."),
                behaviour_cases=copy.deepcopy(feature["sources"]["behaviour_cases"]),
                source_sha256=result.get("readme",{}).get("sha256"))
        if not baseline.get("source_review"):
            result["code_candidates"]=[dict(path=name,status="reviewed-source-owner",
                sha256=hashlib.sha256((root/name).read_bytes()).hexdigest())
                for name in feature["sources"]["code"]]
        if result.get("audit_status")!="source-review-stale":
            result["audit_status"]="source-and-case-definitions-reviewed-awaiting-native-reference-replay"
    result["current_review"],status=current_reference_review(feature,captures or {})
    receipt=feature["review"].get("current_source_review")
    if receipt:
        result["current_review"]["source_reassessment"]=copy.deepcopy(receipt)
        owners={owner["path"]:owner["sha256"] for owner in receipt.get("owners",[])}
        drift=result.get("review_drift",[])
        reassessed=bool(drift) and bool(receipt.get("note")) and all(
            path in owners and (root/path).is_file()
            and hashlib.sha256((root/path).read_bytes()).hexdigest()==owners[path] for path in drift)
        result["current_review"]["source_drift_reassessed"]=reassessed
    else:reassessed=False
    if reviewed and (result.get("audit_status")!="source-review-stale" or reassessed):
        result["audit_status"]=status
    return result

def main():
    from cases import CASES
    import yaml
    previous_path=ROOT/"manual/inventory.json"
    previous=json.loads(previous_path.read_text()) if previous_path.exists() else {}
    previous_by_id={f["id"]:f for f in previous.get("features",[])}
    book=yaml.safe_load((ROOT/"manual/book.yaml").read_text())
    readme_path=ROOT/"manual"/book["legacy_source"]
    readme_identity=readme_path.relative_to(ROOT).as_posix()
    lines=readme_path.read_text().splitlines()
    inventory=json.loads((ROOT/"tests/behaviour/manual-inventory.json").read_text())
    cheat=(ROOT/"cheat_sheet.html").read_text().splitlines()
    code=[ROOT/"mosaic.lua"]+sorted((ROOT/"lib").rglob("*.lua"))
    code=[p for p in code if not any(part in ("tests","nb","test_artefacts") for part in p.relative_to(ROOT).parts)]
    sections=[(i,re.match(r"^(#{2,6})\s+(.+)",line)) for i,line in enumerate(lines)]
    sections=[(i,m) for i,m in sections if m]
    features=[];seen={}
    for pos,(start,match) in enumerate(sections):
        end=sections[pos+1][0] if pos+1<len(sections) else len(lines)
        title=match.group(2);identifier=slug(title)
        seen[identifier]=seen.get(identifier,0)+1
        if seen[identifier]>1:identifier+="-"+str(seen[identifier])
        old=[s for s in inventory["sections"] if s["title"]==title]
        section_ids={s["id"] for s in old}
        req=[r for r in inventory["requirements"] if section_ids.intersection(r["sections"])]
        ids=sorted({case for r in req for case in r.get("cases",[])})
        text="\n".join(lines[start+1:end])
        terms=[word for word in re.findall(r"[a-z]+",title.lower()) if len(word)>3 and word not in ("adding","using","removing","with","mosaic","overview","started")]
        refs=[]
        for p in code:
            content=p.read_text(errors="replace").splitlines()
            hits=[i+1 for i,line in enumerate(content) if terms and all(t in line.lower() for t in terms[:2])]
            if hits:refs.append(dict(path=p.relative_to(ROOT).as_posix(),lines=hits[:8],status="candidate-needs-review"))
        cheat_hits=[i+1 for i,line in enumerate(cheat) if title.lower() in re.sub("<[^>]*>"," ",line).lower()]
        features.append(dict(id=identifier,title=title,level=len(match.group(1)),
            readme=dict(path=readme_identity,start_line=start+1,end_line=end,section_ids=sorted(section_ids),
                        sha256=hashlib.sha256(text.encode()).hexdigest(),excerpt=text),
            controls=[line for line in text.splitlines() if re.search(r"\b[KE][123]\b|hold|press|turn|tap|MIDI keyboard",line,re.I)],
            feedback=[line for line in text.splitlines() if re.search(r"screen|display|LED|lit|flash|grid",line,re.I) and not line.startswith("<")],
            edge_cases=[line for line in text.splitlines() if re.search(r"default|unless|only|preserv|cannot|not |maximum|minimum|bound",line,re.I)],
            interactions=re.findall(r"\[[^]]+\]\(#([^)]+)\)",text),
            requirements=[dict(id=r["id"],statement=r["statement"],oracles=r.get("oracles",[]),status=r.get("status")) for r in req],
            behaviour_cases=[dict(id=i,registered=i in CASES,description=CASES[i]["description"] if i in CASES else "unregistered") for i in ids],
            cheat_sheet=dict(path="cheat_sheet.html",lines=cheat_hits),
            code_candidates=refs,
            audit_status="pilot-reviewed" if identifier in ("masks","adding-trig-masks","adding-melodic-notes-over-harmony-and-drums","adding-chords","removing-masks") else "cross-referenced-awaiting-semantic-review"))
    features=[merge_audit(f,previous_by_id.get(f["id"])) for f in features]
    by_id={f["id"]:f for f in features}
    from manual_book import load as load_book
    captures=native_catalogue()
    for feature in load_book()["features"]:
        current=by_id.get(feature["id"],{})
        entry=book_entry(feature,current,captures=captures)
        by_id[feature["id"]]=entry
    features=list(by_id.values())
    result=dict(schema_version=1,base_revision="54d7b871358fcc68b7166847603cc9fb1461d0b6",
        source_files={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in (readme_identity,"cheat_sheet.html","tests/behaviour/manual-inventory.json")},
        evidence_source_files=previous.get("evidence_source_files",previous.get("source_files",{})),
        features=features,code_files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in code],
        manual_authority="Structured book.yaml sources; legacy README remains frozen evidence")
    (ROOT/"manual/inventory.json").write_text(json.dumps(result,indent=2)+"\n")
    rows=["# Feature inventory","",f"{len(features)} headings cross-referenced. This is a source map, not full campaign acceptance.",
          "","| Stable ID | Feature | README lines | Requirements | Cases | Review |","|---|---|---|---|---|---|"]
    for f in features:
        rows.append("| "+ " | ".join([f["id"],f["title"],(str(f["readme"]["start_line"])+"–"+str(f["readme"]["end_line"])) if f["readme"]["start_line"] else "authored destination",", ".join(r["id"] for r in f["requirements"]) or "unmapped",", ".join(c["id"] for c in f["behaviour_cases"]) or "none mapped",f["audit_status"]])+" |")
    rows+=["","The JSON retains source excerpts, control/feedback/boundary candidates and Lua line references. Empty mappings remain visible. All existing inventory IDs and coverage gaps are preserved. Regenerate with `python3 tools/manual_inventory.py`."]
    (ROOT/"manual/INVENTORY.md").write_text("\n".join(rows)+"\n")
    print(len(features),"features indexed;",len(code),"Lua source identities")

if __name__=="__main__":main()
