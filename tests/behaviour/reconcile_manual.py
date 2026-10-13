"""Reconcile manual-inventory.json (and the hardening matrix) with the manual.

Run after a deliberate README.md or cheat_sheet.html change:
    python3 tests/behaviour/reconcile_manual.py [--check]

It refreshes the manual and manual-source digests, and each README section's
line range and text digest. A section keeps its id when a heading of the same
title and level still exists (matched in order); a new heading gets the next
MAN id marked for statement review; a heading that no longer exists keeps its
id and requirement links but is marked absent, so no requirement silently
loses its manual source. The hardening matrix follows the new digests.
Requirements, statements and cases are never changed here: re-reviewing what
a changed section promises stays a human decision.
"""
import argparse,copy
import hashlib
import json
import re
import sys
from manual_authority import authoring_identity, feature_links, load_compiled, load_authored, verify_authority, verify_manual_sources
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
INVENTORY = REPO / "tests/behaviour/manual-inventory.json"
MATRIX = REPO / "docs/testing/unit-integration-hardening-matrix.json"
FIRST_SECTION = "Getting Started"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manual_sections(text):
    """Headings from FIRST_SECTION on: 0-based start line, inclusive end line."""
    lines = text.split("\n")
    heads = []
    for index, line in enumerate(lines):
        match = re.match(r"^(#{2,6})\s+(.+?)\s*$", line)
        if match:
            heads.append((index, len(match.group(1)), match.group(2)))
    first = next(n for n, head in enumerate(heads) if head[2] == FIRST_SECTION)
    heads = heads[first:]
    sections = []
    for n, (start, level, title) in enumerate(heads):
        end = heads[n + 1][0] - 1 if n + 1 < len(heads) else len(lines) - 1
        body = "\n".join(lines[start:end + 1])
        sections.append(dict(title=title, level=level, start_line=start, end_line=end,
                             text_sha256=hashlib.sha256(body.encode()).hexdigest()))
    return sections


def reconcile(inventory, manual_text):
    current = manual_sections(manual_text)
    # Only README heading sections (MAN-<n>) are reconciled; others, such as the
    # cheat sheet's CHEAT-ALL, are kept exactly as they are.
    kept = [s for s in inventory["sections"] if not s["id"].split("-")[1].isdigit()]
    old = [s for s in inventory["sections"] if s["id"].split("-")[1].isdigit()]
    used = set()
    numbers = [int(s["id"].split("-")[1]) for s in old if s["id"].split("-")[1].isdigit()]
    next_number = max(numbers) + 1
    result = []
    for section in current:
        match = next((o for o in old if id(o) not in used and o["title"] == section["title"]
                      and o.get("level") == section["level"]), None)
        if match is not None:
            used.add(id(match))
            entry = dict(match)
            if entry.get("text_sha256") != section["text_sha256"] and entry.get("status") == "absent-from-current-manual":
                entry["status"] = "unreviewed"
            entry.update(section)
        else:
            entry = dict(id="MAN-%03d" % next_number, classification="pending-statement-reconciliation",
                         requirements=[], status="unreviewed", **section)
            next_number += 1
        result.append(entry)
    for section in old:
        if id(section) not in used:
            entry = dict(section)
            entry["status"] = "absent-from-current-manual"
            result.append(entry)
    return result + kept


def relocate_statements(mappings, historical_manual=None):
    """Point each statement mapping at the line that still carries its text
    (nearest to the recorded line). A text that no longer exists keeps its
    mapping and is flagged for review; its requirements are never dropped."""
    cache = {}
    result = []
    for mapping in mappings:
        source = dict(mapping["source"])
        path = source["path"]
        if path not in cache:
            source_path = historical_manual["path"] if historical_manual and path == "README.md" else path
            cache[path] = (REPO / source_path).read_text(encoding="utf8").split("\n")
        lines = cache[path]
        found = [index + 1 for index, line in enumerate(lines) if source["text"] in line]
        entry = dict(mapping)
        if found:
            line = min(found, key=lambda number: abs(number - source["line"]))
            source["line"] = line
            source["sha256"] = hashlib.sha256(lines[line - 1].encode()).hexdigest()
            entry.pop("source_status", None)
        else:
            entry["source_status"] = "text-absent-review-required"
        entry["source"] = source
        result.append(entry)
    return result


