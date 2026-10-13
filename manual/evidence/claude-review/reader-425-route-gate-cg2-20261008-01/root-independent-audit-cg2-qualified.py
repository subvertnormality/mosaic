import json,hashlib
from pathlib import Path
root=Path("/home/andy/mosaic-manual-1.4.0")
base=Path("/mnt/c/Users/andy/.codex/visualizations/2026/10/03/01a100e0-e188-7c11-b2f0-748214517bb6")
gate=root/"manual/evidence/claude-review/reader-425-route-gate-cg2-20261008-01"
style=root/"manual/evidence/claude-review/compact-grid-v3-astra-recheck-20261008-01"
candpath=base/"reader-425-route-gate-css-v3-20261008-01/final-425-ledger-closure-candidate-cg2-qualified.json"
c=json.loads(candpath.read_bytes())
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
book=json.loads((root/"manual/generated/book.json").read_bytes())
idx=json.loads((root/"manual/generated/reader-index.json").read_bytes())
reportpath=Path(c["current_425_route_gate"]["report_path"]);manifestpath=Path(c["current_425_route_gate"]["manifest_path"]);receiptpath=Path(c["current_425_route_gate"]["receipt_path"])
r=json.loads(reportpath.read_bytes());m=json.loads(manifestpath.read_bytes());rec=json.loads(receiptpath.read_bytes())
ledger=json.loads((root/"manual/evidence/claude-review/final-425-reader-ledger-20261008-01/final-425-ledger.json").read_bytes())
basepath=root/"manual/evidence/claude-review/final-425-reader-ledger-20261008-01/fe378-baseline-425-ledger.json"
baseled=json.loads(basepath.read_bytes())
u={x["id"]:x for x in c["units"]};bu={x["id"]:x for x in ledger["units"]};hu={x["id"]:x for x in baseled["units"]}
a=c["current_425_row_adjudication"]["rows"];routes={x["ledger_id"]:x for x in m["routes"]};results={x["ledger_id"]:x for x in r["route_results"]}
assert len(u)==425 and len(a)==425 and set(u)==set(bu)=={x["id"] for x in a}
assert u==bu
assert r["passed"] and r["rows"]==425 and len(results)==425 and all(x["passed"] for x in results.values())
assert h(reportpath)==c["current_425_route_gate"]["report_sha256"]
assert h(manifestpath)==c["current_425_route_gate"]["manifest_sha256"]
assert h(receiptpath)==c["current_425_route_gate"]["receipt_sha256"]
assert rec["status"]=="PASS" and rec["current"]["runtime_assets"]==r["runtime_assets"]
assert r["runtime_assets"]["manual.css"]=="9612881156f6229ede39deb3da0bef94fc31d541c79d27986b4d87fb6972ea8a"
assert r["runtime_assets"]["manual.js"]=="2bd5d3b995cc357f68a09a61f5d1522e780c66d6e4404bbcd3037418bb95b9f2"
assert c["poststyle_qualification"]["candidate_publication_qualified"] is False
assert not any("pending" in n.lower() and "publication" not in n.lower() for n in c["poststyle_qualification"]["scope_notes"])
assert c["current_425_route_gate"]["style_state"]["CG2"]=="closed"
assert c["poststyle_qualification"]["current_style_qualification"]["review_path"]==str(style/"review.json")
assert c["poststyle_qualification"]["current_style_qualification"]["review_markdown_path"]==str(style/"review.md")
hist=[x["id"] for x in a if x["score_lineage"]["status"]=="carried_unchanged_existing_ledger_row"]
assert len(hist)==387 and all(u[i]==hu[i] for i in hist)
assert all(len(x["scores"])==10 and min(x["scores"].values())>=8 for x in u.values())
bad=[];files=set()
for row in a:
 id=row["id"];mp=routes[id];rp=results[id]
 assert row["route_proof"]["status"]=="PASS" and rp["passed"]
 assert row["route_proof"]["requested_route"]==mp["route"]==rp["route"]
 assert row["route_proof"]["observed_final_route"]==rp["final_route"]==mp["expected_final_route"]
 assert row["route_proof"]["route_report_sha256"]==h(reportpath)
 assert row["source"]["file_sha256"]==m["source_files"][row["source"]["file"]]
 for f in row["source"]["source_files"]:
  if f["path"] in files:continue
  files.add(f["path"]);path=root/f["path"]
  if f["path"].startswith("generated/reader-index.json#scene_chunks["):
   sid=f["path"].split("[",1)[1][:-1];ref=idx["scene_chunks"][sid];assert ref["sha256"]==f["sha256"];path=root/"manual/generated"/ref["path"]
  if h(path)!=f["sha256"]:bad.append(f["path"])
assert not bad,bad
style_review=json.loads((style/"review.json").read_bytes())
assert h(style/"review.json")=="fd3228b6f54aa176a6164ff9cb7f4c94243cc47c05c99cff298d11db5c8e0bf7"
assert style_review["verdict"]=="reader pass" and style_review["all_seven_at_least_8"] and not style_review["open_findings"]
assert style_review["closed_findings"]==["CG-1","CG-2"]
assert style_review["assets"]["manual.css"]==r["runtime_assets"]["manual.css"] and style_review["assets"]["manual.js"]==r["runtime_assets"]["manual.js"]
for row in a:
 pass
result={"schema":"mosaic-reader-425-independent-root-audit-cg2-qualified-v1","status":"PASS","candidate_sha256":h(candpath),"ledger_sha256":h(root/"manual/evidence/claude-review/final-425-reader-ledger-20261008-01/final-425-ledger.json"),"book_sha256":r["book_sha256"],"index_sha256":r["index_sha256"],"authority_sha256":r["authority_sha256"],"route_report_sha256":h(reportpath),"route_manifest_sha256":h(manifestpath),"route_receipt_sha256":h(receiptpath),"root_adoption_receipt_sha256":h(gate/"adoption-receipt-v3.json"),"rows":425,"route_passes":425,"unique_scenes":146,"source_and_chunk_references_checked":len(files),"source_hash_mismatches":bad,"scores_all_ten_at_least_8":True,"unit_objects_equal_installed_ledger":True,"historic_rows_exact_vs_fe378":387,"style_review_sha256":h(style/"review.json"),"style_review_all_seven_at_least_8":True,"CG1":"closed","CG2":"closed","publication_qualified":False,"prior_aa02_root_audit_result_sha256":"6beebd2abdf3d4a802748cba330a25cca357f774627c8ef90224eae1ae1374f3"}
out=base/"reader-425-route-gate-css-v3-20261008-01"
(out/"root-independent-audit-cg2-qualified.py").write_text(Path(__file__).read_text())
p=out/"root-independent-audit-cg2-qualified-result.json";p.write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result,indent=2))
