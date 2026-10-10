"""Embedded compiler schemas must admit the same strict teaching grammar."""
import copy,json
from pathlib import Path
import pytest
from jsonschema import Draft7Validator,ValidationError
ROOT=Path(__file__).resolve().parents[1]
def teaching(kind):
 a={'id':'act','kind':kind,'label':'Perform the musical operation'}
 req={}
 if kind=='play-keyboard-phrase':a.update(port=1,notes=[{'note':60,'velocity':90}]);req={'midi_events_at_target':[{'port':1,'bytes':[144,60,90]}]}
 elif kind=='play-note-silence':a.update(play_step_id='playing',stop_step_id='stopped',window_result_id='silent',window_duration_s=2.8);req={'play_note_silence_at_target':True}
 else:a.update(control='E3',field_label='Trig Probability',field_slot=2,expected_marker='L',while_held_grid={'x':1,'y':4},value='0');req={'parameter_readout_equals':{'schema_version':1,'parameter_label':'Trig Probability','display_label':'Trig Probability','slot':2,'value':'0','marker':'L','picker_step_id':'picker','assignment_step_id':'assigned','readout_step_id':'readout','effect_step_id':'target','effect_assertion':{'kind':'probability-zero-silence','passed':True}}}
 return {'from_step_id':'start','transition_scope':'interval','actions':[a,{'id':'preview','kind':'preview-recorded-result','label':'Hear the result','target_step_id':'target'}],'semantic_requires':req,'human_outcome':'The edited phrase demonstrates the chosen musical change.'}
@pytest.mark.parametrize('name',['book.schema.json','course.schema.json'])
@pytest.mark.parametrize('kind',['play-keyboard-phrase','play-note-silence','select-value'])
def test_compiler_embedded_schema_accepts_current_teaching_actions(name,kind):
 schema=json.loads((ROOT/'manual'/name).read_text());Draft7Validator({'$ref':'#/definitions/teaching_binding','definitions':schema['definitions']}).validate(teaching(kind))
@pytest.mark.parametrize('name',['book.schema.json','course.schema.json'])
def test_embedded_schema_rejects_invalid_keyboard_note(name):
 schema=json.loads((ROOT/'manual'/name).read_text());bad=teaching('play-keyboard-phrase');bad['actions'][0]['notes'][0]['note']=128
 with pytest.raises(ValidationError):Draft7Validator({'$ref':'#/definitions/teaching_binding','definitions':schema['definitions']}).validate(bad)

@pytest.mark.parametrize('name',['book.schema.json','course.schema.json'])
def test_explicit_released_target_boolean_matches_producer_contract(name):
 schema=json.loads((ROOT/'manual'/name).read_text());good=teaching('play-keyboard-phrase');good['preserve_holds_at_target']=False
 validator=Draft7Validator({'$ref':'#/definitions/teaching_binding','definitions':schema['definitions']});validator.validate(good)
 good['preserve_holds_at_target']='false'
 with pytest.raises(ValidationError):validator.validate(good)

@pytest.mark.parametrize('name',['book.schema.json','teaching-binding.schema.json'])
@pytest.mark.parametrize('kind',['play-keyboard-phrase','play-note-silence','select-value'])
def test_whole_feature_lesson_uses_canonical_teaching_grammar(name,kind):
 schema=json.loads((ROOT/'manual'/name).read_text());lesson={'id':'musical-operation','binding':{'status':'controlled-verified','scene':'example','step':'target'},'teaching_binding':teaching(kind)}
 Draft7Validator({'$ref':'#/definitions/feature_teaching_binding','definitions':schema['definitions']}).validate(lesson)
