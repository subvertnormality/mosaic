"""Mosaic-owned physical-input regressions; independent literal musical oracles."""
from driver import REPO,Driver,digest

def four_notes(c):
    c.configure()
    c.playback([(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107),(65,97)]])
    c.tap(5,8);c.tap(5,8);c.tap(4,3)
    c.led_values([(4,3)],[12])
    c.playback([(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107),(67,97)]])

def next_trig_cutoff(c):
    c.configure();c.hold_tap((1,4),(8,4));c.tap(5,8)
    for x in (2,3,4):c.tap(x,4)
    c.tap(5,4);c.tap(5,8);c.tap(5,3);c.tap(3,8);c.tap(5,8)
    c.hold_tap((1,4),(4,4));c.tap(3,4)
    c.led_values([(x,4) for x in range(1,6)],[15,5,15,2,15])
    notes=c.playback([(1,[144,n,v]) for n,v in [(60,127),(64,107),(67,100)]],timeout=6)
    assert_durations(c,notes,[2,1,1]*2)

def assert_durations(c,notes,lengths):
    assert lengths and len(notes)>=len(lengths),'Missing duration observations'
    state=c.snapshot();rows=[]
    for note,length in zip(notes,lengths):
        off=next(m for m in state['midi'] if m['index']>note['index'] and m['port']==1 and m['bytes']==[128,note['bytes'][1],note['bytes'][2]])
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        actual=(off[field]-note[field])/1e9
        rows.append(dict(pitch=note['bytes'][1],expected_seconds=length/6,actual_seconds=actual,error_ms=1000*(actual-length/6)))
    c.results.append(dict(kind='duration',rows=rows))
    # Two nanoseconds cover native integer deadline rounding; no wall jitter in D.
    tolerance_ms=.000002 if c.clock_mode=='controlled-experimental' else 10
    assert all(abs(row['error_ms'])<=tolerance_ms for row in rows),rows

def restore_length(c):
    # The source length must survive temporary interruption by an inserted trig.
    next_trig_cutoff(c)
    c.tap(3,4)
    c.led_values([(x,4) for x in range(1,6)],[15,5,5,5,15])
    notes=c.playback([(1,[144,60,127]),(1,[144,67,100])],timeout=6)
    assert_durations(c,notes,[4,1]*2)
    # Reinsert the collision: the same authored length must shorten again.
    c.tap(3,4)
    c.led_values([(x,4) for x in range(1,6)],[15,5,15,2,15])
    notes=c.playback([(1,[144,60,127]),(1,[144,64,107]),(1,[144,67,100])],timeout=6)
    assert_durations(c,notes,[2,1,1]*2)

def wrapped_length(c,same_pitch=False):
    c.configure();c.hold_tap((1,4),(16,7));c.tap(5,8)
    for x in (2,3,4):c.tap(x,4)
    c.tap(15,7);c.hold_tap((15,7),(2,4))
    c.led_values([(15,7),(16,7),(1,4),(2,4)],[15,5,15,2])
    if not same_pitch:
        c.tap(5,8);c.tap(12,8);c.tap(15,3)
        c.led_values([(15,3)],[12])
    notes=c.playback([(1,[144,60,127]),(1,[144,60 if same_pitch else 67,100])],timeout=38)
    assert_durations(c,notes,[1,2]*2)


