"""Build a traceable inventory from manual sections, requirements and Lua sources."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tests/behaviour"))
from cases import CASES

def slug(title):
    title=re.sub(r"<[^>]*>|[*_`]", "", title)
    return re.sub(r"[^a-z0-9]+","-",title.lower()).strip("-")

def main():
    lines=(ROOT/"README.md").read_text().splitlines()
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
            readme=dict(path="README.md",start_line=start+1,end_line=end,section_ids=sorted(section_ids),
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
    result=dict(schema_version=1,base_revision="54d7b871358fcc68b7166847603cc9fb1461d0b6",
        source_files={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ("README.md","cheat_sheet.html","tests/behaviour/manual-inventory.json")},
        features=features,code_files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in code],
        manual_authority="README.md until pilot approval and full migration")
    (ROOT/"manual/inventory.json").write_text(json.dumps(result,indent=2)+"\n")
    rows=["# Feature inventory","",f"{len(features)} headings cross-referenced. This is a source map, not full campaign acceptance.",
          "","| Stable ID | Feature | README lines | Requirements | Cases | Review |","|---|---|---|---|---|---|"]
    for f in features:
        rows.append("| "+ " | ".join([f["id"],f["title"],str(f["readme"]["start_line"])+"–"+str(f["readme"]["end_line"]),", ".join(r["id"] for r in f["requirements"]) or "unmapped",", ".join(c["id"] for c in f["behaviour_cases"]) or "none mapped",f["audit_status"]])+" |")
    rows+=["","The JSON retains source excerpts, control/feedback/boundary candidates and Lua line references. Empty mappings remain visible. All existing inventory IDs and coverage gaps are preserved. Regenerate with `python3 tools/manual_inventory.py`."]
    (ROOT/"manual/INVENTORY.md").write_text("\n".join(rows)+"\n")
    print(len(features),"features indexed;",len(code),"Lua source identities")

if __name__=="__main__":main()
