"""Byte-level audit for a frozen rendered Rhythm Doctor corpus."""
import argparse, hashlib, json, math, struct, wave
from pathlib import Path

def samples(path):
    with wave.open(str(path), "rb") as audio:
        return audio.getframerate(), audio.getnchannels(), struct.unpack(
            "<%dh" % (audio.getnframes() * audio.getnchannels()), audio.readframes(audio.getnframes()))

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def main(root, manifest, output=None):
    if output and output.exists(): raise FileExistsError("audit output already exists")
    data=json.loads(manifest.read_text()); clips=data["clips"]
    failures=[]
    for clip in clips:
        audio=root/clip["audio"]["path"]
        if sha(audio)!=clip["audio"]["sha256"]: failures.append("audio_hash:"+clip["id"])
        rate,channels,pcm=samples(audio)
        if rate!=16000 or channels not in (1,2): failures.append("format:"+clip["id"])
        with wave.open(str(audio)) as w: duration=w.getnframes()/rate
        if abs(duration-clip["duration_seconds"])>.005: failures.append("duration:"+clip["id"])
    held=[c for c in clips if c["split"]=="held_out"]
    full=[c for c in held if c["stratum"]=="full_mix"]
    unique=len({sha(root/c["audio"]["path"]) for c in full})
    if unique<len(full): failures.append("duplicate_full_mix_pcm")
    phase=next(c for c in clips if "phase_inverted_stereo" in c["tags"])
    rate,channels,pcm=samples(root/phase["audio"]["path"])
    residual=[int(pcm[i])+int(pcm[i+1]) for i in range(0,len(pcm),2)]
    if channels!=2 or min(residual)!=0 or max(residual)!=0: failures.append("phase_not_exact")
    for clip in (c for c in clips if "gain_ladder" in c["tags"]):
        rate,channels,pcm=samples(root/clip["audio"]["path"]); ann=json.loads((root/clip["annotation"]["path"]).read_text())
        lane=next(name for name,events in ann["events"].items() if events); points=[]
        for event in ann["events"][lane]:
            start=int(event["time_seconds"]*rate)*channels; end=min(len(pcm),start+int(.2*rate)*channels); section=pcm[start:end]
            points.append((event["velocity"],math.sqrt(sum(int(x)*int(x) for x in section)/len(section))))
        if not all(points[i][1]<=points[i+1][1] for i in range(len(points)-1)): failures.append("gain_not_monotone:"+clip["id"])
        ratios=[r/v for v,r in points if v]
        if max(ratios)-min(ratios)>.02*max(ratios): failures.append("gain_not_proportional:"+clip["id"])
    report={"scope":"rendered fixture inventory; not transcription quality","manifest_sha256":sha(manifest),"held_full_mix":{"count":len(full),"unique_pcm":unique},"failures":failures,"passed":not failures}
    if output: output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,sort_keys=True)); return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("root",type=Path);p.add_argument("manifest",type=Path);p.add_argument("--output",type=Path,required=True);a=p.parse_args();raise SystemExit(0 if main(a.root,a.manifest,a.output)["passed"] else 1)
