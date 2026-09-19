"""RD-02 candidate A diagnostic. Scores are diagnostic, never release evidence."""
import argparse, hashlib, json, pickle, re, sys
from pathlib import Path
import mido, numpy as np, soundfile as sf
from sklearn.ensemble import RandomForestClassifier

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT / "tests" / "rhythm_doctor"))
from quality import onset_score

LANES = ("BD", "SD", "HH", "TOM", "BASS")
DEV = ("Track00003","Track00004","Track00005","Track00007","Track00010","Track00012","Track00013","Track00017","Track00018")
HELD = ("Track00001","Track00002","Track00006","Track00008","Track00009","Track00011","Track00014","Track00015","Track00016","Track00019","Track00020")
TOLERANCE = .050; HOP = .020; REFRACTORY = .060; SEED = 20260919

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as source:
        for chunk in iter(lambda: source.read(1<<20),b""): h.update(chunk)
    return h.hexdigest()

def midi_onsets(path):
    elapsed=0.; out=[]
    for message in mido.MidiFile(path):
        elapsed += message.time
        if message.type == "note_on" and message.velocity: out.append((elapsed,message.note))
    return out

def stem_kinds(metadata):
    current=None; kinds={}
    for line in metadata.read_text(errors="replace").splitlines():
        found=re.match(r"^  (S\d+):",line)
        if found: current=found.group(1)
        if current and "inst_class: Bass" in line: kinds[current]="BASS"
        if current and "is_drum: true" in line: kinds[current]="DRUM"
    return kinds

def labels(track, meta_root, start, end):
    out={lane:[] for lane in LANES}; kinds=stem_kinds(meta_root/track.name/"metadata.yaml")
    note_map={"BD":(35,36),"SD":(37,38,40),"HH":(42,44,46),"TOM":(41,43,45,47,48,50)}
    for stem,kind in kinds.items():
        midi=track/"MIDI"/(stem+".mid")
        if not midi.exists(): continue
        for onset,note in midi_onsets(midi):
            if not start <= onset < end: continue
            if kind == "BASS": out["BASS"].append(onset-start)
            elif kind == "DRUM":
                for lane,notes in note_map.items():
                    if note in notes: out[lane].append(onset-start)
    return out

def features(audio, sr, times):
    """Stereo magnitude energy (phase-inversion invariant), flux and harmonic bass support."""
    if audio.ndim == 1: audio=audio[:,None]
    n=1024; window=np.hanning(n); frequencies=np.fft.rfftfreq(n,1/sr)
    edges=np.geomspace(25,7500,33)
    rows=[]
    for time in times:
        index=int(time*sr); before=audio[max(0,index-n):index]; after=audio[index:min(len(audio),index+n)]
        before=np.pad(before,((max(0,n-len(before)),0),(0,0))); after=np.pad(after,((0,max(0,n-len(after))),(0,0)))
        old=np.abs(np.fft.rfft(before*window[:,None],axis=0)).mean(1)
        new=np.abs(np.fft.rfft(after*window[:,None],axis=0)).mean(1)
        row=[]
        for low,high in zip(edges[:-1],edges[1:]):
            mask=(frequencies>=low)&(frequencies<high); row += [float(np.log1p(new[mask].sum())),float(np.log1p(new[mask].sum())-np.log1p(old[mask].sum()))]
        harmonic=[]
        for fundamental in (55.,65.4,73.4,82.4,98.,110.,130.8,146.8,164.8,196.):
            harmonic.append(sum(new[np.argmin(abs(frequencies-fundamental*h))] for h in (1,2,3,4)))
        row += [float(max(harmonic)/(new.sum()+1e-9)), float(np.sqrt(np.mean(after*after)))]
        rows.append(row)
    base=np.asarray(rows)
    # Explicit Â±1 frame context carries local attack shape without a recurrent
    # model; edge padding makes every input frame deterministic.
    return np.concatenate((np.vstack((base[0],base[:-1])),base,np.vstack((base[1:],base[-1]))),axis=1)

def peak_times(probabilities, times, threshold):
    out=[]; last=-1e9
    for index,value in enumerate(probabilities):
        left=probabilities[index-1] if index else -1
        right=probabilities[index+1] if index+1<len(probabilities) else -1
        if value>=threshold and value>=left and value>right and times[index]-last>=REFRACTORY:
            out.append(float(times[index])); last=times[index]
    return out

def matched_offsets(reference, predicted):
    """Greedy ordered matching mirrors the independent scorer's tolerance path."""
    offsets=[]; i=j=0
    while i<len(reference) and j<len(predicted):
        delta=predicted[j]-reference[i]
        if abs(delta)<=TOLERANCE:
            offsets.append(delta); i+=1; j+=1
        elif delta<0: j+=1
        else: i+=1
    return offsets

def tune_threshold(examples):
    best=(0., .5)
    for threshold in np.arange(.10,.91,.05):
        scores=[onset_score(reference,peak_times(probability,times,threshold),TOLERANCE)["f1"] for probability,times,reference in examples]
        candidate=(float(np.mean(scores)),float(threshold))
        if candidate>best: best=candidate
    return best[1]

