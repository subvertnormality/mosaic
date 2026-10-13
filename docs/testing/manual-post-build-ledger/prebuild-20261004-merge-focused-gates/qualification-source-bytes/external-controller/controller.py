#!/usr/bin/env python3
"""Read-only gate verification; publication requires a pinned operator attestation."""
import argparse, ctypes, datetime, hashlib, json, os, re, secrets, sys
from pathlib import Path

BUILDER_SHA = "a59e8f2f1e3913033f4c7f3981d364e625f4d30dabf733367d3aa70450d364c8"
OWNER = {"pid", "proc_starttime", "evidence_dir", "builder_sha256", "builder_argv_sha256"}
REQUEST = OWNER | {"schema_version", "stage_index", "stage_name", "stage_sha256", "argv_sha256", "previous_receipt", "nonce"}
SERVICES = {"matron", "crone", "sclang", "jackd", "jackdmp", "jackdbus"}
class Refusal(ValueError): pass

def require(condition, message):
    if not condition: raise Refusal(message)
def blob(value): return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)+"\n").encode()
def sha(data): return hashlib.sha256(data).hexdigest()
def hexsha(value): return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None
def integer(value): return type(value) is int and value > 0
def absolute(value):
    require(type(value) is str and value.startswith("/"), "absolute path required")
    path=Path(value)
    require(str(path.resolve()) == value, "noncanonical or symlink path: "+value)
    return path

def read(path):
    path=absolute(str(path))
    require(path.is_file() and not path.is_symlink(), "missing regular file: "+str(path))
    return path.read_bytes()
def object_pairs(pairs):
    result={}
    for key,value in pairs:
        require(key not in result, "duplicate JSON key: "+key); result[key]=value
    return result

def decode(data):
    try: return json.loads(data, object_pairs_hook=object_pairs, parse_constant=lambda v: (_ for _ in ()).throw(Refusal("invalid JSON number")))
    except (UnicodeError, json.JSONDecodeError) as error: raise Refusal("invalid JSON") from error

def pinned(path, expected):
    require(hexsha(expected), "invalid SHA pin")
    data=read(path); require(sha(data)==expected, "file SHA mismatch: "+str(path))
    return decode(data)

def process(pid, proc):
    require(integer(pid), "invalid PID")
    try:
        fields=(proc/str(pid)/"stat").read_text().rsplit(")",1)[1].split()
        require(fields[0] not in {"Z", "X", "x"}, "builder is not alive")
        require((proc/str(pid)).stat().st_uid==os.geteuid() or os.geteuid()==0, "builder process owned by another user")
        start=fields[19]; require(start.isdigit(), "invalid process starttime")
        argv=(proc/str(pid)/"cmdline").read_bytes()
        require(argv.endswith(b"\0") and argv != b"\0", "empty process argv")
        return start,argv
    except (OSError, IndexError) as error: raise Refusal("builder process unavailable") from error

def native_absent(proc):
    found=[]
    try: entries=list(proc.iterdir())
    except OSError as error: raise Refusal("cannot enumerate process table") from error
    for entry in entries:
        if not entry.name.isdigit(): continue
        try: name=(entry/"comm").read_text().strip()
        except FileNotFoundError: continue
        except OSError as error: raise Refusal("cannot inspect process "+entry.name) from error
        if name in SERVICES: found.append((int(entry.name),name))
    require(not found, "native services present: "+repr(found))

def stage_identity(record, row):
    stage=row["stage"]
    require(all(k in record for k in stage) and blob({k:record[k] for k in stage})==blob(stage), "prior stage identity differs")
    require(record.get("passed") is True and type(record.get("finished_utc")) is str and record["finished_utc"], "prior stage not successfully finished")
    try: finished=datetime.datetime.fromisoformat(record["finished_utc"])
    except ValueError: raise Refusal("invalid prior finish timestamp")
    require(finished.tzinfo is not None and finished.utcoffset()==datetime.timedelta(0), "prior finish timestamp must be UTC")
    if "executed_command" in record:
        require(record["executed_command"]==row["command"] and type(record.get("returncode")) is int and record["returncode"]==0, "prior command failed or changed")
    else:
        require(bool(stage.get("action")) and not any(stage["action"].get(k) for k in ("doctor_publish","course_bind","doctor_ready","doctor_options_audit")), "missing prior executed command")

