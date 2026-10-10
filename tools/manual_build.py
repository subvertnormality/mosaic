"""Rebuild manual captures, audio and publication from one explicit staged plan.

Every run receives a fresh immutable evidence directory. A completed manual
build is separate from the exhaustive behaviour campaign.
"""
import argparse,contextlib,datetime,hashlib,http.server,json,os,shutil,subprocess,sys,threading,time,uuid
from pathlib import Path
import yaml
from resume_adoption import prepare_resume, finalize_resume_source_start
from audio_report_adoption import prepare_audio_report_adoption
from manual_retained_midi_caller import retained_call, projection_arguments, required_producer_inventory
ROOT=Path(__file__).resolve().parents[1]
LOCK=Path("/tmp/mosaic-manual-native.lock")
DOCTOR_OPTION_STAGES={
 "doctor-options-manual-stereo-real":("manual_stereo","real-time","doctor-options-manual-stereo"),
 "doctor-options-auto-left-real":("auto_left","real-time","doctor-options-auto-left"),
 "doctor-options-manual-right-real":("manual_right","real-time","doctor-options-manual-right"),
 "doctor-options-setup-real":("setup_options","real-time","doctor-options-setup-real"),
 "doctor-options-setup-controlled":("setup_options","controlled-experimental","doctor-options-setup-controlled"),
 "doctor-options-ready-real":("ready_options","real-time","doctor-options-ready-real"),
 "doctor-options-ready-controlled":("ready_options","controlled-experimental","doctor-options-ready-controlled"),
}
DOCTOR_AUDIT_ROLES={"manual_stereo":"doctor-options-manual-stereo-real","auto_left":"doctor-options-auto-left-real","manual_right":"doctor-options-manual-right-real","setup_real":"doctor-options-setup-real","setup_controlled":"doctor-options-setup-controlled","ready_real":"doctor-options-ready-real","ready_controlled":"doctor-options-ready-controlled"}
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def safe_plan(name):
    value=Path(name)
    if value.name!=name or not name.startswith("scene-plans") or not name.endswith(".yaml"):
        raise ValueError("Unsafe plan path: "+name)
    return name
def scene_sources(plans,emitted):
    result=[safe_plan(name) for name in plans]
    for name in sorted(emitted):
        if Path(name).name!=name or not name.startswith("scenes-") or not name.endswith(".yaml"):
            raise ValueError("Unsafe emitted scene source: "+name)
        result.append("features/"+name)
    return list(dict.fromkeys(result))
def output_name(name,profile):
    suffix=Path(name).stem[len("scene-plans"):]
    if profile!="base-midi":suffix+="-"+profile
    return "reference"+suffix+"-scenes.json"
def validate_launch_mode(controlled_local,real_install):
    if not controlled_local and not real_install:raise ValueError("Full paired generation requires an explicit qualified real installation")

