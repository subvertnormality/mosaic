"""Independent native norns text-entry raster characterisation.

Player controls cite manual:save-and-load. Pixel geometry characterises pinned
norns lib/textentry.lua; expected glyphs are never sampled from native output.
"""
import base64, hashlib
import json
from pathlib import Path
from frame_oracle import render

KINDS = ('entry', 'delete', 'empty', 'first-character', 'name-entered', 'confirm')
NAME = 'Four notes'

def specification(stage):
    final_position = (ord('s') - 37) % 95
    specs = {'entry': ('new', 1, 1, 28), 'delete': ('new', 1, 0, 28),
             'empty': ('', 1, 0, 28), 'first-character': ('F', 0, 0, (ord('F')-37)%95),
             'name-entered': (NAME, 0, 0, final_position), 'confirm': (NAME, 1, 1, final_position)}
    if stage not in specs: raise ValueError('Unknown literal save-dialog stage')
    return specs[stage]

def expected(stage):
    text, row, delok, position = specification(stage)
    commands = [(0,16,15,''), (0,32,15,text)]
    commands += [(x*8,46,15 if x==5 and row==0 else 2,chr((x+position)%95+32)) for x in range(16)]
    commands += [(0,60,15 if row==1 and delok==0 else 2,'DEL'), ((None),60,15 if row==1 and delok==1 else 2,'OK')]
    # frame_oracle's right alignment uses x=127 when x is None.
    return render(commands)

def matches(state, stage):
    actual = base64.b64decode(state['frame']['pixels_base64'], validate=True)
    wanted = expected(stage)
    return len(actual)==len(wanted)==32768 and all(actual[i]==wanted[i] for i in range(32768) if i%4!=3)

def assert_frame(c, stage):
    state=c.wait(lambda observed: matches(observed,stage))
    text,row,delok,position=specification(stage)
    blob=base64.b64decode(state['frame']['pixels_base64'],validate=True)
    assert hashlib.sha256(blob).hexdigest()==state['frame']['sha256']
    c.results.append(dict(kind='manual-save-dialog-frame',stage=stage,text=text,row=row,
        delok=delok,position=position,native_observation_index=len(c.observations)-1,
        frame_sha256=state['frame']['sha256'],citation='manual:save-and-load',
        layout_characterisation='pinned native norns lib/textentry.lua',passed=True))
    return state

def verify_frame(row,state):
    stage=row.get('stage');text,line,delok,position=specification(stage)
    if any(row.get(k)!=v for k,v in dict(text=text,row=line,delok=delok,position=position).items()):
        raise ValueError('Changed literal save-dialog control/name checkpoint')
    if row.get('citation')!='manual:save-and-load' or not matches(state,stage):
        raise ValueError('Native save-dialog framebuffer differs from literal raster')