def cleanup_report(report):
    """Only the native case-scene schema proves enumerated participant cleanup."""
    if type(report) is not dict or type(report.get("scenes")) is not list or not report["scenes"]: return False
    participants=[]
    for scene in report["scenes"]:
        evidence=scene.get("evidence",{})
        if type(evidence.get("session_context")) is not dict or type(evidence.get("case_participants")) is not list: return False
        participants.append(evidence); participants.extend(evidence["case_participants"])
        pp=evidence.get("case_participants_path"); ph=evidence.get("case_participants_sha256")
        if pp and ph:
            require(pinned(pp,ph)==evidence["case_participants"], "participant manifest changed")
        else: return False
    seen=set()
    for evidence in participants:
        root=absolute(evidence["path"])
        if str(root) in seen: continue
        seen.add(str(root))
        context=pinned(root/"session-context.json",evidence.get("session_context_sha256"))
        require(context==evidence["session_context"], "session context differs")
        require(context.get("finished") is True and context.get("cleanup_verified") is True and type(context.get("held_inputs")) is list and context["held_inputs"]==[], "unfinished session or held inputs")
        rows=pinned(root/"native/cleanup.json",evidence.get("cleanup_sha256"))
        require(type(rows) is list and rows, "missing cleanup service rows")
        names=set()
        for row in rows:
            name=row.get("service"); code=row.get("returncode")
            require(type(name) is str and name not in names and integer(row.get("pid")), "invalid cleanup row")
            names.add(name)
            require(type(code) is int and code in ({0,-15} if name in {"sclang","crow"} else {0}), "cleanup service failed")
        require({"matron","crone","sclang","jack"} <= names, "cleanup service inventory incomplete")
    return True