def pattern_duration_domain(c,lengths=range(1,65),channel_end=64):
    # The documented finite duration domain is1..64 sixteenth-note steps.
    # Author each duration using grid gestures; observe every cell and MIDI off.
    c.configure();c.hold_tap((1,4),((channel_end-1)%16+1,(channel_end-1)//16+4));c.tap(5,8)
    for x in (2,3,4):c.tap(x,4)
    cells=[((step-1)%16+1,(step-1)//16+4) for step in range(1,65)]
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    for length in lengths:
        if length>1:c.hold_tap(cells[0],cells[length-1])
        c.led_values(cells,[15 if step==1 else 5 if step<=length else 2 for step in range(1,65)])
        marker=c.snapshot()['midi_count'];c.tap(1,8)
        def recorded(state):return [m for m in state['midi'] if m['index']>marker and m['port']==1 and m['bytes'][0] in (128,144)]
        # Native capture retains all events; fewer snapshots cannot hide an
        # early release because the emission-time and order assertions follow.
        c.elapse(max(0,length/6-.12))
        state=c.wait(lambda state:any(m['bytes']==[128,60,127] for m in recorded(state)),timeout=13)
        emitted=recorded(state)
        assert emitted[0]['bytes']==[144,60,127],emitted
        release=next(m for m in emitted if m['bytes'][0]==128)
        assert release['bytes']==[128,60,127]
        elapsed=(release[field]-emitted[0][field])/1e9
        assert abs(elapsed-length/6)<=tolerance,dict(length=length,actual=elapsed,expected=length/6)
        # At the full64-step boundary another onset may follow the completed
        # note before Stop arrives. Its ordering and cleanup are still required.
        assert [m['bytes'] for m in emitted[:2]]==[[144,60,127],[128,60,127]],emitted
        assert all(m['bytes'] in ([144,60,127],[128,60,127]) for m in emitted)
        c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])
        c.results.append(dict(kind='pattern-duration-domain',steps=length,expected_seconds=length/6,actual_seconds=elapsed,first_on=emitted[0],first_off=release))


def pattern_duration_controls(c):
    c.configure();c.hold_tap((1,4),(8,4));c.tap(5,8)
    for x in (2,3,4):c.tap(x,4)
    c.tap(5,4);c.tap(5,8);c.tap(5,3);c.tap(3,8);c.tap(5,8)
    cells=[((step-1)%16+1,(step-1)//16+4) for step in range(1,65)]
    def phrase(length):
        c.led_values(cells,[15 if step in (1,5) else 5 if 1<step<=length else 2 for step in range(1,65)])
        notes=c.playback([(1,[144,60,127]),(1,[144,67,100])],cycles=2)
        assert_durations(c,notes,[length,1]*2)
    def long_hold(cell):
        c.action(type='grid',x=cell[0],y=cell[1],state=1)
        try:c.elapse(1.1)
        finally:c.action(type='grid',x=cell[0],y=cell[1],state=0)
        c.elapse(.06)
    phrase(1);c.hold_tap((1,4),(3,4));phrase(3)
    long_hold((1,4));phrase(1)
    # Empty sources must neither create a trigger nor leave hidden length data
    # that changes the existing phrase. Test both the combo and lone hold.
    c.hold_tap((2,4),(4,4));phrase(1)
    long_hold((2,4));phrase(1)
    c.hold_tap((1,4),(4,4));phrase(4)

def live_pattern_duration(c):
    c.configure();c.hold_tap((1,4),(8,4));c.tap(5,8)
    for x in (2,3,4):c.tap(x,4)
    c.hold_tap((1,4),(4,4))
    marker=c.snapshot()['midi_count'];c.tap(1,8)
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    def onsets(state):return [m for m in state['midi'] if m['index']>marker and m['port']==1 and m['bytes']==[144,60,127]]
    state=c.wait(lambda state:len(onsets(state))>=1)
    first=onsets(state)[0]
    c.hold_tap((1,4),(2,4))
    now=c.logical_ns if c.clock_mode=='controlled-experimental' else c.snapshot()['diagnostics']['monotonic_ns']
    assert now<first[field]+round(2e9/6),'Shortening gesture missed the pending note window'
    state=c.wait(lambda state:len(onsets(state))>=2)
    second=onsets(state)[1]
    c.hold_tap((1,4),(4,4))
    now=c.logical_ns if c.clock_mode=='controlled-experimental' else c.snapshot()['diagnostics']['monotonic_ns']
    assert now<second[field]+round(2e9/6),'Extension gesture missed the pending note window'
    state=c.wait(lambda state:len(onsets(state))>=3)
    third=onsets(state)[2]
    c.wait(lambda state:any(m['index']>third['index'] and m['bytes']==[128,60,127] for m in state['midi']))
    c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])
    state=c.snapshot()
    actual=[(m['port'],m['bytes']) for m in state['midi'] if m['index']>marker and 128<=m['bytes'][0]<=159]
    expected=[(1,[144,60,127]),(1,[128,60,127])]*3
    assert actual==expected,dict(expected=expected,actual=actual)
    c.results.append(dict(kind='live-duration-exact-midi',expected=expected,actual=actual))
    # Editing the stored duration affects later onsets. Each already-emitted
    # note retains its scheduled release; neither edit retroactively cuts it.
    assert_durations(c,[first,second,third],[4,2,4])
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    assert all(abs((b[field]-a[field])/1e9-8/6)<=tolerance for a,b in ((first,second),(second,third)))
    cells=[((step-1)%16+1,(step-1)//16+4) for step in range(1,65)]
    c.led_values(cells,[15 if step==1 else 5 if step<=4 else 2 for step in range(1,65)])
    notes=c.playback([(1,[144,60,127])],cycles=2)
    assert_durations(c,notes,[4,4])


def euclidean_workflow(c):
    # Migrated from emulator tests/mosaic_euclidean.py; independent3-in-8 table.
    baseline=[(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107),(65,97)]]
    c.configure();c.hold_tap((1,4),(8,4))
    c.tap(5,8);c.tap(5,8)
    for x,y in [(5,3),(6,2),(7,1),(8,6)]:c.tap(x,y)
    c.tap(3,8);c.tap(5,8) # trig editor
    c.playback(baseline);c.results.append(dict(kind='workflow-check',name='eight-step-loop-baseline',passed=True))
    c.tap(14,2) # Euclidean
    c.tap(2,2) # broad fader minimum: one pulse
    for _ in range(2):c.tap(10,2)
    c.tap(2,3)
    for _ in range(7):c.tap(10,3)
    c.tap(16,8)
    # The manual distinguishes dim overlaps and bright newly proposed steps.
    # Verify both blink phases and all64 cells against fixed authored/candidate
    # sets; no application rhythm calculation supplies the expected positions.
    cells=[((step-1)%16+1,(step-1)//16+4) for step in range(1,65)]
    original={1,2,3,4}
    proposed={step for step in range(1,65) if (step-1)%8+1 in (1,4,7)}
    for overlap,new in ((0,15),(3,12)):
        c.led_values(cells,[overlap if step in original and step in proposed else new if step in proposed else 15 if step in original else 2 for step in range(1,65)])
    c.playback(baseline);c.results.append(dict(kind='workflow-check',name='preview-does-not-paint',passed=True))
    c.tap(14,8);c.led_values([(x,4) for x in range(1,9)],[15]*4+[2]*4)
    c.playback(baseline);c.results.append(dict(kind='workflow-check',name='cancel-retains-pattern',passed=True))
    c.tap(16,8);c.tap(12,8) # shift right: {2,5,8}
    c.led_values([(2,4),(5,4),(8,4)],[0,15,15]);c.tap(16,8)
    shifted={step for step in range(1,65) if (step-1)%8+1 in (2,5,8)}
    painted=original.symmetric_difference(shifted)
    c.led_values(cells,[15 if step in painted else 2 for step in range(1,65)])
    c.playback([(1,[144,n,v]) for n,v in [(60,127),(64,107),(65,97),(67,100),(62,100)]])
    c.results.append(dict(kind='workflow-check',name='shifted-paint-xor',passed=True))
    c.tap(16,8);c.led_values([(2,4),(5,4),(8,4)],[15,0,0]);c.tap(16,8)
    c.playback(baseline);c.results.append(dict(kind='workflow-check',name='repaint-restores-original',passed=True))
    c.tap(16,8);c.tap(10,8) # left: back to {1,4,7}
    c.led_values([(1,4),(4,4),(7,4)],[0,0,15]);c.tap(12,8);c.tap(11,8)
    c.led_values([(1,4),(4,4),(7,4)],[0,0,15]);c.tap(16,8)
    c.playback([(1,[144,n,v]) for n,v in [(62,117),(64,107),(71,100)]])
    c.results.append(dict(kind='workflow-check',name='left-and-center-reset',passed=True))
    c.tap(16,8);c.led_values([(1,4),(4,4),(7,4)],[15,15,0]);c.tap(16,8);c.playback(baseline)
    c.tap(9,2) # fill32, exceeding length8: every step selected
    c.tap(16,8);c.led_values([(1,4),(4,4),(5,4),(16,7)],[0,0,15,15]);c.tap(16,8)
    c.led_values([(x,y) for y in range(4,8) for x in range(1,17)],[2]*4+[15]*60)
    c.playback([(1,[144,n,100]) for n in [67,69,71,62]]);c.results.append(dict(kind='workflow-check',name='dense-fill-boundary',passed=True))

def autosave_restart(c):
    c.configure()
    saved=c.data_directory/'autosave.ptn';pset=c.data_directory/'autosave.pset'
    assert not saved.exists() and not pset.exists(),'Fresh fixture unexpectedly contains autosave'
    c.elapse(59)
    assert not saved.exists(),'Autosave occurred before the documented60-second idle period'
    c.elapse(2)
    c.wait(lambda _:saved.is_file() and pset.is_file(),timeout=2)
    assert saved.stat().st_size>0 and pset.stat().st_size>0
    c.results.append(dict(kind='saved-project',files=[dict(name=p.name,sha256=digest(p)) for p in (saved,pset)]))
    c.finish()
    out=c.out/'reloaded';out.mkdir()
    loaded=Driver(out,project_seed=c.data_directory,**c.launch_options)
    try:
        # Read the restored pattern through the visible grid and complete MIDI
        # phrases. Do not re-create notes or inspect the serialized model.
        loaded.tap(3,8);loaded.tap(5,8)
        loaded.led_values([(x,4) for x in range(1,5)],[15,15,15,15])
        loaded.playback([(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107),(65,97)]])
    finally:loaded.finish()

def menu_label(c,text,x=0):
    from frame_oracle import selected_line
    c.wait(lambda s:selected_line(s,text,x));c.results.append(dict(kind='selected-menu-label',text=text))

def menu_value(c,text):
    from frame_oracle import selected_value
    c.wait(lambda s:selected_value(s,text));c.results.append(dict(kind='selected-menu-value',text=text))

def route_fixed_note(c,source_position,source_name):
    assert c.profile=='midi-modulation','This case requires actual matrix/toolkit mods'
    c.configure()
    c.key(1);c.enc(2,1);c.key(3);menu_label(c,'DEVICES > ')
    c.enc(2,2);menu_label(c,'MODS >');c.key(3);menu_label(c,'MATRIX >',4)
    c.key(3);menu_label(c,'LEVELS >')
    roots=c.snapshot()['diagnostics']['parameter_roots']
    position=next(i for i,v in enumerate(roots) if v['id']=='midi_device_params_group_channel_1')
    c.enc(2,position);c.key(3);menu_label(c,'Fixed Note')
    c.key(3);menu_label(c,'rhythm 1')
    c.enc(2,source_position);menu_label(c,source_name)
    c.enc(3,100);menu_value(c,'1.00')

def toolkit_parameter_group(c,name):
    c.enc(1,4);c.key(3);menu_label(c,'LEVELS >')
    roots=c.snapshot()['diagnostics']['parameter_roots']
    position=next(i for i,v in enumerate(roots) if v['name']==name)
    c.enc(2,position);c.key(3)

def macro_route_clear(c):
    route_fixed_note(c,12,'macro 1')
    toolkit_parameter_group(c,'macro 1');menu_label(c,'active')
    c.enc(2,1);menu_label(c,'value');c.enc(3,100);c.key(1)
    c.playback([(1,[144,127,v]) for v in (127,117,107,97)])
    # Return to the retained Matrix source selection, then zero its depth.
    c.key(1);c.enc(1,-4);c.key(3);c.key(3);c.key(3)
    menu_label(c,'macro 1');c.key(3);menu_value(c,'-');c.key(1)
    c.playback([(1,[144,n,v]) for n,v in ((60,127),(62,117),(64,107),(65,97))])

def held_macro_rebind(c):
    macro_route_clear(c)
    # The macro still holds1. Rebinding must apply it without touching the
    # source or waiting for another source event.
    c.key(1);menu_label(c,'macro 1');c.enc(3,100);menu_value(c,'1.00');c.key(1)
    c.playback([(1,[144,127,v]) for v in (127,117,107,97)])

def pulse_lfo(c):
    route_fixed_note(c,4,'lfo 1')
    toolkit_parameter_group(c,'lfo 1');menu_label(c,'clocked');c.key(3)
    c.enc(2,1);menu_label(c,'beats');c.enc(3,9)
    c.enc(2,2);menu_label(c,'shape');c.enc(3,2);c.key(1)
    # A4-beat pulse with50% width is high for8 sixteenth notes and low for8.
    # Place playback safely inside the high half using a verified native clock
    # read (not Mosaic state); E/R jitter and the24PPQN mod sample cannot cross
    # a half-cycle boundary at this1/8-beat offset.
    import math
    state=c.snapshot();beat=state['diagnostics']['beats']
    target=4*(math.floor(beat/4)+1)+.125
    c.elapse((target-beat)*2/3)
    expected=[]
    notes=[(60,127),(62,117),(64,107),(65,97)]
    for i in range(16):
        note,velocity=notes[i%4];expected.append((1,[144,127 if i<8 else note,velocity]))
    emitted=c.playback(expected,cycles=2,timeout=8)
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    # Opening-pulse phase is separately exposed by M-LEN-001. Here check every
    # subsequent onset plus the full LFO period against90BPM, not merely ratios.
    anchor=emitted[1][field];rows=[]
    for i,event in enumerate(emitted[1:]):
        actual=(event[field]-anchor)/1e9;expected_seconds=i/6
        rows.append(dict(index=i+1,expected_seconds=expected_seconds,actual_seconds=actual))
    c.results.append(dict(kind='steady-lfo-timing',rows=rows,opening_phase_case='M-LEN-001'))
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    assert all(abs(row['actual_seconds']-row['expected_seconds'])<=tolerance for row in rows),rows

def phrase_timing(c):
    # Establish the edited 8-step phrase through the existing grid recipe, then
    # restart and measure every complete phrase against the fixed 90BPM oracle.
    next_trig_cutoff(c)
    notes=c.playback([(1,[144,n,v]) for n,v in [(60,127),(64,107),(67,100)]],cycles=20,timeout=32)
    assert_durations(c,notes,[2,1,1]*20)
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    anchor=notes[0][field];rows=[]
    for i,note in enumerate(notes[:61]):
        expected=(8*(i//3)+(0,2,4)[i%3])/6
        actual=(note[field]-anchor)/1e9
        rows.append(dict(index=i,expected_seconds=expected,actual_seconds=actual))
    c.results.append(dict(kind='twenty-phrase-onsets',rows=rows))
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    assert len(rows)==61 and all(abs(r['actual_seconds']-r['expected_seconds'])<=tolerance for r in rows),rows

def restart_phase_edges(c):
    import math
    next_trig_cutoff(c)
    for offset_ns in (-100,-1,0,1,100):
        beat=c.snapshot()['diagnostics']['beats']
        boundary=(math.ceil(beat*96)+96)/96
        c.elapse((boundary-beat)*2/3+offset_ns/1e9)
        observed=c.snapshot()['diagnostics']['beats']
        error_ns=(observed-boundary)*2/3*1e9
        c.results.append(dict(kind='restart-phase',requested_offset_ns=offset_ns,observed_offset_ns=error_ns,exact_phase=c.clock_mode=='controlled-experimental'))
        if c.clock_mode=='controlled-experimental':
            assert abs(error_ns-offset_ns)<=2,(offset_ns,error_ns)
        notes=c.playback([(1,[144,n,v]) for n,v in [(60,127),(64,107),(67,100)]],cycles=2,timeout=4)
        assert_durations(c,notes,[2,1,1]*2)

def midi_clock_transport(c):
    import time
    c.configure()
    c.key(1);c.enc(1,4);c.key(3);menu_label(c,'LEVELS >')
    roots=c.snapshot()['diagnostics']['parameter_roots']
    position=next(i for i,v in enumerate(roots) if v['name']=='CLOCK')
    c.enc(2,position);c.key(3);menu_label(c,'source')
    menu_value(c,'internal');c.enc(3,1);menu_value(c,'midi')
    def inject(value,at=None):
        action=dict(type='midi',port=1,bytes=[value])
        if at is not None:action['at_monotonic_ns']=at
        c.action(**action)
    def pulses(count):
        start=time.monotonic_ns()
        for i in range(count):
            if c.clock_mode=='controlled-experimental':c.elapse(.025);inject(248)
            else:inject(248,start+(i+1)*25000000)
    # Replace the native estimator startup window with49 evenly spaced pulses.
    before=c.snapshot()['midi_count']
    first_play_pulse=None
    if c.clock_mode=='controlled-experimental':
        pulses(49)
        def new_notes():return [m for m in c.snapshot()['midi'] if m['index']>before and m['bytes'][0]==144 and m['bytes'][2]>0]
        assert not new_notes(),'Clock pulses alone started playback'
        inject(250);c.elapse(0)
        assert not new_notes(),'Transport started before the next MIDI clock pulse'
        pulses(60);inject(252)
    else:
        # One native queue avoids requiring every client roundtrip to finish
        # inside the25ms MIDI clock interval. Keep pulse spacing at100BPM.
        origin=time.monotonic_ns()+500000000
        packets=[(i*25000000,248) for i in range(1,50)]
        packets += [(1240000000,250)]
        packets += [(1250000000+i*25000000,248) for i in range(60)]
        packets += [(2735000000,252)]
        events=[dict(port=1,bytes=[value],at_monotonic_ns=origin+offset) for offset,value in packets]
        c.action(type='midi_schedule',schedule_id=1,events=events)
        state=c.wait(lambda state:len(state['midi_input_schedule']['delivered'])==len(events),timeout=5)
        delivered=state['midi_input_schedule']['delivered']
        first_play_pulse=delivered[50]['actual_monotonic_ns']
        c.results.append(dict(kind='native-midi-clock-stimulus',events=events,delivered=delivered))
    c.wait(lambda s:not s['midi_capture']['outstanding'])
    state=c.snapshot();notes=[m for m in state['midi'] if m['index']>before and m['bytes'][0]==144 and m['bytes'][2]>0]
    if first_play_pulse is not None:
        assert not [m for m in notes if m['monotonic_ns']<first_play_pulse],'Warmup/transport emitted notes before the first playback pulse'
    expected=[(60,127),(62,117),(64,107),(65,97)]
    assert len(notes)>=9,notes
    assert [(m['port'],m['bytes']) for m in notes]==[(1,[144,*expected[i%4]]) for i in range(len(notes))],notes
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    rows=[]
    for i,note in enumerate(notes[:9]):
        rows.append(dict(index=i,expected_seconds=i*.15,actual_seconds=(note[field]-notes[0][field])/1e9))
    c.results.append(dict(kind='midi-clock-onsets',rows=rows))
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    assert all(abs(r['actual_seconds']-r['expected_seconds'])<=tolerance for r in rows),rows
    durations=[]
    for note in notes[:8]:
        off=next(m for m in state['midi'] if m['index']>note['index'] and m['bytes']==[128,note['bytes'][1],note['bytes'][2]])
        durations.append((off[field]-note[field])/1e9)
    c.results.append(dict(kind='midi-clock-durations',expected_seconds=.15,actual_seconds=durations))
    assert all(abs(d-.15)<=tolerance for d in durations),durations
    c.enc(3,-1);menu_value(c,'internal')
    # Native clock.lua updates clock_tempo from the external source; returning
    # to internal uses that adopted tempo. Explicitly edit it back to90BPM.
    c.enc(2,1);menu_label(c,'tempo');menu_value(c,'100')
    c.enc(3,-10);menu_value(c,'90');c.key(1)
    internal=c.playback([(1,[144,n,v]) for n,v in expected])
    restored=[(m[field]-internal[0][field])/1e9 for m in internal[:9]]
    c.results.append(dict(kind='restored-internal-onsets',actual_seconds=restored))
    assert len(restored)==9 and all(abs(t-i/6)<=tolerance for i,t in enumerate(restored)),restored

def live_clock_handoff(c):
    import math,time
    next_trig_cutoff(c)
    c.key(1);c.enc(1,4);c.key(3);menu_label(c,'LEVELS >')
    position=next(i for i,v in enumerate(c.snapshot()['diagnostics']['parameter_roots']) if v['name']=='CLOCK')
    c.enc(2,position);c.key(3);menu_label(c,'source');menu_value(c,'internal')
    pulse_cursor=0
    controlled=c.clock_mode=='controlled-experimental'
    domain='logical' if controlled else 'monotonic'
    origin=c.logical_ns if controlled else time.monotonic_ns()+500000000
    events=[dict(port=1,bytes=[248],**{'at_'+domain+'_ns':origin+(i+1)*25000000}) for i in range(83)]
    events.append(dict(port=1,bytes=[252],**{'at_'+domain+'_ns':origin+84*25000000}))
    request=dict(type='midi_schedule',schedule_id=1,events=events)
    if controlled:request['time_domain']='logical'
    c.action(**request)
    def pulses(count):
        nonlocal pulse_cursor
        pulse_cursor+=count
        if controlled:
            delta=origin+pulse_cursor*25000000-c.logical_ns
            assert delta>=0,'Control work crossed the requested observation deadline'
            c.elapse(delta/1e9)
            assert len(c.snapshot()['midi_input_schedule']['delivered'])>=pulse_cursor
        else:c.wait(lambda s:len(s['midi_input_schedule']['delivered'])>=pulse_cursor)
    pulses(49)
    before=c.snapshot();start_beat=before['diagnostics']['beats'];marker=before['midi_count']
    c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
    pulses(4)
    pending=c.snapshot()
    assert pending['midi_capture']['outstanding'],'No pending note at source switch'
    elapsed_ticks=math.floor((pending['diagnostics']['beats']-start_beat)*96)
    assert 0<elapsed_ticks<48,elapsed_ticks
    switch_ack=c.action(type='enc',n=3,delta=2)
    handoff=c.snapshot();beat=handoff['diagnostics']['beats']
    if not controlled:
        # A pre-input snapshot can precede the audible onset by tens of ms.
        # Anchor to emitted MIDI and the runtime's applied control timestamp,
        # not HTTP receipt or a stale pre-grid observation.
        onset=next(m for m in pending['midi'] if m['index']>marker and m['bytes']==[144,60,127])
        applied=switch_ack['native']['monotonic_ns']
        start_beat=before['diagnostics']['beats']+(onset['monotonic_ns']-before['diagnostics']['monotonic_ns'])*1.5e-9
        elapsed_ticks=math.floor((applied-onset['monotonic_ns'])*144e-9)
        beat-=(handoff['diagnostics']['monotonic_ns']-applied)*(100/60)*1e-9
        assert 0<elapsed_ticks<48,elapsed_ticks
    quantum=1/96;phase=start_beat%quantum;epsilon=2**-23
    next_beat=math.ceil((beat+epsilon)/quantum)*quantum+phase-quantum
    while next_beat<beat+epsilon:next_beat+=quantum
    # One two-step note is48 ticks. Only its pending next wait is rephased;
    # remaining ticks proceed at100BPM (0.6 seconds per quarter note).
    remaining_seconds=(next_beat-beat)*.6+(48-elapsed_ticks-1)*.6/96
    origin_ns=c.logical_ns if controlled else applied
    expected_off_ns=origin_ns+remaining_seconds*1e9
    pulses(30);pulses(1)
    arrivals=c.snapshot()['midi_input_schedule']['delivered']
    errors=[e['actual_'+domain+'_ns']-e['intended_'+domain+'_ns'] for e in arrivals]
    c.results.append(dict(kind='continuous-midi-arrival-errors',time_domain=domain,errors_ns=errors))
    assert len(arrivals)==84 and all(0<=e<=(0 if controlled else 10000000) for e in errors),errors
    c.wait(lambda s:not s['midi_capture']['outstanding']);state=c.snapshot()
    notes=[m for m in state['midi'] if m['index']>marker and m['bytes'][0]==144 and m['bytes'][2]>0]
    assert [(m['port'],m['bytes']) for m in notes]==[(1,[144,60,127]),(1,[144,64,107]),(1,[144,67,100])],notes
    off=next(m for m in state['midi'] if m['index']>notes[0]['index'] and m['bytes']==[128,60,127])
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    error_ns=off[field]-expected_off_ns
    c.results.append(dict(kind='pending-note-source-handoff',elapsed_ticks=elapsed_ticks,expected_off_ns=expected_off_ns,actual_off_ns=off[field],error_ns=error_ns))
    assert abs(error_ns)<=(2 if c.clock_mode=='controlled-experimental' else 10000000),c.results[-1]
    menu_value(c,'midi')
    reverse_live_clock_handoff(c)

def reverse_live_clock_handoff(c):
    import math,time
    # Establish100BPM on the internal reference while stopped, then return to
    # MIDI. This isolates phase/source transfer from internal24PPQN tempo
    # publication latency; pending tempo changes remain a separate edge case.
    c.enc(3,-1);menu_value(c,'internal');c.elapse(.1)
    c.enc(3,1);menu_value(c,'midi')
    controlled=c.clock_mode=='controlled-experimental'
    domain='logical' if controlled else 'monotonic'
    origin=c.logical_ns if controlled else time.monotonic_ns()+500000000
    events=[dict(port=1,bytes=[248],**{'at_'+domain+'_ns':origin+(i+1)*25000000}) for i in range(83)]
    events.append(dict(port=1,bytes=[252],**{'at_'+domain+'_ns':origin+84*25000000}))
    request=dict(type='midi_schedule',schedule_id=2,events=events)
    if controlled:request['time_domain']='logical'
    c.action(**request)
    def until(pulse):
        if controlled:
            delta=origin+pulse*25000000-c.logical_ns
            assert delta>=0
            c.elapse(delta/1e9)
        else:c.wait(lambda s:len(s['midi_input_schedule']['delivered'])>=pulse)
    until(49)
    before=c.snapshot();start_beat=before['diagnostics']['beats'];marker=before['midi_count']
    c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
    until(53);c.elapse(.001)  # Avoid observing exactly on a strict sync boundary.
    pending=c.snapshot();assert pending['midi_capture']['outstanding']
    elapsed_ticks=math.floor((pending['diagnostics']['beats']-start_beat)*96)
    assert 0<elapsed_ticks<48,elapsed_ticks
    switch_ack=c.action(type='enc',n=3,delta=-2)
    handoff=c.snapshot();beat=handoff['diagnostics']['beats']
    if not controlled:
        onset=next(m for m in pending['midi'] if m['index']>marker and m['bytes']==[144,60,127])
        applied=switch_ack['native']['monotonic_ns']
        start_beat=before['diagnostics']['beats']+(onset['monotonic_ns']-before['diagnostics']['monotonic_ns'])*(100/60)*1e-9
        elapsed_ticks=math.floor((applied-onset['monotonic_ns'])*160e-9)
        beat-=(handoff['diagnostics']['monotonic_ns']-applied)*(100/60)*1e-9
        assert 0<elapsed_ticks<48,elapsed_ticks
    assert abs(handoff['diagnostics']['tempo']-100)<1e-6,handoff['diagnostics']
    quantum=1/96;phase=start_beat%quantum;epsilon=2**-23
    next_beat=math.ceil((beat+epsilon)/quantum)*quantum+phase-quantum
    while next_beat<beat+epsilon:next_beat+=quantum
    remaining=(next_beat-beat)*.6+(48-elapsed_ticks-1)*.6/96
    expected_off=(c.logical_ns if controlled else applied)+remaining*1e9
    until(84)
    def onsets(state):return [m for m in state['midi'] if m['index']>marker and m['bytes'][0]==144 and m['bytes'][2]>0]
    # The scheduled MIDI Stop is no longer the selected transport. Internal
    # playback must continue into the next phrase until a physical grid Stop.
    c.wait(lambda state:len(onsets(state))>=4,timeout=2)
    c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])
    state=c.snapshot();notes=onsets(state)
    assert [(m['port'],m['bytes']) for m in notes]==[(1,[144,60,127]),(1,[144,64,107]),(1,[144,67,100]),(1,[144,60,127])],notes
    off=next(m for m in state['midi'] if m['index']>notes[0]['index'] and m['bytes']==[128,60,127])
    field='logical_ns' if controlled else 'monotonic_ns';error=off[field]-expected_off
    c.results.append(dict(kind='pending-note-reverse-handoff',elapsed_ticks=elapsed_ticks,expected_off_ns=expected_off,actual_off_ns=off[field],error_ns=error))
    assert abs(error)<=(2 if controlled else 10000000),c.results[-1]
    arrivals=state['midi_input_schedule']['delivered']
    errors=[e['actual_'+domain+'_ns']-e['intended_'+domain+'_ns'] for e in arrivals]
    c.results.append(dict(kind='reverse-continuous-midi-arrival-errors',time_domain=domain,errors_ns=errors))
    assert len(arrivals)==84 and all(0<=e<=(0 if controlled else 10000000) for e in errors),errors
    menu_value(c,'internal')

def scale_edit_selection(c):
    from frame_oracle import header,matches
    def selected(slot,applied):
        expected=header('Scale slot '+str(slot)+' ',selected=1,tabs=3)
        c.wait(lambda state:matches(state,expected))
        c.results.append(dict(kind='scale-edit-header',slot=slot))
        levels=[15 if n==applied else 4 if n==slot else 2 for n in range(1,17)]
        c.led_values([(n,3) for n in range(1,17)],levels)
    def phrase(pitches):
        c.playback([(1,[144,p,v]) for p,v in zip(pitches,[127,117,107,97])])
    def shift_slot(slot):
        c.action(type='key',n=1,state=1)
        try:
            c.elapse(.3)  # Native K1 hold threshold is250ms before script dispatch.
            c.tap(slot,3)
        finally:c.action(type='key',n=1,state=0)
    def long_slot(slot):
        c.action(type='grid',x=slot,y=3,state=1)
        try:c.elapse(1.1)
        finally:c.action(type='grid',x=slot,y=3,state=0)
        c.elapse(.06)
    c.configure();c.tap(4,8)
    selected(1,1)
    shift_slot(2);selected(2,1)
    # Root C -> D, saved through E2/E3/K3. Editing an unused scale must not
    # change playback: the applied C-major scale still governs these notes.
    c.enc(2,-1);c.enc(3,2);c.key(3)
    selected(2,1);phrase([60,62,64,65])
    c.tap(2,3);selected(2,2);phrase([62,64,66,67])
    # Long-selecting a different editor retains the D-major applied scale.
    long_slot(3);selected(3,2);phrase([62,64,66,67])
    # Saving an already applied scale does alter playback, even when selected
    # through the edit-only gesture. D -> E remains a major scale.
    shift_slot(2);selected(2,2)
    c.enc(3,2);c.key(3);phrase([64,66,68,69])
    # Select another editing slot, then long-press it again. Global off must
    # restore chromatic relative intervals and clear the editor indicator.
    long_slot(3);selected(3,2)
    long_slot(3);selected(0,0);phrase([60,61,62,63])
    # State can be re-entered following global off; stored scale edits persist.
    c.tap(2,3);selected(2,2);phrase([64,66,68,69])


def scale_lock_lifetime(c):
    from cases import menu_label,menu_value
    from frame_oracle import selected_line
    def phrase(pitches):
        c.playback([(1,[144,p,v]) for p,v in zip(pitches,[127,117,107,97])])
    def edit_slot(slot,semitones):
        c.action(type='key',n=1,state=1)
        try:
            c.elapse(.3)  # Native K1 hold threshold is250ms before script dispatch.
            c.tap(slot,3)
        finally:c.action(type='key',n=1,state=0)
        c.enc(3,semitones);c.key(3)
    c.configure();c.tap(4,8);c.enc(2,-1)
    edit_slot(2,2);edit_slot(3,4)  # Unused D-major and E-major scales.
    # Global D lock at step1; channel E lock at step2. Four-step channel wraps
    # repeatedly inside the independent 64-step global scale track.
    c.hold_tap((1,4),(2,3));c.tap(3,8)
    c.hold_tap((2,4),(3,3))
    phrase([62,66,68,69])
    # Native menu navigation only; the diagnostic root names locate the group,
    # while rasterized labels and MIDI establish the user-perceived result.
    c.key(1);c.enc(1,4);c.key(3);menu_label(c,'LEVELS >')
    roots=c.snapshot()['diagnostics']['parameter_roots']
    c.enc(2,next(i for i,v in enumerate(roots) if v['id']=='mosaic'))
    c.key(3)
    for _ in range(40):
        if selected_line(c.snapshot(),'Scales lock until ptn end'):break
        c.enc(2,1)
    else:raise AssertionError('Scale lifetime control absent from native menu')
    menu_label(c,'Scales lock until ptn end');menu_value(c,'On')
    c.enc(3,-1);menu_value(c,'Off');c.key(1)
    phrase([62,66,66,67])
    # Remove the channel lock by repeating its physical gesture. The global D
    # lock must still apply on every channel note with channel hold disabled.
    c.hold_tap((2,4),(3,3));phrase([62,64,66,67])
    # Remove global lock too: this restores the C-major default, proving the
    # preceding D phrase came from global persistence rather than stale state.
    c.tap(4,8);c.hold_tap((1,4),(2,3));c.tap(3,8)
    phrase([60,62,64,65])


def trig_merge_sets(c):
    c.configure()
    c.tap(5,8);c.tap(5,8);c.tap(4,3)  # Pattern1 fourth note F -> G.
    c.tap(5,8);c.tap(5,8)  # Back to trig editor.
    c.tap(2,1)
    for step in (2,4):c.tap(step,4)
    c.tap(3,8);c.tap(2,2)
    c.hold_tap((15,8),(1,2));c.hold_tap((16,8),(1,2))
    notes={1:(60,127),2:(62,117),3:(64,107),4:(67,97)}
    def phrase(steps):
        observed=c.playback([(1,[144,*notes[s]]) for s in steps])
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        errors=[]
        for index,(a,b) in enumerate(zip(observed,observed[1:])):
            left=steps[index%len(steps)];right=steps[(index+1)%len(steps)]
            expected=((right-left)%4 or 4)/6
            errors.append((b[field]-a[field])/1e9-expected)
        c.results.append(dict(kind='merge-rest-spacing',steps=steps,errors_seconds=errors))
        assert errors and all(abs(e)<=(2e-9 if c.clock_mode=='controlled-experimental' else .01) for e in errors),errors
    def mode(level,steps):
        c.led_values([(14,8)],[level]);phrase(steps)
    mode(2,[1,3])  # Exactly one contributing pattern.
    c.tap(14,8);mode(5,[2,4])  # Two contributors only.
    c.tap(14,8);mode(8,[1,2,3,4])  # Set union.
    # A third pattern overlapping step2 distinguishes exactly-one from odd
    # parity and proves Only accepts two or more contributors.
    c.tap(5,8);c.tap(3,1)
    for step in (2,3):c.tap(step,4)
    c.tap(3,8);c.tap(3,2)
    c.tap(14,8);mode(2,[1])
    c.tap(14,8);mode(5,[2,3,4])
    c.tap(14,8);mode(8,[1,2,3,4])
    # With one assigned pattern there are no overlaps. Only must be silent,
    # not keep a stale merged pattern after unassignment.
    c.tap(2,2);c.tap(3,2);c.tap(14,8);c.tap(14,8)
    c.led_values([(14,8)],[5]);before=c.snapshot()['midi_count']
    c.tap(1,8);c.elapse(1.5);c.tap(1,8)
    state=c.snapshot()
    emitted=[m for m in state['midi'] if m['index']>before and m['bytes'][0]==144 and m['bytes'][2]>0]
    assert not emitted,emitted
    assert not state['midi_capture']['outstanding']
    c.results.append(dict(kind='only-without-overlap-silent',seconds=1.5))


def all_pattern_slots(c):
    c.configure();c.tap(5,8)
    for x in range(1,5):c.tap(x,4)  # Clear only the fixture's initial trigs.
    pitches=[60,62,64,65,67,69,71]
    authored={};previous=1
    cells=[(x,y) for y in range(4,8) for x in range(1,17)]
    for slot in range(1,17):
        c.tap(slot,1)
        # An untouched slot must not inherit the previous slot's authored data.
        c.led_values(cells,[2]*64)
        x=1+(slot-1)%4
        active={(x,4),(slot,5),(17-slot,7)}
        for cell in sorted(active):c.tap(*cell)
        c.tap(5,8);c.tap(x,7-(slot-1)%7)
        c.tap(5,8);c.tap(5,8)
        expected=[15 if cell in active else 2 for cell in cells]
        c.led_values(cells,expected);authored[slot]=expected
        c.tap(3,8)
        if slot!=previous:
            c.tap(previous,2);c.tap(slot,2)
        c.led_values([(slot,2)],[15])
        # Four-step channel length excludes both deliberately authored outer
        # trigs. Exactly one pitched event per loop may reach the MIDI port.
        velocity=[127,117,107,97][x-1] if slot==1 else 100
        notes=c.playback([(1,[144,pitches[(slot-1)%7],velocity])])
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        errors=[(b[field]-a[field])/1e9-4/6 for a,b in zip(notes,notes[1:])]
        assert errors and all(abs(e)<=(2e-9 if c.clock_mode=='controlled-experimental' else .01) for e in errors),errors
        c.results.append(dict(kind='pattern-slot-playback',slot=slot,pitch=pitches[(slot-1)%7],spacing_errors_seconds=errors))
        previous=slot;c.tap(5,8)
    # Revisit every slot after all edits: editing slot16 must not overwrite
    # previous slots, even where pitches or active short-loop steps coincide.
    for slot in range(1,17):
        c.tap(slot,1);c.led_values(cells,authored[slot])


def scale_stop_indicator(c):
    c.configure();c.tap(4,8);c.tap(2,3)
    c.led_values([(2,3)],[15])
    c.playback([(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107),(65,97)]])
    # Stopping transport does not disable the applied scale. The bright
    # applied indicator must survive the playing-to-stopped transition.
    c.led_values([(2,3)],[15])
    # A held global step displays its own lock, not the stopped default.
    c.action(type='grid',x=2,y=4,state=1)
    try:
        c.tap(3,3);c.led_values([(2,3),(3,3)],[2,15])
    finally:c.action(type='grid',x=2,y=4,state=0)
    c.led_values([(2,3),(3,3)],[15,2])

def channel_long_hold(c):
    c.configure()
    c.action(type='grid',x=2,y=4,state=1)
    try:c.elapse(1.1)
    finally:c.action(type='grid',x=2,y=4,state=0)
    c.led_values([(x,4) for x in range(1,5)],[15,15,15,15])
    c.playback([(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107),(65,97)]])
    c.action(type='grid',x=2,y=4,state=1)
    try:
        c.elapse(1.1);c.tap(4,4)
    finally:c.action(type='grid',x=2,y=4,state=0)
    c.led_values([(x,4) for x in range(1,5)],[0,15,15,15])
    notes=c.playback([(1,[144,n,v]) for n,v in [(62,117),(64,107),(65,97)]])
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    gaps=[(b[field]-a[field])/1e9 for a,b in zip(notes,notes[1:])]
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    c.results.append(dict(kind='range-loop-spacing',expected_seconds=1/6,actual_seconds=gaps))
    assert all(abs(gap-1/6)<=tolerance for gap in gaps),gaps

def adjacent_channel_ranges(c):
    # Fill every step through the pattern editor. The first four authored
    # pitches/velocities distinguish step addressing; later steps use C/100.
    c.configure();c.tap(5,8)
    cell=lambda step:((step-1)%16+1,(step-1)//16+4)
    for step in range(5,65):c.tap(*cell(step))
    c.tap(3,8)
    cells=[cell(step) for step in range(1,65)]
    values=[(60,127),(62,117),(64,107),(65,97)]+[(60,100)]*60
    # Every possible adjacent pair, including all row boundaries and step64.
    # Ascending ranges are documented; reversed endpoints remain a separate
    # failure-mode investigation, never silently normalized by this oracle.
    for start,end in [(s,s+1) for s in range(1,64)]+[(1,64)]:
        c.hold_tap(cell(start),cell(end))
        c.led_values(cells,[15 if start<=step<=end else 0 for step in range(1,65)])
        expected=[(1,[144,n,v]) for n,v in values[start-1:end]]
        notes=c.playback(expected,cycles=2,timeout=(end-start+1)/3+3)
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        gaps=[(b[field]-a[field])/1e9 for a,b in zip(notes,notes[1:])]
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        c.results.append(dict(kind='adjacent-range',start=start,end=end,expected_gap_seconds=1/6,actual_gaps=gaps))
        assert all(abs(gap-1/6)<=tolerance for gap in gaps),dict(start=start,end=end,gaps=gaps)

def channel_mute_gestures(c):
    c.configure()
    phrase=[(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107),(65,97)]]
    def hold(seconds):
        c.action(type='grid',x=1,y=1,state=1)
        try:c.elapse(seconds)
        finally:c.action(type='grid',x=1,y=1,state=0)
    def shift_mute():
        c.action(type='key',n=1,state=1)
        try:
            c.elapse(.3);c.tap(1,1)
        finally:c.action(type='key',n=1,state=0)
    def silence(seconds):
        before=c.snapshot()['midi_count'];c.elapse(seconds);state=c.snapshot()
        notes=[m for m in state['midi'] if m['index']>before and 144<=m['bytes'][0]<=159 and m['bytes'][2]>0]
        c.results.append(dict(kind='mute-silence',seconds=seconds,new_note_ons=notes))
        assert not notes,notes
        assert not state['midi_capture']['outstanding'],'Muted phrase retained active notes'
    hold(.8);c.led_values([(1,1)],[15]);c.playback(phrase)
    hold(1.1);c.led_values([(1,1)],[7])
    c.tap(1,8);silence(1.5);c.tap(1,8)
    shift_mute();c.led_values([(1,1)],[15]);c.playback(phrase)
    # Muting and unmuting during playback must leave transport running and
    # release existing notes; resumed pitches follow the unchanged phrase.
    c.tap(1,8)
    c.wait(lambda s:s['midi_capture']['outstanding']!=[])
    hold(1.1);c.led_values([(1,1)],[7]);silence(1.5)
    marker=c.snapshot()['midi_count'];shift_mute();c.led_values([(1,1)],[15])
    def emitted(s):
        return [m for m in s['midi'] if m['index']>marker and m['bytes'][0]==144 and m['bytes'][2]>0]
    state=c.wait(lambda s:len(emitted(s))>=9)
    actual=[(m['port'],m['bytes']) for m in emitted(state)]
    start=phrase.index(actual[0]);expected=[phrase[(start+i)%4] for i in range(len(actual))]
    assert actual==expected,dict(expected=expected,actual=actual)
    c.results.append(dict(kind='unmute-live-phrase',expected=expected,actual=actual))
    c.tap(1,8);c.wait(lambda s:not s['midi_capture']['outstanding'])

def channel_routing_isolation(c):
    c.configure()
    phrase=[(60,127),(62,117),(64,107),(65,97)]
    for channel in range(2,17):
        c.tap(channel,1)
        from frame_oracle import header,matches
        title='Ch. '+str(channel)+' Device Config';expected_header=header(title,selected=5)
        c.wait(lambda state:matches(state,expected_header))
        c.results.append(dict(kind='screen-header',expected=title,matched=True))
        c.enc(3,1) # none -> generic CC device
        c.enc(2,1);c.enc(3,channel-1) # distinct MIDI channel
        c.enc(2,1)
        if channel%2==0:c.enc(3,1) # second virtual port
        c.key(3);c.tap(1,2);c.hold_tap((1,4),(4,4))
        c.led_values([(channel,1),(1,2)],[15,15])
    def verify(active):
        marker=c.snapshot()['midi_count'];c.tap(1,8)
        def ons(state):
            return [m for m in state['midi'] if m['index']>marker and 144<=m['bytes'][0]<=159 and m['bytes'][2]>0]
        if active:
            state=c.wait(lambda state:all(sum(m['bytes'][0]==143+ch for m in ons(state))>=9 for ch in active),timeout=5)
        else:
            c.elapse(1.5);state=c.snapshot()
        notes=ons(state)
        assert {m['bytes'][0]-143 for m in notes}==set(active),dict(active=active,actual=[m['bytes'] for m in notes])
        traces={}
        for ch in active:
            trace=[m for m in notes if m['bytes'][0]==143+ch]
            actual=[(m['port'],m['bytes']) for m in trace]
            expected=[(1 if ch%2 else 2,[143+ch,*phrase[i%4]]) for i in range(len(trace))]
            assert actual==expected,dict(channel=ch,expected=expected,actual=actual)
            field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
            times=[m[field] for m in trace];tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
            assert all(abs((b-a)/1e9-1/6)<=tolerance for a,b in zip(times,times[1:])),dict(channel=ch,times=times)
            traces[ch]=times
        # Equal-rate channels must stay aligned; retain within-channel order.
        if traces:
            firsts=[times[0] for times in traces.values()]
            tolerance_ns=2 if c.clock_mode=='controlled-experimental' else 10000000
            assert max(firsts)-min(firsts)<=tolerance_ns,firsts
        c.results.append(dict(kind='channel-routing-isolation',active_channels=active,note_on_count=len(notes),times_by_channel=traces))
        c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])
    def toggle(ch):
        c.action(type='key',n=1,state=1)
        try:
            c.elapse(.3);c.tap(ch,1)
        finally:c.action(type='key',n=1,state=0)
    verify(list(range(1,17)))
    for ch in range(1,17):
        toggle(ch);c.led_values([(ch,1)],[7 if ch==16 else 0]);verify(list(range(ch+1,17)))
    for ch in range(16,0,-1):
        toggle(ch);c.led_values([(ch,1)],[15 if ch==16 else 2]);verify(list(range(ch,17)))

