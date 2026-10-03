"""Audit published pilot data against authoring and captured semantic bindings."""
import base64, hashlib, json
from pathlib import Path
from manual_model import ROOT, MANUAL, load, validate, source_hash, validate_capture

def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def check_frame(output, case, results, observations):
    levels=[]
    for value,count in output["screen_rle"]:
        if type(count) is not int or count<1 or len(levels)+count>8192:
            raise ValueError("Invalid RLE")
        levels.extend([value]*count)
    validate_capture(dict(levels=levels,grid=output["grid"]))
    binding=output["binding"]
    native=[o["state"] for o in observations if o["state"]["frame"]["sha256"]==binding["sha256"]
            and o["state"]["grid"]==output["grid"]]
    if not native:raise ValueError("Missing native observation")
    # Native BGRA includes zero-alpha black pixels; browser paints brightness opaque.
    if not any(hashlib.sha256(base64.b64decode(o["frame"]["pixels_base64"])).hexdigest()==binding["sha256"]
               and [v//17 for v in base64.b64decode(o["frame"]["pixels_base64"])[::4]]==levels for o in native):
        raise ValueError("Framebuffer brightness/hash mismatch")
    if hashlib.sha256(bytes(output["grid"])).hexdigest()!=binding["grid_sha256"]:
        raise ValueError("Grid hash mismatch")
    if binding not in results or not binding["passed"] or binding["semantic_assertions"]<1:
        raise ValueError("Unbound capture")
    if not binding["name"].startswith("manual/"+case+"/"):
        raise ValueError("Wrong behaviour case")

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
    for filename in audio["files"]:
        if not (MANUAL/filename).is_file():raise ValueError("Missing compressed audio")
    print("Verified",len(data["scenes"]),"scenes,",frames,"native captures and independent audio acceptance.")
if __name__=="__main__":main()