def plan(options,plans,controlled_local=False):
    retained=retained_call(ROOT,getattr(options,'retained_midi_admissions',None),getattr(options,'retained_midi_admissions_sha256',None),mode='retained-resume' if getattr(options,'resume_from',None) and (getattr(options,'retained_midi_admissions',None) or getattr(options,'retained_midi_admissions_sha256',None)) else 'fresh')
    if retained and not controlled_local:raise ValueError('Retained checkpoint projection is controlled-local only')
    retained_args=projection_arguments(ROOT,retained)
    fresh_args=[]
    def stage(name,command,emulator=None,lock=False,action=None):
        return dict(name=name,command=[str(v) for v in command],emulator=emulator,
                    exclusive_lock=lock,action=action)
    real_install=getattr(options,"real_install",None)
    if not real_install and not controlled_local:raise ValueError("Generic real captures require an explicit qualified real installation")
    py=getattr(options,"python",sys.executable)
    if not retained:
        fresh_args=["--fresh-target-midi-manifest","{evidence}/fresh-target-midi-manifest.json",
            "--fresh-target-midi-sha256","{fresh-midi-sha256}","--fresh-build-root","{evidence}"]
    capture=[py,str(ROOT/"tools/manual_capture.py")]
    audio_args=["--mod-code-root",options.mod_code_root,"--audio-emulator",options.audio_emulator,
                "--audio-install",options.audio_install,"--ffmpeg",options.ffmpeg]
    stages=[stage("masks-real",capture+audio_args+["--experimental-install",str(real_install)],options.emulator,True),
        stage("masks-controlled",capture+audio_args+["--visuals-only","--verify-only","--clock-mode",
          "controlled-experimental","--experimental-install",options.controlled_install],options.emulator,True)]
    first_sound=capture+["--source",str(ROOT/"manual/features/first-sound-capture.yaml"),"--visuals-only"]
    stages.extend([stage("first-sound-real",first_sound+["--clock-mode","real-time","--experimental-install",str(real_install)],options.emulator,True),
        stage("first-sound-controlled",first_sound+["--verify-only","--clock-mode",
            "controlled-experimental","--experimental-install",options.controlled_install],options.emulator,True)])
    if not plans or len(set(plans))!=len(plans):raise ValueError("Select unique nonempty plan files")
    outputs=[]
    for name in plans:
        safe_plan(name)
        path=ROOT/"manual"/name
        data=yaml.safe_load(path.read_text()) if path.is_file() else {"scenes":[]}
        profiles=sorted({s.get("profile","base-midi") for s in data["scenes"]}) or ["base-midi"]
        for profile in profiles:
            if profile not in ("base-midi","midi-modulation","manual-player-ui"):
                raise ValueError("Unsupported case plan profile: "+profile)
            outfile=output_name(name,profile);outputs.append(outfile)
            args=[py,str(ROOT/"tools/manual_case_capture.py"),"--plans",str(path),
                  "--profile",profile,"--output",outfile,"--output-root","{evidence}/scene-captures"]
            case_ids={s["behaviour_case"] for s in data["scenes"] if s.get("profile","base-midi")==profile}
            local_helpers=set()
            for case in case_ids:
                if case in ("M-MANUAL-REASON-001","M-MANUAL-SWING-001"):
                    local_helpers.add("manual_reason_swing_cases.py")
                elif case.startswith("M-MANUAL-COURSE-"):
                    local_helpers.add("manual_course_cases.py")
                elif case.startswith("M-MANUAL-CLOSURE-"):
                    local_helpers.add("manual_closure_cases.py")
                elif case == "M-MANUAL-PLAYER-APPLY-001":
                    local_helpers.add("manual_player_apply_cases.py")
                elif case in ("M-MANUAL-RESET-REPEAT-PUBLIC-001", "M-MANUAL-SNAP-MASK-PUBLIC-001", "M-MANUAL-UI-MOTION-FRAME-001"):
                    local_helpers.add("manual_native_public_gap_cases.py")
                elif case == "M-MANUAL-MODULATION-001":
                    local_helpers.add("manual_extra_matrix_macro_modest.py")
                elif case == "M-MANUAL-SAVE-DIALOG-001":
                    local_helpers.add("manual_save_dialog_cases.py")
            for helper in sorted(local_helpers):
                args += ["--extra-cases",str(ROOT/"tools"/helper)]
            emulator=options.emulator
            controlled=options.controlled_install
            if profile=="manual-player-ui":
                mod_root=getattr(options,"mod_code_root",None)
                if not mod_root:raise ValueError("Player UI plans require --mod-code-root for the pinned player source check")
                args += ["--mod-code-root",mod_root]
                label=Path(name).stem+"-"+profile
                stages.append(stage("reference-controlled-"+label,args+["--clock-mode","controlled-experimental",
                    "--experimental-install",controlled],emulator))
                continue
            if profile=="midi-modulation":
                mod_root=getattr(options,"modulation_code_root",None)
                if not mod_root:raise ValueError("Modulation plans require --modulation-code-root separately from voice sources")
                args+=["--mod-code-root",mod_root,"--mod-patches"]
                emulator=getattr(options,"modulation_emulator",None) or options.emulator
                controlled=getattr(options,"modulation_controlled_install",None) or options.controlled_install
            label=Path(name).stem+"-"+profile
            real_args=args+["--clock-mode","real-time","--publish"]
            installation=real_install
            if name=="scene-plans-readability.yaml":
                installation=getattr(options,"readability_real_install",None)
                if not installation and not controlled_local:raise ValueError("Real readability requires an explicit qualified output-boundary installation")
            real_args += ["--experimental-install",str(installation)]
            stages.append(stage("reference-real-"+label,real_args,emulator))
            stages.append(stage("reference-controlled-"+label,args+["--clock-mode","controlled-experimental",
                "--experimental-install",controlled],emulator))
    for mode,source in (("manual","doctor-scene.yaml"),("auto","doctor-auto-probe.yaml")):
        row=stage("doctor-"+mode+"-real",[py,str(ROOT/"tools/manual_doctor_capture.py"),
            "--source",str(ROOT/"manual"/source),"--audio-install",options.audio_install,
            "--output-root","{evidence}/doctor-"+mode],options.audio_emulator)
        row["doctor_capture"]=mode;stages.append(row)
    stages.append(stage("doctor-publish",[],action={"doctor_publish":True,"python":py}))
    outputs.append("doctor-scenes.json")
    for name,(case,clock,suffix) in DOCTOR_OPTION_STAGES.items():
        installation=options.audio_install if clock=="real-time" else options.controlled_install
        command=[py,str(ROOT/"tools/doctor_options_capture.py"),"--case",case,"--installation",installation,"--clock-mode",clock,"--output-root","{evidence}/"+suffix]
        if case=="manual_right":command.append("--save-ready-fixture")
        row=stage(name,command,options.audio_emulator,action={"doctor_ready":True} if case=="ready_options" else None)
        row["doctor_options"]=dict(case=case,clock_mode=clock,output_suffix=suffix)
        stages.append(row)
    stages.append(stage("doctor-options-audit",[],action={"doctor_options_audit":True,"python":py}))
    stages.append(stage("musical-audio",[py,str(ROOT/"tools/manual_audio.py"),"--mod-code-root",
        options.mod_code_root,"--audio-install",options.audio_install,"--ffmpeg",options.ffmpeg,
        "--midi-emulator",options.emulator,"--midi-real-install",str(real_install),"--midi-controlled-install",options.controlled_install],options.audio_emulator))
    stages.append(stage("player-routes",[py,str(ROOT/"tools/manual_player_routes.py")],options.audio_emulator))
    outputs.append("player-routes.json")
    stages.append(stage("refresh-scene-index",[],action={"plans":plans,"outputs":outputs}))
    stages.append(stage("refresh-editorial",[py,str(ROOT/"tools/manual_publication_verify.py"),"--refresh-editorial","--ffmpeg",options.ffmpeg]))
    stages.append(stage("raw-publication-audit",[py,str(ROOT/"tools/manual_publication_verify.py"),"--raw-only"]))
    stages.append(stage("caption-rebind",[py,str(ROOT/"tools/manual_caption_rebind.py"),"--evidence","{evidence}/caption-rebind"]))
    if "scene-plans-course.yaml" in plans:
        stages.append(stage("course-bind",[],action={"course_bind":True,"python":py}))
    stages.append(stage("feature-bind",[py,str(ROOT/"tools/manual_feature_bind.py"),"--build-evidence","{evidence}","--evidence","{evidence}/feature-bind"],options.audio_emulator))
    stages.append(stage("compile-book",[py,str(ROOT/"tools/manual_book.py")]))
    if not retained:
        stages.append(stage("fresh-target-midi-producer",[py,str(ROOT/"tools/manual_fresh_target_midi.py"),
            "--book",str(ROOT/"manual/generated/book.json"),"--project-root",str(ROOT),
            "--build-root","{evidence}","--output","{evidence}/fresh-target-midi-manifest.json"]))
    stages.append(stage("reader-projection",[py,str(ROOT/"tools/manual_reader_projection.py"),
        "--book",str(ROOT/"manual/generated/book.json"),
        "--audio",str(ROOT/"manual/generated/audio-scenes.json"),
        "--output-dir",str(ROOT/"manual/generated"),"--project-root",str(ROOT)]+retained_args+fresh_args))
    stages.append(stage("quick-reference",[py,str(ROOT/"tools/manual_quick_reference.py"),"--output",
        str(ROOT/getattr(options,"quick_output","manual/generated/quick-reference.html"))]))
    stages.append(stage("inventory",[py,str(ROOT/"tools/manual_inventory.py")],options.emulator))
    stages.append(stage("publication-audit",[py,str(ROOT/"tools/manual_publication_verify.py")]+retained_args+fresh_args))
    if options.browser_tests:
        node=getattr(options,"node","node")
        for name in ("manual_inline.cjs","manual_browser.cjs","manual_book_browser.cjs","manual_audio_race.cjs","manual_narrative_browser.cjs","manual_course_browser.cjs","manual_controls_browser.cjs","manual_reader_text_browser.cjs"):
            stages.append(stage("browser-"+Path(name).stem,[node,str(ROOT/"tests/behaviour"/name)]))
    return controlled_local_plan(stages) if controlled_local else stages