def memory_navigation(c):
    from frame_oracle import render
    import base64
    c.configure();c.enc(1,-2);c.screen_header('Ch. 1 Memory')
    baseline=[(60,127),(62,117),(64,107),(65,97)]
    first=[(72,90),*baseline[1:]]
    both=[(72,90),(76,80),*baseline[2:]]
    branch=[(72,90),(62,117),(79,70),(65,97)]
    def counter(current,total):
        expected=render([(0,23,15,str(current)),(0,49,15,str(total))],font_size=10,antialias=1)
        indexes=[(y*128+x)*4+k for y in list(range(13,26))+list(range(39,52)) for x in range(16) for k in range(3)]
        def match(state):
            actual=base64.b64decode(state['frame']['pixels_base64'])
            return all(actual[i]==expected[i] for i in indexes)
        c.wait(match);c.results.append(dict(kind='memory-position',current=current,total=total,frame_matched=True))
    def phrase(values):c.playback([(1,[144,n,v]) for n,v in values],cycles=2)
    def record(step,note,velocity):
        c.action(type='grid',x=step,y=4,state=1)
        try:
            c.action(type='midi',port=1,bytes=[144,note,velocity]);c.elapse(.05)
            c.action(type='midi',port=1,bytes=[128,note,0])
        finally:c.action(type='grid',x=step,y=4,state=0)
        c.elapse(.1)
    counter(0,0);c.key(2);c.key(3);c.enc(3,-3);c.enc(3,3);counter(0,0);phrase(baseline)
    c.enc(1,-2);c.screen_header('Ch. 1 Note Masks');record(1,72,90);record(2,76,80)
    c.enc(1,2);counter(2,2);phrase(both)
    c.enc(3,-1);counter(1,2);phrase(first)
    c.enc(3,-1);counter(0,2);phrase(baseline)
    c.enc(3,-3);counter(0,2);phrase(baseline)
    c.enc(3,1);counter(1,2);phrase(first)
    c.enc(3,1);counter(2,2);phrase(both)
    c.enc(3,3);counter(2,2);phrase(both)
    c.key(2);counter(0,2);phrase(baseline)
    c.key(3);counter(2,2);phrase(both)
    c.enc(3,-1);counter(1,2)
    c.enc(1,-2);record(3,79,70);c.enc(1,2);counter(2,2);phrase(branch)
    c.key(3);counter(2,2);phrase(branch)
    c.key(2);counter(0,2);phrase(baseline)
    c.key(3);counter(2,2);phrase(branch)