def verification(request_path, plan_path, plan_sha, proc=Path("/proc")):
    plan=pinned(plan_path,plan_sha)
    require(type(plan) is dict and set(plan)=={"schema_version","builder_path","builder_sha256","builder_argv","evidence_dir","stages"} and type(plan["schema_version"]) is int and plan["schema_version"]==1, "invalid plan schema")
    require(plan["builder_sha256"]==BUILDER_SHA and sha(read(plan["builder_path"]))==BUILDER_SHA, "builder source not pinned candidate")
    require(type(plan["builder_argv"]) is list and plan["builder_argv"] and all(type(v) is str and v and "\0" not in v for v in plan["builder_argv"]), "invalid builder argv plan")
    require(plan["builder_path"] in plan["builder_argv"], "builder script absent from planned argv")
    evidence=absolute(plan["evidence_dir"]); require(evidence.is_dir(), "evidence directory missing")
    gate_arg=None
    for n,arg in enumerate(plan["builder_argv"]):
        if arg=="--stage-gate-dir" and n+1<len(plan["builder_argv"]): gate_arg=plan["builder_argv"][n+1]
        elif arg.startswith("--stage-gate-dir="): gate_arg=arg.split("=",1)[1]
    require(gate_arg is not None and str(absolute(gate_arg))==str(Path(request_path).parent.resolve()), "request outside builder gate directory")
    raw=read(request_path); request=decode(raw)
    require(type(request) is dict and set(request)==REQUEST and blob(request)==raw, "request schema or canonical bytes differ")
    require(type(request["schema_version"]) is int and request["schema_version"]==1 and integer(request["pid"]) and integer(request["stage_index"]), "request integer types differ")
    require(type(request["proc_starttime"]) is str and request["proc_starttime"].isdigit(), "invalid request starttime")
    require(type(request["nonce"]) is str and re.fullmatch(r"[0-9a-f]{32}",request["nonce"]), "invalid nonce")
    require(all(hexsha(request[k]) for k in ("stage_sha256","argv_sha256","builder_sha256","builder_argv_sha256")), "invalid request hash")
    request_sha=sha(raw); stem=f"{request['stage_index']:03d}-{request_sha}"
    require(Path(request_path).name==stem+".request.json", "request filename SHA/index differs")
    owner=decode(read(Path(request_path).parent/"owner.json"))
    require(type(owner) is dict and set(owner)==OWNER and blob(owner)==blob({k:request[k] for k in OWNER}), "owner identity differs")
    start,argv=process(request["pid"],proc)
    planned_argv=b"\0".join(v.encode() for v in plan["builder_argv"])+b"\0"
    require(start==request["proc_starttime"] and argv==planned_argv and sha(argv)==request["builder_argv_sha256"], "live builder identity differs")
    require(request["builder_sha256"]==BUILDER_SHA and request["evidence_dir"]==str(evidence), "request source/evidence differs")
    rows=plan["stages"]; index=request["stage_index"]
    require(type(rows) is list and index<=len(rows), "stage outside plan")
    names=[]
    for row in rows:
        require(type(row) is dict and set(row)=={"stage","command"} and type(row["stage"]) is dict and type(row["command"]) is list and all(type(v) is str for v in row["command"]), "invalid planned stage")
        name=row["stage"].get("name"); require(type(name) is str and re.fullmatch(r"[a-zA-Z0-9_-]+",name), "unsafe stage name")
        names.append(name)
    require(len(set(names))==len(names), "duplicate stage name")
    row=rows[index-1]
    require(request["stage_name"]==row["stage"]["name"] and request["stage_sha256"]==sha(blob(row["stage"])) and request["argv_sha256"]==sha(blob(row["command"])), "planned stage identity differs")
    previous=request["previous_receipt"]; records=[]
    if index==1: require(previous is None, "unexpected preceding receipt")
    else:
        require(type(previous) is dict and set(previous)=={"path","sha256"}, "missing preceding receipt")
        last=evidence/(names[index-2]+".json")
        require(previous["path"]==str(last), "preceding receipt path differs")
        pinned(last,previous["sha256"])
    for number in range(index-1):
        receipt=evidence/(names[number]+".json"); record=decode(read(receipt)); stage_identity(record,rows[number])
        if "log_sha256" in record: require(sha(read(evidence/(names[number]+".log")))==record["log_sha256"], "prior log changed")
        records.append(record)
    cleanup="not-applicable-first-stage"; report_pin=None
    if records:
        reference=records[-1].get("native_report")
        if reference:
            require(type(reference) is dict and set(reference)=={"path","sha256"}, "invalid native report pin")
            report=pinned(reference["path"],reference["sha256"]); report_pin=reference["sha256"]
            require(report.get("passed",True) is True, "native report failed")
            cleanup="native-participant-files" if cleanup_report(report) else "external-root-review-required"
        else: cleanup="external-root-review-required"
    native_absent(proc)
    release=Path(request_path).with_name(stem+".resume.json")
    require(not release.exists() and not release.is_symlink(), "duplicate release exists")
    require(not (evidence/"stage-gates"/(stem+".json")).exists(), "request already accepted")
    require(not list((evidence/"stage-gates").glob(f"{index:03d}-*.json")), "stage already accepted")
    resume={k:request[k] for k in OWNER | {"stage_index","stage_name","argv_sha256","nonce"}}
    resume["request_sha256"]=request_sha
    return dict(request=request,request_sha256=request_sha,resume=resume,release=str(release),cleanup_scope=cleanup,report_sha256=report_pin)

