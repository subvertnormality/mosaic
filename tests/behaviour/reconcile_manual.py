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
import hashlib
import json
import re
import sys
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


def relocate_statements(mappings):
    """Point each statement mapping at the line that still carries its text
    (nearest to the recorded line). A text that no longer exists keeps its
    mapping and is flagged for review; its requirements are never dropped."""
    cache = {}
    result = []
    for mapping in mappings:
        source = dict(mapping["source"])
        path = source["path"]
        if path not in cache:
            cache[path] = (REPO / path).read_text(encoding="utf8").split("\n")
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


def main():
    check = "--check" in sys.argv
    inventory = json.loads(INVENTORY.read_text())
    manual = REPO / inventory["manual"]
    updated = dict(inventory)
    updated["manual_sha256"] = digest(manual)
    updated["manual_sources"] = [dict(source, sha256=digest(REPO / source["path"])) if "path" in source else source
                                 for source in inventory["manual_sources"]]
    updated["sections"] = reconcile(inventory, manual.read_text(encoding="utf8"))
    updated["statement_mappings"] = relocate_statements(inventory["statement_mappings"])
    updated["image_references"] = image_references(inventory, manual.read_text(encoding="utf8"))
    inventory_text = json.dumps(updated, indent=1) + "\n"
    matrix = json.loads(MATRIX.read_text())
    matrix["manual_sha256"] = updated["manual_sha256"]
    matrix["inventory_sha256"] = hashlib.sha256(inventory_text.encode()).hexdigest()
    matrix_text = json.dumps(matrix, indent=1) + "\n"
    if check:
        stale = [p.name for p, text in ((INVENTORY, inventory_text), (MATRIX, matrix_text)) if p.read_text() != text]
        if stale:
            sys.exit("stale: " + ", ".join(stale) + "; run tests/behaviour/reconcile_manual.py")
        print("manual inventory current")
        return
    INVENTORY.write_text(inventory_text)
    MATRIX.write_text(matrix_text)
    added = [s["id"] for s in updated["sections"] if s["id"] not in {o["id"] for o in inventory["sections"]}]
    absent = [s["id"] for s in updated["sections"] if s.get("status") == "absent-from-current-manual"]
    missing = [m["source"]["text"] for m in updated["statement_mappings"] if m.get("source_status")]
    print("sections", len(updated["sections"]), "added", added, "absent", absent, "statements needing review", missing)


if __name__ == "__main__":
    main()