def memory_channel_isolation(c):
    from frame_oracle import header,matches,render
    import base64
    c.configure();c.tap(2,1);c.enc(3,1);c.enc(2,1);c.enc(3,1);c.enc(2,1);c.enc(3,1);c.key(3)
    c.tap(1,2);c.hold_tap((1,4),(4,4));c.enc(1,-4)
    baseline=[(60,127),(62,117),(64,107),(65,97)]
    edited_one=[(72,90),*baseline[1:]]
    edited_two=[baseline[0],(79,80),*baseline[2:]]
    def record(step,note,velocity):
        c.action(type='grid',x=step,y=4,state=1)
        try:
            c.action(type='midi',port=1,bytes=[144,note,velocity]);c.elapse(.05)
            c.action(type='midi',port=1,bytes=[128,note,0])
        finally:c.action(type='grid',x=step,y=4,state=0)
        c.elapse(.1)
    def history(channel,current,total=1):
        expected=header('Ch. '+str(channel)+' Memory',selected=3)
        c.wait(lambda state:matches(state,expected))
        expected=render([(0,23,15,str(current)),(0,49,15,str(total))],font_size=10,antialias=1)
        indices=[(y*128+x)*4+k for y in list(range(13,26))+list(range(39,52)) for x in range(16) for k in range(3)]
        def match(state):
            pixels=base64.b64decode(state['frame']['pixels_base64'])
            return all(pixels[i]==expected[i] for i in indices)
        c.wait(match);c.results.append(dict(kind='channel-history-counter',channel=channel,current=current,total=total))
    def verify(one,two):
        marker=c.snapshot()['midi_count'];c.tap(1,8)
        def notes(state):return [m for m in state['midi'] if m['index']>marker and 144<=m['bytes'][0]<=159 and m['bytes'][2]>0]
        state=c.wait(lambda state:all(sum(m['bytes'][0]==status for m in notes(state))>=9 for status in (144,145)),timeout=5)
        observed=notes(state)
        assert {m['bytes'][0] for m in observed}=={144,145}
        for port,status,phrase in [(1,144,one),(2,145,two)]:
            actual=[(m['port'],m['bytes']) for m in observed if m['bytes'][0]==status]
            expected=[(port,[status,*phrase[i%4]]) for i in range(len(actual))]
            assert actual==expected,dict(channel=status-143,expected=expected,actual=actual)
            c.results.append(dict(kind='history-musical-isolation',channel=status-143,expected=expected,actual=actual))
        c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])
    record(2,79,80);c.tap(1,1);record(1,72,90);c.enc(1,2)
    history(1,1);verify(edited_one,edited_two)
    c.enc(3,-1);history(1,0);verify(baseline,edited_two)
    c.tap(2,1);history(2,1);c.key(2);history(2,0);verify(baseline,baseline)
    c.tap(1,1);history(1,0);c.key(3);history(1,1);verify(edited_one,baseline)
    c.tap(2,1);history(2,0);c.enc(3,1);history(2,1);verify(edited_one,edited_two)
    # Switching to an untouched channel and navigating its empty history must
    # not affect either audible channel or borrow their history counters.
    c.tap(3,1);history(3,0,0);c.key(2);c.key(3);c.enc(3,-2);c.enc(3,2);history(3,0,0);verify(edited_one,edited_two)
    c.tap(1,1);history(1,1);c.tap(2,1);history(2,1)

