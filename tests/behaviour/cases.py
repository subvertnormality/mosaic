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

CASES={
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