def image_references(inventory, manual_text):
    """Every image the README shows, in order, with its line and file digest.
    An image keeps its review status when its reference is unchanged."""
    previous = {r["reference"]: r for r in inventory["image_references"]}
    result = []
    for number, line in enumerate(manual_text.split("\n"), 1):
        for reference in re.findall(r'(?:src="|\]\()([^")\s]*images/[^")\s]+)', line):
            path = reference[reference.index("images/"):]
            entry = dict(previous.get(reference, dict(status="pending-visual-spec-reconciliation")))
            entry.update(source="README.md", line=number, reference=reference, path=path)
            if (REPO / path).is_file():
                entry["sha256"] = digest(REPO / path)
            result.append(entry)
    return result



ORIGINAL_README_SHA256="532f08b5fff1d2b90022f02ba418dcbef3b77017e8a1a5c6e057d04a9e41b51c"
ORIGINAL_CHEAT_SHA256="edf0df405c75727a8ff29a16d3640b71af2c6bfe4b5ddb5db603474e02bed561"

def original_identity():
    path="manual/legacy/README-1.4.0.md"
    if not (REPO/path).is_file() or digest(REPO/path)!=ORIGINAL_README_SHA256:
        raise ValueError("Original README archive identity changed")
    return dict(original_path="README.md",path=path,sha256=ORIGINAL_README_SHA256)

def freeze_sources(inventory):
    """Plan immutable source revisions; never create snapshots before validation."""
    original=original_identity()
    cheat_original="manual/legacy/cheat-sheet-1.4.0.html"
    if not (REPO/cheat_original).is_file() or digest(REPO/cheat_original)!=ORIGINAL_CHEAT_SHA256:
        raise ValueError("Original cheat archive identity changed")
    manual_sections((REPO/"README.md").read_text()) # A short overview cannot masquerade as the full manual.
    updated=copy.deepcopy(inventory);snapshots={};aliases={}
    for original_path,stem,suffix in [("README.md","README-before-authority",".md"),("cheat_sheet.html","cheat-sheet-before-authority",".html")]:
        raw=(REPO/original_path).read_bytes()
        identity=hashlib.sha256(raw).hexdigest()
        path="manual/legacy/"+stem+"-"+identity+suffix
        if (REPO/path).exists() and (REPO/path).read_bytes()!=raw:raise ValueError("Immutable source snapshot changed")
        snapshots[path]=raw
        aliases[original_path]=dict(path=path,sha256=identity,original_path=original_path)
    def content(path):
        return snapshots[path] if path in snapshots else (REPO/path).read_bytes()
    def archived_source(source):
        candidates=[]
        if source["path"].startswith("manual/legacy/"):candidates.append(source["path"])
        if source["path"]=="README.md":candidates.extend([original["path"],aliases["README.md"]["path"]])
        elif source["path"]=="cheat_sheet.html":candidates.extend([cheat_original,aliases["cheat_sheet.html"]["path"]])
        if not candidates:return copy.deepcopy(source)
        for candidate in dict.fromkeys(candidates):
            lines=content(candidate).decode("utf8").split("\n")
            matches=[i+1 for i,line in enumerate(lines) if source["text"] in line and hashlib.sha256(line.encode()).hexdigest()==source["sha256"]]
            if matches:
                line=min(matches,key=lambda n:abs(n-source["line"]))
                return dict(source,path=candidate,line=line)
        raise ValueError("No exact historical source line/hash for: "+source["text"])
    for mapping in updated["statement_mappings"]:
        mapping.setdefault("historical_source",copy.deepcopy(mapping["source"]))
        mapping.setdefault("historical_record",copy.deepcopy({k:v for k,v in mapping.items() if k!="historical_record"}))
        mapping["source"]=archived_source(mapping["source"])
        if mapping.get("source_status"):raise ValueError("Unreviewed historical statement cannot be archived")
        if mapping.get("current_claims"):
            mapping.setdefault("current_claim_history",copy.deepcopy(mapping["current_claims"]))
            mapping["current_claims"]=[archived_source(claim) for claim in mapping["current_claims"]]
    for requirement in updated["requirements"]:
        if requirement.get("current_control_review",{}).get("claims"):
            review=requirement["current_control_review"]
            review.setdefault("historical_claim_records",copy.deepcopy(review["claims"]))
            review["claims"]=[archived_source(claim) for claim in review["claims"]]
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"tools"))
    from manual_quick_reference import legacy_rows
    rows=legacy_rows(REPO/cheat_original)
    if len(rows)!=77:raise ValueError("Original cheat row inventory is not exactly 77")
    updated["legacy_cheat_history"]=dict(path=cheat_original,sha256=ORIGINAL_CHEAT_SHA256,rows=rows,scope="All original quick-reference rows retained verbatim; content preservation is not native acceptance.")
    updated["original_manual"]=original
    updated["manual_source_aliases"]=aliases
    updated["section_manual"]=copy.deepcopy(aliases["README.md"])
    updated["manual"]=aliases["README.md"]["path"]
    updated["manual_sha256"]=aliases["README.md"]["sha256"]
    updated["source_transition"]=dict(status="frozen-provisional-full-manual",authority_active=False,complete_regression_run=False)
    return updated,snapshots