def live_record_placement(c,input_offsets=(1430000000,1730000000),expected_steps=(2,4),range_start=1,clock_delta=0,rate_factor=1,boundary_witness=False):
    import time
    c.configure()
    if boundary_witness:
        # An independent audible channel marks the active step through MIDI.
        # Same four-step range and clock; no application-state oracle.
        c.tap(2,1);c.enc(3,1);c.enc(2,1);c.enc(3,1);c.enc(2,1);c.enc(3,1);c.key(3)
        c.tap(1,2);c.hold_tap((1,4),(4,4))
        # Build a separate pattern; channel1's source will be cleared below.
        c.tap(5,8);c.tap(2,1)
        for x in range(1,5):c.tap(x,4)
        c.tap(5,8)
        for x,y in ((1,7),(2,6),(3,5),(4,4)):c.tap(x,y)
        c.tap(5,8)
        for x,y in ((1,1),(2,2),(3,3),(4,4)):c.tap(x,y)
        c.tap(3,8);c.tap(1,2);c.tap(2,2);c.tap(1,1)
    c.tap(5,8)
    if boundary_witness:c.tap(1,1)
    for x in range(1,5):c.tap(x,4)
    c.tap(3,8)
    cell=lambda step:((step-1)%16+1,(step-1)//16+4)
    if range_start!=1:c.hold_tap(cell(range_start),cell(range_start+3))
    cells=[cell(step) for step in range(1,65)]
    c.led_values(cells,[2 if range_start<=step<=range_start+3 else 0 for step in range(1,65)])
    if clock_delta:
        from frame_oracle import header,matches
        c.enc(1,-1);c.wait(lambda state:matches(state,header('Ch. 1 Clocks',selected=4)))
        c.enc(3,clock_delta);c.key(3)
    c.key(1);c.enc(1,4);c.key(3);menu_label(c,'LEVELS >')
    position=next(i for i,v in enumerate(c.snapshot()['diagnostics']['parameter_roots']) if v['name']=='CLOCK')
    c.enc(2,position);c.key(3);menu_label(c,'source');c.enc(3,1);menu_value(c,'midi');c.key(1)
    c.tap(2,8) # arm recording through the grid
    controlled=c.clock_mode=='controlled-experimental';domain='logical' if controlled else 'monotonic'
    origin=c.logical_ns+100000000 if controlled else time.monotonic_ns()+500000000
    # 24PPQN at100BPM:25ms pulses,150ms per sixteenth. FA follows49 warmup
    # pulses; pulse50 begins step1. Notes well inside steps2/4 isolate address
    # placement from the separate exact-boundary ordering campaign.
    packets=[(i*25000000,[248]) for i in range(1,113)]
    packets += [(1230000000,[250]),(input_offsets[0],[144,72,90]),(input_offsets[0]+20000000,[128,72,0]),(input_offsets[1],[144,79,80]),(input_offsets[1]+20000000,[128,79,0]),(2805000000,[252])]
    events=[dict(port=1,bytes=data,**{'at_'+domain+'_ns':origin+offset}) for offset,data in sorted(packets,key=lambda pair:pair[0])]
    request=dict(type='midi_schedule',schedule_id=1,events=events)
    if controlled:request['time_domain']='logical'
    c.action(**request)
    if controlled:c.elapse((origin+2820000000-c.logical_ns)/1e9)
    else:c.wait(lambda state:len(state['midi_input_schedule']['delivered'])==len(events),timeout=5)
    state=c.snapshot();assert len(state['midi_input_schedule']['delivered'])==len(events)
    if boundary_witness:
        emitted=state['midi'];field='logical_ns' if controlled else 'monotonic_ns'
        arrivals=state['midi_input_schedule']['delivered']
        limit=0 if controlled else 10000000
        for sent,received in zip(events,arrivals):
            assert received['bytes']==sent['bytes'] and received['port']==sent['port']
            assert received['intended_'+domain+'_ns']==sent['at_'+domain+'_ns']
            assert 0<=received['actual_'+domain+'_ns']-received['intended_'+domain+'_ns']<=limit,received
        assert all(a['actual_'+domain+'_ns']<=b['actual_'+domain+'_ns'] for a,b in zip(arrivals,arrivals[1:]))
        witness=[m for m in emitted if m['port']==2 and m['bytes'][0]==145 and m['bytes'][2]>0]
        phrase=[(60,127),(62,117),(64,107),(65,97)]
        # FA at1.23s, first playback pulse at1.25s; stop at2.805s permits
        # exactly11 sixteenths at100BPM. Anchor to stimulus, not captured output.
        assert [m['bytes'] for m in witness]==[[145,*phrase[i%4]] for i in range(11)],witness
        for i,m in enumerate(witness):
            assert abs(m[field]-(origin+1250000000+i*150000000))<=(2 if controlled else 10000000),m
        evidence=[]
        for pitch,step in zip((72,79),expected_steps):
            active_pitch=phrase[step-1][0]
            preview=next(m for m in emitted if m['port']==1 and m['bytes'][:2]==[144,pitch])
            prior=[m for m in emitted if m['index']<preview['index'] and m['port']==2 and m['bytes'][0]==145 and m['bytes'][2]>0]
            following=[m for m in emitted if m['index']>preview['index'] and m['port']==2 and m['bytes'][0]==145 and m['bytes'][2]>0]
            assert prior and following,'Missing MIDI step witness'
            assert prior[-1]['bytes'][1]==active_pitch,dict(preview=preview,prior=prior[-1])
            assert following[0]['bytes'][1]==phrase[step%4][0]
            assert prior[-1][field]<=preview[field]<following[0][field]
            delivery=next(d for d in arrivals if d['bytes'][:2]==[144,pitch])
            assert 0<=preview[field]-delivery['actual_'+domain+'_ns']<=(0 if controlled else 10000000)
            if controlled and input_offsets==(1400000000,1700000000):
                assert following[0][field]-preview[field]==1
            evidence.append(dict(recorded_step=step,preview=preview,active_step_onset=prior[-1],next_step_onset=following[0],gap_to_next_ns=following[0][field]-preview[field]))
        c.results.append(dict(kind='boundary-active-step-midi-witness',events=evidence))
    c.wait(lambda state:not state['midi_capture']['outstanding']);c.tap(2,8)
    c.led_values(cells,[15 if step in expected_steps else (2 if range_start<=step<=range_start+3 else 0) for step in range(1,65)])
    c.results.append(dict(kind='recorded-step-placement',expected_steps=list(expected_steps),input_note_on_offsets_ns=list(input_offsets),clock_step_ns=round(150000000*rate_factor),channel_range=[range_start,range_start+3]))
    # Replay in normal internal clock after disarming; preview MIDI cannot
    # satisfy this oracle because playback takes a fresh capture marker.
    c.key(1);c.key(3);menu_label(c,'source');c.enc(3,-1);menu_value(c,'internal')
    c.enc(2,1);menu_label(c,'tempo');c.enc(3,-10);menu_value(c,'90');c.key(1)
    # Independent step positions define playback order, including wrap input.
    phrase=sorted(zip(expected_steps,[(1,[144,72,90]),(1,[144,79,80])]))
    if boundary_witness:
        c.tap(2,1);c.tap(2,2);c.tap(1,1)
    notes=c.playback([event for step,event in phrase],cycles=3)
    field='logical_ns' if controlled else 'monotonic_ns'
    gaps=[(b[field]-a[field])/1e9 for a,b in zip(notes,notes[1:])]
    expected_gaps=[((phrase[(i+1)%2][0]-phrase[i%2][0])%4)*rate_factor/6 for i in range(len(gaps))]
    tolerance=2e-9 if controlled else .01
    assert all(abs(gap-expected)<=tolerance for gap,expected in zip(gaps,expected_gaps)),dict(actual=gaps,expected=expected_gaps)
    c.results.append(dict(kind='recorded-replay-spacing',expected_seconds=expected_gaps,actual_seconds=gaps))

def recorded_note_channel_switch(c,hold_ns=500000000,expected_duration=.5,release_status=128,input_channel=1,disarm_while_held=False):
    c.configure();c.tap(2,1);c.enc(3,1);c.enc(2,1);c.enc(3,1);c.enc(2,1);c.enc(3,1);c.key(3)
    c.tap(1,2);c.hold_tap((1,4),(4,4));c.tap(1,1)
    c.tap(2,8);marker=c.snapshot()['midi_count'];c.tap(1,8)
    controlled=c.clock_mode=='controlled-experimental'
    field='logical_ns' if controlled else 'monotonic_ns'
    state=c.wait(lambda state:any(m['index']>marker and m['port']==1 and m['bytes']==[144,60,127] for m in state['midi']))
    anchor=next(m[field] for m in state['midi'] if m['index']>marker and m['port']==1 and m['bytes']==[144,60,127])
    # The next four-step loop starts2/3s after the observed first onset.
    # Enter50ms into step1; supply the requested hold with native deadlines.
    # Client snapshots/channel selection must not lengthen the keyboard hold.
    origin=anchor+666666667+50000000
    events=[dict(port=1,bytes=data,**{'at_'+field:origin+offset}) for offset,data in [(0,[143+input_channel,72,90]),(hold_ns,[release_status+input_channel-1,72,0])]]
    request=dict(type='midi_schedule',schedule_id=1,events=events)
    if controlled:request['time_domain']='logical'
    c.action(**request)
    if controlled:c.elapse((origin+100000000-c.logical_ns)/1e9)
    else:c.wait(lambda state:len(state['midi_input_schedule']['delivered'])>=1,timeout=2)
    c.tap(2,1)
    if disarm_while_held:c.tap(2,8)
    marker=c.snapshot()['midi_count']
    if controlled:c.elapse((origin+hold_ns+10000000-c.logical_ns)/1e9)
    else:c.wait(lambda state:len(state['midi_input_schedule']['delivered'])==2,timeout=2)
    state=c.snapshot()
    c.results.append(dict(kind='scheduled-keyboard-hold',expected_ns=hold_ns,events=events,delivered=state['midi_input_schedule']['delivered']))
    releases=[(m['port'],m['bytes']) for m in state['midi'] if m['index']>marker and 128<=m['bytes'][0]<=143 and m['bytes'][1]==72]
    c.results.append(dict(kind='held-input-release-route',expected=[(1,[128,72,0])],actual=releases))
    assert releases==[(1,[128,72,0])],releases
    if disarm_while_held:
        # New post-disarm notes may preview, but must not alter channel2 replay.
        c.action(type='midi',port=1,bytes=[144,79,80]);c.elapse(.03)
        c.action(type='midi',port=1,bytes=[128,79,0])
    c.tap(1,8)
    if not disarm_while_held:c.tap(2,8)
    c.wait(lambda state:not state['midi_capture']['outstanding'])
    marker=c.snapshot()['midi_count'];c.tap(1,8)
    def notes(state):return [m for m in state['midi'] if m['index']>marker and m['bytes'][0] in (144,145) and m['bytes'][2]>0]
    state=c.wait(lambda state:all(sum(m['bytes'][0]==status for m in notes(state))>=13 for status in (144,145)),timeout=5)
    rows=notes(state);field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    for port,status,phrase,pitch,duration in [(1,144,[(72,90),(62,117),(64,107),(65,97)],72,expected_duration),(2,145,[(60,127),(62,117),(64,107),(65,97)],60,1/6)]:
        channel_notes=[m for m in rows if m['bytes'][0]==status]
        actual=[(m['port'],m['bytes']) for m in channel_notes];expected=[(port,[status,*phrase[i%4]]) for i in range(len(actual))]
        assert actual==expected,dict(expected=expected,actual=actual)
        durations=[]
        for note in [m for m in channel_notes if m['bytes'][1]==pitch][:3]:
            off=next(m for m in state['midi'] if m['index']>note['index'] and m['port']==port and m['bytes'][:2]==[status-16,pitch])
            durations.append((off[field]-note[field])/1e9)
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        assert all(abs(value-duration)<=tolerance for value in durations),dict(channel=status-143,durations=durations,expected=duration)
        c.results.append(dict(kind='recording-origin-channel',channel=status-143,expected=expected,actual=actual,durations=durations,expected_duration=duration))
    c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])

