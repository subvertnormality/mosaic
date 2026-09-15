"""Elektron program changes (README MAN "Elektron Program Changes" / channel).

A seeded session supplies the repository's Digitakt device configuration next to
the emulator test device; the shared test seed is not changed, so device-picker
positions in every other case stay the same.
"""
import base64,shutil
from pathlib import Path
from driver import Driver,REPO

def program_changes(state,marker,ports=(1,2)):
    return [(m['port'],m['bytes']) for m in state['midi'] if m['index']>marker and m['port'] in ports and m['bytes'][0]&240==192]

def pick_device(e,name):
    from frame_oracle import render
    expected=render([(10,35,15,name)])
    indices=[(y*128+x)*4+k for y in range(27,37) for x in range(10,58) for k in range(3)] # name column only
    def visible(state):
        pixels=base64.b64decode(state['frame']['pixels_base64'])
        return all(pixels[i]==expected[i] for i in indices)
    for _ in range(40):
        if visible(e.snapshot()):break
        e.enc(3,1)
    else:raise AssertionError('Device not visible in picker: '+name)
    e.key(3);e.results.append(dict(kind='device-picker-frame',label=name,matched=True))

def set_mosaic_number(e,label,delta,shown):
    from cases import menu_label,menu_option_row
    from frame_oracle import selected_line
    e.key(1);e.enc(1,4);e.key(3);menu_label(e,'LEVELS >')
    position=next(i for i,value in enumerate(e.snapshot()['diagnostics']['parameter_roots']) if value['id']=='mosaic')
    e.enc(2,position);e.key(3);e.enc(2,-60)
    for _ in range(40):
        if selected_line(e.snapshot(),label):break
        e.enc(2,1)
    else:raise AssertionError('Required Mosaic option not reached: '+label)
    e.enc(3,delta);menu_option_row(e,label,shown)
    e.results.append(dict(kind='mosaic-number-input',label=label,value=shown))
    e.key(2);e.enc(2,-60);menu_label(e,'LEVELS >');e.key(2);e.key(1)

STEP_SECONDS=1/6 # default tempo: one sequencer step

def transition_checks(e,state,marker,slots_seen):
    """Manual oracle: Play names the playing slot; each change is announced once, ahead of it."""
    controlled=e.clock_mode=='controlled-experimental'
    field='logical_ns' if controlled else 'monotonic_ns'
    lead=STEP_SECONDS/2 # a receiver that queues pattern changes needs them before the boundary
    rows=[m for m in state['midi'] if m['index']>marker and m['port']==1 and (m['bytes'][0]&240==192 or (m['bytes'][0]==144 and m['bytes'][2]>0))]
    events=[(m[field],'pc',m['bytes'][1]+1) if m['bytes'][0]&240==192 else (m[field],'slot',1 if m['bytes'][1]<72 else 2) for m in rows]
    first=next(i for i,row in enumerate(events) if row[1]=='slot')
    before=[row for row in events[:first] if row[1]=='pc']
    assert before and before[-1][2]==events[first][2],('Play must name the playing slot last',events[:first+1])
    boundaries=[];current=events[first][2];previous_time=events[first][0]
    pending=[]
    for time,kind,value in events[first+1:]:
        if kind=='pc':pending.append((time,value));continue
        if value==current:continue
        assert len(pending)==1 and pending[0][1]==value,('One program change naming the incoming slot',value,pending)
        assert (time-pending[0][0])/1e9>=lead,('Program change not ahead of the slot boundary',(time-pending[0][0])/1e9)
        boundaries.append(dict(slot=value,lead_seconds=(time-pending[0][0])/1e9));current=value;pending=[]
    assert len(boundaries)>=slots_seen,('Too few song transitions observed',boundaries)
    return boundaries

def elektron_program_changes(c,length=4,settings=True):
    from cases import set_mosaic_options
    seed=c.out/'elektron-seed';(seed/'config').mkdir(parents=True)
    shutil.copy(REPO/'tests/behaviour/config/emu-midi.json',seed/'config/emu-midi.json')
    shutil.copy(REPO/'lib/config/elektron_digitakt.json',seed/'config/elektron_digitakt.json')
    # The standard session proves the ordinary seed boots, then hands over to
    # the seeded session (an unused session has no action trace to verify).
    c.configure();c.finish()
    out=c.out/'elektron';out.mkdir()
    e=Driver(out,project_seed=seed,**c.launch_options)
    try:
        e.configure();pick_device(e,'Digitakt')
        # Song slot 1 of the given global length, copied to slot 2 and raised an octave there.
        e.tap(6,8);e.tap(2,7)
        for _ in range(length-1):e.tap(8,7)
        e.hold_tap((1,1),(2,1));e.tap(2,1);e.tap(3,8);e.tap(11,8);e.tap(6,8);e.tap(1,1)
        def run(seconds):
            marker=e.snapshot()['midi_count'];e.tap(1,8);e.elapse(seconds);e.tap(1,8)
            state=e.wait(lambda s:not s['midi_capture']['outstanding'])
            return state,marker
        if settings:
            # Default Off: Play and slot selection send no program change.
            state,marker=run(1.2);assert program_changes(state,marker)==[],program_changes(state,marker)
            marker=e.snapshot()['midi_count'];e.tap(2,1);e.tap(1,1);e.elapse(.2)
            assert program_changes(e.snapshot(),marker)==[]
            e.results.append(dict(kind='elektron-program-change',stage='default-off',sent=[],passed=True))
        set_mosaic_options(e,[('Elektron program changes',True)])
        if settings:
            # Stopped slot selection mirrors the slot on default channel 10 (status 201).
            marker=e.snapshot()['midi_count'];e.tap(2,1);e.elapse(.2);e.tap(1,1);e.elapse(.2)
            sent=program_changes(e.snapshot(),marker)
            assert sent==[(1,[201,1]),(1,[201,0])],sent
            e.results.append(dict(kind='elektron-program-change',stage='stopped-selection',sent=sent,passed=True))
        state,marker=run(4*length*STEP_SECONDS+.1)
        assert all(b[0]==201 for p,b in program_changes(state,marker)),program_changes(state,marker)
        boundaries=transition_checks(e,state,marker,3)
        e.results.append(dict(kind='elektron-program-change',stage='playing-transitions',global_length=length,boundaries=boundaries,passed=True))
        if settings:
            # The channel setting selects the program-change channel (1 -> status 192).
            set_mosaic_number(e,'Elektron p.change channel',-9,'1')
            marker=e.snapshot()['midi_count'];e.tap(2,1);e.elapse(.2)
            sent=program_changes(e.snapshot(),marker)
            assert sent==[(1,[192,1])],sent
            e.results.append(dict(kind='elektron-program-change',stage='channel-1',sent=sent,passed=True))
    finally:e.finish()
    c.results.append(dict(kind='elektron-program-change-session',nested=str(out),global_length=length,passed=True))
