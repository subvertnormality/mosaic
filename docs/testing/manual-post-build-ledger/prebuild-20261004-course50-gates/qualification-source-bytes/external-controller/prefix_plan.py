#!/usr/bin/env python3
"""Append one exact resolved stage to an independently pinned complete original plan."""
import argparse, json, sys
from pathlib import Path
import controller as c

CONTEXT={"schema_version","builder_path","builder_sha256","builder_argv","evidence_dir"}
def extend(original, context, command, index, previous=None, expected_count=72):
    c.require(type(original) is list and len(original)==expected_count and expected_count>0, "original complete stage count differs")
    c.require(type(context) is dict and set(context)==CONTEXT and type(context["schema_version"]) is int and context["schema_version"]==1, "invalid bootstrap context")
    c.require(context["builder_sha256"]==c.BUILDER_SHA and c.sha(c.read(context["builder_path"]))==c.BUILDER_SHA, "bootstrap builder differs")
    c.require(c.absolute(context["evidence_dir"]).is_dir(), "bootstrap evidence directory unavailable")
    argv=context["builder_argv"]
    c.require(type(argv) is list and argv and all(type(v) is str and v and "\0" not in v for v in argv) and context["builder_path"] in argv, "invalid bootstrap argv")
    c.require(c.integer(index) and index<=len(original), "stage outside original plan")
    c.require(type(command) is list and all(type(v) is str for v in command), "invalid resolved command")
    names=[]
    for stage in original:
        c.require(type(stage) is dict and type(stage.get("name")) is str, "invalid original stage")
        names.append(stage["name"])
    c.require(len(set(names))==len(names), "duplicate original stage")
    if previous is None:
        c.require(index==1, "bootstrap must begin at stage one"); rows=[]
    else:
        c.require(type(previous) is dict and set(previous)==CONTEXT|{"stages"}, "invalid previous prefix")
        c.require(c.blob({k:previous[k] for k in CONTEXT})==c.blob(context), "bootstrap identity changed")
        rows=previous["stages"]
        c.require(type(rows) is list and len(rows)==index-1, "prefix must extend by exactly one stage")
        for number,row in enumerate(rows):
            c.require(type(row) is dict and set(row)=={"stage","command"} and c.blob(row["stage"])==c.blob(original[number]), "previous stage differs from original plan")
            c.require(type(row["command"]) is list and all(type(v) is str for v in row["command"]), "invalid previous resolved command")
    # Copy through JSON to prevent callers mutating an earlier accepted prefix by alias.
    return json.loads(c.blob(dict(context,stages=rows+[dict(stage=original[index-1],command=command)])))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("original-plan","context","command"):
        parser.add_argument("--"+name,required=True); parser.add_argument("--"+name+"-sha256",required=True)
    parser.add_argument("--previous-prefix"); parser.add_argument("--previous-prefix-sha256")
    parser.add_argument("--stage-index",type=int,required=True); parser.add_argument("--original-count",type=int,default=72)
    parser.add_argument("--output-directory",required=True)
    args=parser.parse_args()
    try:
        c.require(bool(args.previous_prefix)==bool(args.previous_prefix_sha256), "previous prefix path and pin required together")
        original=c.pinned(args.original_plan,args.original_plan_sha256); context=c.pinned(args.context,args.context_sha256); command=c.pinned(args.command,args.command_sha256)
        previous=c.pinned(args.previous_prefix,args.previous_prefix_sha256) if args.previous_prefix else None
        value=extend(original,context,command,args.stage_index,previous,args.original_count)
        output=c.absolute(args.output_directory); c.require(output.is_dir(), "version directory missing")
        pin=c.sha(c.blob(value)); stem=f"{args.stage_index:03d}-{pin}"
        plan_path=output/(stem+".plan.json"); receipt_path=output/(stem+".receipt.json")
        receipt=dict(schema_version=1,stage_index=args.stage_index,original_stage_count=args.original_count,original_plan=dict(path=str(c.absolute(args.original_plan)),sha256=args.original_plan_sha256),context=dict(path=str(c.absolute(args.context)),sha256=args.context_sha256),resolved_command=dict(path=str(c.absolute(args.command)),sha256=args.command_sha256),previous_prefix=None if previous is None else dict(path=str(c.absolute(args.previous_prefix)),sha256=args.previous_prefix_sha256),prefix=dict(path=str(plan_path),sha256=pin),release_published=False)
        c.require(not plan_path.exists() and not receipt_path.exists(), "duplicate plan version")
        c.publish_exclusive(plan_path,value); c.publish_exclusive(receipt_path,receipt)
        print(json.dumps(receipt,sort_keys=True,indent=2)); return 0
    except (c.Refusal,OSError,KeyError,TypeError,ValueError) as error:
        print(json.dumps({"release_published":False,"refused":str(error)}),file=sys.stderr); return 2
if __name__=="__main__": sys.exit(main())
