"""Saved-range rejection and recovery rendering contracts."""
import base64,shutil,subprocess
from pathlib import Path
from driver import Driver,digest
from frame_oracle import render
from persisted_ranges import serializer_source

def rejected_saved_range(c):
    c.ui.configure();c.elapse(59);c.elapse(2)
    c.wait(lambda _:all((c.data_directory/name).is_file() for name in ['autosave.ptn','autosave.pset']))
    c.finish()
    original={name:digest(c.data_directory/name) for name in ['autosave.ptn','autosave.pset']}
    seed=c.out/'bad-range-seed';shutil.copytree(c.data_directory,seed)
    script=c.out/'bad-range.lua'
    script.write_text("local root,path=table.unpack(arg);local tab=dofile(root..'/lua/lib/tabutil.lua');local saved=assert(tab.load(path));local channel=saved[2].song_patterns[1].channels[1];channel.start_trig={4,4};channel.end_trig={2,4};assert(tab.save(saved,path)==nil)")
    source=serializer_source(c)
    subprocess.run(['lua5.3',str(script),source,str(seed/'autosave.ptn')],check=True)
    rejected={name:digest(seed/name) for name in original}
    # The rejection message is shown at boot. Skip the zero-lead menu setup, which
    # would cover it; the loaded project already stores the lead set before saving.
    out=c.out/'rejected-load';out.mkdir();loaded=Driver(out,project_seed=seed,**dict(c.launch_options,midi_lead_time_ms=None))
    try:
        expected=render([(0,62,10,'Slot 1 ch 1 reversed')])
        def feedback(state):
            actual=base64.b64decode(state['frame']['pixels_base64'])
            return all(actual[(y*128+x)*4+k]==expected[(y*128+x)*4+k] for y in range(55,64) for x in range(128) for k in range(3))
        loaded.wait(feedback)
        for deadline in [1,2]:
            # Inputs must not release the autosave inhibition latch.
            loaded.ui.menu('channel_editor');loaded.elapse(59);loaded.elapse(2)
            actual={name:digest(loaded.data_directory/name) for name in rejected}
            assert actual==rejected,'Rejected autosave was overwritten after input/idle'
            loaded.results.append(dict(kind='rejected-load-file-preservation',deadline=deadline,sha256=actual,passed=True))
        marker=loaded.snapshot()['midi_count'];loaded.ui.play();loaded.elapse(.8);loaded.ui.stop()
        state=loaded.snapshot()
        assert not [m for m in state['midi'] if m['index']>marker and 144<=m['bytes'][0]<=159 and m['bytes'][2]>0]
        assert not state['midi_capture']['outstanding']
        assert {name:digest(seed/name) for name in rejected}==rejected
        assert {name:digest(c.data_directory/name) for name in original}==original
        loaded.results.append(dict(kind='malformed-range-cold-rejection',visible_reason='Slot 1 ch 1 reversed',no_invalid_playback=True,source_preserved=True,passed=True))
    finally:loaded.finish()
    c.results.append(dict(kind='saved-range-native-rejection',nested=str(out),passed=True))


def select_project_action(c,offset,returning=False,activate=True):
    from cases import menu_label
    from frame_oracle import selected_line
    c.key(1)
    if not returning:
        c.enc(1,4);c.key(3);menu_label(c,'LEVELS >')
        position=next(i for i,value in enumerate(c.snapshot()['diagnostics']['parameter_roots']) if value['id']=='mosaic')
        c.enc(2,position);c.key(3)
    # Norns retains the current parameter group when K1 closes the menu.
    c.enc(2,-60);c.enc(2,1)
    # The first selectable row is the project-management separator.
    # Move once to Save before checking its selected label.
    # The preceding project-management separator draws its rule at y22.
    # Keep the full selected label assertion, excluding only that rule.
    c.wait(lambda state:selected_line(state,'< Save project',top=23))
    c.results.append(dict(kind='selected-menu-label',text='< Save project'))
    if offset:
        c.enc(2,offset);menu_label(c,{1:'> Load project',2:'+ New'}[offset])
    if activate:c.key(3)

def select_project_file(c,name,returning=False):
    from frame_oracle import selected_line
    select_project_action(c,1,returning)
    c.action(type='enc',n=2,delta=-100)
    for _ in range(30):
        if selected_line(c.snapshot(),name):return
        c.action(type='enc',n=2,delta=1);c.elapse(.03)
    raise AssertionError('Project file not reached: '+name)