def controlled_local_plan(stages):
    """Select complete controlled manual-generation evidence and asset-only real work."""
    result=[]
    for stage in stages:
        name=stage["name"]
        if name in ("masks-real","first-sound-real") or name.startswith("reference-real-"):
            continue
        if name.startswith("doctor-options-"):
            continue
        if name in ("masks-controlled","first-sound-controlled"):
            command=stage["command"]
            if "--verify-only" in command:command.remove("--verify-only")
            if name=="masks-controlled" and "--visuals-only" in command:command.remove("--visuals-only")
            command.append("--controlled-local")
        elif name.startswith("reference-controlled-"):
            stage["command"] += ["--publish","--controlled-local"]
        elif name=="musical-audio":
            stage["name"]="musical-audio-assets"
            command=stage["command"]
            if "--midi-real-install" in command:
                index=command.index("--midi-real-install");del command[index:index+2]
            command.append("--controlled-local")
        elif name=="course-bind":
            stage["action"]["controlled_local"]=True
        elif name in ("caption-rebind","feature-bind"):
            stage["command"].append("--controlled-local")
        elif name=="raw-publication-audit":
            stage["command"].append("--controlled-local")
        elif name=="publication-audit":
            stage["command"] += ["--controlled-local","--build-evidence","{evidence}"]
        elif name=="doctor-options-audit":
            stage["action"]["controlled_local"]=True
        result.append(stage)
    return result
@contextlib.contextmanager
def exclusive(enabled):
    if not enabled:yield;return
    import fcntl
    with LOCK.open("a") as handle:
        fcntl.flock(handle,fcntl.LOCK_EX)
        yield
