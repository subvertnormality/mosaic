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
    pulses(49)
    def new_notes():return [m for m in c.snapshot()['midi'] if m['index']>before and m['bytes'][0]==144 and m['bytes'][2]>0]
    assert not new_notes(),'Clock pulses alone started playback'
    inject(250)
    if c.clock_mode=='controlled-experimental':c.elapse(0)
    assert not new_notes(),'Transport started before the next MIDI clock pulse'
    pulses(60);inject(252)
    c.wait(lambda s:not s['midi_capture']['outstanding'])
    state=c.snapshot();notes=[m for m in state['midi'] if m['index']>before and m['bytes'][0]==144 and m['bytes'][2]>0]
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

CASES={
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
 'M-LEN-003':dict(run=wrapped_length,requirements=['PAT-LENGTH-003'],description='A length crossing step64 ends at the next trig on step1; verify complete64-step MIDI loops and LEDs'),
 'M-LEN-002':dict(run=restore_length,requirements=['PAT-LENGTH-002'],description='Delete and reinsert an interrupting trig; MIDI duration and grid restore the authored length'),
 'M-PAT-001':dict(run=four_notes,requirements=['PAT-EDIT-001'],description='Create four notes; edit through grid; verify screen, LEDs and complete MIDI phrases'),
 'M-LEN-001':dict(run=next_trig_cutoff,requirements=['PAT-LENGTH-001'],description='A later trig cuts off preceding MIDI duration, matching manual and grid')}
