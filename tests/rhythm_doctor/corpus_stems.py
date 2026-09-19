"""Build v3 sparse/isolated fixtures from original BabySlakh stems only."""
import argparse,audioop,hashlib,json,shutil,wave
from pathlib import Path
import yaml
LANES=("BD","SD","HH","TOM","BASS")
def sha(path):
 h=hashlib.sha256()
 with open(path,"rb")as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def desc(root,path):return {"path":str(path.relative_to(root)).replace("\\","/"),"sha256":sha(path)}
def crop(source,target,start,duration):
 with wave.open(str(source),"rb")as a:
  rate=a.getframerate();a.setpos(round(start*rate));raw=a.readframes(round(duration*rate));params=a.getparams()
 with wave.open(str(target),"wb")as b:b.setparams(params);b.writeframes(raw)
def main(root,v2,v3):
 v3.mkdir(parents=True,exist_ok=True)
 for part in ("audio","annotations","recipes","timbres"):(v3/part).mkdir(exist_ok=True)
 manifest=json.loads((v2/"manifest.json").read_text()); new=[]
 for index,base in enumerate([x for x in manifest["clips"] if x["split"]=="held_out"][:5]):
  recipe=json.loads((root/base["render"]["recipe"]["path"]).read_text());track=recipe["source_track"]
  meta=yaml.safe_load((root/"slakh/babyslakh-meta/babyslakh_16k"/track/"metadata.yaml").read_text())
  drum=next(stem for stem,info in meta["stems"].items()if info.get("is_drum"));bass=next(stem for stem,info in meta["stems"].items()if info.get("inst_class")=="Bass")
  stems=root/"slakh/babyslakh-stems/babyslakh_16k"/track/"stems";start=base["source_start_seconds"];duration=base["duration_seconds"]
  source_ann=json.loads((root/base["annotation"]["path"]).read_text())
  for kind in ("isolated_bass","sparse_drum_bass"):
   ident=f"v3-{kind}-{index:02d}";audio=v3/"audio"/f"{ident}.wav"
   if kind=="isolated_bass":crop(stems/f"{bass}.wav",audio,start,duration);events={x:[]for x in LANES};events["BASS"]=source_ann["events"]["BASS"];render_kind="isolated_stem";stratum="isolated"
   else:
    a=v3/"audio"/f"{ident}.drum.wav";b=v3/"audio"/f"{ident}.bass.wav";crop(stems/f"{drum}.wav",a,start,duration);crop(stems/f"{bass}.wav",b,start,duration)
    with wave.open(str(a),"rb")as wa, wave.open(str(b),"rb")as wb:
     pa,ra=wa.getparams(),wa.readframes(wa.getnframes());rb=wb.readframes(wb.getnframes())
    with wave.open(str(audio),"wb")as out:out.setparams(pa);out.writeframes(audioop.add(audioop.mul(ra,pa.sampwidth,.5),audioop.mul(rb,pa.sampwidth,.5),pa.sampwidth))
    a.unlink();b.unlink();events=source_ann["events"];render_kind="frozen_submix";stratum="sparse"
   ann=v3/"annotations"/f"{ident}.json";ann.write_text(json.dumps({"reference_origin":"independent_render_metadata","annotator_id":"babyslakh-midi-v1","events":events},sort_keys=True)+"\n")
   rec=v3/"recipes"/f"{ident}.json";rec.write_text(json.dumps({"kind":render_kind,"original_stems":[f"{track}/stems/{drum}.wav",f"{track}/stems/{bass}.wav"],"operation":"frozen PCM crop; no model separation"},sort_keys=True)+"\n")
   ev=v3/"timbres"/f"{ident}.json";ev.write_text(json.dumps({"lanes":{x:{"timbre":"unverified","basis":"source_patch_metadata","source":"original Slakh stem; timbre unresolved"}for x in LANES}},sort_keys=True)+"\n")
   clip=dict(base);clip.update({"id":ident,"audio":desc(root,audio),"annotation":desc(root,ann),"render":{"kind":render_kind,"recipe":desc(root,rec)},"timbre_evidence":desc(root,ev),"stratum":stratum,"timbres":{x:"unverified"for x in LANES},"tags":["preliminary","rendered_domain","original_stems"]});new.append(clip)
 manifest["corpus_id"]="rd02-babyslakh-preliminary-v3-stems";manifest["clips"]+=new;(v3/"manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
 (v3/"gate-report.json").write_text(json.dumps({"accepted":False,"created":{"isolated_BASS":5,"sparse_drum_bass":5},"truth":"original stems plus frozen MIDI; no model separation","unresolved":["BD/SD/HH/TOM isolated fixtures unavailable: aggregate drum stem is not relabelled","all timbres unverified","long acquisition fixtures and lane-negative inventory absent"]},indent=2)+"\n");print(v3/"manifest.json")
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("root",type=Path);p.add_argument("v2",type=Path);p.add_argument("v3",type=Path);a=p.parse_args();main(a.root,a.v2,a.v3)