def canonical_registry():
    path=REPO/"tests/behaviour/cases.py"
    if not path.is_file():return {},{} # Standalone fixture inventories have no canonical app registry.
    sys.path.insert(0,str(path.parent))
    import cases
    if Path(cases.__file__).resolve()!=path.resolve():raise ValueError("Canonical case registry loaded from another repository")
    return cases.CASES,dict(path="tests/behaviour/cases.py",sha256=digest(path))

def add_registered_cases(inventory,registry,source):
    """Add declared canonical links without changing any historical requirement claim."""
    updated=copy.deepcopy(inventory)
    requirements={row["id"]:row for row in updated["requirements"]}
    unknown=[(case,requirement) for case,spec in registry.items() for requirement in spec.get("requirements",[]) if requirement not in requirements]
    if unknown:raise ValueError("Unknown canonical requirement registrations: "+repr(unknown))
    for case,spec in registry.items():
        added=[]
        prior_cases=sorted({identifier for row in updated["requirements"] for identifier in row["cases"]})
        for requirement in dict.fromkeys(spec.get("requirements",[])):
            if case not in requirements[requirement]["cases"]:
                requirements[requirement]["cases"].append(case);added.append(requirement)
        if added:
            updated.setdefault("inventory_extensions",[]).append(dict(kind="additive-canonical-registration",case=case,requirements=added,registration_source=copy.deepcopy(source),description=spec.get("description",""),prior_case_count=len(prior_cases),prior_case_ids_sha256=hashlib.sha256(json.dumps(prior_cases,separators=(",",":")).encode()).hexdigest(),acceptance="Registration only; native qualification and remaining requirement domains are not promoted.",complete_regression_run=False))
    return updated