def live_playhead_feedback(c,clock_delta=0):
    import time
    c.configure()
    if clock_delta:
        from frame_oracle import header,matches
        c.enc(1,-1);c.wait(lambda state:matches(state,header('Ch. 1 Clocks',selected=4)))
        c.enc(3,clock_delta);c.key(3)
    marker=c.snapshot()['midi_count']
    c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
    controlled=c.clock_mode=='controlled-experimental'
    field='logical_ns' if controlled else 'monotonic_ns'
    started=c.logical_ns if controlled else time.monotonic_ns()
    samples=[];settled=set();last_rows=[]
    # Grid redraw sleeps50ms. D permits only integer-nanosecond rounding;
    # R adds the existing10ms scheduler allowance, not a whole extra step.
    limit=50000002 if controlled else 60000000
    while (c.logical_ns if controlled else time.monotonic_ns())-started<3000000000:
        before=c.logical_ns if controlled else time.monotonic_ns()
        state=c.snapshot()
        after=c.logical_ns if controlled else time.monotonic_ns()
        rows=[m for m in state['midi'] if m['index']>marker and m['port']==1 and m['bytes'][0]==144 and m['bytes'][2]>0]
        if rows:
            expected=[[144,n,v] for n,v in [(60,127),(62,117),(64,107),(65,97)]]
            assert [m['bytes'] for m in rows]==[expected[i%4] for i in range(len(rows))]
            current=(len(rows)-1)%4+1;previous=(current-2)%4+1
            visible=[step for step in range(1,65) if state['grid'][48+step-1]==10]
            assert len(visible)<=1,visible
            age_low=before-rows[-1][field];age_high=after-rows[-1][field]
            if visible:assert visible[0] in (current,previous),dict(current=current,visible=visible)
            if age_low>limit:assert visible==[current],dict(current=current,visible=visible,age_low_ns=age_low,age_high_ns=age_high)
            if visible==[current]:settled.add(len(rows))
            samples.append(dict(note_ordinal=len(rows),current_step=current,visible=visible,age_lower_ns=age_low,age_upper_ns=age_high))
            last_rows=rows
            if len(rows)>=9 and 9 in settled:break
        c.elapse(.01 if controlled else .005)
    assert len(last_rows)>=9 and set(range(1,10))<=settled,dict(notes=len(last_rows),settled=sorted(settled))
    stale=[x for x in samples if x['visible']!=[x['current_step']]]
    c.results.append(dict(kind='live-playhead-latency',redraw_period_ns=50000000,maximum_allowed_stale_ns=limit,samples=samples,max_observed_stale_lower_ns=max([x['age_lower_ns'] for x in stale],default=0)))
    c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])
    c.led_values([(x,4) for x in range(1,5)],[15]*4)

def keyboard_input_channels(c):
    import time
    c.configure();marker=c.snapshot()['midi_count']
    controlled=c.clock_mode=='controlled-experimental';field='logical_ns' if controlled else 'monotonic_ns'
    origin=c.logical_ns+100000000 if controlled else time.monotonic_ns()+500000000
    events=[];expected=[];ordinal=0
    for port in (1,2):
        for channel in range(1,17):
            for release in (128,144):
                note=60+(channel-1)%12;onset=origin+ordinal*60000000
                events += [dict(port=port,bytes=[143+channel,note,90],**{'at_'+field:onset}),dict(port=port,bytes=[release+channel-1,note,0],**{'at_'+field:onset+30000000})]
                expected += [(1,[144,note,90]),(1,[128,note,0])]
                ordinal+=1
    request=dict(type='midi_schedule',schedule_id=1,events=events)
    if controlled:request['time_domain']='logical'
    c.action(**request)
    if controlled:c.elapse((origin+ordinal*60000000-c.logical_ns)/1e9)
    else:c.wait(lambda state:len(state['midi_input_schedule']['delivered'])==len(events),timeout=6)
    state=c.snapshot();assert len(state['midi_input_schedule']['delivered'])==128
    actual=[(m['port'],m['bytes']) for m in state['midi'] if m['index']>marker and 128<=m['bytes'][0]<=159]
    assert actual==expected,dict(expected=expected,actual=actual)
    assert not state['midi_capture']['outstanding']
    c.results.append(dict(kind='keyboard-input-channel-matrix',input_ports=[1,2],input_channels=list(range(1,17)),release_status_types=[128,144],expected=expected,actual=actual))

def overlapping_keyboard_sources(c,second_port=2,second_channel=1):
    c.configure();c.tap(2,1);c.enc(3,1);c.enc(2,1);c.enc(3,1);c.enc(2,1);c.enc(3,1);c.key(3)
    for order in ((0,1),(1,0)):
        c.tap(1,1);marker=c.snapshot()['midi_count']
        c.action(type='midi',port=1,bytes=[144,72,90])
        c.tap(2,1);c.action(type='midi',port=second_port,bytes=[143+second_channel,72,80])
        inputs=[(1,1),(second_port,second_channel)]
        expected=[(1,[144,72,90]),(2,[145,72,80])]
        for owner in order:
            port,channel=inputs[owner]
            c.action(type='midi',port=port,bytes=[127+channel,72,0])
            expected.append((owner+1,[128+owner,72,0]))
            state=c.snapshot()
            actual=[(m['port'],m['bytes']) for m in state['midi'] if m['index']>marker and 128<=m['bytes'][0]<=159]
            assert actual==expected,dict(release_order=order,expected=expected,actual=actual)
        assert not state['midi_capture']['outstanding']
        c.results.append(dict(kind='overlapping-keyboard-source-isolation',input_sources=inputs,release_order=order,expected=expected,actual=actual))

