"""Publish exact pre-apply Device routes from successful immutable native audio evidence."""
import argparse,base64,copy,hashlib,json,os,sys
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]
MANUAL=ROOT/"manual"
sys.path.insert(0,str(ROOT/"tests/behaviour"))
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def canonical(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def choose_frame(observations,results,actions,voice,channel,matcher):
    assertions=[(i,row) for i,row in enumerate(results) if row.get("kind")=="device-picker-frame" and row.get("label")==voice and row.get("matched") is True]
    if len(assertions)!=1:raise ValueError("Missing unique matched player assertion")
    candidates=[]
    for index,row in enumerate(observations):
        if not matcher(row["state"],voice,channel):continue
        before=[v for v in actions if v["ack"]["monotonic_ns"]<=row["monotonic_ns"]]
        after=[v for v in actions if v["ack"]["monotonic_ns"]>row["monotonic_ns"]][:2]
        if len(after)!=2:continue
        expected=[{"type":"key","n":3,"state":1},{"type":"key","n":3,"state":0}]
        if [v["request"]["action"] for v in after]!=expected or any(v["ack"]["status"]!="applied" for v in after):continue
        if any(v["ack"]["status"]!="applied" for v in before):raise ValueError("Unapplied public route input")
        candidates.append(dict(observation_index=index,assertion_index=assertions[0][0],assertion=assertions[0][1],
                               public_actions=before,following_actions=after))
    if len(candidates)!=1:raise ValueError("Missing unique pre-apply selected player frame")
    return candidates[0]
def rle(values):
    output=[]
    for value in values:
        if output and output[-1][0]==value:output[-1][1]+=1
        else:output.append([value,1])
    return output
def frame_matches(state,voice,channel):
    from frame_oracle import selected_field_matches,live_header_matches
    from ui import header_parts
    header=header_parts("midi_config",channel=channel)
    return selected_field_matches(state,header[2],"Device",voice) and live_header_matches(state,*header)
def page_matches(state,channel):
    from frame_oracle import live_header_matches
    from ui import header_parts
    return live_header_matches(state,*header_parts("midi_config",channel=channel))

def extract(source_path,audio_path):
    source=yaml.safe_load(Path(source_path).read_text())
    if source.get("source_schema")!="player-route-projection/v1" or source.get("fixture_kind")!="external-native-evidence":
        raise ValueError("Wrong projection source contract")
    audio=json.loads(Path(audio_path).read_text())
    if not audio.get("passed"):raise ValueError("Unsuccessful audio parent")
    matching=[v for v in audio["examples"] if v["id"]==source["recording_example"]]
    if len(matching)!=1:raise ValueError("Missing unique parent audio example")
    parent=matching[0];out=Path(parent["evidence"]["path"])
    results=json.loads((out/"results.json").read_text());observations=json.loads((out/"observations.json").read_text())
    actions=[json.loads(line) for line in (out/"native/actions.jsonl").read_text().splitlines()]
    recipe=json.loads((out/"recipe.json").read_text())
    identity=json.loads((out/"native/identity.json").read_text())
    cleanup=json.loads((out/"native/cleanup.json").read_text())
    if not cleanup or any(row.get("returncode") is None for row in cleanup):raise ValueError("Incomplete native cleanup")
    receipt=dict(path=str(out),results_sha256=digest(out/"results.json"),observations_sha256=digest(out/"observations.json"),
                 actions_sha256=digest(out/"native/actions.jsonl"),recipe_sha256=digest(out/"recipe.json"),
                 identity_sha256=digest(out/"native/identity.json"),cleanup_sha256=digest(out/"native/cleanup.json"),
                 source_yaml_sha256=digest(out.parent/"source.yaml"),capture_tool_sha256=digest(out.parent/"capture-tool.py"),
                 session_id=identity["session_id"])
    immutable_parent=out.parent/"audio-scenes.json"
    baseline=json.loads(immutable_parent.read_text())
    original=[v for v in baseline["examples"] if v["id"]==parent["id"]]
    if len(original)!=1 or not baseline.get("passed"):raise ValueError("Missing successful immutable audio baseline")
    for field in ("tracks","bars","bpm","profile","evidence","timeline","metrics","solo_contributions"):
        if parent[field]!=original[0][field]:raise ValueError("Changed parent native audio evidence")
    tracks={track["voice"]:track["channel"] for track in parent["tracks"]}
    scenes=[]
    for plan in source["scenes"]:
        voice=plan["player"]
        if voice not in tracks:raise ValueError("Player absent from captured parent")
        channel=tracks[voice]
        if plan.get("channel")!=channel:raise ValueError("Authored channel differs from native player route")
        chosen=choose_frame(observations,results,actions,voice,channel,frame_matches)
        index=chosen["observation_index"];row=observations[index];state=row["state"]
        prefix=[v["request"]["action"] for v in chosen["public_actions"]]
        if recipe[:len(prefix)]!=prefix:raise ValueError("Native route differs from original public recipe")
        start=index
        while start>0 and page_matches(observations[start-1]["state"],channel):start-=1
        page_start_ns=observations[start]["monotonic_ns"]
        route=[v["request"]["action"] for v in chosen["public_actions"] if v["ack"]["monotonic_ns"]>page_start_ns]
        def projection(index,binding_fields,inputs,trace,frame_oracle):
            row=observations[index];state=row["state"]
            pixels=base64.b64decode(state["frame"]["pixels_base64"])
            if len(pixels)!=32768 or any(v%17 for v in pixels[::4]):raise ValueError("Non-native greyscale frame")
            levels=[v//17 for v in pixels[::4]];grid=state["grid"]
            if len(grid)!=128 or any(not isinstance(v,int) or not 0<=v<=15 for v in grid):raise ValueError("Grid contract")
            binding=dict(kind="external-native-frame-projection",name="manual/"+parent["acceptance_case"]+"/"+binding_fields.pop("name"),
                         sha256=state["frame"]["sha256"],stable_rows=55,stable_sha256=hashlib.sha256(pixels[:128*55*4]).hexdigest(),
                         grid_sha256=hashlib.sha256(bytes(grid)).hexdigest(),passed=True,
                         observation_index=index,observation_monotonic_ns=row["monotonic_ns"],
                         assertion_index=chosen["assertion_index"],assertion=chosen["assertion"],
                         assertion_sha256=canonical(chosen["assertion"]),trace_sha256=canonical(trace),
                         frame_oracle=frame_oracle,
                         parent_example_id=parent["id"],**binding_fields)
            return inputs,dict(screen_rle=rle(levels),grid=grid,binding=binding)
        if len(plan["steps"])!=1:raise ValueError("Projection requires one pre-apply step per player")
        inputs,output=projection(index,dict(name=plan["id"],capture_stage="before-apply",full_public_trace_sha256=canonical(prefix),
                                            following_apply=chosen["following_actions"],parent_step_id="device-picker-frame/"+voice),route,route,
                                 dict(page="midi_config",channel=channel,selected_label="Device",selected_value=voice,matched=True))
        step=copy.deepcopy(plan["steps"][0]);step.update(inputs=inputs,expect=dict(assertion=chosen["assertion"]),output=output)
        projected=[step]
        scenes.append(dict(id=plan["id"],feature_id=plan["feature_id"],title=plan["title"],
                           behaviour_case=parent["acceptance_case"],profile=parent["profile"],
                           setup=dict(fixture="external-native-evidence",recording=parent["id"],page="midi_config",
                                      channel=channel,input_units="native; encoder units are twice the detents"),
                           requirements=["README.md#mods-and-software-devices"],steps=projected,evidence=receipt))
    return dict(schema_version=1,publication_kind="audio-route-projection",source_schema=source["source_schema"],
                source=dict(authoring_path=str(Path(source_path).relative_to(ROOT)),authoring_sha256=digest(source_path),
                            adapter_sha256=digest(Path(__file__))),
                parent_publication=dict(path=str(Path(audio_path).relative_to(ROOT)),sha256=digest(audio_path),
                                        example_id=parent["id"],acceptance_case=parent["acceptance_case"],
                                        immutable_path=str(immutable_parent),immutable_sha256=digest(immutable_parent)),
                scenes=scenes,complete_regression_run=False,passed=True,
                scope="Selected Device rows before subsequent K3 application. No mod-installation or post-apply field-persistence frame.")
def audit(path=MANUAL/"generated/player-routes.json"):
    actual=json.loads(Path(path).read_text())
    source=ROOT/actual["source"]["authoring_path"];parent=ROOT/actual["parent_publication"]["path"]
    expected=extract(source,parent)
    if actual!=expected:raise ValueError("Player route projection differs from exact native evidence")
    return dict(scenes=len(actual["scenes"]),frames=sum(len(v["steps"]) for v in actual["scenes"]),passed=True)
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",type=Path,default=MANUAL/"player-routes.yaml")
    parser.add_argument("--audio",type=Path,default=MANUAL/"generated/audio-scenes.json")
    parser.add_argument("--output",type=Path,default=MANUAL/"generated/player-routes.json")
    parser.add_argument("--audit",action="store_true")
    options=parser.parse_args()
    if options.audit:print(audit(options.output));return 0
    result=extract(options.source,options.audio)
    options.output.write_text(json.dumps(result,indent=2)+"\n")
    print(len(result["scenes"]),"faithful pre-apply player route projections")
    return 0
if __name__=="__main__":sys.exit(main())
