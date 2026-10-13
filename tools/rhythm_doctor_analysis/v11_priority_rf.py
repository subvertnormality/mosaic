"""V11 rendered-domain BD/SD/HH diagnostic with development-only selection."""
import argparse, hashlib, json, pickle, sys
from pathlib import Path
import numpy as np
import soundfile as sf
from sklearn.ensemble import RandomForestClassifier

ROOT=Path(__file__).parents[2]
sys.path.insert(0,str(ROOT/'tests'/'rhythm_doctor'))
from quality import onset_score

LANES=('BD','SD','HH')
SEED=20260919
HOP=.020
TOLERANCE=.050
REFRACTORY=.060
VALIDATION_KIT='ar_modern_white_kit_full.nkm'

def sha256(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for block in iter(lambda:f.read(1<<20),b''):h.update(block)
 return h.hexdigest()

def partition_development(clips):
 development=[c for c in clips if c.get('split')=='development']
 train=[c for c in development if c.get('kit_id')!=VALIDATION_KIT]
 validation=[c for c in development if c.get('kit_id')==VALIDATION_KIT]
 if not train or not validation or {c.get('kit_id') for c in train}&{c.get('kit_id') for c in validation}:
  raise ValueError('fixed source-kit validation split is unavailable')
 return train,validation

def phase_safe_mono(audio):
 x=np.asarray(audio,dtype=np.float32)
 if x.ndim==1:return x
 if x.ndim!=2 or not x.shape[1]:raise ValueError('invalid audio')
 mean=x.mean(axis=1); rms=np.mean(x*x,axis=0); strongest=x[:,int(np.argmax(rms))]
 return strongest if np.max(rms)>0 and np.mean(mean*mean)/np.max(rms)<.1 else mean

def feature_matrix(audio,sr):
 x=phase_safe_mono(audio); n=1024; half=n//2; window=np.hanning(n); freqs=np.fft.rfftfreq(n,1/sr)
 edges=np.geomspace(30,9000,25); masks=[(freqs>=lo)&(freqs<hi) for lo,hi in zip(edges[:-1],edges[1:])]
 times=np.arange(.05,max(.05,len(x)/sr-.05),HOP); rows=[]; prior=None
 for t in times:
  center=int(t*sr); frame=x[max(0,center-half):min(len(x),center+half)]
  frame=np.pad(frame,(max(0,half-(center)),max(0,n-len(frame)-max(0,half-center))))[:n]
  mag=np.abs(np.fft.rfft(frame*window)); band=np.log1p(np.array([mag[m].sum() for m in masks]))
  delta=band-(prior if prior is not None else band); prior=band
  total=float(np.log1p(mag.sum())); centroid=float((freqs*mag).sum()/(mag.sum()+1e-9)/9000)
  low=float(np.log1p(mag[(freqs>=30)&(freqs<180)].sum())); high=float(np.log1p(mag[(freqs>=2500)&(freqs<9000)].sum()))
  rows.append(np.r_[band,delta,total,centroid,low,high])
 base=np.asarray(rows,dtype=np.float32)
 return times,np.c_[np.vstack((base[0],base[:-1])),base,np.vstack((base[1:],base[-1]))]

def references(annotation):
 data=json.loads(annotation.read_text(encoding='utf8'))
 return {lane:[float(e['time_seconds']) for e in data['events'].get(lane,[])] for lane in LANES}

def nearest_frame_labels(times,events):
 """Assign each onset to one nearest analysis frame, never an onset-width mask."""
 moments=np.asarray(times,dtype=float); labels=np.zeros(len(moments),dtype=bool)
 if not len(moments): return labels
 for event in events:
  right=int(np.searchsorted(moments,event,side='left')); left=max(0,right-1); right=min(right,len(moments)-1)
  index=left if abs(moments[left]-event)<=abs(moments[right]-event) else right
  if abs(moments[index]-event)<=TOLERANCE: labels[index]=True
 return labels

def balanced(x,y,rng):
 pos=np.flatnonzero(y); neg=np.flatnonzero(~y); keep_neg=min(len(neg),max(2000,8*len(pos)))
 chosen=neg if keep_neg==len(neg) else rng.choice(neg,keep_neg,replace=False)
 keep=np.sort(np.r_[pos,chosen]); return x[keep],y[keep]

def positive_probability(model,x):
 classes=np.asarray(model.classes_); index=np.flatnonzero(classes==True)
 if len(index)!=1:return np.zeros(len(x),dtype=float)
 return model.predict_proba(x)[:,index[0]]

def peaks(prob,times,threshold):
 out=[]; last=-1e9
 for i,p in enumerate(prob):
  left=prob[i-1] if i else -1.; right=prob[i+1] if i+1<len(prob) else -1.
  if p>=threshold and p>=left and p>right and times[i]-last>=REFRACTORY:out.append(float(times[i]));last=times[i]
 return out

def aggregate(rows):
 tp=sum(x['tp'] for x in rows); fp=sum(x['fp'] for x in rows); fn=sum(x['fn'] for x in rows)
 return {'tp':tp,'fp':fp,'fn':fn,'precision':tp/(tp+fp) if tp+fp else 0.,'recall':tp/(tp+fn) if tp+fn else 0.,'f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 1.}

def choose_threshold(prepared,lane):
 options=[]
 for threshold in np.arange(.10,.91,.05):
  scores=[onset_score(refs[lane],peaks(probability,times,float(threshold)),TOLERANCE) for probability,times,refs in prepared]
  options.append((float(np.mean([s['f1'] for s in scores])),float(threshold)))
 return max(options)[1]

def main():
 p=argparse.ArgumentParser();p.add_argument('--corpus',type=Path,required=True);p.add_argument('--cache-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 if a.out.exists():raise SystemExit('fresh output directory required')
 manifest=json.loads((a.corpus/'manifest.json').read_text(encoding='utf8'));train_clips,val_clips=partition_development(manifest['clips']);held=[c for c in manifest['clips'] if c.get('split')=='held_out' and c['id'].startswith('v11-')]
 if len(held)!=66:raise SystemExit('expected frozen 66 v11 held clips')
 def prepare(clips):
  out=[]
  for c in clips:
   audio,sr=sf.read(a.cache_root/c['audio']['path'],always_2d=True);times,x=feature_matrix(audio,sr);out.append((c,times,x,references(a.cache_root/c['annotation']['path'])))
  return out
 train=prepare(train_clips); validation=prepare(val_clips)
 thresholds={}; selected={}; rng=np.random.default_rng(SEED)
 for lane_i,lane in enumerate(LANES):
  x=np.vstack([d[2] for d in train]);y=np.concatenate([nearest_frame_labels(d[1],d[3][lane]) for d in train]);bx,by=balanced(x,y,np.random.default_rng(SEED+lane_i))
  model=RandomForestClassifier(n_estimators=160,max_depth=16,min_samples_leaf=1,max_features=.65,class_weight='balanced_subsample',random_state=SEED+lane_i,n_jobs=1).fit(bx,by)
  validation_probabilities=[(positive_probability(model,x),times,refs) for _,times,x,refs in validation]
  thresholds[lane]=choose_threshold(validation_probabilities,lane);selected[lane]={'train_rows':int(len(bx)),'positive_rows':int(by.sum()),'validation_clips':[d[0]['id'] for d in validation]}
 # Refit after fixed development-only architecture/threshold selection. Held remains unread until this point.
 models={}
 all_development=train+validation
 for lane_i,lane in enumerate(LANES):
  x=np.vstack([d[2] for d in all_development]);y=np.concatenate([nearest_frame_labels(d[1],d[3][lane]) for d in all_development]);bx,by=balanced(x,y,np.random.default_rng(SEED+100+lane_i))
  models[lane]=RandomForestClassifier(n_estimators=160,max_depth=16,min_samples_leaf=1,max_features=.65,class_weight='balanced_subsample',random_state=SEED+100+lane_i,n_jobs=1).fit(bx,by)
 # Both the architecture/threshold selection and full-development refit precede all held reads.
 held_data=prepare(held)
 predictions={};metrics={lane:[] for lane in LANES};absent={lane:{'clips':0,'false_positives':0} for lane in LANES}
 for clip,times,x,refs in held_data:
  predictions[clip['id']]={}
  for lane in LANES:
   guess=peaks(positive_probability(models[lane],x),times,thresholds[lane]);predictions[clip['id']][lane]=guess;score=onset_score(refs[lane],guess,TOLERANCE);metrics[lane].append(score)
   if not refs[lane]:absent[lane]['clips']+=1;absent[lane]['false_positives']+=score['fp']
 a.out.mkdir(parents=True);pickle.dump(models,open(a.out/'models.pkl','wb'));(a.out/'predictions.json').write_text(json.dumps(predictions,indent=2),encoding='utf8')
 report={'acceptance_claimed':False,'scope':'Frozen v11 rendered-domain priority-lane diagnostic. Development-only source-kit validation chose thresholds; held labels were not used for training or selection.','seed':SEED,'manifest_sha256':sha256(a.corpus/'manifest.json'),'train_ids':[d[0]['id'] for d in train],'validation_ids':[d[0]['id'] for d in validation],'held_ids':[d[0]['id'] for d in held_data],'validation_kit':VALIDATION_KIT,'model':{'estimator':'RandomForestClassifier','n_estimators':160,'max_depth':16,'max_features':.65,'min_samples_leaf':1,'class_weight':'balanced_subsample'},'thresholds_validation_only':thresholds,'selection':selected,'per_class':{lane:aggregate(metrics[lane]) for lane in LANES},'absent_lane_false_positives':absent,'source_hashes':{'script':sha256(Path(__file__)),'model':sha256(a.out/'models.pkl'),'predictions':sha256(a.out/'predictions.json')},'limitations':['Rendered-domain kits differ from held Hydrogen kits; this is not physical-device, latency, BASS/TOM, velocity, or full acceptance evidence.','Per-class held metrics are independent one-to-one 50 ms onset scores; no held threshold tuning occurred.']}
 (a.out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
