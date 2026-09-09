"""Project-dialog lifecycle through native controls and two MIDI routes."""
from persisted_ranges import select_project_action
from range_rejection import rejected_range_channel_isolation

def project_dialog_while_playing(c,action):
    from cases import assert_durations
    rejected_range_channel_isolation(c)
    # Place the UI before the decisive gesture without replacing project state.
    select_project_action(c,{'new':2,'accept-save':0,'cancel-save':0,'cancel-load':1}[action],activate=action!='new')
    marker=c.snapshot()['midi_count'];c.tap(1,8)
    def emitted(state):return [m for m in state['midi'] if m['index']>marker and 144<=m['bytes'][0]<=159 and m['bytes'][2]>0]
    state=c.wait(lambda state:all(sum(m['port']==port for m in emitted(state))>=3 for port in [1,2]),3)
    assert state['midi_capture']['outstanding'],'Fixture must exercise active notes'
    before=c.snapshot()['midi_count']
    c.key(3 if action in ('new','accept-save') else 2)
    c.key(1)
    if action in ('new','accept-save'):
        # New clears the phrase. Existing voices must still receive their
        # original-route releases; no delayed chord voices exist in this setup.
        c.elapse(.6)
        state=c.snapshot()
        assert not [m for m in emitted(state) if m['index']>before],action+' continued the old phrase'
        assert not state['midi_capture']['outstanding'],action+' stranded an old-project note'
        if action=='accept-save':
            assert all((c.data_directory/name).is_file() for name in ['new.ptn','new.pset'])
        c.results.append(dict(kind='project-action-pending-releases',action=action,routes=2,no_old_phrase=True,no_outstanding=True,passed=True))
        return
    state=c.wait(lambda state:all(sum(m['port']==port for m in emitted(state))>=17 for port in [1,2]),4)
    notes=emitted(state);c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])
    phrases={1:[[144,60,127],[144,62,117],[144,64,107],[144,65,97]],2:[[145,79,40],[145,81,60],[145,79,40]]}
    assert all((m['port'],m['bytes'][0]) in [(1,144),(2,145)] for m in notes)
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    for port,phrase in phrases.items():
        lane=[m for m in notes if m['port']==port]
        assert [m['bytes'] for m in lane]==[phrase[i%len(phrase)] for i in range(len(lane))]
        for i,note in enumerate(lane):assert abs((note[field]-lane[0][field])/1e9-i/6)<=tolerance
        assert_durations(c,lane,[1]*12 if port==1 else [.5,1.25,.5]*4)
    c.results.append(dict(kind='cancel-project-dialog-playing',action=action,routes=2,phase_and_gates_preserved=True,passed=True))
