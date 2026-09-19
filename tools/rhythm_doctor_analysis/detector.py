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
    """Return per-lane references; None means declared source MIDI is incomplete."""
    out={lane:[] for lane in LANES}; kinds=stem_kinds(meta_root/track.name/"metadata.yaml")
    note_map={"BD":(35,36),"SD":(37,38,40),"HH":(42,44,46),"TOM":(41,43,45,47,48,50)}
    missing={stem for stem in kinds if not (track/"MIDI"/(stem+".mid")).exists()}
    # Missing declared source material is unknown, never a negative. A missing
    # drum stem makes every mapped drum lane unscorable because its notes could
    # belong to any of those lanes; no declared Bass remains a known empty lane.
    for stem in missing:
        if kinds[stem] == "BASS": out["BASS"]=None
        elif kinds[stem] == "DRUM":
            for lane in note_map: out[lane]=None
    for stem,kind in kinds.items():
        midi=track/"MIDI"/(stem+".mid")
        if stem in missing: continue
        for onset,note in midi_onsets(midi):
            if not start <= onset < end: continue
            if kind == "BASS" and out["BASS"] is not None: out["BASS"].append(onset-start)
            elif kind == "DRUM":
                for lane,notes in note_map.items():
                    if out[lane] is not None and note in notes: out[lane].append(onset-start)
    return out

def lane_is_scorable(reference_by_lane, lane):
    return reference_by_lane[lane] is not None

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
    # Explicit +/-1 frame context carries local attack shape without a recurrent
    # model; edge padding makes every input frame deterministic.
    return np.concatenate((np.vstack((base[0],base[:-1])),base,np.vstack((base[1:],base[-1]))),axis=1)

def balanced_training_rows(feature_rows, labels, max_rows=60000, rng=None):
    """Keep every positive frame; cap only empty frames without negative sizes."""
    x=np.asarray(feature_rows); y=np.asarray(labels,dtype=bool)
    if x.ndim < 1 or x.shape[0] != y.shape[0] or max_rows < 1:
        raise ValueError("invalid training rows")
    if len(x) <= max_rows:
        return x,y
    positives=np.flatnonzero(y); negatives=np.flatnonzero(~y)
    negative_budget=max(0,max_rows-len(positives))
    if negative_budget == 0:
        keep=positives
    elif negative_budget >= len(negatives):
        keep=np.r_[positives,negatives]
    else:
        chooser=rng if rng is not None else np.random.default_rng(SEED)
        keep=np.r_[positives,chooser.choice(negatives,negative_budget,replace=False)]
    keep.sort()
    return x[keep],y[keep]

def classifier_probabilities(model, feature_rows):
    """Return the probability of label True, including one-class fitted models."""
    classes=np.asarray(model.classes_)
    if len(classes) == 1:
        return np.full(len(feature_rows),1. if classes[0] == 1 else 0.)
    positive=np.flatnonzero(classes == 1)
    if len(positive) != 1:
        raise ValueError("classifier has no unique positive class")
    probabilities=np.asarray(model.predict_proba(feature_rows))
    if probabilities.ndim != 2 or probabilities.shape[0] != len(feature_rows) or probabilities.shape[1] != len(classes):
        raise ValueError("invalid classifier probabilities")
    return probabilities[:,positive[0]]