def rejected_manual_range(c,recovery="load"):
    from range_rejection import rejected_range_channel_isolation
    from cases import assert_durations
    rejected_range_channel_isolation(c)
    c.elapse(59);c.elapse(2)
    c.wait(lambda _:all((c.data_directory/n).is_file() for n in ['autosave.ptn','autosave.pset']))
    bad=c.data_directory/'broken.ptn';shutil.copyfile(c.data_directory/'autosave.ptn',bad)
    script=c.out/'bad-manual-range.lua'
    script.write_text("local root,path=table.unpack(arg);local tab=dofile(root..'/lua/lib/tabutil.lua');local saved=assert(tab.load(path));local channel=saved[2].song_patterns[1].channels[17];channel.start_trig={4,4};channel.end_trig={2,4};assert(tab.save(saved,path)==nil)")
    source=serializer_source(c)
    subprocess.run(['lua5.3',str(script),source,str(bad)],check=True)
    preserved={n:digest(c.data_directory/n) for n in ['autosave.ptn','autosave.pset','broken.ptn']}
    select_project_file(c,'broken.ptn')
    marker=c.snapshot()['midi_count'];c.tap(1,8)
    def emitted(state):return [m for m in state['midi'] if m['index']>marker and 144<=m['bytes'][0]<=159 and m['bytes'][2]>0]
    c.wait(lambda state:len(emitted(state))>=8)
    c.key(3);c.key(1)
    expected_frame=render([(0,62,10,'Slot 1 ch 17 reversed')])
    def feedback(state):
        actual=base64.b64decode(state['frame']['pixels_base64'])
        return all(actual[(y*128+x)*4+k]==expected_frame[(y*128+x)*4+k] for y in range(55,64) for x in range(128) for k in range(3))
    c.wait(feedback)
    state=c.wait(lambda state:all(sum(m['port']==port for m in emitted(state))>=17 for port in [1,2]),5)
    notes=emitted(state);c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    def verify(notes,first_phrase,completed):
        phrases={1:[[144,p,v] for p,v in first_phrase],2:[[145,79,40],[145,81,60],[145,79,40]]}
        assert all((m['port'],m['bytes'][0]) in [(1,144),(2,145)] for m in notes)
        for port,phrase in phrases.items():
            lane=[m for m in notes if m['port']==port]
            assert [m['bytes'] for m in lane]==[phrase[i%len(phrase)] for i in range(len(lane))]
            for i,note in enumerate(lane):assert abs((note[field]-lane[0][field])/1e9-i/6)<=tolerance
            assert_durations(c,lane,[1]*completed if port==1 else ([.5,1.25,.5]*4)[:completed])
    verify(notes,[(60,127),(62,117),(64,107),(65,97)],12)
    # Rejected manual load must retain a usable, editable current project.
    c.hold_tap((1,4),(3,4));marker=c.snapshot()['midi_count'];c.tap(1,8)
    state=c.wait(lambda state:all(sum(m['port']==port for m in emitted(state))>=10 for port in [1,2]),4)
    notes=emitted(state);c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])
    verify(notes,[(60,127),(62,117),(64,107)],6)
    c.elapse(59);c.elapse(2)
    assert {n:digest(c.data_directory/n) for n in preserved}==preserved
    # Each explicit recovery action must re-enable saving through native UI.
    if recovery=='new':
        select_project_action(c,2,returning=True);c.key(1)
        c.tap(3,8)
        marker=c.snapshot()['midi_count'];c.tap(1,8);c.elapse(.8);c.tap(1,8)
        state=c.snapshot();assert not emitted(state)
        assert not state['midi_capture']['outstanding']
        before=(c.data_directory/'autosave.ptn').stat().st_mtime_ns
        c.elapse(59);c.elapse(2)
        c.wait(lambda _:(c.data_directory/'autosave.ptn').stat().st_mtime_ns>before)
        assert digest(bad)==preserved['broken.ptn']
        c.results.append(dict(kind='manual-range-rejection-recovery',action='new',empty_playback=True,autosave_resumed=True,passed=True))
        return
    if recovery=='save':
        select_project_action(c,0,returning=True)
        # Official textentry enters with default name 'new' and OK selected.
        expected=render([(0,32,15,'new')])
        def name_visible(state):
            actual=base64.b64decode(state['frame']['pixels_base64'])
            return all(actual[(y*128+x)*4+k]==expected[(y*128+x)*4+k] for y in range(24,34) for x in range(70) for k in range(3))
        c.wait(name_visible);c.key(3);c.key(1)
        c.wait(lambda _:all((c.data_directory/n).is_file() for n in ['new.ptn','new.pset']))
        before=(c.data_directory/'autosave.ptn').stat().st_mtime_ns
        c.elapse(59);c.elapse(2)
        c.wait(lambda _:(c.data_directory/'autosave.ptn').stat().st_mtime_ns>before)
        c.results.append(dict(kind='named-save-resumes-autosave-before-load',passed=True))
        # Reload the named file to prove that both actual serializers worked.
        select_project_file(c,'new.ptn',returning=True);c.key(3);c.key(1)
        expected_phrase=[(60,127),(62,117),(64,107)]
        c.led_values([(1,4),(2,4),(3,4),(4,4)],[15,15,15,0])
    else:
        assert recovery=='load'
        select_project_file(c,'autosave.ptn',returning=True);c.key(3);c.key(1)
        expected_phrase=[(60,127),(62,117),(64,107),(65,97)]
        c.led_values([(1,4),(2,4),(3,4),(4,4)],[15,15,15,15])
    marker=c.snapshot()['midi_count'];c.tap(1,8)
    state=c.wait(lambda state:all(sum(m['port']==port for m in emitted(state))>=10 for port in [1,2]),4)
    notes=emitted(state);c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])
    verify(notes,expected_phrase,6)
    before=(c.data_directory/'autosave.ptn').stat().st_mtime_ns
    c.elapse(59);c.elapse(2)
    c.wait(lambda _:(c.data_directory/'autosave.ptn').stat().st_mtime_ns>before)
    assert digest(bad)==preserved['broken.ptn']
    c.results.append(dict(kind='manual-range-rejection-playing',routes=2,edited_after_rejection=True,files_preserved=True,recovery_action=recovery,autosave_reenabled=True,passed=True))