def external_checks(result, path, pin, now=None):
    checks=pinned(path,pin)
    required={"schema_version","request_sha256","stage_sha256","previous_receipt_sha256","checked_utc","memory_preflight"}
    require(type(checks) is dict and required <= set(checks) and set(checks)<=required|{"cleanup_review"}, "invalid external check schema")
    request=result["request"]; previous=request["previous_receipt"]
    require(type(checks["schema_version"]) is int and checks["schema_version"]==1 and checks["request_sha256"]==result["request_sha256"] and checks["stage_sha256"]==request["stage_sha256"] and checks["previous_receipt_sha256"]==(previous["sha256"] if previous else None), "external checks not bound to request")
    try: instant=datetime.datetime.fromisoformat(checks["checked_utc"])
    except (TypeError,ValueError): raise Refusal("invalid check timestamp")
    require(instant.tzinfo is not None and instant.utcoffset()==datetime.timedelta(0), "check timestamp must be UTC")
    age=((now or datetime.datetime.now(datetime.timezone.utc))-instant).total_seconds()
    require(-5<=age<=300, "external checks stale or future")
    require(blob(checks["memory_preflight"])==blob({"passed":True,"scope":"entire-next-stage"}), "whole-stage memory preflight required")
    if result["cleanup_scope"]=="external-root-review-required":
        review=checks.get("cleanup_review",{})
        require(type(review) is dict and set(review)=={"passed","scope","report_sha256","assertions","evidence"}, "external cleanup review required")
        require(review["passed"] is True and review["scope"]=="all-prior-stage-native-participants" and review["report_sha256"]==result["report_sha256"], "external cleanup scope differs")
        require(blob(review["assertions"])==blob({"finished":True,"no_held_inputs":True,"cleanup_verified":True}), "external cleanup assertions required")
        require(type(review["evidence"]) is list and review["evidence"], "external cleanup evidence required")
        for ref in review["evidence"]:
            require(type(ref) is dict and set(ref)=={"path","sha256"}, "invalid external evidence reference")
            require(sha(read(ref["path"]))==ref["sha256"], "external cleanup evidence changed")
        result["cleanup_scope"]="external-root-review"
    return checks

def publish_exclusive(path, value):
    path=Path(path); temporary=path.parent/(".resume-"+secrets.token_hex(16)+".tmp")
    library=ctypes.CDLL(None,use_errno=True)
    require(hasattr(library,"renameat2"), "renameat2 unavailable; refusing publication")
    rename=library.renameat2; rename.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]; rename.restype=ctypes.c_int
    try:
        descriptor=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(descriptor,"wb") as handle:
            handle.write(blob(value)); handle.flush(); os.fsync(handle.fileno())
        if rename(-100,os.fsencode(temporary),-100,os.fsencode(path),1)!=0:
            error=ctypes.get_errno(); raise Refusal("exclusive rename failed: "+os.strerror(error))
        descriptor=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try: os.fsync(descriptor)
        finally: os.close(descriptor)
    finally:
        if temporary.exists(): temporary.unlink()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request",required=True); parser.add_argument("--plan",required=True); parser.add_argument("--plan-sha256",required=True)
    parser.add_argument("--checks"); parser.add_argument("--checks-sha256"); parser.add_argument("--publish",action="store_true")
    args=parser.parse_args()
    try:
        result=verification(args.request,args.plan,args.plan_sha256)
        if args.publish:
            require(args.checks and args.checks_sha256, "pinned external checks required for release")
            external_checks(result,args.checks,args.checks_sha256)
            # Repeat all read-only checks immediately before the exclusive publication.
            result=verification(args.request,args.plan,args.plan_sha256)
            external_checks(result,args.checks,args.checks_sha256)
            publish_exclusive(result["release"],result["resume"])
        result["published"]=args.publish
        print(json.dumps(result,sort_keys=True,indent=2)); return 0
    except (Refusal,OSError,KeyError,TypeError,ValueError) as error:
        print(json.dumps({"published":False,"refused":str(error)},sort_keys=True),file=sys.stderr); return 2
if __name__=="__main__": sys.exit(main())