def onset_frame_targets(times, reference, tolerance=TOLERANCE):
    """Assign each reference to its nearest analysis frame within tolerance.

    Unlike the old +/- tolerance training mask, one bass attack cannot turn five
    neighbouring frames into positive examples.  The output remains one boolean
    per input frame and permits normal peak selection at inference time.
    """
    moments=np.asarray(times,dtype=float)
    events=np.asarray(reference,dtype=float)
    targets=np.zeros(len(moments),dtype=bool)
    if not len(moments) or not len(events):
        return targets
    right=np.searchsorted(moments,events,side="left")
    left=np.maximum(right-1,0); right=np.minimum(right,len(moments)-1)
    nearest=np.where(np.abs(events-moments[left]) <= np.abs(moments[right]-events),left,right)
    accepted=np.abs(moments[nearest]-events) <= tolerance
    targets[nearest[accepted]]=True
    return targets
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
    dev_refs={}; dev_features={}; dev_times={}; durations={}
    for name in DEV:
        audio,sr,duration=load_track(available[name],args.dev_seconds); times=np.arange(.1,duration,HOP); ref=labels(available[name],args.meta,0,duration)
        durations[name]=duration; dev_refs[name]=ref; dev_times[name]=times; dev_features[name]=features(audio,sr,times)
    models=[]; thresholds=[]; development_diagnostics={}; provenance={lane:{"development_unknown_tracks":[],"held_unknown_tracks":[]} for lane in LANES}
    for lane_index,lane in enumerate(LANES):
        scorable_dev=[name for name in DEV if lane_is_scorable(dev_refs[name],lane)]
        provenance[lane]["development_unknown_tracks"]=[name for name in DEV if name not in scorable_dev]
        x=np.vstack([dev_features[name] for name in scorable_dev])
        y=np.concatenate([np.array([any(abs(time-event)<=TOLERANCE for event in dev_refs[name][lane]) for time in dev_times[name]]) for name in scorable_dev])
        # Keep all event-neighbour frames and deterministically subsample empty
        # frames per lane. Unknown-reference rows never reach fit or tuning.
        x,y=balanced_training_rows(x,y,max_rows=60000,rng=np.random.default_rng(SEED+lane_index))
        model=RandomForestClassifier(n_estimators=64,max_depth=10,min_samples_leaf=2,max_features="sqrt",random_state=SEED+lane_index,n_jobs=1,class_weight="balanced_subsample").fit(x,y); models.append(model)
        examples=[(classifier_probabilities(model,dev_features[name]),dev_times[name],dev_refs[name][lane]) for name in scorable_dev]
        threshold=tune_threshold(examples); thresholds.append(threshold)
        predicted=[peak_times(probability,times,threshold) for probability,times,_ in examples]
        offsets=[offset for (_,_,reference),guess in zip(examples,predicted) for offset in matched_offsets(reference,guess)]
        values=[onset_score(reference,guess,TOLERANCE) for (_,_,reference),guess in zip(examples,predicted)]
        tp,fp,fn=(sum(score[key] for score in values) for key in ("tp","fp","fn"))
        development_diagnostics[lane]={"tp":tp,"fp":fp,"fn":fn,"precision":tp/(tp+fp) if tp+fp else 0.,"recall":tp/(tp+fn) if tp+fn else 0.,"scorable_tracks":scorable_dev,"unknown_tracks":provenance[lane]["development_unknown_tracks"],"matched_offset_mean_ms":float(np.mean(offsets)*1000) if offsets else None,"matched_offset_p95_abs_ms":float(np.percentile(abs(np.asarray(offsets)),95)*1000) if offsets else None}
    raw={}; scores={lane:[] for lane in LANES}
    for name in HELD:
        audio,sr,duration=load_track(available[name],args.held_seconds); times=np.arange(.1,duration,HOP); durations[name]=duration; matrix=features(audio,sr,times); refs=labels(available[name],args.meta,0,duration); raw[name]={}
        for index,lane in enumerate(LANES):
            probabilities=classifier_probabilities(models[index],matrix); predicted=peak_times(probabilities,times,thresholds[index]); raw[name][lane]=predicted
            if lane_is_scorable(refs,lane): scores[lane].append(onset_score(refs[lane],predicted,TOLERANCE))
            else: provenance[lane]["held_unknown_tracks"].append(name)
    summary={}
    for lane,values in scores.items():
        tp,fp,fn=(sum(score[key] for score in values) for key in ("tp","fp","fn"))
        summary[lane]={"f1":2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 1.,"macro_track_f1":float(np.mean([score["f1"] for score in values])) if values else None,"tp":tp,"fp":fp,"fn":fn,"scorable_track_count":len(values),"unknown_track_count":len(provenance[lane]["held_unknown_tracks"])}
    args.out.mkdir(parents=True,exist_ok=True); pickle.dump(models,open(args.out/"candidate_a.pkl","wb")); (args.out/"predictions.json").write_text(json.dumps(raw))
    archive=args.corpus.parent.parent/"babyslakh_16k.tar.gz"
    counts={lane:{"development_reference_events":sum(len(dev_refs[name][lane]) for name in DEV if lane_is_scorable(dev_refs[name],lane)),"development_scorable_tracks":len(development_diagnostics[lane]["scorable_tracks"]),"development_unknown_tracks":development_diagnostics[lane]["unknown_tracks"],"held_reference_events":sum(summary[lane][key] for key in ("tp","fn")),"held_predicted_peaks":sum(summary[lane][key] for key in ("tp","fp")),"held_scorable_tracks":summary[lane]["scorable_track_count"],"held_unknown_tracks":provenance[lane]["held_unknown_tracks"]} for lane in LANES}
    report={"acceptance_claimed":False,"status":"DIAGNOSTIC_INCOMPLETE_CORPUS_STRATA","seed":SEED,"development":DEV,"heldout":HELD,"development_seconds":"full_source", "held_seconds":args.held_seconds,"durations_seconds":durations,"onset_tolerance_s":TOLERANCE,"refractory_s":REFRACTORY,"thresholds_tuned_development_only":dict(zip(LANES,thresholds)),"development_diagnostics":development_diagnostics,"per_lane":summary,"quality_counts":counts,"label_provenance":provenance,"source_hashes":{"archive":sha256(archive),"model":sha256(args.out/"candidate_a.pkl")},"limitations":["This preliminary corpus lacks required source/kit and isolated/sparse/full-mixture held-out strata; no grid F1 or acceptance gate is reported.","Declared stems with missing MIDI are unknown and excluded from fitting, threshold tuning, scoring, and counts; prior RF reports that treated them as empty negatives are measured-tainted configuration evidence, not architecture failure."]}
    (args.out/"report.json").write_text(json.dumps(report,indent=2)); print(json.dumps(report))

if __name__=="__main__": main()