def link_case_extensions(matrix,inventory):
    """Extend domain traceability; registration never closes domain/native gaps."""
    revised=copy.deepcopy(matrix)
    for extension in inventory.get("inventory_extensions",[]):
        case=extension["case"]
        requirements=extension.get("requirements",[extension["requirement"]] if "requirement" in extension else [])
        domains=[]
        for domain in revised.get("domains",[]):
            if set(requirements)&set(domain.get("requirement_ids",[])):
                if case not in domain.setdefault("linked_behaviour_cases",[]):domain["linked_behaviour_cases"].append(case)
                domains.append(domain["id"])
        if domains and not any(row["case"]==case for row in revised.get("case_registration_extensions",[])):
            revised.setdefault("case_registration_extensions",[]).append(dict(case=case,requirements=requirements,domains=domains,scope="Additive canonical traceability only; historical linked cases, domain status and gaps remain unchanged.",complete_regression_run=False))
    if revised.get("domains"):
        covered={identifier for domain in revised["domains"] for identifier in domain.get("requirement_ids",[])}
        declared={row["id"] for row in inventory["requirements"]}
        revised["current_inventory_counts"]=dict(manual_requirements=len(declared),domain_requirements=len(covered),case_ids=len({case for row in inventory["requirements"] for case in row["cases"]}),outside_domain_requirement_ids=sorted(declared-covered),scope="Current source inventory, not a completed campaign.")
    return revised

def plan_transition(inventory,matrix,freeze=False,prepare=False,activate=False):
    """Return the complete transaction. Every failing gate runs before any write."""
    registry,registration_source=canonical_registry()
    updated=add_registered_cases(inventory,registry,registration_source);snapshots={}
    activate=activate or (prepare and inventory.get("manual_authority",{}).get("status")=="active")
    if freeze and inventory.get("manual_authority",{}).get("status")=="active":raise ValueError("Cannot freeze provisional sources after activation")
    book=load_compiled(REPO) if activate else None
    if activate and book.get("complete_manual") is not True:
        raise ValueError("Manual content migration incomplete: review all features before activating authority")
    if freeze or (activate and not updated.get("section_manual")):
        updated,snapshots=freeze_sources(updated)
    if prepare or activate:
        authored=load_authored(REPO)
        crossrefs=json.loads((REPO/"manual/inventory.json").read_text())
        section_ids={sid:f["id"] for f in crossrefs["features"] for sid in f["readme"]["section_ids"]}
        links=feature_links(updated,authored["features"],section_ids)
        missing=[s["id"] for s in updated["sections"] if s["id"].startswith("MAN-") and s.get("status")!="absent-from-current-manual" and not links.get(s["id"])]
        if missing:raise ValueError("Missing feature links: "+",".join(missing))
        updated["manual_authority"]=dict(status="active" if activate else "inactive",prepared=True,feature_links=links,campaign_complete=False)
        if activate:
            historical=original_identity()
            if updated.get("original_manual",historical)!=historical:raise ValueError("Original README identity changed")
            updated["historical_manual"]=historical
            updated["manual"]="manual/book.yaml"
            updated["manual_authority"]["identity"]=authoring_identity(REPO)
            verify_authority(REPO,updated)
            updated["source_transition"]=dict(status="yaml-authority-active",authority_active=True,complete_regression_run=False)
    elif updated.get("manual_authority"):
        verify_authority(REPO,updated)
    def bytes_for(path):
        if path in snapshots:return snapshots[path]
        return (REPO/path).read_bytes()
    def file_digest(path):return hashlib.sha256(bytes_for(path)).hexdigest()
    if updated.get("section_manual"):
        item=updated["section_manual"]
        if file_digest(item["path"])!=item["sha256"]:raise ValueError("Frozen manual source changed")
        section_path=item["path"]
    elif updated.get("historical_manual"):section_path=updated["historical_manual"]["path"]
    else:section_path=updated["manual"]
    updated["manual_sha256"]=file_digest(updated["manual"])
    for source in updated["manual_sources"]:
        if "path" in source:
            alias=updated.get("manual_source_aliases",{}).get(source["path"])
            path=alias["path"] if alias else (updated["historical_manual"]["path"] if updated.get("historical_manual") and source["path"]=="README.md" else source["path"])
            source["sha256"]=file_digest(path)
    manual_text=bytes_for(section_path).decode("utf8")
    updated["sections"]=reconcile(updated,manual_text)
    # Frozen mappings already cite exact immutable revisions and are verified after snapshots exist.
    if not snapshots:updated["statement_mappings"]=relocate_statements(updated["statement_mappings"],updated.get("historical_manual"))
    updated["image_references"]=image_references(updated,manual_text)
    revised=link_case_extensions(matrix,updated)
    revised.update(manual=updated["manual"],manual_sha256=updated["manual_sha256"],inventory_sha256=hashlib.sha256((json.dumps(updated,indent=1)+"\n").encode()).hexdigest())
    return updated,revised,snapshots

