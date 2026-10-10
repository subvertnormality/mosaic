"""Audit published pilot data against authoring and captured semantic bindings."""
import base64, hashlib, json
from pathlib import Path
from manual_model import ROOT, MANUAL, load, validate, source_hash, validate_capture
from manual_screen_codec import decode_screen_payload, ScreenEncodingError

def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def check_frame(output, case, results, observations):
    try: screen_format,samples=decode_screen_payload(output)
    except ScreenEncodingError as error: raise ValueError(str(error)) from error
    grid=output.get("grid")
    if screen_format=="legacy16": validate_capture(dict(levels=samples,grid=grid))
    else: validate_capture(dict(levels=[0]*8192,grid=grid))
    binding=output["binding"]
    native=[o["state"] for o in observations if o["state"]["frame"]["sha256"]==binding["sha256"] and o["state"]["grid"]==grid]
    if not native: raise ValueError("Missing native observation")
    def matches(state):
        pixels=base64.b64decode(state["frame"]["pixels_base64"],validate=True)
        if len(pixels)!=32768 or hashlib.sha256(pixels).hexdigest()!=binding["sha256"]: return False
        channel0=pixels[::4]
        if screen_format=="legacy16": return all(value%17==0 for value in channel0) and [value//17 for value in channel0]==samples
        if any(pixels[i]!=pixels[i+1] or pixels[i]!=pixels[i+2] for i in range(0,len(pixels),4)): return False
        return list(channel0)==samples
    if not any(matches(state) for state in native): raise ValueError("Framebuffer brightness/hash mismatch")
    if hashlib.sha256(bytes(grid)).hexdigest()!=binding["grid_sha256"]: raise ValueError("Grid hash mismatch")
    if binding not in results or not binding["passed"] or binding["semantic_assertions"]<1: raise ValueError("Unbound capture")
    if not binding["name"].startswith("manual/"+case+"/"): raise ValueError("Wrong behaviour case")

def main():
    authored=validate(load())
    data=json.loads((MANUAL/"generated/pilot.json").read_text())
    if data["source_sha256"]!=source_hash(authored):raise ValueError("Stale authoring")
    if data["feature"]!=authored["feature"]:raise ValueError("Stale feature")
    if not data["validation"]["pilot_complete"]:raise ValueError("Incomplete pilot")
    if len(data["scenes"])!=len(authored["scenes"]):raise ValueError("Missing scenes")
    frames=0
    for scene,source in zip(data["scenes"],authored["scenes"]):
        if scene["id"]!=source["id"]:raise ValueError("Wrong scene")
        evidence=scene["evidence"]; path=Path(evidence["path"])
        if digest(path/"results.json")!=evidence["results_sha256"]:raise ValueError("Changed evidence")
        results=json.loads((path/"results.json").read_text()); observations=json.loads((path/"observations.json").read_text())
        if len(scene["steps"])!=len(source["steps"]):raise ValueError("Missing steps")
        for step,original in zip(scene["steps"],source["steps"]):
            if {k:v for k,v in step.items() if k!="output"}!=original:
                raise ValueError("Stale step")
            semantics=[r for r in results if r.get("kind")=="manual-semantic" and r.get("step")==step["id"] and r.get("passed")]
            if len(semantics)!=1 or semantics[0]["expected"]!=step["expect"]:
                raise ValueError("Missing exact semantic assertion")
            check_frame(step["output"],scene["behaviour_case"],results,observations);frames+=1
    audio=data["audio"]
    if {k:audio[k] for k in authored["audio"]}!=authored["audio"]:raise ValueError("Stale audio")
    registry=json.loads((MANUAL/"contracts.json").read_text())["cases"]
    if "manual-audio" not in registry:raise ValueError("Unknown audio case")
    path=Path(audio["evidence"]["path"]); results=json.loads((path/"results.json").read_text()); observations=json.loads((path/"observations.json").read_text())
    if len([r for r in results if r.get("kind")=="manual-audio-track" and r.get("passed")])!=len(audio["tracks"]):
        raise ValueError("Missing voice assertions")
    if not any(r.get("kind")=="manual-audio-PCM" and r.get("passed") for r in results):
        raise ValueError("Missing PCM oracle")
    for frame in audio["timeline"]:check_frame(frame["output"],"manual-audio",results,observations);frames+=1
    if len({tuple(f["output"]["grid"]) for f in audio["timeline"]})<2:raise ValueError("Static playhead")
    hashes=json.loads((MANUAL/"evidence/audio-files.json").read_text())
    for filename in audio["files"]:
        if not (MANUAL/filename).is_file():raise ValueError("Missing compressed audio")
        if digest(MANUAL/filename)!=hashes[filename]:raise ValueError("Changed compressed audio")
    print("Verified",len(data["scenes"]),"scenes,",frames,"native captures and independent audio acceptance.")
if __name__=="__main__":main()