def load_track(track, seconds):
    info=sf.info(track/"mix.wav"); stop=None if seconds<=0 else min(info.frames,int(seconds*info.samplerate))
    audio,sr=sf.read(track/"mix.wav",stop=stop); return audio,sr,len(audio)/sr

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--corpus",type=Path,required=True); parser.add_argument("--meta",type=Path,required=True); parser.add_argument("--out",type=Path,required=True); parser.add_argument("--dev-seconds",type=float,default=0.); parser.add_argument("--held-seconds",type=float,default=60.)
    args=parser.parse_args(); available={p.name:p for p in args.corpus.glob("Track*") if (p/"mix.wav").exists()}
    if any(name not in available for name in DEV+HELD): raise SystemExit("frozen manifest is not materialized")
    x=[]; y=[]; dev_refs={}; dev_features={}; dev_times={}; durations={}
    for name in DEV:
        audio,sr,duration=load_track(available[name],args.dev_seconds); times=np.arange(.1,duration,HOP); ref=labels(available[name],args.meta,0,duration); durations[name]=duration; dev_refs[name]=ref; dev_times[name]=times
        dev_features[name]=features(audio,sr,times); x.append(dev_features[name]); y.append(np.array([[any(abs(time-event)<=TOLERANCE for event in ref[lane]) for lane in LANES] for time in times]))
    x=np.vstack(x); y=np.vstack(y)
    # Keep all event-neighbour frames and deterministically subsample empty
    # frames, bounding development memory without discarding rare TOM examples.
    if len(x)>60000:
        rng=np.random.default_rng(SEED); positive=np.any(y,axis=1); negative=np.flatnonzero(~positive)
        keep=np.r_[np.flatnonzero(positive), rng.choice(negative,60000-int(positive.sum()),replace=False)]; keep.sort(); x,y=x[keep],y[keep]
    models=[]; thresholds=[]; development_diagnostics={}
    for lane_index,lane in enumerate(LANES):
        model=RandomForestClassifier(n_estimators=64,max_depth=10,min_samples_leaf=2,max_features="sqrt",random_state=SEED+lane_index,n_jobs=1,class_weight="balanced_subsample").fit(x,y[:,lane_index]); models.append(model)
        examples=[]
        for name in DEV:
            examples.append((model.predict_proba(dev_features[name])[:,1] if len(model.classes_)==2 else np.zeros(len(dev_times[name])),dev_times[name],dev_refs[name][lane]))
        threshold=tune_threshold(examples); thresholds.append(threshold)
        predicted=[peak_times(probability,times,threshold) for probability,times,_ in examples]
        offsets=[offset for (_,_,reference),guess in zip(examples,predicted) for offset in matched_offsets(reference,guess)]
        scores=[onset_score(reference,guess,TOLERANCE) for (_,_,reference),guess in zip(examples,predicted)]
        tp,fp,fn=(sum(score[key] for score in scores) for key in ("tp","fp","fn"))
        development_diagnostics[lane]={"tp":tp,"fp":fp,"fn":fn,"precision":tp/(tp+fp) if tp+fp else 0.,"recall":tp/(tp+fn) if tp+fn else 0.,"matched_offset_mean_ms":float(np.mean(offsets)*1000) if offsets else None,"matched_offset_p95_abs_ms":float(np.percentile(abs(np.asarray(offsets)),95)*1000) if offsets else None}
    raw={}; scores={lane:[] for lane in LANES}
    for name in HELD:
        audio,sr,duration=load_track(available[name],args.held_seconds); times=np.arange(.1,duration,HOP); durations[name]=duration; matrix=features(audio,sr,times); refs=labels(available[name],args.meta,0,duration); raw[name]={}
        for index,lane in enumerate(LANES):
            probabilities=models[index].predict_proba(matrix)[:,1] if len(models[index].classes_)==2 else np.zeros(len(times)); predicted=peak_times(probabilities,times,thresholds[index]); raw[name][lane]=predicted; scores[lane].append(onset_score(refs[lane],predicted,TOLERANCE))
    summary={}
    for lane,values in scores.items():
        tp,fp,fn=(sum(score[key] for score in values) for key in ("tp","fp","fn"))
        summary[lane]={"f1":2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 1.,"macro_track_f1":float(np.mean([score["f1"] for score in values])),"tp":tp,"fp":fp,"fn":fn}
    args.out.mkdir(parents=True,exist_ok=True); pickle.dump(models,open(args.out/"candidate_a.pkl","wb")); (args.out/"predictions.json").write_text(json.dumps(raw))
    archive=args.corpus.parent.parent/"babyslakh_16k.tar.gz"
    counts={lane:{"development_reference_events":sum(len(dev_refs[name][lane]) for name in DEV),"held_reference_events":sum(summary[lane][key] for key in ("tp","fn")),"held_predicted_peaks":sum(summary[lane][key] for key in ("tp","fp"))} for lane in LANES}
    report={"acceptance_claimed":False,"status":"DIAGNOSTIC_INCOMPLETE_CORPUS_STRATA","seed":SEED,"development":DEV,"heldout":HELD,"development_seconds":"full_source", "held_seconds":args.held_seconds,"durations_seconds":durations,"onset_tolerance_s":TOLERANCE,"refractory_s":REFRACTORY,"thresholds_tuned_development_only":dict(zip(LANES,thresholds)),"development_diagnostics":development_diagnostics,"per_lane":summary,"quality_counts":counts,"source_hashes":{"archive":sha256(archive),"model":sha256(args.out/"candidate_a.pkl")},"limitations":["This preliminary corpus lacks required source/kit and isolated/sparse/full-mixture held-out strata; no grid F1 or acceptance gate is reported."]}
    (args.out/"report.json").write_text(json.dumps(report,indent=2)); print(json.dumps(report))

if __name__=="__main__": main()