@contextlib.contextmanager
def preview(enabled):
    if not enabled:yield None;return
    handler=lambda *args,**kwargs:http.server.SimpleHTTPRequestHandler(*args,directory=str(ROOT),**kwargs)
    server=http.server.ThreadingHTTPServer(("127.0.0.1",0),handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield "http://127.0.0.1:"+str(server.server_port)+"/manual/"
    finally:server.shutdown();server.server_close();thread.join()
def refresh_index(action,evidence):
    expected=set(action["outputs"])
    generated=ROOT/"manual/generated";features=ROOT/"manual/features"
    expected_yaml={"scenes-"+Path(name).stem+".yaml" for name in expected}
    missing=[name for name in expected if not (generated/name).is_file()]
    missing += [name for name in expected_yaml if not (features/name).is_file()]
    if missing:raise ValueError("Missing emitted scene publication: "+",".join(sorted(missing)))
    archive=evidence/"previous-publication";archive.mkdir()
    for folder,pattern,keep in ((generated,"reference*.json",expected),(features,"scenes-*.yaml",expected_yaml)):
        for path in folder.glob(pattern):
            if path.name not in keep:
                target=archive/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(path,target);path.unlink()
    config=ROOT/"manual/book.yaml";book=yaml.safe_load(config.read_text())
    prior=[name for name in book.get("scene_sources",[]) if not name.startswith("scene-plans") and not name.startswith("features/scenes-")]
    emitted=[path.name for path in features.glob("scenes-*.yaml")]
    book["scene_sources"]=scene_sources(action["plans"],emitted)+prior
    config.write_text(yaml.safe_dump(book,sort_keys=False))
def case_capture_result(log,output_root=Path("/home/andy/mosaic-manual-runs"),validation_scope=None):
    lines=Path(log).read_text().splitlines()
    if not lines:raise ValueError("Missing final case report")
    folder=Path(lines[-1])
    if not folder.is_absolute():raise ValueError("Missing final case report path")
    path=(folder/"reference-scenes.json").resolve();root=Path(output_root).resolve()
    if root not in path.parents or not path.is_file():raise ValueError("Case report outside capture output")
    data=json.loads(path.read_text())
    if data.get("schema_version")!=1 or not data.get("scenes"):raise ValueError("Invalid case report")
    if validation_scope and (data.get("validation_scope")!=validation_scope or data.get("realtime_qualification")!="pending-ci" or data.get("clock_mode")!="controlled-experimental" or data.get("complete_regression_run") is not False):raise ValueError("Controlled manual-generation scope changed")
    return dict(path=str(path),sha256=digest(path))
def course_bind_command(evidence,python,controlled_local=False):
    arguments=[]
    lanes=(("controlled","controlled"),) if controlled_local else (("real","real"),("controlled","controlled"))
    for lane,flag in lanes:
        name="reference-"+lane+"-scene-plans-course-base-midi"
        record=json.loads((evidence/(name+".json")).read_text())
        if record.get("execution_status")=="adopted-verified":
            # An adopted stage's log is a stub; its report is proven through the adoption proof.
            from resume_adoption import verify_adopted_reference_stage
            report=verify_adopted_reference_stage(evidence,name,record,ROOT)
            checked=dict(path=report,sha256=digest(report))
        else:checked=case_capture_result(evidence/(name+".log"),evidence/"scene-captures")
        if record.get("passed") is not True or record.get("native_report")!=checked:
            raise ValueError("Course capture receipt changed: "+lane)
        arguments.extend(["--"+flag+"-report",checked["path"]])
    command=[python,str(ROOT/"tools/manual_course_bind.py")]+arguments+["--evidence",str(evidence/"course-bind")]
    if controlled_local:command += ["--controlled-report",checked["path"],"--controlled-local"]
    return command
def doctor_capture_result(log,output_root):
    lines=Path(log).read_text().splitlines()
    try:summary=json.loads(lines[-1])
    except (IndexError,json.JSONDecodeError) as error:raise ValueError("Missing final Doctor result") from error
    if summary.get("passed") is not True:raise ValueError("Doctor capture failed")
    path=Path(summary.get("report","")).resolve();root=Path(output_root).resolve()
    if root not in path.parents or path.name!="report.json":raise ValueError("Doctor report outside capture output")
    data=json.loads(path.read_text())
    if data.get("passed") is not True:raise ValueError("Doctor report failed")
    return dict(path=str(path),sha256=digest(path))
def doctor_publish_command(evidence,python):
    paths=[]
    for mode in ("manual","auto"):
        name="doctor-"+mode+"-real"
        record=json.loads((evidence/(name+".json")).read_text())
        if record.get("passed") is not True:raise ValueError("Doctor capture receipt failed: "+mode)
        if record.get("execution_status")=="adopted-verified":
            from resume_adoption import verify_adopted_doctor_stage
            report=verify_adopted_doctor_stage(evidence,name,record,ROOT)
            checked=dict(path=report,sha256=digest(report))
            if record.get("native_report")!=checked:raise ValueError("Doctor adopted report identity changed: "+mode)
        else:
            checked=doctor_capture_result(evidence/(name+".log"),evidence/("doctor-"+mode))
            if record.get("native_report")!=checked:raise ValueError("Doctor capture receipt changed: "+mode)
        paths.extend(["--"+mode+"-report",checked["path"]])
    return [python,str(ROOT/"tools/manual_doctor_publish.py")]+paths+["--publish"]
def qualify_ready_fixture(path,expected_report):
    sys.path.insert(0,str(ROOT/"tests/behaviour"))
    from contract.rhythm_doctor_options import _qualify_fixture
    fixture=json.loads(Path(path).read_text())
    if Path(fixture.get("acquisition_report","")).resolve()!=Path(expected_report).resolve() or fixture.get("acquisition_report_sha256")!=digest(expected_report):raise ValueError("Ready fixture acquisition report differs")
    _qualify_fixture(fixture)

def doctor_options_result(log,output_root,case,clock):
    try:summary=json.loads(Path(log).read_text().splitlines()[-1])
    except (IndexError,json.JSONDecodeError) as error:raise ValueError("Missing final Doctor qualification result") from error
    if summary.get("passed") is not True:raise ValueError("Doctor qualification capture failed")
    path=Path(summary.get("report","")).resolve();root=Path(output_root).resolve()
    if root not in path.parents or path.name!="report.json":raise ValueError("Doctor qualification report outside capture output")
    data=json.loads(path.read_text())
    if data.get("passed") is not True or data.get("publication_kind")!="doctor-options-qualification" or data.get("case")!=case or data.get("clock_mode")!=clock or data.get("complete_regression_run") is not False:raise ValueError("Doctor qualification report failed or changed role")
    result=dict(native_report=dict(path=str(path),sha256=digest(path)))
    exported=summary.get("fixture")
    if case=="manual_right":
        if not exported:raise ValueError("ManualRight qualification lacks its finalized Ready fixture")
        fixture=Path(exported).resolve()
        if fixture!=path.parent/"ready-fixture/fixture.json":raise ValueError("Ready fixture outside exact ManualRight run")
        qualify_ready_fixture(fixture,path)
        result["ready_fixture"]=dict(path=str(fixture),sha256=digest(fixture))
    elif exported is not None:raise ValueError("Unexpected qualification fixture export")
    return result

def doctor_option_receipt(evidence,name):
    case,clock,suffix=DOCTOR_OPTION_STAGES[name]
    record=json.loads((evidence/(name+".json")).read_text());log=evidence/(name+".log")
    if record.get("name")!=name or record.get("passed") is not True or record.get("returncode")!=0 or record.get("log_sha256")!=digest(log):raise ValueError("Doctor qualification stage receipt changed: "+name)
    result=doctor_options_result(log,evidence/suffix,case,clock)
    if result["native_report"]!=record.get("native_report") or case=="manual_right" and result.get("ready_fixture")!=record.get("ready_fixture"):raise ValueError("Doctor qualification native report or fixture receipt changed: "+name)
    return result

def doctor_ready_arguments(evidence):
    result=doctor_option_receipt(evidence,"doctor-options-manual-right-real")
    fixture=result["ready_fixture"]
    return ["--ready-fixture",fixture["path"],"--ready-fixture-sha256",fixture["sha256"]]

def doctor_options_audit_command(evidence,python,controlled_local=False):
    args=[]
    roles={k:v for k,v in DOCTOR_AUDIT_ROLES.items() if not controlled_local or k not in ("setup_real","ready_real")}
    for role,name in roles.items():
        result=doctor_option_receipt(evidence,name)
        args.extend(["--"+role.replace("_","-")+"-report",result["native_report"]["path"]])
    fixture=doctor_option_receipt(evidence,"doctor-options-manual-right-real")["ready_fixture"]
    return [python,str(ROOT/"tools/doctor_options_audit.py")]+args+["--fixture",fixture["path"],"--fixture-sha256",fixture["sha256"],"--output",str(evidence/"doctor-options-audit-proof.json")]

def verify_doctor_completion(stages):
    required=set(DOCTOR_OPTION_STAGES)|{"doctor-options-audit"}
    records=[s for s in stages if s.get("name") in required]
    if len(records)!=8 or {s["name"] for s in records}!=required or any(s.get("passed") is not True or s.get("returncode")!=0 for s in records):raise ValueError("Doctor qualification requires all seven gates and independent audit")
    for record in records:
        field="qualification_audit" if record["name"]=="doctor-options-audit" else "native_report"
        proof=record.get(field,{})
        path=Path(proof.get("path",""))
        if not path.is_file() or digest(path)!=proof.get("sha256"):raise ValueError("Doctor qualification proof changed: "+record["name"])
        data=json.loads(path.read_text())
        if data.get("passed") is not True or data.get("complete_regression_run") is not False:raise ValueError("Doctor qualification proof failed")
        if record["name"] in DOCTOR_OPTION_STAGES:
            case,clock,suffix=DOCTOR_OPTION_STAGES[record["name"]]
            if data.get("publication_kind")!="doctor-options-qualification" or data.get("case")!=case or data.get("clock_mode")!=clock:raise ValueError("Doctor qualification proof role changed")

def stage_command(stage,evidence):
    action=stage.get("action") or {}
    if action.get("course_bind"):return course_bind_command(evidence,action["python"],action.get("controlled_local",False))
    if action.get("doctor_publish"):return doctor_publish_command(evidence,action["python"])
    if action.get("doctor_options_audit"):return doctor_options_audit_command(evidence,action["python"],action.get("controlled_local",False))
    command=[]
    for value in stage["command"]:
        value=value.replace("{evidence}",str(evidence))
        if "{fresh-midi-sha256}" in value:
            receipt=evidence/"fresh-target-midi-manifest.json"
            if not receipt.is_file():raise ValueError("Fresh target MIDI manifest is missing before projection/audit")
            value=value.replace("{fresh-midi-sha256}",digest(receipt))
        command.append(value)
    if action.get("doctor_ready"):command+=doctor_ready_arguments(evidence)
    return command

def prepare_stage_gate(options,evidence):
    value=getattr(options,"stage_gate_dir",None)
    if value is None:return
    directory=Path(value).resolve()
    directory.mkdir(parents=True,exist_ok=False)
    (directory/"owner.json").write_text(json.dumps(gate_owner(evidence),sort_keys=True)+"\n")
def gate_owner(evidence):
    # Field 22 follows the process name (which may itself contain spaces).
    fields=Path("/proc/self/stat").read_text().rsplit(")",1)[1].split()
    return dict(pid=os.getpid(),proc_starttime=fields[19],evidence_dir=str(evidence.resolve()),
        builder_sha256=digest(Path(__file__)),
        builder_argv_sha256=hashlib.sha256(Path("/proc/self/cmdline").read_bytes()).hexdigest())
def gate_blob(value):return (json.dumps(value,sort_keys=True,separators=(",",":"))+"\n").encode()
def await_stage_gate(stage,index,evidence,options,completed):
    value=getattr(options,"stage_gate_dir",None)
    if value is None:return
    if len(completed)!=index-1 or any(row.get("passed") is not True for row in completed):
        raise ValueError("Stage gate requires every preceding stage to pass")
    directory=Path(value).resolve();owner=gate_owner(evidence)
    if gate_blob(json.loads((directory/"owner.json").read_text()))!=gate_blob(owner):
        raise ValueError("Stage gate owner changed")
    previous=None
    if completed:
        last=completed[-1];receipt=evidence/(last["name"]+".json")
        if gate_blob(json.loads(receipt.read_text()))!=gate_blob(last):raise ValueError("Prior stage receipt changed")
        previous=dict(path=str(receipt.resolve()),sha256=digest(receipt))
    command=stage_command(stage,evidence)
    request=dict(schema_version=1,**owner,stage_index=index,stage_name=stage["name"],
        stage_sha256=hashlib.sha256(gate_blob(stage)).hexdigest(),
        argv_sha256=hashlib.sha256(gate_blob(command)).hexdigest(),
        previous_receipt=previous,nonce=uuid.uuid4().hex)
    blob=gate_blob(request);sha=hashlib.sha256(blob).hexdigest()
    stem=f"{index:03d}-{sha}";request_path=directory/(stem+".request.json")
    with request_path.open("xb") as handle:handle.write(blob)
    expected=dict(request_sha256=sha,**owner,stage_index=index,stage_name=stage["name"],
        argv_sha256=request["argv_sha256"],nonce=request["nonce"])
    release=directory/(stem+".resume.json")
    print("Stage gate ready:",request_path,flush=True)
    while not release.exists():time.sleep(0.1)
    accepted=json.loads(release.read_text())
    if gate_blob(accepted)!=gate_blob(expected):raise ValueError("Stage gate resume identity mismatch")
    if request_path.read_bytes()!=blob or gate_owner(evidence)!=owner:
        raise ValueError("Stage gate request or owner changed")
    if previous and (digest(receipt)!=previous["sha256"] or
            gate_blob(json.loads(receipt.read_text()))!=gate_blob(last)):
        raise ValueError("Prior stage receipt changed while awaiting resume")
    archive=evidence/"stage-gates";archive.mkdir(exist_ok=True)
    with (archive/(stem+".json")).open("x") as handle:
        json.dump(dict(request=request,request_sha256=sha,resume=accepted),handle,indent=2);handle.write("\n")

def preserve_reader_projection(evidence):
    """Archive old derived reader outputs; canonical inputs and strict audits stay intact."""
    generated=ROOT/"manual/generated"
    paths=[generated/"reader-index.json",generated/"reader-chunks"]
    existing=[path for path in paths if path.exists() or path.is_symlink()]
    if not existing:return []
    if generated.is_symlink() or any(path.is_symlink() for path in existing):
        raise ValueError("Refusing symlinked reader publication")
    files=[]
    for path in existing:
        candidates=list(path.rglob("*")) if path.is_dir() else [path]
        if any(item.is_symlink() for item in candidates):
            raise ValueError("Refusing symlinked reader publication file")
        files.extend(item for item in candidates if item.is_file())
    archive=evidence/"previous-reader-projection"
    archive.mkdir()
    receipts=[]
    for path in files:
        relative=path.relative_to(ROOT);target=archive/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        before=digest(path);shutil.copyfile(path,target)
        if digest(target)!=before:raise ValueError("Reader publication archive digest mismatch")
        receipts.append(dict(path=relative.as_posix(),sha256=before,archived_path=str(target)))
    for path in existing:
        if path.is_dir():shutil.rmtree(path)
        else:path.unlink()
    (archive/"receipt.json").write_text(json.dumps(receipts,indent=2)+"\n")
    return receipts

def run_stage(stage,evidence,options,browser_url):
    record=dict(stage,passed=False)
    log=evidence/(stage["name"]+".log")
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        if stage["action"] and not any(stage["action"].get(key) for key in ("doctor_publish","course_bind","doctor_ready","doctor_options_audit")):
            refresh_index(stage["action"],evidence)
        else:
            command=stage_command(stage,evidence)
            record["executed_command"]=command
            env=dict(os.environ)
            if stage["emulator"]:env["MONOME_EMULATOR"]=stage["emulator"]
            if browser_url:env["MOSAIC_MANUAL_URL"]=browser_url
            if options.node_path:env["NODE_PATH"]=options.node_path
            with exclusive(stage["exclusive_lock"]),log.open("x") as output:
                process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,text=True)
                try:
                    for line in process.stdout:output.write(line);output.flush();print(line,end="",flush=True)
                    code=process.wait()
                except BaseException:
                    process.terminate();process.wait(timeout=30);raise
                finally:process.stdout.close()
                record["returncode"]=code
                if code:raise subprocess.CalledProcessError(code,command)
            if stage["name"]=="fresh-target-midi-producer":
                receipt=evidence/"fresh-target-midi-manifest.json"
                if not receipt.is_file():raise ValueError("Fresh target MIDI manifest was not produced")
                data=json.loads(receipt.read_text())
                if data.get("kind")!="fresh-native-target-midi-v1":raise ValueError("Fresh target MIDI producer emitted the wrong receipt")
                record["fresh_target_midi_manifest"]={"path":str(receipt.resolve()),"sha256":digest(receipt),"qualification":data.get("qualification")}
                record["fresh_target_midi_producer_sha256"]=digest(ROOT/"tools/manual_fresh_target_midi.py")
            if stage["name"]=="reader-projection":
                lines=log.read_text().splitlines()
                if not lines:raise ValueError("Reader projection report is missing")
                projection_report=json.loads(lines[-1])
                if projection_report.get("passed") is not True:raise ValueError("Reader projection did not pass")
                record["reader_projection"]=projection_report
            if stage["name"].startswith("reference-real-") or stage["name"].startswith("reference-controlled-"):
                record["native_report"]=case_capture_result(log,evidence/"scene-captures",validation_scope="controlled-manual-generation" if getattr(options,"controlled_local",False) and stage["name"].startswith("reference-controlled-") else None)
            if stage.get("doctor_capture"):
                record["native_report"]=doctor_capture_result(log,evidence/("doctor-"+stage["doctor_capture"]))
            if stage.get("doctor_options"):
                contract=stage["doctor_options"]
                result=doctor_options_result(log,evidence/contract["output_suffix"],contract["case"],contract["clock_mode"])
                record["native_report"]=result["native_report"]
                if result.get("ready_fixture"):record["ready_fixture"]=result["ready_fixture"]
                if contract["case"]=="ready_options":
                    expected=doctor_ready_arguments(evidence)
                    source=json.loads(Path(record["native_report"]["path"]).read_text()).get("ready_fixture")
                    if source!={"path":expected[1],"sha256":expected[3]}:raise ValueError("Ready run used a different qualified fixture")
                    record["ready_fixture"]=source
            if stage.get("action",{} ) and stage["action"].get("doctor_options_audit"):
                proof=evidence/"doctor-options-audit-proof.json";data=json.loads(proof.read_text())
                if data.get("passed") is not True or data.get("complete_regression_run") is not False:raise ValueError("Doctor qualification audit failed")
                record["qualification_audit"]=dict(path=str(proof),sha256=digest(proof))
        record["passed"]=True
    except BaseException as error:record["failure"]=repr(error);raise
    finally:
        record["started_utc"]=started
        record["finished_utc"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
        if log.exists():record["log_sha256"]=digest(log)
        with (evidence/(stage["name"]+".json")).open("x") as handle:json.dump(record,handle,indent=2);handle.write("\n")
    return record
def scene_ids_for_plans(plans):
    ids=[]
    for name in plans:
        data=yaml.safe_load((ROOT/"manual"/name).read_text()) or {}
        ids.extend(scene["id"] for scene in data.get("scenes",[]))
    if len(ids)!=len(set(ids)):raise ValueError("Duplicate scene IDs across selected plans")
    return sorted(ids)

def write_generation_context(evidence,selected_plans,required_plans,source_files):
    selected_ids=scene_ids_for_plans(selected_plans);required_ids=scene_ids_for_plans(required_plans)
    context=dict(schema_version=1,validation_scope="controlled-manual-generation",realtime_qualification="pending-ci",
        clock_mode="controlled-experimental",complete_regression_run=False,selected_plans=selected_plans,required_plans=required_plans,
        selected_scene_ids=selected_ids,required_scene_ids=required_ids,source_files_before=source_files,
        producer_source_sha256={name:digest(ROOT/name) for name in ("tools/manual_capture.py","tools/manual_build.py")})
    with (evidence/"generation-context.json").open("x") as handle:json.dump(context,handle,indent=2);handle.write("\n")
    return context

def complete_manual_generation(browser_validated,selected_plans,required_plans,book,stages):
    if not browser_validated or set(selected_plans)!=set(required_plans):return False
    if book.get("complete_manual") is not True or any(row.get("passed") is not True for row in stages):return False
    projections=[row for row in stages if row.get("name")=="reader-projection"]
    if len(projections)!=1 or projections[0].get("reader_projection",{}).get("passed") is not True:return False
    captures=[row for row in stages if row.get("name","").startswith("reference-controlled-")]
    expected=1
    for name in required_plans:
        data=yaml.safe_load((ROOT/"manual"/name).read_text()) or {}
        expected+=len({scene.get("profile","base-midi") for scene in data.get("scenes",[])})
    expected-=1
    return len(captures)==expected and all(row.get("native_report") for row in captures)

def run_build_stages(stages,evidence,options,browser_url,adopted,manifest):
    for index,stage in enumerate(stages,1):
        await_stage_gate(stage,index,evidence,options,manifest["stages"])
        print("Stage:",stage["name"],flush=True)
        try:
            if stage["name"] in adopted:
                record=adopted[stage["name"]]
                log=evidence/(stage["name"]+".log")
                origin=record["adopted_from"]
                if "parent_manifest_sha256" in origin:
                    details="parent_manifest_sha256="+origin["parent_manifest_sha256"]+chr(10)+"parent_log_sha256="+origin["parent_log_sha256"]+chr(10)
                else:
                    details="source_report_sha256="+origin["report_sha256"]+chr(10)+"adoption_proof_sha256="+origin["proof_sha256"]+chr(10)
                log.write_text("ADOPTED VERIFIED"+chr(10)+details)
                record["log_sha256"]=digest(log)
                with (evidence/(stage["name"]+".json")).open("x") as handle:
                    json.dump(record,handle,indent=2);handle.write(chr(10))
                manifest["stages"].append(record)
            else:
                if stage["name"]=="reader-projection":
                    if (evidence/"reader-projection.log").exists():
                        raise FileExistsError("Reader projection evidence already exists")
                    preserve_reader_projection(evidence)
                manifest["stages"].append(run_stage(stage,evidence,options,browser_url))
        except BaseException:
            record=evidence/(stage["name"]+".json")
            if record.exists():manifest["stages"].append(json.loads(record.read_text()))
            raise

def merge_stage_adoptions(*collections):
    """Combine independent explicit adoption proofs while rejecting stage overlap."""
    merged={}
    for collection in collections:
        overlap=set(merged)&set(collection)
        if overlap:raise ValueError("Conflicting adopted stage proofs: "+",".join(sorted(overlap)))
        merged.update(collection)
    return merged

def complete_build(browser_validated,selected_plans,required_plans,book,stages=None):
    if book.get("complete_manual") is not True:
        raise ValueError("Manual is incomplete: finish verified feature and course bindings before completion")
    complete=bool(browser_validated and set(selected_plans)==set(required_plans))
    projections=[row for row in (stages or []) if row.get("name")=="reader-projection"]
    complete=complete and len(projections)==1 and projections[0].get("passed") is True and projections[0].get("reader_projection",{}).get("passed") is True
    if complete:verify_doctor_completion(stages or [])
    return complete
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--real-install",help="Explicit qualified installation for generic real-time captures")
    parser.add_argument("--controlled-local",action="store_true",help="Generate the manual from controlled native captures; REAL qualification remains pending CI")
    parser.add_argument("--emulator",required=True);parser.add_argument("--audio-emulator",required=True)
    parser.add_argument("--controlled-install",required=True);parser.add_argument("--audio-install",required=True)
    parser.add_argument("--mod-code-root",required=True);parser.add_argument("--ffmpeg",default="ffmpeg")
    parser.add_argument("--readability-real-install",help="Explicit qualified native output-boundary installation for real readability")
    parser.add_argument("--modulation-emulator");parser.add_argument("--modulation-controlled-install")
    parser.add_argument("--modulation-code-root");parser.add_argument("--plans",action="append")
    parser.add_argument("--python",default=sys.executable);parser.add_argument("--node",default="node")
    parser.add_argument("--node-path",default=os.environ.get("NODE_PATH"))
    parser.add_argument("--skip-browser-tests",dest="browser_tests",action="store_false",default=True)
    parser.add_argument("--quick-output",default="manual/generated/quick-reference.html")
    parser.add_argument("--artifacts",type=Path,default=ROOT.parent/"mosaic-manual-build-runs")
    parser.add_argument("--stage-gate-dir",type=Path,help="Fresh opt-in between-stage coordination directory; exact resume required")
    parser.add_argument("--resume-from",type=Path,help="Adopt only current-source-validated reference and Doctor asset captures from a failed controlled run")
    parser.add_argument("--resume-manifest-sha256",help="Required immutable parent manifest SHA256 pin")
    parser.add_argument("--adopt-audio-report",type=Path,help="Explicit complete controlled-local standalone audio report to adopt")
    parser.add_argument("--adopt-audio-report-sha256",help="Required SHA256 pin for --adopt-audio-report")
    parser.add_argument("--retained-midi-admissions",type=Path,help="Explicit tracked receipt for retained resume projection only")
    parser.add_argument("--retained-midi-admissions-sha256",help="Literal reviewed receipt SHA256")
    parser.add_argument("--plan-only",action="store_true")
    options=parser.parse_args()
    if bool(options.resume_from) != bool(options.resume_manifest_sha256):parser.error("--resume-from and --resume-manifest-sha256 must be supplied together")
    if options.resume_from and not options.controlled_local:parser.error("Checkpoint adoption is controlled-local only")
    if bool(options.adopt_audio_report) != bool(options.adopt_audio_report_sha256):parser.error("--adopt-audio-report and --adopt-audio-report-sha256 must be supplied together")
    if options.adopt_audio_report and not options.controlled_local:parser.error("Audio report adoption is controlled-local only")
    try:validate_launch_mode(getattr(options,"controlled_local",False),getattr(options,"real_install",None))
    except ValueError as error:parser.error(str(error))
    retained=retained_call(ROOT,options.retained_midi_admissions,options.retained_midi_admissions_sha256,mode='retained-resume' if options.resume_from and (options.retained_midi_admissions or options.retained_midi_admissions_sha256) else 'fresh')
    all_plans=[p.name for p in sorted((ROOT/"manual").glob("scene-plans*.yaml"))]
    plans=options.plans or all_plans
    stages=plan(options,plans,controlled_local=getattr(options,"controlled_local",False))
    if options.plan_only:print(json.dumps(stages,indent=2));return 0
    evidence=options.artifacts.resolve()/uuid.uuid4().hex;evidence.mkdir(parents=True,exist_ok=False)
    prepare_stage_gate(options,evidence)
    sources={str(p.relative_to(ROOT)):digest(p) for p in sorted((ROOT/"manual").rglob("*.yaml"))}
    for name in sources:
        target=evidence/"authoring-before"/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,target)
    adopted={}
    resume_proof=evidence/"resume-adoption.json"
    manifest=dict(schema_version=1,passed=False,build_complete=False,complete_regression_run=False,
        controlled_time_admitted=False,source_files_before=sources,tool_sha256=digest(Path(__file__)),
        revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        selected_plans=plans,required_plans=all_plans,renderer_validated=False,stages=[])
    try:
        if getattr(options,"controlled_local",False):
            context=write_generation_context(evidence,plans,all_plans,sources)
            manifest.update(validation_scope=context["validation_scope"],realtime_qualification=context["realtime_qualification"],
                clock_mode=context["clock_mode"],controlled_local=True,selected_scene_ids=context["selected_scene_ids"],required_scene_ids=context["required_scene_ids"])
        if options.adopt_audio_report:
            audio_stage=next((row for row in stages if row["name"]=="musical-audio-assets"),None)
            if audio_stage is None:raise ValueError("Current plan has no musical-audio-assets stage to adopt")
            audio_record=prepare_audio_report_adoption(options.adopt_audio_report,
                options.adopt_audio_report_sha256,ROOT,evidence)
            audio_record={**audio_stage,**audio_record,"name":"musical-audio-assets"}
            adopted["musical-audio-assets"]=audio_record
            manifest["audio_adoption"]={"path":"audio-report-adoption.json",
                "sha256":audio_record["audio_adoption_proof"]["sha256"]}
        if options.resume_from:
            from manual_publication_verify import audit_reference, audit_doctor
            checkpoint_adopted,resume_details=prepare_resume(options.resume_from,ROOT,stages,
                expected_parent_manifest_sha256=options.resume_manifest_sha256,
                current_builder_sha=digest(Path(__file__)),
                producer_hashes={name:digest(ROOT/name) for name in required_producer_inventory(ROOT,retained)},
                retained_midi_admission=retained,
                audit_native=audit_reference,audit_doctor=audit_doctor,proof_path=resume_proof)
            if resume_details.get('retained_midi_admission'):
                manifest['retained_midi_admission']=resume_details['retained_midi_admission']
            adopted=merge_stage_adoptions(adopted,checkpoint_adopted)
            finalize_resume_source_start(resume_proof,evidence)
            manifest["resume_lineage"]={"path":"resume-adoption.json","sha256":digest(resume_proof)}
        with preview(options.browser_tests) as browser_url:
            run_build_stages(stages,evidence,options,browser_url,adopted,manifest)
        book=json.loads((ROOT/"manual/generated/book.json").read_text())
        if getattr(options,"controlled_local",False):
            manifest.update(validation_scope="controlled-manual-generation",realtime_qualification="pending-ci",
                clock_mode="controlled-experimental",controlled_local=True)
            manifest["manual_generation_complete"]=complete_manual_generation(options.browser_tests,plans,all_plans,book,manifest["stages"])
            manifest["build_complete"]=False
            if not manifest["manual_generation_complete"]:raise ValueError("Controlled manual generation did not complete")
        else:
            manifest["build_complete"]=complete_build(options.browser_tests,plans,all_plans,book,manifest["stages"])
        manifest["passed"]=True;manifest["renderer_validated"]=options.browser_tests
    except BaseException as error:
        manifest["failure"]=repr(error);raise
    finally:
        manifest["source_files_after"]={str(p.relative_to(ROOT)):digest(p) for p in sorted((ROOT/"manual").rglob("*.yaml"))}
        with (evidence/"manifest.json").open("x") as handle:json.dump(manifest,handle,indent=2);handle.write("\n")
        print("Immutable build evidence:",evidence,flush=True)
    return 0
if __name__=="__main__":sys.exit(main())