def verify_checkpoint(step, observations, path):
    """Strict supplementary publication check, called by an explicit verifier branch."""
    binding=step['output']['binding'];row=binding['assertion'];kind=row.get('kind')
    supported={'manual-save-dialog-frame','manual-save-dialog-cancel','manual-save-dialog-return','manual-save-dialog-persistence'}
    if kind not in supported:raise ValueError('Unsupported save-dialog semantic kind')
    source_root=Path(path).parent
    source=json.loads((source_root/'start-source-identity.json').read_text())
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    for relative in ['tests/behaviour/manual_save_dialog_oracle.py','tests/behaviour/frame_oracle.py','tests/behaviour/driver.py','tests/behaviour/ui_map.py','tests/behaviour/manual_save_project_canonical.py','tests/behaviour/persisted_digest.lua']:
        cached=source_root/'case-source'/relative
        if source.get('case_sources',{}).get(relative)!=digest(cached):raise ValueError('Unhashed or changed transitive dialog oracle source')
    for name in ['DERIVATION.json','Course seed.ptn','Course seed.pset','CANONICAL-RUNTIME.json','canonical-runtime/lua/lib/tabutil.lua']:
        relative='tests/behaviour/config/manual-save-dialog/'+name
        cached=source_root/'fixture-source'/relative
        if source.get('fixture_sources',{}).get(relative)!=digest(cached):raise ValueError('Unhashed or changed derived dialog fixture source')
    states=[x['state'] for x in observations if x['state']['frame']['sha256']==binding['sha256'] and x['state']['grid']==step['output']['grid']]
    if not states:raise ValueError('Missing actual bound save-dialog frame')
    if row.get('citation')!='manual:save-and-load':raise ValueError('Changed save-dialog citation')
    if kind=='manual-save-dialog-frame':
        index=row.get('native_observation_index')
        if type(index)is not int or not 0<=index<len(observations):raise ValueError('Invalid exact dialog observation index')
        state=observations[index]['state']
        if state['frame']['sha256']!=row.get('frame_sha256') or state['frame']['sha256']!=binding['sha256']:
            raise ValueError('Changed dialog observation/frame binding')
        verify_frame(row,state);return
    fixture=Path(path).parent/'fixture-source/tests/behaviour/config/manual-save-dialog'
    manifest_path=fixture/'DERIVATION.json';manifest=json.loads(manifest_path.read_text())
    literal={'Four notes.ptn':'eae271198e0a439612dae3be8ee56035c181a73fc82f41a6e0a400844fc50c3e',
             'Four notes.pset':'929b42d76afee564354f744cb89af3f753e3dd8d179108010eb5cf2e0d2252fd'}
    def fixture_source(raw):
        source=Path(raw)
        return source if source.is_absolute() else fixture/source
    if manifest['original_files']!=literal:raise ValueError('Changed literal original course persistence fixture')
    for name,origin in zip(literal,manifest['origins']):
        source=fixture_source(origin['path'])
        if origin.get('original_name')!=name or origin.get('sha256')!=literal[name] or digest(source)!=literal[name]:raise ValueError('Changed captured original course project source')
    report=fixture_source(manifest['original_course_report'])
    if digest(report)!=manifest['original_course_report_sha256']:raise ValueError('Changed captured original course report')
    if 'original_course_results' in manifest and digest(fixture_source(manifest['original_course_results']))!=manifest.get('original_course_results_sha256'):raise ValueError('Changed captured original course results')
    for name,value in manifest['derived_files'].items():
        if digest(fixture/name)!=value:raise ValueError('Changed derived seed fixture')
    witness=Path(path)/'save-dialog-evidence'
    if kind=='manual-save-dialog-cancel':
        from frame_oracle import selected_line
        if row.get('stage')!='cancel' or not any(selected_line(s,'< Save project',top=23) for s in states):
            raise ValueError('Cancellation did not return to public Save project menu')
        receipt_path=witness/'cancel.json';receipt=json.loads(receipt_path.read_text())
        if digest(receipt_path)!=row.get('receipt_sha256') or digest(manifest_path)!=row.get('fixture_sha256'):
            raise ValueError('Changed cancellation/source receipt')
        if receipt.get('named_files_absent') is not True or any(n in receipt['files'] for n in literal):
            raise ValueError('Cancelled save produced named project files')
        for name,value in manifest['derived_files'].items():
            if receipt['files'].get(name)!=value or digest(witness/name)!=value:raise ValueError('Cancellation changed seed project')
        if not any(v.get('type')=='key' and v.get('n')==2 and v.get('state')==0 for v in step['inputs']):
            raise ValueError('Cancellation lacks native released K2 input')
    elif kind=='manual-save-dialog-return':
        from frame_oracle import live_header_matches
        if row.get('stage')!='returned' or row.get('header')!=dict(title='SLOT SETUP',scope='SONG 01',layout='vertical_list'):
            raise ValueError('Changed returned arrangement screen contract')
        if not any(live_header_matches(s,'SLOT SETUP','SONG 01','vertical_list') for s in states):
            raise ValueError('Save did not return to actual arrangement screen')
    else:
        if row.get('stage')!='saved' or row.get('name')!=NAME or row.get('original_files')!=literal or row.get('files',{}).get('Four notes.pset')!=literal['Four notes.pset']:
            raise ValueError('Changed exact retained arrangement persistence witness')
        if row.get('picker_confirmed') is not True or row.get('held_controls')!=[] or row.get('outstanding_notes') is not False:
            raise ValueError('Incomplete named save/recovery qualification')
        if digest(manifest_path)!=row.get('fixture_sha256'):raise ValueError('Changed persistence fixture pin')
        if set(row.get('files',{}))!=set(literal):raise ValueError('Changed native saved file inventory')
        for name,value in row['files'].items():
            if digest(witness/name)!=value:raise ValueError('Changed native saved project copy')
        from importlib.util import spec_from_file_location,module_from_spec
        spec=spec_from_file_location('frozen_project_canonical',source_root/'case-source/tests/behaviour/manual_save_project_canonical.py');helper=module_from_spec(spec);spec.loader.exec_module(helper)
        original=fixture_source(manifest['origins'][0]['path'])
        if digest(original)!=literal['Four notes.ptn']:raise ValueError('Changed pinned original project bytes')
        content=helper.prove(witness/'Four notes.ptn',original,fixture,source_root/'case-source/tests/behaviour/persisted_digest.lua')
        if row.get('content')!=content:raise ValueError('Changed complete decoded project proof')
        if not any(x.get('kind')=='selected-menu-label' and x.get('text')=='Four notes.ptn' for x in json.loads((Path(path)/'results.json').read_text())):
            raise ValueError('Named file lacked public picker witness')
        if any(s.get('held') or s.get('midi_capture',{}).get('outstanding') for s in states):
            raise ValueError('Save evidence leaves held controls or active notes')
