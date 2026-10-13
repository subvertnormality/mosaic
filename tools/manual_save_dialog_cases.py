"""Isolated supplementary save procedure from a retained, source-pinned project.

No shared course/case driver changes. Only native public controls after a
declared disposable-file fixture. Does not replace the continuous course.
"""
from pathlib import Path
import hashlib,json
from manual_save_dialog_oracle import assert_frame,matches,NAME

ROOT=Path(__file__).resolve().parents[1]
CASE='M-MANUAL-SAVE-DIALOG-001'
FIXTURE=ROOT/'tests/behaviour/config/manual-save-dialog'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def fixture_origin_path(origin):
    relative=Path(origin["path"])
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise ValueError("Save Dialog origin must stay within its pinned fixture")
    path=FIXTURE/relative
    if path.is_symlink() or not path.is_file():
        raise ValueError("Save Dialog origin is missing from its pinned fixture")
    return path

def save_dialog(c):
    manifest=json.loads((FIXTURE/'DERIVATION.json').read_text())
    witness=c.out/'save-dialog-evidence';witness.mkdir()
    for suffix in ('.ptn','.pset'):
        source=FIXTURE/('Course seed'+suffix);target=c.data_directory/source.name
        assert sha(source)==manifest['derived_files'][source.name]
        target.write_bytes(source.read_bytes())
        (witness/source.name).write_bytes(source.read_bytes())
    (witness/'DERIVATION.json').write_bytes((FIXTURE/'DERIVATION.json').read_bytes())
    c.ui.select_project_file('Course seed.ptn');c.ui.press_key(3);c.ui.press_key(1)
    # Loading currently leaves an incompatible Song/C01 router presentation.
    # G04 is the documented public Song grid control and replaces both fields.
    # This explicit starting navigation does not claim to fix that app defect.
    from frame_oracle import live_header_matches,selected_line
    c.ui.song_editor()
    c.wait(lambda s:live_header_matches(s,'SONG PLAYBACK','SONG 01','dashboard'))
    c.enc(1,1)
    c.wait(lambda s:live_header_matches(s,'SONG TASKS','SONG 01','detail'))
    from ui_map import TASK_ROWS
    c.enc(2,-len(TASK_ROWS['Song']));c.enc(2,TASK_ROWS['Song'].index('slot_setup'))
    c.ui.expect_selected_field(layout='detail',label='Slot setup')
    c.ui.press_key(3)
    c.wait(lambda s:live_header_matches(s,'SLOT SETUP','SONG 01','vertical_list'))
    assert not c.snapshot()['held']
    originals={p.name:sha(p) for p in c.data_directory.iterdir() if p.is_file()}
    assert not any((c.data_directory/(NAME+s)).exists() for s in ('.ptn','.pset'))
    # Cancellation has its own checkpoint and must preserve seeded project files.
    c.ui.select_project_action('save',returning=True)
    c.wait(lambda s:matches(s,'entry'));c.ui.press_key(2)
    c.wait(lambda s:selected_line(s,'< Save project',top=23))
    assert {p.name:sha(p) for p in c.data_directory.iterdir() if p.is_file()}==originals
    receipt=dict(stage='cancel',files=originals,named_files_absent=True,
        fixture_sha256=sha(FIXTURE/'DERIVATION.json'))
    (witness/'cancel.json').write_text(json.dumps(receipt,sort_keys=True)+'\n')
    c.results.append(dict(kind='manual-save-dialog-cancel',stage='cancel',receipt_sha256=sha(witness/'cancel.json'),
        fixture_sha256=receipt['fixture_sha256'],citation='manual:save-and-load',passed=True))
    c.ui.press_key(3);assert_frame(c,'entry')
    c.ui.turn(2,-1);assert_frame(c,'delete')
    for _ in range(3):c.ui.press_key(3)
    assert_frame(c,'empty');c.ui.turn(3,-1);position=28
    for index,character in enumerate(NAME):
        target=(ord(character)-37)%95;delta=(target-position)%95
        if delta>47:delta-=95
        if delta:c.ui.turn(2,delta)
        c.ui.press_key(3);position=target
        if index==0:assert_frame(c,'first-character')
    assert_frame(c,'name-entered')
    c.ui.turn(3,1);c.ui.turn(2,1);assert_frame(c,'confirm')
    c.ui.press_key(3);c.ui.press_key(1)
    state=c.wait(lambda s:live_header_matches(s,'SLOT SETUP','SONG 01','vertical_list'))
    c.results.append(dict(kind='manual-save-dialog-return',stage='returned',header=dict(title='SLOT SETUP',scope='SONG 01',layout='vertical_list'),citation='manual:save-and-load',passed=True))
    saved={NAME+s:sha(c.data_directory/(NAME+s)) for s in ('.ptn','.pset')}
    # tab.save iteration order varies; all decoded fields/types must be equal.
    # Original and observed byte hashes remain distinct, and pset stays exact.
    from manual_save_project_canonical import prove
    origin=manifest['origins'][0]
    original=fixture_origin_path(origin)
    assert sha(original)==origin['sha256']==manifest['original_files'][origin['original_name']]
    assert saved['Four notes.pset']==manifest['original_files']['Four notes.pset']
    content=prove(c.data_directory/(NAME+'.ptn'),original,FIXTURE,ROOT/'tests/behaviour/persisted_digest.lua')
    for filename in saved:(witness/filename).write_bytes((c.data_directory/filename).read_bytes())
    c.ui.select_project_file('Four notes.ptn',returning=True)
    c.ui.expect_menu_label('Four notes.ptn')
    c.ui.press_key(2);c.ui.press_key(1)
    c.wait(lambda s:live_header_matches(s,'SLOT SETUP','SONG 01','vertical_list'))
    state=c.snapshot()
    assert not state['held']
    assert not state['midi_capture']['outstanding']
    c.results.append(dict(kind='manual-save-dialog-persistence',stage='saved',name=NAME,files=saved,original_files=manifest['original_files'],content=content,
        fixture_sha256=sha(FIXTURE/'DERIVATION.json'),picker_confirmed=True,held_controls=[],
        outstanding_notes=False,citation='manual:save-and-load',passed=True))

CASES={CASE:dict(run=save_dialog,requirements=['SAVE-NAMED'],description='Supplementary same-arrangement native DEL, character selection, OK confirmation, cancellation and named persistence')}