def recorded_chord_release(c,release_order=(76,79,72),onset_offsets=(0,0,0),preview_release_ns=None,release_offsets=(300000000,400000000,500000000)):
    c.configure();c.tap(2,8)
    marker=c.snapshot()['midi_count'];c.tap(1,8)
    controlled=c.clock_mode=='controlled-experimental'
    field='logical_ns' if controlled else 'monotonic_ns'
    state=c.wait(lambda state:any(m['index']>marker and m['port']==1 and m['bytes']==[144,60,127] for m in state['midi']))
    anchor=next(m[field] for m in state['midi'] if m['index']>marker and m['port']==1 and m['bytes']==[144,60,127])
    origin=anchor+666666667+50000000
    packets=[(offset,[144,pitch,90]) for offset,pitch in zip(onset_offsets,(72,76,79))]
    packets += [(offset,[128,pitch,0]) for offset,pitch in zip(release_offsets,release_order)]
    if preview_release_ns is not None:
        packets += [(100000000,[144,83,80]),(preview_release_ns,[128,83,0])]
    packets.sort(key=lambda item:item[0])
    events=[dict(port=1,bytes=data,**{'at_'+field:origin+offset}) for offset,data in packets]
    request=dict(type='midi_schedule',schedule_id=1,events=events)
    if controlled:request['time_domain']='logical'
    c.action(**request)
    if controlled:c.elapse((origin+(10000000 if preview_release_ns is not None else 100000000)-c.logical_ns)/1e9)
    else:c.wait(lambda state:sum(event['bytes'][0]==144 and event['bytes'][1] in (72,76,79) for event in state['midi_input_schedule']['delivered'])>=3,timeout=2)
    c.tap(2,8) # Disarm after all three chord presses; some voices may already be released.
    if controlled:c.elapse((origin+max(500000000,preview_release_ns or 0)+10000000-c.logical_ns)/1e9)
    else:c.wait(lambda state:len(state['midi_input_schedule']['delivered'])==len(events),timeout=2)
    state=c.snapshot()
    c.results.append(dict(kind='scheduled-recorded-chord',release_order=release_order,events=events,delivered=state['midi_input_schedule']['delivered']))
    if preview_release_ns is not None:
        preview=[(m['port'],m['bytes']) for m in state['midi'] if m['bytes'][1:2]==[83] and m['bytes'][0] in (128,144)]
        expected_preview=[(1,[144,83,80]),(1,[128,83,0])]
        c.results.append(dict(kind='post-disarm-preview',expected=expected_preview,actual=preview))
        assert preview==expected_preview,dict(expected=expected_preview,actual=preview)
    c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])
    marker=c.snapshot()['midi_count'];c.tap(1,8)
    def notes(state):return [m for m in state['midi'] if m['index']>marker and m['bytes'][0]==144 and m['bytes'][2]>0]
    state=c.wait(lambda state:len(notes(state))>=19,timeout=5)
    rows=notes(state)
    phrase=[(72,90),(76,90),(79,90),(62,117),(64,107),(65,97)]
    expected=[(1,[144,*phrase[i%6]]) for i in range(len(rows))]
    actual=[(m['port'],m['bytes']) for m in rows]
    c.results.append(dict(kind='recorded-chord-replay',expected=expected,actual=actual))
    assert actual==expected,dict(expected=expected,actual=actual)
    durations=[]
    for note in [m for m in rows if m['bytes'][1] in (72,76,79)][:9]:
        off=next(m for m in state['midi'] if m['index']>note['index'] and m['port']==1 and m['bytes'][:2]==[128,note['bytes'][1]])
        durations.append((off[field]-note[field])/1e9)
    tolerance=2e-9 if controlled else .01
    c.results.append(dict(kind='recorded-chord-length',expected=.5,actual=durations,release_order=release_order))
    assert len(durations)==9 and all(abs(value-.5)<=tolerance for value in durations),dict(expected=.5,durations=durations,release_order=release_order)
    c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])

def recorded_input_sources(c,second_port=2,second_channel=1):
    hold_ns=500000000;expected_duration=.5;release_status=128;input_channel=1;disarm_while_held=False
    c.configure();c.tap(2,1);c.enc(3,1);c.enc(2,1);c.enc(3,1);c.enc(2,1);c.enc(3,1);c.key(3)
    c.tap(1,2);c.hold_tap((1,4),(4,4));c.tap(1,1)
    c.tap(2,8);marker=c.snapshot()['midi_count'];c.tap(1,8)
    controlled=c.clock_mode=='controlled-experimental'
    field='logical_ns' if controlled else 'monotonic_ns'
    state=c.wait(lambda state:any(m['index']>marker and m['port']==1 and m['bytes']==[144,60,127] for m in state['midi']))
    anchor=next(m[field] for m in state['midi'] if m['index']>marker and m['port']==1 and m['bytes']==[144,60,127])
    # The next four-step loop starts2/3s after the observed first onset.
    # Enter20ms into step1, select channel2, then enter its note100ms later.
    # Client snapshots/channel selection must not lengthen the keyboard hold.
    origin=anchor+666666667+20000000
    events=[dict(port=1,bytes=data,**{'at_'+field:origin+offset}) for offset,data in [(0,[143+input_channel,72,90]),(hold_ns,[release_status+input_channel-1,72,0])]]
    events += [dict(port=second_port,bytes=data,**{'at_'+field:origin+offset}) for offset,data in [(100000000,[143+second_channel,72,80]),(600000000,[127+second_channel,72,0])]]
    events.sort(key=lambda event:event['at_'+field])
    request=dict(type='midi_schedule',schedule_id=1,events=events)
    if controlled:request['time_domain']='logical'
    c.action(**request)
    if controlled:c.elapse((origin+10000000-c.logical_ns)/1e9)
    else:c.wait(lambda state:len(state['midi_input_schedule']['delivered'])>=1,timeout=2)
    c.tap(2,1)
    if disarm_while_held:c.tap(2,8)
    marker=c.snapshot()['midi_count']
    if controlled:c.elapse((origin+610000000-c.logical_ns)/1e9)
    else:c.wait(lambda state:len(state['midi_input_schedule']['delivered'])==4,timeout=2)
    state=c.snapshot()
    c.results.append(dict(kind='scheduled-keyboard-hold',expected_ns=hold_ns,events=events,delivered=state['midi_input_schedule']['delivered']))
    releases=[(m['port'],m['bytes']) for m in state['midi'] if m['index']>marker and 128<=m['bytes'][0]<=143 and m['bytes'][1]==72]
    c.results.append(dict(kind='held-input-release-route',expected=[(1,[128,72,0]),(2,[129,72,0])],actual=releases))
    assert releases==[(1,[128,72,0]),(2,[129,72,0])],releases
    if disarm_while_held:
        # New post-disarm notes may preview, but must not alter channel2 replay.
        c.action(type='midi',port=1,bytes=[144,79,80]);c.elapse(.03)
        c.action(type='midi',port=1,bytes=[128,79,0])
    c.tap(1,8)
    if not disarm_while_held:c.tap(2,8)
    c.wait(lambda state:not state['midi_capture']['outstanding'])
    marker=c.snapshot()['midi_count'];c.tap(1,8)
    def notes(state):return [m for m in state['midi'] if m['index']>marker and m['bytes'][0] in (144,145) and m['bytes'][2]>0]
    state=c.wait(lambda state:all(sum(m['bytes'][0]==status for m in notes(state))>=13 for status in (144,145)),timeout=5)
    rows=notes(state);field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    for port,status,phrase,pitch,duration in [(1,144,[(72,90),(62,117),(64,107),(65,97)],72,expected_duration),(2,145,[(72,80),(62,117),(64,107),(65,97)],72,.5)]:
        channel_notes=[m for m in rows if m['bytes'][0]==status]
        actual=[(m['port'],m['bytes']) for m in channel_notes];expected=[(port,[status,*phrase[i%4]]) for i in range(len(actual))]
        assert actual==expected,dict(expected=expected,actual=actual)
        durations=[]
        for note in [m for m in channel_notes if m['bytes'][1]==pitch][:3]:
            off=next(m for m in state['midi'] if m['index']>note['index'] and m['port']==port and m['bytes'][:2]==[status-16,pitch])
            durations.append((off[field]-note[field])/1e9)
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        assert all(abs(value-duration)<=tolerance for value in durations),dict(channel=status-143,durations=durations,expected=duration)
        c.results.append(dict(kind='recording-origin-channel',channel=status-143,expected=expected,actual=actual,durations=durations,expected_duration=duration))
    c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])

def keyboard_pitch_range(c):
    import time
    c.configure();marker=c.snapshot()['midi_count']
    controlled=c.clock_mode=='controlled-experimental';field='logical_ns' if controlled else 'monotonic_ns'
    origin=c.logical_ns+100000000 if controlled else time.monotonic_ns()+500000000
    events=[];expected=[];ordinal=0
    for note in range(128):
        for release,velocity in ((128,1),(144,127)):
            onset=origin+ordinal*30000000
            events += [dict(port=1,bytes=[144,note,velocity],**{'at_'+field:onset}),dict(port=1,bytes=[release,note,0],**{'at_'+field:onset+15000000})]
            expected += [(1,[144,note,velocity]),(1,[128,note,0])]
            ordinal+=1
    request=dict(type='midi_schedule',schedule_id=1,events=events)
    if controlled:request['time_domain']='logical'
    c.action(**request)
    if controlled:c.elapse((origin+ordinal*30000000-c.logical_ns)/1e9)
    else:c.wait(lambda state:len(state['midi_input_schedule']['delivered'])==len(events),timeout=12)
    state=c.snapshot();assert len(state['midi_input_schedule']['delivered'])==512
    actual=[(m['port'],m['bytes']) for m in state['midi'] if m['index']>marker and 128<=m['bytes'][0]<=159]
    assert actual==expected,dict(expected=expected,actual=actual)
    assert not state['midi_capture']['outstanding']
    c.results.append(dict(kind='keyboard-pitch-range',pitches=list(range(128)),velocities=[1,127],release_status_types=[128,144],expected=expected,actual=actual))

