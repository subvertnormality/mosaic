"""Add frozen control fixtures to a preliminary external corpus without rewriting it."""
import argparse, audioop, hashlib, json, shutil, struct, wave
from pathlib import Path

LANES = ("BD", "SD", "HH", "TOM", "BASS")

def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()

def desc(root, path): return {"path": str(path.relative_to(root)).replace("\\", "/"), "sha256": sha(path)}

def copy_wav(source, target, transform=None):
    with wave.open(str(source), "rb") as inp:
        params, frames = inp.getparams(), inp.readframes(inp.getnframes())
    if transform: frames = transform(frames, params)
    with wave.open(str(target), "wb") as out:
        out.setparams(params); out.writeframes(frames)

def empty_annotation(path):
    path.write_text(json.dumps({"reference_origin":"independent_render_metadata","annotator_id":"frozen-control-render-v1","events":{lane:[] for lane in LANES}}, sort_keys=True) + "\n")

def main(root, v1, v2):
    v2.mkdir(parents=True, exist_ok=True)
    for directory in ("audio", "annotations", "recipes", "timbres"):
        (v2 / directory).mkdir(exist_ok=True)
    manifest = json.loads((v1 / "manifest.json").read_text())
    base = manifest["clips"][0]
    source = root / base["audio"]["path"]
    controls = []
    def add(ident, tag, transform=None, silence=False):
        audio = v2 / "audio" / f"{ident}.wav"
        if silence:
            copy_wav(source, audio, lambda frames, _params: b"\0" * len(frames))
        elif tag == "phase_inverted_stereo":
            with wave.open(str(source), "rb") as inp:
                params, frames = inp.getparams(), inp.readframes(inp.getnframes())
            if params.sampwidth != 2 or params.nchannels != 1: raise ValueError("expected 16-bit mono")
            values = struct.unpack("<" + "h" * (len(frames) // 2), frames)
            stereo = [sample for value in values for sample in (value, -value if value != -32768 else 32767)]
            with wave.open(str(audio), "wb") as out:
                out.setparams(params._replace(nchannels=2)); out.writeframes(struct.pack("<" + "h" * len(stereo), *stereo))
        else: copy_wav(source, audio, transform)
        annotation = v2 / "annotations" / f"{ident}.json"
        if silence: empty_annotation(annotation)
        else: shutil.copyfile(root / base["annotation"]["path"], annotation)
        recipe = v2 / "recipes" / f"{ident}.json"
        recipe.write_text(json.dumps({"kind":"frozen_submix","operation":tag,"input_sha256":base["audio"]["sha256"],"no_classifier_output":True}, sort_keys=True)+"\n")
        evidence = v2 / "timbres" / f"{ident}.json"
        evidence.write_text(json.dumps({"lanes":{lane:{"timbre":"unverified","basis":"source_render_spec","source":"control transform; source timbre unresolved"} for lane in LANES}},sort_keys=True)+"\n")
        clip = dict(base); clip.update({"id":ident,"audio":desc(root,audio),"annotation":desc(root,annotation),"render":{"kind":"frozen_submix","recipe":desc(root,recipe)},"timbre_evidence":desc(root,evidence),"tags":["preliminary",tag]})
        controls.append(clip)
    add("control-clipping-00", "clipping", lambda frames, params: audioop.mul(frames, params.sampwidth, 4.0))
    add("control-phase-inverted-00", "phase_inverted_stereo")
    for index in range(3): add(f"control-silence-{index:02d}", "silence", silence=True)
    def simultaneous(clip):
        events = json.loads((root / clip["annotation"]["path"]).read_text())["events"]
        return any(abs(bd["time_seconds"] - bass["time_seconds"]) <= 0.002 for bd in events["BD"] for bass in events["BASS"])
    unison = [clip for clip in manifest["clips"] if simultaneous(clip)]
    if unison:
        unison[0]["tags"] = sorted(set(unison[0]["tags"] + ["kick_bass_unison"]))
    manifest["corpus_id"] = "rd02-babyslakh-preliminary-v2-controls"
    manifest["clips"] += controls
    (v2 / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True)+"\n")
    report = {"accepted":False,"created_controls":[clip["id"] for clip in controls],"kick_bass_unison_found":bool(unison),"missing_gates":["source-backed acoustic/electronic timbre labels","sparse mixtures from original stems","isolated per-lane BD/SD/HH/TOM/BASS audio","independently annotated long acquisition fixtures","full negative-lane inventory","real recorded-music domain evidence"]}
    (v2 / "gate-report.json").write_text(json.dumps(report, indent=2)+"\n")
    print(v2 / "manifest.json")

if __name__ == "__main__":
    p=argparse.ArgumentParser();p.add_argument("root",type=Path);p.add_argument("v1",type=Path);p.add_argument("v2",type=Path);a=p.parse_args();main(a.root,a.v1,a.v2)
