import copy,importlib.util,json,hashlib
from pathlib import Path
import pytest
ROOT=Path(__file__).parents[1]
SRC=ROOT/"tests/fixtures/manual-keyboard-mapped-minor-v1.json"
PIN="c36568bdfb96f07a9032a183ad3d24dc931cf6f0f546b8d108eae6dd41a6b4ff"
MODULE=Path(__file__).parents[1]/"tools"/"manual_keyboard_phrase.py"
def _load():
 s=importlib.util.spec_from_file_location("manual_keyboard_phrase_candidate",MODULE);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def _fixture():
 assert hashlib.sha256(SRC.read_bytes()).hexdigest()==PIN
 return copy.deepcopy(json.loads(SRC.read_text())["step"])
def _expect():
 s=_fixture(); notes=[{"note":n,"velocity":90} for n in range(60,73)]; out=s["output"]["midi"]["events"]; return s,notes,out
def test_play_keyboard_phrase_accepts_exact_source_input_and_mapped_output():
 m=_load();s,n,o=_expect();r=m.validate([s],"mapped-minor",1,n,s["output"]["midi"],o);assert r["kind"]=="keyboard-midi-phrase-v1" and r["input_sha256"] and r["output_sha256"]
def test_reject_keyboard_phrase_wrong_port():
 m=_load();s,n,o=_expect()
 with pytest.raises(m.KeyboardPhraseError):m.validate([s],"mapped-minor",2,n,s["output"]["midi"],o)
def test_reject_keyboard_phrase_reordered_midi_inputs():
 m=_load();s,n,o=_expect();s["inputs"][14],s["inputs"][16]=s["inputs"][16],s["inputs"][14]
 with pytest.raises(m.KeyboardPhraseError):m.validate([s],"mapped-minor",1,n,s["output"]["midi"],o)
def test_reject_keyboard_phrase_changed_pitch():
 m=_load();s,n,o=_expect();s["inputs"][14]["bytes"][1]=61
 with pytest.raises(m.KeyboardPhraseError):m.validate([s],"mapped-minor",1,n,s["output"]["midi"],o)
def test_reject_keyboard_phrase_mapped_result_mutation():
 m=_load();s,n,o=_expect();o=copy.deepcopy(o);o[2]["bytes"][1]=63
 with pytest.raises(m.KeyboardPhraseError):m.validate([s],"mapped-minor",1,n,s["output"]["midi"],o)
def test_reject_keyboard_phrase_truncated_target():
 m=_load();s,n,o=_expect();s["output"]["midi"]["truncated"]=True
 with pytest.raises(m.KeyboardPhraseError):m.validate([s],"mapped-minor",1,n,s["output"]["midi"],o)