CASES={
 'M-ALG-001':dict(run=euclidean_workflow,requirements=['PAT-ALGORITHM', 'PAT-FADERS', 'PAT-PREVIEW', 'PAT-PAINT', 'PAT-CANCEL', 'PAT-MOVE'],description='Euclidean3-in-8: full-grid two-phase preview, unchanged playback, cancel, shifted XOR paint/repaint, left/reset and dense-fill boundary'),
 'M-PAT-004':dict(run=pattern_duration_controls,requirements=['PAT-DURATION'],description='Length extension/reset and empty-step gestures preserve exact grid and MIDI phrase'),
 'M-PAT-005':dict(run=live_pattern_duration,requirements=['PAT-DURATION'],description='Shorten and extend during playback: pending release unchanged, following onsets use edited length, phrase timing preserved'),
 'M-LEN-004':dict(run=lambda c:pattern_duration_domain(c,(4,),4),requirements=['PAT-DURATION','MIDI-RELEASE-001'],description='Full-loop same-pitch retrigger must release the previous note before emitting the next note-on'),
 'M-PAT-003':dict(run=pattern_duration_domain,requirements=['PAT-DURATION'],description='All64 authored duration endpoints through grid gestures, full length LEDs and independent MIDI durations with stop cleanup'),
 'M-REC-032':dict(run=lambda c:live_record_placement(c,(1398000000,1698000000),(1,3),boundary_witness=True),requirements=['REC-LIVE-NOTES'],description='Two milliseconds before boundary: independent active-step MIDI witness, grid and replay'),
 'M-REC-033':dict(run=lambda c:live_record_placement(c,(1402000000,1702000000),(2,4),boundary_witness=True),requirements=['REC-LIVE-NOTES'],description='Two milliseconds after boundary: independent active-step MIDI witness, grid and replay'),
 'M-MIDI-005':dict(run=keyboard_pitch_range,requirements=['MIDI-RELEASE-001'],description='All128 MIDI pitches at minimum/maximum velocity with both release forms; exact preview and no outstanding notes'),
 'M-REC-030':dict(run=lambda c:recorded_chord_release(c,(72,76,79),(0,0,80000000),release_offsets=(40000000,400000000,500000000)),requirements=['REC-LIVE-NOTES','REC-ARM'],description='Add third voice after root release while second voice remains held; preserve chord and first onset'),
 'M-REC-031':dict(run=lambda c:recorded_chord_release(c,(76,72,79),(0,0,80000000),release_offsets=(40000000,400000000,500000000)),requirements=['REC-LIVE-NOTES','REC-ARM'],description='Add third voice after second voice release while root remains held; preserve all recorded voices'),
 'M-REC-028':dict(run=lambda c:recorded_chord_release(c,preview_release_ns=600000000),requirements=['REC-LIVE-NOTES','REC-ARM'],description='Post-disarm preview outlasts a recorded chord without extending or losing its shared length'),
 'M-REC-029':dict(run=lambda c:recorded_chord_release(c,preview_release_ns=250000000),requirements=['REC-LIVE-NOTES','REC-ARM'],description='Post-disarm preview releases before the recorded chord without altering replay'),
 'M-REC-026':dict(run=lambda c:recorded_chord_release(c,(72,76,79),(0,40000000,80000000)),requirements=['REC-LIVE-NOTES','REC-ARM'],description='Staggered chord with root released first spans first press to final release'),
 'M-REC-027':dict(run=lambda c:recorded_chord_release(c,(76,79,72),(0,40000000,80000000)),requirements=['REC-LIVE-NOTES','REC-ARM'],description='Staggered chord with root released last retains first-press to final-release shared length'),
 'M-REC-024':dict(run=recorded_input_sources,requirements=['REC-LIVE-NOTES','MIDI-RELEASE-001'],description='Two ports record the same pitch on distinct channels in the same step; independent replay and lengths'),
 'M-REC-025':dict(run=lambda c:recorded_input_sources(c,1,16),requirements=['REC-LIVE-NOTES','MIDI-RELEASE-001'],description='Two input channels record overlapping notes on distinct Mosaic channels; independent replay and lengths'),
 'M-REC-020':dict(run=lambda c:recorded_chord_release(c,(72, 79, 76)),requirements=['REC-LIVE-NOTES','REC-ARM'],description='Disarmed held chord release order (72, 79, 76) retains full shared length'),
 'M-REC-021':dict(run=lambda c:recorded_chord_release(c,(76, 72, 79)),requirements=['REC-LIVE-NOTES','REC-ARM'],description='Disarmed held chord release order (76, 72, 79) retains full shared length'),
 'M-REC-022':dict(run=lambda c:recorded_chord_release(c,(79, 72, 76)),requirements=['REC-LIVE-NOTES','REC-ARM'],description='Disarmed held chord release order (79, 72, 76) retains full shared length'),
 'M-REC-023':dict(run=lambda c:recorded_chord_release(c,(79, 76, 72)),requirements=['REC-LIVE-NOTES','REC-ARM'],description='Disarmed held chord release order (79, 76, 72) retains full shared length'),

 'M-REC-018':dict(run=recorded_chord_release,requirements=['REC-LIVE-NOTES','REC-ARM'],description='Disarmed held chord records complete shared length when root is released last'),
 'M-REC-019':dict(run=lambda c:recorded_chord_release(c,(72,76,79)),requirements=['REC-LIVE-NOTES','REC-ARM'],description='Disarmed held chord records complete shared length when root is released first'),
 'M-MIDI-003':dict(run=overlapping_keyboard_sources,requirements=['MIDI-RELEASE-001'],description='Two input ports hold the same pitch on different Mosaic channels; both release orders preserve ownership'),
 'M-MIDI-004':dict(run=lambda c:overlapping_keyboard_sources(c,1,16),requirements=['MIDI-RELEASE-001'],description='Two input channels on one port hold the same pitch on different Mosaic channels; both release orders preserve ownership'),
 'M-REC-017':dict(run=lambda c:recorded_note_channel_switch(c,disarm_while_held=True),requirements=['REC-LIVE-NOTES','REC-ARM'],description='Disarm while holding a recorded keyboard note; release commits its full quantised length on the original channel'),
 'M-MIDI-002':dict(run=keyboard_input_channels,requirements=['MIDI-RELEASE-001','REC-LIVE-NOTES'],description='All16 keyboard input channels across both ports and both release forms produce exact selected-channel preview MIDI with no stuck notes'),
 'M-REC-016':dict(run=lambda c:recorded_note_channel_switch(c,input_channel=16),requirements=['REC-LIVE-NOTES','MIDI-RELEASE-001'],description='Keyboard on MIDI input channel16 records and releases on the selected Mosaic channel independently of its input channel'),
 'M-REC-015':dict(run=lambda c:recorded_note_channel_switch(c,release_status=144),requirements=['REC-LIVE-NOTES','MIDI-RELEASE-001'],description='Velocity-zero Note On releases the original held note and commits its recorded length after channel selection changes'),
 'M-UI-002':dict(run=lambda c:live_playhead_feedback(c,3),requirements=['CLOCK-PHRASE-001','NAV-TRANSPORT'],description='Twice-rate live grid playhead follows emitted MIDI within one redraw period across two loops'),
 'M-UI-001':dict(run=live_playhead_feedback,requirements=['CLOCK-PHRASE-001','NAV-TRANSPORT'],description='Live grid playhead follows independently checked emitted MIDI steps within one redraw period; two loops and stopped grid'),
 'M-REC-013':dict(run=lambda c:live_record_placement(c,(1355000000,1505000000),(16,18),15,3,.5),requirements=['REC-LIVE-NOTES','CH-RANGE'],description='Twice-rate channel records on its own steps across a grid row; absolute LEDs and independent replay gaps'),
 'M-REC-014':dict(run=lambda c:live_record_placement(c,(1580000000,2180000000),(62,64),61,-2,2),requirements=['REC-LIVE-NOTES','CH-RANGE'],description='Half-rate channel records on its own steps near step64; absolute LEDs and independent replay gaps'),
 'M-REC-011':dict(run=lambda c:live_record_placement(c,(1730000000,1880000000),(4,1),1),requirements=['REC-LIVE-NOTES','CH-RANGE'],description='Live keyboard input across range1..4 wrap; absolute recorded cells and disarmed replay order/spacing'),
 'M-REC-012':dict(run=lambda c:live_record_placement(c,(1730000000,1880000000),(64,61),61),requirements=['REC-LIVE-NOTES','CH-RANGE'],description='Live keyboard input across range61..64 wrap; absolute recorded cells and disarmed replay order/spacing'),
 'M-REC-008':dict(run=lambda c:live_record_placement(c,expected_steps=(3,5),range_start=2),requirements=['REC-LIVE-NOTES','CH-RANGE'],description='Live keyboard notes target absolute steps3/5 in channel range2..5; all64 LEDs and disarmed MIDI replay'),
 'M-REC-009':dict(run=lambda c:live_record_placement(c,expected_steps=(16,18),range_start=15),requirements=['REC-LIVE-NOTES','CH-RANGE'],description='Live keyboard notes target absolute steps16/18 in channel range15..18; all64 LEDs and disarmed MIDI replay'),
 'M-REC-010':dict(run=lambda c:live_record_placement(c,expected_steps=(62,64),range_start=61),requirements=['REC-LIVE-NOTES','CH-RANGE'],description='Live keyboard notes target absolute steps62/64 in channel range61..64; all64 LEDs and disarmed MIDI replay'),
 'M-REC-007':dict(run=lambda c:recorded_note_channel_switch(c,210000000,5/24),requirements=['REC-LIVE-NOTES'],description='A210ms keyboard hold quantises to1.25 steps at90BPM; replay lasts5/24s'),
 'M-REC-006':dict(run=lambda c:recorded_note_channel_switch(c,550000000,13/24),requirements=['REC-LIVE-NOTES'],description='A550ms keyboard hold at90BPM quantises to3.25 sixteenth steps; replay lasts13/24s on the origin channel'),
 'M-REC-005':dict(run=recorded_note_channel_switch,requirements=['REC-LIVE-NOTES','MIDI-RELEASE-001'],description='Switch selected channel while recording a held note; release route and recorded length remain on origin channel'),
 'M-REC-002':dict(run=lambda c:live_record_placement(c,(1398000000,1698000000),(1,3)),requirements=['REC-LIVE-NOTES'],description='Live notes2ms before step boundaries belong to preceding steps; recorded grid and replay'),
 'M-REC-003':dict(run=lambda c:live_record_placement(c,(1402000000,1702000000),(2,4)),requirements=['REC-LIVE-NOTES'],description='Live notes2ms after step boundaries belong to new steps; recorded grid and replay'),
 'M-REC-004':dict(run=lambda c:live_record_placement(c,(1400000000,1700000000),(1,3),boundary_witness=True),requirements=['REC-LIVE-NOTES'],description='Equal-deadline pulse/note uses current active step; transport-anchored independent MIDI witness, grid and disarmed replay'),
 'M-REC-001':dict(run=live_record_placement,requirements=['REC-LIVE-NOTES'],description='Queued keyboard notes land on independently planned steps under MIDI clock; exact recorded LEDs and disarmed replay MIDI'),
 'M-MEMORY-002':dict(run=memory_channel_isolation,requirements=['MEMORY-NAV','MEMORY-RECORD','REC-KEYBOARD-STEP'],description='Independent histories on two routed channels sharing a pattern; untouched channel navigation cannot alter either phrase'),
 'M-MEMORY-001':dict(run=memory_navigation,requirements=['MEMORY-NAV','MEMORY-RECORD','REC-KEYBOARD-STEP'],description='Held-step MIDI edits, visible memory counter, undo/redo bounds and history branching verified through exact musical output'),
 'M-CHANNEL-001':dict(run=channel_routing_isolation,requirements=['CH-SELECT','CH-DEVICE','CH-ASSIGN','CH-MUTE'],description='All16 independently routed MIDI channels across two ports; cumulative mute/unmute preserves other phrases and clock alignment'),
 'M-MUTE-001':dict(run=channel_mute_gestures,requirements=['CH-MUTE'],description='Below-threshold hold, long hold and K1 mute toggles; stopped/live silence, resumed phrase and releases'),
 'M-RANGE-002':dict(run=adjacent_channel_ranges,requirements=['CH-RANGE'],description='All63 adjacent channel ranges plus full64-step range: exact grid, complete MIDI loops and spacing'),
 'M-RANGE-001':dict(run=channel_long_hold,requirements=['CH-RANGE'],description='A lone long hold is inactive; a delayed end-step combination still selects the range with exact MIDI loop spacing'),
 'M-SCALE-003':dict(run=scale_stop_indicator,requirements=['SCALE-SELECT'],description='Applied scale stays brightly lit after transport stops'),
 'M-SCALE-001':dict(run=scale_edit_selection,requirements=['SCALE-SELECT', 'SCALE-EDIT'],description='Editing-only gestures, applying edited scales, global off and reentry through screen/grid/MIDI'),
 'M-SCALE-002':dict(run=scale_lock_lifetime,requirements=['LOCK-SCALE', 'OPT-SCALE-LIFETIME'],description='Channel hold on/off and independent global scale-lock persistence through emitted notes'),
 'M-MERGE-001':dict(run=trig_merge_sets,requirements=['MERGE-TRIG-ALL', 'MERGE-TRIG-SKIP', 'MERGE-TRIG-ONLY'],description='All/Skip/Only across two and three patterns; literal MIDI and rest spacing; silence without overlap'),
 'M-PAT-002':dict(run=all_pattern_slots,requirements=['PAT-SELECT', 'PAT-TRIG', 'PAT-NOTE-CELLS', 'CH-ASSIGN'],description='All16 pattern slots retain independent grid edits and produce expected assigned-channel MIDI'),
 'M-TIM-004':dict(run=live_clock_handoff,requirements=['CLOCK-LIVE-HANDOFF-001'],description='Switch both clock-source directions with a note pending; preserve release timing and selected transport semantics'),
 'M-TIM-003':dict(run=midi_clock_transport,requirements=['CLOCK-MIDI-TRANSPORT-001'],description='Native menu selects MIDI clock; physical MIDI starts/stops playback at100BPM; return to internal clock'),
 'M-TIM-002':dict(run=restart_phase_edges,requirements=['CLOCK-PHASE-EDGE-001'],description='Restart around96PPQN boundaries; preserve full MIDI durations at five start phases'),
 'M-TIM-001':dict(run=phrase_timing,requirements=['CLOCK-PHRASE-001'],description='Restart edited phrase; verify every onset and duration through20 complete phrases at90BPM'),
 'M-MOD-003':dict(run=held_macro_rebind,requirements=['MOD-HELD-001'],description='Rebind an already-held nonzero macro; MIDI must immediately reflect its current value without a new source event'),
 'M-MOD-001':dict(run=macro_route_clear,requirements=['MOD-ROUTE-001'],description='Route macro through native Matrix menu; assert affected MIDI pitches and restoration after clearing depth'),
 'M-MOD-002':dict(run=pulse_lfo,requirements=['MOD-LFO-001'],description='Configure a clocked4-beat pulse LFO through native menus and verify two complete modulation cycles of MIDI pitches'),
 'M-SAVE-001':dict(run=autosave_restart,requirements=['PERSIST-AUTO-001'],description='Create notes through the grid; idle autosave; boot a fresh native process from saved data and verify restored LEDs and MIDI'),
 'M-MIDI-001':dict(run=lambda c:wrapped_length(c,same_pitch=True),requirements=['MIDI-RELEASE-001'],description='Repeated pitch at wrapped duration boundary emits balanced note releases and drains after stop'),
 'M-LEN-003':dict(run=wrapped_length,requirements=['PAT-LENGTH-003','PAT-DURATION'],description='A length crossing step64 ends at the next trig on step1; verify complete64-step MIDI loops and LEDs'),
 'M-LEN-002':dict(run=restore_length,requirements=['PAT-LENGTH-002','PAT-DURATION'],description='Delete and reinsert an interrupting trig; MIDI duration and grid restore the authored length'),
 'M-PAT-001':dict(run=four_notes,requirements=['PAT-EDIT-001'],description='Create four notes; edit through grid; verify screen, LEDs and complete MIDI phrases'),
 'M-LEN-001':dict(run=next_trig_cutoff,requirements=['PAT-LENGTH-001','PAT-DURATION'],description='A later trig cuts off preceding MIDI duration, matching manual and grid')}
