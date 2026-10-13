"""Typed source-bound MIDI keyboard phrase proof candidate."""
import hashlib,json
class KeyboardPhraseError(ValueError): pass
def _sha(x): return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def expected_messages(port,notes):
 if type(port) is not int or not 0<=port<=255: raise KeyboardPhraseError("invalid MIDI port")
 if not isinstance(notes,list) or not notes: raise KeyboardPhraseError("phrase needs notes")
 out=[]
 for row in notes:
  if not isinstance(row,dict) or set(row)!={"note","velocity"}: raise KeyboardPhraseError("note row needs exact note and velocity")
  n,v=row["note"],row["velocity"]
  if type(n) is not int or not 0<=n<=127 or type(v) is not int or not 1<=v<=127: raise KeyboardPhraseError("note/velocity outside MIDI range")
  out.extend([{"type":"midi","port":port,"bytes":[144,n,v]},{"type":"midi","port":port,"bytes":[128,n,0]}])
 return out
def _bytes(row):
 value=row.get("bytes") if isinstance(row,dict) else None
 if isinstance(value,list): return value
 if isinstance(value,str):
  try: values=[int(part) for part in value.split()]
  except ValueError as exc: raise KeyboardPhraseError("published MIDI bytes are malformed") from exc
  if not value.strip() or any(not 0<=part<=255 for part in values): raise KeyboardPhraseError("published MIDI bytes are outside MIDI range")
  return values
 raise KeyboardPhraseError("published MIDI bytes are missing")
def validate(interval,target_id,port,notes,target_midi,expected_output):
 if not isinstance(interval,list) or not interval: raise KeyboardPhraseError("missing captured source interval")
 observed=[]
 for step in interval:
  if not isinstance(step,dict) or not isinstance(step.get("inputs"),list): raise KeyboardPhraseError("malformed source step")
  observed.extend(x for x in step["inputs"] if isinstance(x,dict) and x.get("type")=="midi")
 if observed!=expected_messages(port,notes): raise KeyboardPhraseError("ordered public MIDI input differs from the authored phrase")
 if not isinstance(target_midi,dict) or target_midi.get("truncated") is not False or not isinstance(target_midi.get("events"),list) or target_midi.get("total")!=len(target_midi["events"]): raise KeyboardPhraseError("target output is incomplete")
 actual=[{"port":row.get("port"),"bytes":_bytes(row)} for row in target_midi["events"]]
 if not isinstance(expected_output,list): raise KeyboardPhraseError("expected mapped output is malformed")
 expected=[{"port":row.get("port"),"bytes":_bytes(row)} for row in expected_output if isinstance(row,dict)]
 if len(expected)!=len(expected_output) or actual!=expected: raise KeyboardPhraseError("target MIDI does not equal the exact mapped output")
 return {"kind":"keyboard-midi-phrase-v1","target_step_id":target_id,"port":port,"notes":notes,"input_sha256":_sha(observed),"output_sha256":_sha(target_midi)}