def commit_transition(updated,matrix,snapshots):
    """Preserve snapshots, then atomically replace each gate file with rollback."""
    for relative,raw in snapshots.items():
        target=REPO/relative;target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():
            if target.read_bytes()!=raw:raise ValueError("Immutable source snapshot changed")
        else:
            with target.open("xb") as handle:handle.write(raw)
    before={p:p.read_bytes() for p in (INVENTORY,MATRIX)};temps={}
    try:
        for path,value in [(INVENTORY,updated),(MATRIX,matrix)]:
            temp=path.with_suffix(path.suffix+".transition.tmp")
            with temp.open("x") as handle:json.dump(value,handle,indent=1);handle.write("\n")
            temps[path]=temp
        for path,temp in temps.items():temp.replace(path)
    except BaseException:
        for path,raw in before.items():path.write_bytes(raw)
        raise
    finally:
        for temp in temps.values():
            if temp.exists():temp.unlink()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true")
    parser.add_argument("--plan",action="store_true",help="Validate and describe a transaction without writing files")
    parser.add_argument("--freeze-manual-sources",action="store_true",help="Archive the final full pre-overview README/cheat and preserve all original citations")
    parser.add_argument("--prepare-authority",action="store_true",help="Prepare stable mappings with YAML authority explicitly inactive")
    parser.add_argument("--activate-authority",action="store_true",help="Activate only a complete, current compiled manual")
    options=parser.parse_args(argv)
    inventory=json.loads(INVENTORY.read_text());matrix=json.loads(MATRIX.read_text())
    updated,revised,snapshots=plan_transition(inventory,matrix,freeze=options.freeze_manual_sources,prepare=options.prepare_authority,activate=options.activate_authority)
    inventory_text=json.dumps(updated,indent=1)+"\n";matrix_text=json.dumps(revised,indent=1)+"\n"
    if options.plan:
        print(json.dumps(dict(manual=updated["manual"],manual_authority=updated.get("manual_authority"),snapshots={path:hashlib.sha256(raw).hexdigest() for path,raw in snapshots.items()},original_manual=updated.get("original_manual"),section_manual=updated.get("section_manual"),sections=len(updated["sections"]),requirements=len(updated["requirements"]),cases=len({case for row in updated["requirements"] for case in row["cases"]}),writes_performed=False),indent=2));return
    if options.check:
        stale=[p.name for p,text in ((INVENTORY,inventory_text),(MATRIX,matrix_text)) if p.read_text()!=text]
        stale += [path for path,raw in snapshots.items() if not (REPO/path).is_file() or (REPO/path).read_bytes()!=raw]
        if stale:sys.exit("stale: "+", ".join(stale)+"; run tests/behaviour/reconcile_manual.py")
        verify_manual_sources(REPO,updated)
        print("manual inventory current");return
    commit_transition(updated,revised,snapshots)
    added=[s["id"] for s in updated["sections"] if s["id"] not in {o["id"] for o in inventory["sections"]}]
    absent=[s["id"] for s in updated["sections"] if s.get("status")=="absent-from-current-manual"]
    missing=[m["source"]["text"] for m in updated["statement_mappings"] if m.get("source_status")]
    print("sections",len(updated["sections"]),"added",added,"absent",absent,"statements needing review",missing)
if __name__=="__main__":main()
