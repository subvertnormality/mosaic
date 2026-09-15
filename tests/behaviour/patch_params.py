"""Documented stored MIDI patch parameters, tested through native controls."""
import json
from frame_oracle import selected_line
def open_patch_control(c,configured=False,setup=True):
    from cases import menu_label,menu_value
    if setup:
        c.configure()
        if configured:c.enc(3,1);c.key(3)
    c.key(1);c.enc(1,4);c.key(3);menu_label(c,'LEVELS >')
    roots=c.snapshot()['diagnostics']['parameter_roots']
    position=next(i for i,row in enumerate(roots) if row['id']=='midi_device_params_group_channel_1')
    c.enc(2,position);c.key(3)
    label='Control 1' if configured else 'CC 1'
    for _ in range(180):
        if selected_line(c.snapshot(),label):break
        c.enc(2,1)
    else:raise AssertionError('Configured patch control not reachable: '+label)
    menu_label(c,label)
    return label
def turn(c,steps):
    assert -63<=steps<=63 and steps
    c.elapse(.05) # Beyond the official native encoder acceleration window.
    c.action(type='enc',n=3,delta=2*steps)
    c.elapse(.03)
def patch_boundaries(c,configured=False):
    from cases import menu_value
    open_patch_control(c,configured)
    menu_value(c,'X') # Documented -1 sentinel, including configured devices.
    before=c.snapshot()['midi_count'];expected=[];value=-1
    for delta in (-1,1,1,62,1,62,1,1,-63,-63,-2,-1):
        wanted=max(-1,min(127,value+delta));turn(c,delta)
        if wanted!=value and wanted!=-1:expected.append((1,[176,1,wanted]))
        value=wanted;menu_value(c,'X' if value==-1 else str(value))
        actual=[(e['port'],e['bytes']) for e in c.snapshot()['midi'] if e['index']>before]
        assert actual==expected,dict(expected=expected,actual=actual)
    c.results.append(dict(kind='stored-patch-sentinel-boundaries',configured=configured,values=[-1,0,1,63,64,126,127],clamped_attempts=True,expected=expected,passed=True))
def patch_play_recall(c,repetitions=1):
    from cases import menu_value
    open_patch_control(c);menu_value(c,'X');turn(c,63);turn(c,1);menu_value(c,'63')
    c.key(1);windows=[]
    for _ in range(repetitions):
        before=c.snapshot()['midi_count']
        c.playback([(1,[144,n,v]) for n,v in ((60,127),(62,117),(64,107),(65,97))],cycles=2)
        windows.append((before,c.snapshot()['midi_count']))
    c.finish()
    try:
        events=[json.loads(line) for line in (c.out/'native/native-events.jsonl').read_text().splitlines()]
        midi=[e for e in events if e.get('kind') in (3,11)]
        assert [e['sequence'] for e in midi]==list(range(1,len(midi)+1))
        for before,after in windows:
            window=midi[before:after];cc=[e for e in window if e['bytes'][0]&240==176]
            actual=[(e['port'],e['bytes']) for e in cc]
            c.results.append(dict(kind='stored-unmapped-patch-play-recall',actual=actual,expected=[(1,[176,1,63])]))
            assert actual==[(1,[176,1,63])],'Play did not recall exactly the stored unassigned CC parameter'
            first_note=next(e for e in window if e['bytes'][0]&240==144 and e['bytes'][2]>0)
            assert cc[0]['sequence']<first_note['sequence'],'Patch recall followed the first note'
            c.results.append(dict(kind='stored-unmapped-patch-play-recall-complete',passed=True))
    finally:(c.out/'results.json').write_text(json.dumps(c.results,indent=2)+'\n')

def patch_muted_recall(c):
    from cases import menu_value
    open_patch_control(c);turn(c,63);turn(c,1);menu_value(c,'63');c.key(1)
    c.action(type='grid',x=1,y=1,state=1)
    try:c.elapse(1.1)
    finally:c.action(type='grid',x=1,y=1,state=0)
    c.led_values([(1,1)],[7])
    before=c.snapshot()['midi_count'];c.tap(1,8);c.elapse(1.5);c.tap(1,8)
    state=c.snapshot();after=state['midi_count']
    assert not state['midi_capture']['outstanding']
    c.finish()
    try:
        events=[json.loads(line) for line in (c.out/'native/native-events.jsonl').read_text().splitlines()]
        midi=[e for e in events if e.get('kind') in (3,11)]
        assert [e['sequence'] for e in midi]==list(range(1,len(midi)+1))
        window=midi[before:after]
        cc=[(e['port'],e['bytes']) for e in window if e['bytes'][0]&240==176]
        notes=[e for e in window if e['bytes'][0]&240==144 and e['bytes'][2]>0]
        assert cc==[(1,[176,1,63])],cc
        assert not notes,notes
        c.results.append(dict(kind='muted-stored-patch-recall',seconds=1.5,cc=cc,note_ons=0,passed=True))
    finally:(c.out/'results.json').write_text(json.dumps(c.results,indent=2)+'\n')

def patch_nrpn_bytes(c):
    from cases import menu_value,menu_label
    open_patch_control(c,True)
    for _ in range(180):
        if selected_line(c.snapshot(),'NRPN14'):break
        c.enc(2,1)
    else:raise AssertionError('NRPN14 control not reachable')
    menu_label(c,'NRPN14');menu_value(c,'X')
    before=c.snapshot()['midi_count'];turn(c,1);menu_value(c,'126')
    actual=[(e['port'],e['bytes']) for e in c.snapshot()['midi'] if e['index']>before]
    expected=[(1,[176,99,4]),(1,[176,98,5]),(1,[176,6,0]),(1,[176,38,126])]
    c.results.append(dict(kind='nrpn-native-byte-regression',expected=expected,actual=actual))
    assert actual==expected,dict(expected=expected,actual=actual)

def patch_restart(c,off=False):
    from cases import menu_value
    from driver import Driver,digest
    open_patch_control(c);turn(c,63);turn(c,1);menu_value(c,'63')
    if off:turn(c,-63);turn(c,-1);menu_value(c,'X')
    c.key(1);c.elapse(59);c.elapse(2)
    files=[c.data_directory/'autosave.ptn',c.data_directory/'autosave.pset']
    c.wait(lambda _:all(p.is_file() and p.stat().st_size for p in files),timeout=3)
    c.results.append(dict(kind='patch-autosave',files=[dict(name=p.name,sha256=digest(p)) for p in files]))
    c.finish();out=c.out/'reloaded';out.mkdir()
    loaded=Driver(out,project_seed=c.data_directory,**c.launch_options)
    try:
        boot_end=loaded.snapshot()['midi_count']
        open_patch_control(loaded,setup=False);menu_value(loaded,'X' if off else '63');loaded.key(1)
        before=loaded.snapshot()['midi_count']
        loaded.playback([(1,[144,n,v]) for n,v in ((60,127),(62,117),(64,107),(65,97))],cycles=2)
        after=loaded.snapshot()['midi_count']
        loaded.finish()
        events=[json.loads(line) for line in (out/'native/native-events.jsonl').read_text().splitlines()]
        midi=[e for e in events if e.get('kind') in (3,11)]
        assert [e['sequence'] for e in midi]==list(range(1,len(midi)+1))
        expected=[] if off else [(1,[176,1,63])]
        for label,window in [('cold-load',midi[:boot_end]),('play-after-load',midi[before:after])]:
            actual=[(e['port'],e['bytes']) for e in window if e['bytes'][0]&240==176]
            loaded.results.append(dict(kind='stored-patch-'+label,off=off,expected=expected,actual=actual))
            assert actual==expected,dict(window=label,expected=expected,actual=actual)
    finally:
        loaded.finish();(out/'results.json').write_text(json.dumps(loaded.results,indent=2)+'\n')

def patch_sparse_range(c,high=False):
    from cases import menu_label,menu_value
    open_patch_control(c,True);label='SparseHigh' if high else 'SparseLow';cc=3 if high else 2
    for _ in range(180):
        if selected_line(c.snapshot(),label):break
        c.enc(2,1)
    else:raise AssertionError('Sparse control not reachable: '+label)
    menu_label(c,label);menu_value(c,'X');before=c.snapshot()['midi_count'];expected=[]
    # Enumerate every active value, with saturation and both Off transitions.
    direction=-1 if high else 1
    turn(c,-direction);menu_value(c,'X')
    for value in (range(127,99,-1) if high else range(100,128)):
        turn(c,direction);menu_value(c,str(value));expected.append((1,[176,cc,value]))
        actual=[(e['port'],e['bytes']) for e in c.snapshot()['midi'] if e['index']>before]
        assert actual==expected,dict(expected=expected,actual=actual)
    turn(c,direction);menu_value(c,'100' if high else '127')
    # Pinned native Control 1/28 endpoint callback; proven independently without Mosaic.
    expected.append((1,[176,cc,100 if high else 127]))
    turn(c,-direction*63);menu_value(c,'X');after=c.snapshot()['midi_count'];c.finish()
    try:
        events=[json.loads(line) for line in (c.out/'native/native-events.jsonl').read_text().splitlines()]
        midi=[e for e in events if e.get('kind') in (3,11)]
        assert [e['sequence'] for e in midi]==list(range(1,len(midi)+1))
        actual=[(e['port'],e['bytes']) for e in midi[before:after]]
        assert actual==expected,dict(expected=expected,actual=actual)
        c.results.append(dict(kind='sparse-CC-domain',range=[100,127],off=200 if high else -1,values=28,expected=expected,actual=actual,passed=True))
    finally:(c.out/'results.json').write_text(json.dumps(c.results,indent=2)+'\n')

def patch_lock_precedence(c,lock_value=99):
    from cases import menu_value,assign_trig_parameter
    open_patch_control(c);turn(c,63);turn(c,1);menu_value(c,'63');c.key(1)
    c.enc(1,-3);assign_trig_parameter(c,'CC 1')
    c.action(type='grid',x=1,y=4,state=1)
    try:
        if lock_value==63:
            c.enc(3,1);c.enc(3,-1)
        else:
            for _ in range(abs(lock_value-63)):c.enc(3,1 if lock_value>63 else -1)
    finally:c.action(type='grid',x=1,y=4,state=0)
    before=c.snapshot()['midi_count']
    c.playback([(1,[144,n,v]) for n,v in ((60,127),(62,117),(64,107),(65,97))],cycles=2)
    after=c.snapshot()['midi_count']
    c.key(1);menu_value(c,'63');c.finish()
    try:
        events=[json.loads(line) for line in (c.out/'native/native-events.jsonl').read_text().splitlines()]
        midi=[e for e in events if e.get('kind') in (3,11)]
        assert [e['sequence'] for e in midi]==list(range(1,len(midi)+1))
        window=midi[before:after]
        first_note=next(i for i,e in enumerate(window) if e['bytes'][0]&240==144 and e['bytes'][2]>0)
        prior=[(e['port'],e['bytes']) for e in window[:first_note] if e['bytes'][0]&240==176]
        expected=[(1,[176,1,63])]+([] if lock_value==-1 else [(1,[176,1,lock_value])])
        c.results.append(dict(kind='stored-patch-first-step-lock-order',expected=expected,actual=prior))
        assert prior==expected,dict(expected=expected,actual=prior)
        pending=[];ordinal=0
        for event in window:
            packet=event['bytes'];kind=packet[0]&240
            if kind==176:pending.append((event['port'],packet))
            elif kind==144 and packet[2]>0:
                wanted=expected if ordinal==0 else ([] if ordinal%4==0 and lock_value==-1 else [(1,[176,1,lock_value if ordinal%4==0 else 63])])
                assert pending==wanted,dict(note_ordinal=ordinal,expected=wanted,actual=pending)
                pending=[];ordinal+=1
        assert ordinal>=9 and not pending,dict(note_count=ordinal,trailing_cc=pending)
        c.results.append(dict(kind='patch-lock-complete-phrase-order',lock_value=lock_value,notes=ordinal,passed=True))
    finally:(c.out/'results.json').write_text(json.dumps(c.results,indent=2)+'\n')

def patch_adjacent_locks(c,start=1):
    from cases import menu_value,assign_trig_parameter
    open_patch_control(c);turn(c,63);turn(c,1);menu_value(c,'63');c.key(1)
    c.enc(1,-3);assign_trig_parameter(c,'CC 1')
    for step in range(1,5):
        c.action(type='grid',x=step,y=4,state=1)
        try:
            # The native lock calculator retains its prior edit. Clamp to Off
            # first, then enter the independently specified absolute value.
            c.elapse(.05);c.action(type='enc',n=3,delta=-126)
            c.enc(3,64+step)
        finally:c.action(type='grid',x=step,y=4,state=0)
    if start!=1:c.hold_tap((start,4),(4,4))
    before=c.snapshot()['midi_count']
    phrase=[(1,[144,n,v]) for n,v in ((60,127),(62,117),(64,107),(65,97))][start-1:]
    c.playback(phrase,cycles=3)
    after=c.snapshot()['midi_count'];c.key(1);menu_value(c,'63');c.finish()
    try:
        events=[json.loads(line) for line in (c.out/'native/native-events.jsonl').read_text().splitlines()]
        midi=[e for e in events if e.get('kind') in (3,11)]
        assert [e['sequence'] for e in midi]==list(range(1,len(midi)+1))
        pending=[];ordinal=0;notes=[]
        for e in midi[before:after]:
            kind=e['bytes'][0]&240
            if kind==176:pending.append((e['port'],e['bytes']))
            elif kind==144 and e['bytes'][2]>0:
                step=start+ordinal%len(phrase)
                wanted=([(1,[176,1,63])] if ordinal==0 else [])+[(1,[176,1,63+step])]
                assert pending==wanted,dict(ordinal=ordinal,step=step,expected=wanted,actual=pending)
                pending=[];notes.append(e);ordinal+=1
        assert ordinal>=3*len(phrase)+1 and not pending
        field='logical_ns' if c.clock_mode!='real-time' else 'monotonic_ns'
        origin=notes[0][field];tolerance=2e-9 if c.clock_mode!='real-time' else .01
        for i,note in enumerate(notes):
            elapsed=(note[field]-origin)/1e9
            assert abs(elapsed-i/6)<=tolerance,dict(ordinal=i,elapsed=elapsed,expected=i/6)
        c.results.append(dict(kind='adjacent-locks-at-musical-onset',start=start,end=4,notes=ordinal,cc_values=list(range(63+start,68)),stored_value=63,passed=True))
    finally:(c.out/'results.json').write_text(json.dumps(c.results,indent=2)+'\n')

def patch_slide_timing(c,wrap=False,target=96,fractional=False,swing=None,shuffle=False,off_middle=False,stop_restarts=0,step_local=False,global_roundtrip=False,default_off=False):
    lock_step=2 if swing is not None or shuffle else 3
    assert sum((fractional,swing is not None,shuffle))<=1
    from cases import menu_value,assign_trig_parameter,set_mosaic_options
    if wrap:
        c.configure();set_mosaic_options(c,[('Wrap param slides',True)])
    open_patch_control(c,configured=default_off,setup=not wrap)
    if default_off:
        for _ in range(180):
            if selected_line(c.snapshot(),'CCdefault'):break
            c.enc(2,1)
        else:raise AssertionError('Default-Off CC control unreachable')
    turn(c,63);turn(c,1);menu_value(c,'63');c.key(1)
    c.enc(1,-3);assign_trig_parameter(c,'CCdefault' if default_off else 'CC 1')
    locks=[(1,24),(lock_step,target)]+([(2,-1)] if off_middle else [])+([(4,48)] if step_local else [])
    for step,value in locks:
        c.action(type='grid',x=step,y=4,state=1)
        try:
            c.elapse(.05);c.action(type='enc',n=3,delta=-126);c.enc(3,value+1)
        finally:c.action(type='grid',x=step,y=4,state=0)
    if step_local:
        # Documented held-step K3: only source step1 slides; global remains off.
        c.action(type='grid',x=1,y=4,state=1)
        try:c.key(3)
        finally:c.action(type='grid',x=1,y=4,state=0)
    else:c.key(3) # Documented global slide toggle for the selected parameter.
    if fractional:
        # Parameter page 2 -> clocks page 4; /1 (index13) -> x5.3 (index5).
        from frame_oracle import header,matches
        c.enc(1,2);c.wait(lambda state:matches(state,header('Ch. 1 Clocks',selected=4)))
        c.enc(3,8);c.key(3);c.enc(1,-2)
    if swing is not None:
        from frame_oracle import header,matches
        c.enc(1,2);c.wait(lambda state:matches(state,header('Ch. 1 Clocks',selected=4)))
        c.enc(2,1);c.enc(3,1);c.key(3) # Local Swing, not inherited X.
        c.enc(2,1);c.enc(3,swing+51);c.key(3);c.enc(1,-2)
    if shuffle:
        from frame_oracle import header,matches
        c.enc(1,2);c.wait(lambda state:matches(state,header('Ch. 1 Clocks',selected=4)))
        c.enc(2,1);c.enc(3,2);c.key(3) # Local Shuffle.
        c.enc(2,1);c.enc(3,3);c.key(3) # Heavy feel.
        c.enc(2,1);c.enc(3,4);c.key(3) # Basis6.
        c.enc(2,1);c.enc(3,100);c.key(3);c.enc(1,-2)
    global_window=None
    if global_roundtrip:
        assert step_local and not wrap
        c.key(3) # Enable global slides alongside the existing local flag.
        global_before=c.snapshot()['midi_count']
        c.playback([(1,[144,n,v]) for n,v in ((60,127),(62,117),(64,107),(65,97))],cycles=2)
        global_window=(global_before,c.snapshot()['midi_count'])
        c.key(3) # Disable global; the original local flag must survive.
    for attempt in range(stop_restarts):
        initial=c.snapshot()['midi_count']
        c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
        def intermediate(state):
            return [e for e in state['midi'] if e['index']>initial and e['bytes'][:2]==[176,1] and 24<e['bytes'][2]<60]
        state=c.wait(lambda state:bool(intermediate(state)),timeout=2)
        seen=intermediate(state)
        c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
        # A short observation drain excludes already queued pre-stop delivery.
        c.elapse(.03);stopped=c.snapshot()['midi_count'];c.elapse(1)
        state=c.snapshot()
        unwanted=[e for e in state['midi'] if e['index']>stopped and
                  (e['bytes'][0]&240==176 or (e['bytes'][0]&240==144 and e['bytes'][2]>0))]
        assert not unwanted,dict(stale_after_stop=unwanted)
        assert not state['midi_capture']['outstanding']
        c.results.append(dict(kind='active-slide-stop',attempt=attempt,intermediate_values=[e['bytes'][2] for e in seen],quiet_seconds=1,delivery_drain_seconds=.03,passed=True))
    before=c.snapshot()['midi_count']
    c.playback([(1,[144,n,v]) for n,v in ((60,127),(62,117),(64,107),(65,97))],cycles=2)
    after=c.snapshot()['midi_count'];c.key(1);menu_value(c,'63');c.finish()
    try:
        events=[json.loads(line) for line in (c.out/'native/native-events.jsonl').read_text().splitlines()]
        midi=[e for e in events if e.get('kind') in (3,11)]
        assert [e['sequence'] for e in midi]==list(range(1,len(midi)+1))
        window=midi[before:after];notes=[e for e in window if e['bytes'][0]&240==144 and e['bytes'][2]>0]
        field='logical_ns' if c.clock_mode!='real-time' else 'monotonic_ns'
        timing_tolerance=2e-9 if c.clock_mode!='real-time' else .01
        # At90BPM the96ppqn lattice advances144 pulses/sec. x5.3 has
        # 240/53 pulses per sixteenth; nearest pulse with the declared initial
        # half-pulse seed and constructor preview fix the expected onsets independently of output.
        from fractions import Fraction
        from fractional_deadlines import quantised_pulse
        planned=[quantised_pulse(Fraction(240,53),i)/144 if fractional else i/6 for i in range(len(notes))]
        if swing is not None:
            # Signed50 at /1 gives alternating36/12 pulses (or12/36).
            # Four-step range has no odd-length swing reset.
            long_first=swing>0
            planned=[(48*(i//2)+(36 if long_first else 12)*(i%2))/144 for i in range(len(notes))]
        if shuffle:
            # Heavy basis6 at100%: three16-pulse gaps then one48-pulse gap.
            # The source slide spans16 pulses; its wrapped return spans80.
            planned=[(96*(i//4)+(0,16,32,48)[i%4])/144 for i in range(len(notes))]
        origin=notes[0][field]
        for index,note in enumerate(notes):
            assert abs((note[field]-origin)/1e9-planned[index])<=timing_tolerance,dict(note=index,expected=planned[index],actual=(note[field]-origin)/1e9)
        if global_window:
            prior=midi[global_window[0]:global_window[1]]
            prior_notes=[e for e in prior if e['bytes'][0]==144 and e['bytes'][2]>0]
            global_checks=[]
            for cycle in range(2):
                source,destination=prior_notes[cycle*4+2:cycle*4+4]
                ramp=[e for e in prior if source['sequence']<e['sequence']<destination['sequence'] and e['bytes'][:2]==[176,1]]
                assert len(ramp)>=3,'Global toggle did not enable the later slide'
                for e in ramp:
                    elapsed=(e[field]-source[field])/1e9
                    ideal=96-48*max(0,min(1,elapsed/(1/6)))
                    assert e['port']==1 and abs(e['bytes'][2]-ideal)<=1+288*timing_tolerance
                assert ramp[-1]['bytes'][2]==48
                assert abs((ramp[-1][field]-destination[field])/1e9)<=timing_tolerance
                global_checks.append([e['bytes'][2] for e in ramp])
            c.results.append(dict(kind='local-global-slide-roundtrip',global_on_later_slides=global_checks,passed=True))
        checks=[]
        for cycle in range(2):
            first,last=notes[4*cycle],notes[4*cycle+lock_step-1]
            duration=(last[field]-first[field])/1e9
            expected_duration=planned[4*cycle+lock_step-1]-planned[4*cycle]
            assert abs(duration-expected_duration)<=timing_tolerance
            ramp=[e for e in window if first['sequence']<e['sequence']<last['sequence'] and e['bytes'][:2]==[176,1]]
            assert len(ramp)>=(2 if target==25 or fractional or swing is not None or shuffle else 3),'Slide produced no meaningful intermediate values'
            assert not any(e['bytes'][2]==24 for e in ramp), 'Slide re-emitted its initial lock after the note'
            for e in ramp:
                elapsed=(e[field]-first[field])/1e9
                ideal=24+(target-24)*max(0,min(1,elapsed/expected_duration))
                error=abs(e['bytes'][2]-ideal)
                checks.append(dict(cycle=cycle,elapsed=elapsed,value=e['bytes'][2],ideal=ideal,error=error))
                assert error<=1+abs(target-24)/expected_duration*timing_tolerance,checks[-1]
            assert ramp[-1]['bytes'][2]==target,'Destination lock did not arrive before its note'
            assert abs((ramp[-1][field]-last[field])/1e9)<=timing_tolerance,'Explicit destination lock was suppressed after early rounding'
            tail=[e['bytes'][2] for e in window if last['sequence']<e['sequence']<notes[4*cycle+lock_step]['sequence'] and e['bytes'][:2]==[176,1]]
            if not wrap:
                assert tail==([48] if step_local else [63]),dict(stale_slide_after_destination=tail)
            else:
                destination=notes[4*cycle+4]
                descending=[e for e in window if last['sequence']<e['sequence']<destination['sequence'] and e['bytes'][:2]==[176,1]]
                assert len(descending)>=(2 if fractional else 3),'Wrapped slide produced no meaningful intermediate values'
                expected_duration=planned[4*cycle+4]-planned[4*cycle+lock_step-1]
                assert abs((destination[field]-last[field])/1e9-expected_duration)<=timing_tolerance
                for e in descending:
                    elapsed=(e[field]-last[field])/1e9
                    ideal=target-(target-24)*max(0,min(1,elapsed/expected_duration))
                    error=abs(e['bytes'][2]-ideal)
                    checks.append(dict(cycle=cycle,wrapped=True,elapsed=elapsed,value=e['bytes'][2],ideal=ideal,error=error))
                    assert error<=1+abs(target-24)/expected_duration*timing_tolerance,checks[-1]
                assert descending[-1]['bytes'][2]==24,'Wrapped destination not applied before its note'
        c.results.append(dict(kind='slide-musical-time',from_value=24,to_value=target,step_distance=lock_step-1,off_middle=off_middle,step_local=step_local,swing=swing,shuffle='Heavy6-100' if shuffle else None,clock_ratio='x5.3' if fractional else '/1',planned_onsets=planned,checks=checks,passed=True))
    finally:
        if 'checks' in locals():c.results.append(dict(kind='slide-timing-samples',samples=checks))
        (c.out/'results.json').write_text(json.dumps(c.results,indent=2)+'\n')


def patch_slide_live_division(c,type_switch=False,reset=False,repeated_edits=False):
    assert not (type_switch and reset)
    """Queued /3 -> /6 edit crosses an active slide at the pattern boundary."""
    import math
    from cases import menu_value,assign_trig_parameter,set_mosaic_options
    from frame_oracle import header,matches
    if reset:
        c.configure();set_mosaic_options(c,[('Song mode',True),('Reset on pattern repeat',True),('Wrap param slides',True)])
    open_patch_control(c,setup=not reset);turn(c,63);turn(c,1);menu_value(c,'63');c.key(1)
    c.enc(1,-3);assign_trig_parameter(c,'CC 1')
    for step,value in [(4 if reset else 1,24),(3,96)]:
        c.action(type='grid',x=step,y=4,state=1)
        try:
            c.elapse(.05);c.action(type='enc',n=3,delta=-126);c.enc(3,value+1)
        finally:c.action(type='grid',x=step,y=4,state=0)
    c.key(3)
    c.enc(1,2);c.wait(lambda state:matches(state,header('Ch. 1 Clocks',selected=4)))
    c.enc(3,-4);c.key(3) # Initial /3 (index17), committed while stopped.
    if type_switch:
        # Store Heavy6 at100%, then return to Swing before playback.
        c.enc(2,1);c.enc(3,2);c.key(3)
        c.enc(2,1);c.enc(3,3);c.key(3)
        c.enc(2,1);c.enc(3,4);c.key(3)
        c.enc(2,1);c.enc(3,100);c.key(3)
        c.enc(2,-3);c.enc(3,-1);c.key(3)
    before=c.snapshot()['midi_count']
    c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
    c.enc(3,1 if type_switch else -4) # Queue Shuffle, or /3 index17 -> /6 index21.
    c.key(3)
    if repeated_edits:
        assert not type_switch and not reset
        # Several confirmed edits queue before the same global boundary.
        # /6 -> /4 -> /6 -> /4 -> /6: only final /6 governs future onsets.
        for delta in (1,-1,1,-1):
            c.enc(3,delta);c.key(3)
    import base64
    from frame_oracle import render
    label='Shuffle' if type_switch else '/6'
    xpos=70 if type_switch else 0
    expected_rate=render([(xpos,26,15,label)])
    pixels=[(y*128+x)*4+k for y in range(20,30) for x in range(xpos,128 if type_switch else 48) for k in range(3)]
    def rate_readback(state):
        frame=base64.b64decode(state['frame']['pixels_base64'])
        return all(frame[i]==expected_rate[i] for i in pixels)
    c.wait(rate_readback)
    c.results.append(dict(kind='clock-rate-readback',value=label,passed=True))
    def notes(state):
        return [e for e in state['midi'] if e['index']>before and e['bytes'][0]==144 and e['bytes'][2]>0]
    c.wait(lambda state:len(notes(state))>=(25 if reset else 23),timeout=15)
    c.elapse(.12)
    after=c.snapshot()['midi_count']
    c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
    c.wait(lambda state:not state['midi_capture']['outstanding']);c.finish()
    checks=[]
    try:
        all_events=[json.loads(line) for line in (c.out/'native/native-events.jsonl').read_text().splitlines()]
        events=[e for e in all_events if e.get('kind') in (3,11)][before:after]
        onsets=[e for e in events if e['bytes'][0]==144 and e['bytes'][2]>0]
        assert len(onsets)>=(25 if reset else 23)
        for i,note in enumerate(onsets):
            slot=(i-22)%4 if reset and i>=22 else i%4
            assert (note['port'],note['bytes'])==(1,[144,(60,62,64,65)[slot],(127,117,107,97)[slot]])
        controlled=c.clock_mode!='real-time';field='logical_ns' if controlled else 'monotonic_ns'
        start=onsets[0][field]
        # The default64-step global pattern commits queued controls at1536
        # pulses. Channel /3 starts steps1,2,3 at1440,1512,1584 before editing.
        # At1536 the remaining48 pulses stretch to96: destination becomes1632.
        effective_pulse=1536
        source_pulse=1368 if reset else 1440
        target_pulse=1824 if reset else (1568 if type_switch else 1632)
        source_index=19 if reset else 20
        target_index=24 if reset else 22
        tolerance=2e-9 if controlled else .01
        for index,note in enumerate(onsets):
            pulse=index*72 if index<=21 else (1536+(index-22)*144 if reset else target_pulse+(index-22)*(48 if type_switch else 144))
            assert abs((note[field]-start)/1e9-pulse/144)<=tolerance,dict(index=index,expected_pulse=pulse,actual=(note[field]-start)*144/1e9)
        ramp=[e for e in events if onsets[source_index]['sequence']<e['sequence']<onsets[target_index]['sequence'] and e['bytes'][:2]==[176,1]]
        assert len(ramp)>=4
        value_at_edit=80 if reset else 72
        old_duration=216 if reset else 144
        for event in ramp:
            pulse=(event[field]-start)*144/1e9
            ideal=24+72*(pulse-source_pulse)/old_duration if pulse<=effective_pulse else value_at_edit+(96-value_at_edit)*(pulse-effective_pulse)/(target_pulse-effective_pulse)
            error=abs(event['bytes'][2]-ideal)
            checks.append(dict(pulse=pulse,value=event['bytes'][2],ideal=ideal,error=error))
            assert error<=1+216*tolerance,checks[-1]
        assert ramp[-1]['bytes'][2]==96
        assert abs((ramp[-1][field]-onsets[target_index][field])/1e9)<=tolerance
        c.results.append(dict(kind='live-slide-rate-edit',type_switch=type_switch,reset=reset,repeated_edits=repeated_edits,edit_pulse=effective_pulse,source_pulse=source_pulse,target_pulse=target_pulse,checks=checks,passed=True))
    finally:
        c.results.append(dict(kind='live-slide-rate-samples',checks=checks))
        (c.out/'results.json').write_text(json.dumps(c.results,indent=2)+'\n')


def patch_slide_song_cutoff(c):
    from cases import menu_value,assign_trig_parameter,set_mosaic_options
    c.configure()
    set_mosaic_options(c,[('Song mode',True),('Reset on song seq change',False),('Reset on pattern repeat',False)])
    open_patch_control(c,setup=False);turn(c,63);turn(c,1);menu_value(c,'63');c.key(1)
    c.enc(1,-3);assign_trig_parameter(c,'CC 1')
    for step,value in [(1,24),(3,96)]:
        c.action(type='grid',x=step,y=4,state=1)
        try:
            c.elapse(.05);c.action(type='enc',n=3,delta=-126);c.enc(3,value+1)
        finally:c.action(type='grid',x=step,y=4,state=0)
    c.key(3);c.enc(1,2);c.enc(3,-4);c.key(3) # /3, 72pulses/step.
    c.tap(6,8);c.hold_tap((1,1),(2,1));c.led_values([(1,1),(2,1)],[15,7])
    c.tap(2,1);c.tap(3,8);c.tap(11,8);c.tap(6,8);c.tap(1,1)
    before=c.snapshot()['midi_count'];c.tap(1,8)
    def notes(state):return [e for e in state['midi'] if e['index']>before and e['bytes'][0]==144 and e['bytes'][2]>0]
    c.wait(lambda state:len(notes(state))>=24,timeout=15)
    c.led_values([(1,1),(2,1)],[7,15])
    after=c.snapshot()['midi_count'];c.tap(1,8)
    c.wait(lambda state:not state['midi_capture']['outstanding']);c.finish()
    try:
        raw=[json.loads(line) for line in (c.out/'native/native-events.jsonl').read_text().splitlines()]
        window=[e for e in raw if e.get('kind') in (3,11)][before:after]
        onsets=[e for e in window if e['bytes'][0]==144 and e['bytes'][2]>0]
        assert len(onsets)>=24
        field='logical_ns' if c.clock_mode!='real-time' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode!='real-time' else .01
        origin=onsets[0][field]
        for index,note in enumerate(onsets):
            pulse=index*72;epoch=pulse//1536;slot=index%4
            assert (note['port'],note['bytes'])==(1,[144,(60,62,64,65)[slot]+12*epoch,(127,117,107,97)[slot]])
            assert abs((note[field]-origin)/1e9-pulse/144)<=tolerance
        # Old pattern's step1 slide starts1440, would end1584. Pattern2
        # takes ownership at1536; its first note/lock is at1584 without reset.
        before_change=[e for e in window if e['bytes'][:2]==[176,1] and 1440/144<(e[field]-origin)/1e9<1536/144-tolerance]
        assert len(before_change)>=3,'Old slide was not active before transition'
        stale=[e for e in window if e['bytes'][:2]==[176,1] and 1536/144+tolerance<(e[field]-origin)/1e9<1584/144-tolerance]
        assert not stale,dict(stale_cross_song_slide=stale)
        new_lock=[e for e in window if e['bytes']==[176,1,96] and e['sequence']<onsets[22]['sequence'] and abs(e[field]-onsets[22][field])/1e9<=tolerance]
        assert len(new_lock)==1,'New pattern must apply its own explicit lock before its note'
        c.results.append(dict(kind='cross-song-slide-cutoff',boundary_pulse=1536,next_lock_pulse=1584,active_before=len(before_change),stale_after=0,passed=True))
    finally:(c.out/'results.json').write_text(json.dumps(c.results,indent=2)+'\n')

def patch_slide_trigless(c,enabled=True):
    from cases import menu_value,assign_trig_parameter,set_mosaic_options
    c.configure();set_mosaic_options(c,[('Trigless locks',enabled)])
    # Remove the destination note using the pattern trig page; keep its lock.
    c.tap(5,8);c.tap(3,4);c.tap(3,8)
    open_patch_control(c,setup=False);turn(c,63);turn(c,1);menu_value(c,'63');c.key(1)
    c.enc(1,-3);assign_trig_parameter(c,'CC 1')
    for step,value in [(1,24),(3,96)]:
        c.action(type='grid',x=step,y=4,state=1)
        try:
            c.elapse(.05);c.action(type='enc',n=3,delta=-126);c.enc(3,value+1)
        finally:c.action(type='grid',x=step,y=4,state=0)
    c.key(3)
    before=c.snapshot()['midi_count']
    c.playback([(1,[144,n,v]) for n,v in ((60,127),(62,117),(65,97))],cycles=2)
    after=c.snapshot()['midi_count'];c.key(1);menu_value(c,'63');c.finish()
    try:
        events=[json.loads(line) for line in (c.out/'native/native-events.jsonl').read_text().splitlines()]
        midi=[e for e in events if e.get('kind') in (3,11)]
        assert [e['sequence'] for e in midi]==list(range(1,len(midi)+1))
        window=midi[before:after]
        notes=[e for e in window if e['bytes'][0]&240==144 and e['bytes'][2]>0]
        field='logical_ns' if c.clock_mode!='real-time' else 'monotonic_ns'
        tol=2e-9 if c.clock_mode!='real-time' else .01
        origin=notes[0][field]
        for i,n in enumerate(notes):
            expected=(4*(i//3)+(0,1,3)[i%3])/6
            assert abs((n[field]-origin)/1e9-expected)<=tol,dict(note=i,expected=expected)
        checks=[]
        for cycle in range(2):
            start=notes[3*cycle];end=notes[3*cycle+3]
            cc=[e for e in window if start['sequence']<e['sequence']<end['sequence'] and e['bytes'][:2]==[176,1]]
            assert all(e['port']==1 for e in cc)
            if not enabled:
                # With no eligible destination, each active unlocked step (2,4)
                # recalls the stored patch; silent step3 sends nothing.
                assert [e['bytes'][2] for e in cc]==[63,63,24],cc
                for e,expected in zip(cc,(1/6,1/2,2/3)):
                    assert abs((e[field]-start[field])/1e9-expected)<=tol
            else:
                ramp=[e for e in cc if (e[field]-start[field])/1e9<.5-tol]
                assert len(ramp)>=3,ramp
                for e in ramp:
                    elapsed=(e[field]-start[field])/1e9
                    ideal=24+72*min(1,max(0,elapsed/(1/3)))
                    assert abs(e['bytes'][2]-ideal)<=1+216*tol,dict(elapsed=elapsed,value=e['bytes'][2],ideal=ideal)
                assert ramp[-1]['bytes'][2]==96
                assert abs((ramp[-1][field]-start[field])/1e9-1/3)<=tol
                assert [e['bytes'][2] for e in cc if e not in ramp]==[63,24],cc
            checks.append(dict(cycle=cycle,trigless=enabled,cc=[e['bytes'][2] for e in cc]))
        c.results.append(dict(kind='silent-destination-slide',trigless=enabled,checks=checks,passed=True))
    finally:(c.out/'results.json').write_text(json.dumps(c.results,indent=2)+'\n')

def patch_slide_live_destination(c,off=False,clear=False,reassign=False,clear_all=False,unassign=False):
    assert sum((off,clear,reassign,clear_all,unassign))<=1
    from cases import assign_trig_parameter,menu_value
    from frame_oracle import header,matches
    open_patch_control(c);turn(c,63);turn(c,1);menu_value(c,'63');c.key(1)
    c.enc(1,-3);assign_trig_parameter(c,'CC 1')
    for step,value in [(1,24),(3,96)]:
        c.action(type='grid',x=step,y=4,state=1)
        try:
            c.elapse(.05);c.action(type='enc',n=3,delta=-126);c.enc(3,value+1)
        finally:c.action(type='grid',x=step,y=4,state=0)
    c.key(3)
    c.enc(1,2);c.wait(lambda s:matches(s,header('Ch. 1 Clocks',selected=4)))
    c.enc(3,-8);c.key(3);c.enc(1,-2) # /6: one second per note at90BPM.
    before=c.snapshot()['midi_count']
    c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
    c.wait(lambda s:any(e['index']>before and e['bytes'][:2]==[176,1] and 24<e['bytes'][2]<40 for e in s['midi']))
    if clear_all:
        c.action(type='key',n=1,state=1);c.elapse(.3) # Native K1 shift hold, not menu tap.
        try:c.key(2)
        finally:c.action(type='key',n=1,state=0)
    elif reassign or unassign:
        from cases import parameter_list_label
        c.key(2)
        if unassign:
            c.elapse(.05);c.action(type='enc',n=3,delta=-126);c.elapse(.15)
            parameter_list_label(c,'None')
        else:c.enc(3,1);parameter_list_label(c,'CC 2')
        c.key(3);c.key(2)
    else:
        c.action(type='grid',x=3,y=4,state=1)
        try:
            if clear:c.key(2) # Documented held-step clear, while transport runs.
            elif off:
                c.elapse(.05);c.action(type='enc',n=3,delta=-126) # Saturate to Off.
            else:c.enc(3,-12) #96 ->84, authored while original slide is active.
        finally:c.action(type='grid',x=3,y=4,state=0)
    edit_done=c.snapshot()['midi_count']
    def notes(s):return [e for e in s['midi'] if e['index']>before and e['bytes'][0]==144 and e['bytes'][2]>0]
    c.wait(lambda s:len(notes(s))>=9,timeout=12)
    after=c.snapshot()['midi_count'];c.tap(1,8);c.wait(lambda s:not s['midi_capture']['outstanding'])
    c.key(1);menu_value(c,'63');c.finish()
    try:
        events=[json.loads(line) for line in (c.out/'native/native-events.jsonl').read_text().splitlines()]
        midi=[e for e in events if e.get('kind') in (3,11)]
        assert [e['sequence'] for e in midi]==list(range(1,len(midi)+1))
        window=midi[before:after];ns=[e for e in window if e['bytes'][0]==144 and e['bytes'][2]>0]
        field='logical_ns' if c.clock_mode!='real-time' else 'monotonic_ns';tol=2e-9 if c.clock_mode!='real-time' else .01
        for i,e in enumerate(ns):
            assert (e['port'],e['bytes'])==(1,[144,(60,62,64,65)[i%4],(127,117,107,97)[i%4]])
            assert abs((e[field]-ns[0][field])/1e9-i)<=tol
        assert ns[0]['sequence']<edit_done<ns[2]['sequence'],'Edit missed active-slide window'
        if reassign or unassign:
            confirmations=[e for e in events if e.get('kind')=='input' and e.get('type')==1 and e['args']==[3,1] and e['monotonic_ns']>ns[0]['monotonic_ns']]
            assert len(confirmations)==1,'Ambiguous parameter confirmation trace'
            confirmation=confirmations[0]['monotonic_ns']
            stale=[e for e in window if e['monotonic_ns']>confirmation and e['bytes'][:2]==[176,1]]
            assert not stale,dict(stale_old_parameter_after_confirmation=stale)
            if unassign:
                assert not [e for e in window if e['monotonic_ns']>confirmation and e['bytes'][0]&240==176]
                c.results.append(dict(kind='live-parameter-unassignment',silent_after_confirmation=True,notes_preserved=len(ns),passed=True))
                return
            # The confirmed replacement owns this slot at its next locked onset.
            dest=ns[2]
            first_new=[e for e in window if edit_done<e['sequence']<dest['sequence'] and e['bytes'][:2]==[176,2]]
            assert first_new and first_new[-1]['bytes']==[176,2,96],'Old slide suppressed the reassigned parameter destination'
            assert abs((first_new[-1][field]-dest[field])/1e9)<=tol
            following=[e for e in window if ns[4]['sequence']<e['sequence']<ns[8]['sequence'] and e['bytes'][0]&240==176]
            assert all(e['port']==1 and e['bytes'][1]==2 for e in following),'Old CC emitted in next cycle'
            ramp=[e for e in following if e['sequence']<ns[6]['sequence']]
            assert len(ramp)>=20 and ramp[-1]['bytes']==[176,2,96]
            for e in ramp:
                elapsed=(e[field]-ns[4][field])/1e9
                assert abs(e['bytes'][2]-(24+72*min(1,max(0,elapsed/2))))<=1+36*tol
            assert [e['bytes'] for e in following if e not in ramp]==[[176,2,24]]
            c.results.append(dict(kind='live-parameter-reassignment',old_cc=1,new_cc=2,destination_applied=True,next_cycle_curve=True,passed=True))
            return
        if clear_all:
            cc=[e for e in window if ns[4]['sequence']<e['sequence']<ns[8]['sequence'] and e['bytes'][0]&240==176]
            assert [e['bytes'] for e in cc]==[[176,1,63]]*4,cc
            for e,expected in zip(cc,(1,2,3,4)):
                assert e['port']==1 and abs((e[field]-ns[4][field])/1e9-expected)<=tol
            c.results.append(dict(kind='live-channel-lock-clear',source_and_destination_removed=True,stored_recalls=4,passed=True))
            return
        if clear:
            # A cleared lock is absent, unlike Off: stored patch recalls on step3.
            # The source lock remains24. No old destination96 or slide is allowed
            # in the following complete cycle.
            cc=[e for e in window if ns[4]['sequence']<e['sequence']<ns[8]['sequence'] and e['bytes'][:2]==[176,1]]
            assert [e['bytes'][2] for e in cc]==[63,63,63,24],cc
            for e,expected in zip(cc,(1,2,3,4)):
                assert e['port']==1 and abs((e[field]-ns[4][field])/1e9-expected)<=tol
            c.results.append(dict(kind='live-clear-destination',source_preserved=True,next_cycle_stored_recalls=True,passed=True))
            return
        if off:
            # Off neither sends a sentinel nor cancels the captured active slide.
            ramp=[e for e in window if ns[0]['sequence']<e['sequence']<ns[3]['sequence'] and e['bytes'][:2]==[176,1]]
            assert ramp[-1]['bytes'][2]==63 # Stored recall at next active unlocked note.
            ramp=ramp[:-1]
            assert len(ramp)>=20
            for e in ramp:
                elapsed=(e[field]-ns[0][field])/1e9
                ideal=24+72*min(1,max(0,elapsed/2))
                assert e['port']==1 and abs(e['bytes'][2]-ideal)<=1+36*tol
            assert ramp[-1]['bytes'][2]==96,'Off cancelled the active slide'
            endpoint=(ramp[-1][field]-ns[0][field])/1e9
            assert 2-tol<=endpoint<=2+8/144+tol
            # The following cycle has no eligible destination, hence no slide.
            cc=[e for e in window if ns[4]['sequence']<e['sequence']<ns[8]['sequence'] and e['bytes'][:2]==[176,1]]
            assert [e['bytes'][2] for e in cc]==[63,63,24],cc
            for e,expected in zip(cc,(1,3,4)):
                assert abs((e[field]-ns[4][field])/1e9-expected)<=tol
            c.results.append(dict(kind='live-off-destination',active_slide_continues=True,next_cycle_excludes_off=True,endpoint_seconds=endpoint,passed=True))
            return
        for cycle in range(2):
            destination=ns[cycle*4+2]
            preceding=[e for e in window if ns[cycle*4]['sequence']<e['sequence']<destination['sequence'] and e['bytes'][:2]==[176,1]]
            assert preceding[-1]['bytes'][2]==84,'Edited destination was overwritten by stale slide endpoint'
            assert abs((preceding[-1][field]-destination[field])/1e9)<=tol
            tail=[e['bytes'][2] for e in window if destination['sequence']<e['sequence']<ns[cycle*4+3]['sequence'] and e['bytes'][:2]==[176,1]]
            assert tail==[63],dict(stale_tail=tail)
            if cycle==1:
                assert len(preceding)>=10
                for e in preceding:
                    elapsed=(e[field]-ns[4][field])/1e9
                    assert e['port']==1 and abs(e['bytes'][2]-(24+60*min(1,max(0,elapsed/2))))<=1+30*tol
        c.results.append(dict(kind='live-destination-edit',old_destination=96,new_destination=84,edit_during_active_slide=True,next_cycle_curve=True,passed=True))
    finally:(c.out/'results.json').write_text(json.dumps(c.results,indent=2)+'\n')

def patch_clear_mask_boundary(c,inverse=False,single=False,copy_isolation=False):
    assert not copy_isolation or not inverse
    assert not single or inverse
    from cases import assign_trig_parameter,menu_value,length_mask_display
    open_patch_control(c);turn(c,63);turn(c,1);menu_value(c,'63');c.key(1)
    c.enc(1,-4);c.enc(2,2)
    if inverse:
        for step in range(1,5):
            c.action(type='grid',x=step,y=4,state=1)
            try:c.enc(3,8);length_mask_display(c,'1/2')
            finally:c.action(type='grid',x=step,y=4,state=0)
    else:c.enc(3,8);length_mask_display(c,'1/2')
    c.enc(1,1);assign_trig_parameter(c,'CC 1')
    for step,value in [(1,24),(3,96)]:
        c.action(type='grid',x=step,y=4,state=1)
        try:
            c.elapse(.05);c.action(type='enc',n=3,delta=-126);c.enc(3,value+1)
        finally:c.action(type='grid',x=step,y=4,state=0)
    c.hold_tap((2,4),(11,8)) # Separate octave lock +1 at step2.
    windows=[]
    if copy_isolation:
        c.tap(6,8);c.hold_tap((1,1),(2,1));c.led_values([(1,1),(2,1)],[15,7]);c.tap(3,8)
    phases=[(1,False),(2,False),(2,True),(1,False),(2,True)] if copy_isolation else [(1,False),(1,True)]
    for slot,cleared in phases:
        pitches=(60,74,64,65) if not cleared or inverse else (60,62,64,65)
        if copy_isolation:
            c.tap(6,8);c.tap(slot,1)
            c.led_values([(1,1),(2,1)],[7,15] if slot==2 else [15,7]);c.tap(3,8)
        if cleared:
            if inverse:c.enc(1,-1) # Mask-page K1+K2 must preserve all non-mask locks.
            if single:
                c.action(type='grid',x=2,y=4,state=1)
                try:c.key(2)
                finally:c.action(type='grid',x=2,y=4,state=0)
            else:
                c.action(type='key',n=1,state=1)
                try:c.elapse(.3);c.key(2)
                finally:c.action(type='key',n=1,state=0)
        before=c.snapshot()['midi_count']
        c.playback([(1,[144,n,v]) for n,v in zip(pitches,(127,117,107,97))],cycles=2)
        windows.append((slot,cleared,before,c.snapshot()['midi_count']))
    if not inverse:c.enc(1,-1)
    length_mask_display(c,'X' if inverse else '1/2');c.finish()
    try:
        events=[json.loads(line) for line in (c.out/'native/native-events.jsonl').read_text().splitlines()]
        midi=[e for e in events if e.get('kind') in (3,11)]
        assert [e['sequence'] for e in midi]==list(range(1,len(midi)+1))
        field='logical_ns' if c.clock_mode!='real-time' else 'monotonic_ns';tol=2e-9 if c.clock_mode!='real-time' else .01
        for slot,cleared,before,after in windows:
            window=midi[before:after];ns=[e for e in window if e['bytes'][0]==144 and e['bytes'][2]>0]
            for i,n in enumerate(ns):
                assert abs((n[field]-ns[0][field])/1e9-i/6)<=tol
                releases=[e for e in window if len(e['bytes'])==3 and e['sequence']>n['sequence'] and e['port']==n['port'] and e['bytes'][1]==n['bytes'][1] and (e['bytes'][0]==128 or e['bytes'][0]==144 and e['bytes'][2]==0)]
                # The final closing onset is immediately stopped by playback().
                if i<len(ns)-1:
                    assert releases and abs((releases[0][field]-n[field])/1e9-(1/6 if inverse and cleared and (not single or i%4==1) else 1/12))<=tol,'Wrong length after clear boundary'
                prior=ns[i-1]['sequence'] if i else 0
                cc=[e for e in window if prior<e['sequence']<n['sequence'] and e['bytes'][:2]==[176,1]]
                # First note may include the separately documented Play recall.
                expected=63 if cleared and not inverse else (24,63,96,63)[i%4]
                assert cc and cc[-1]['bytes'][2]==expected
                if i:assert len(cc)==1
            c.results.append(dict(kind='parameter-grid-clear-mask-boundary',cleared=cleared,inverse=inverse,single=single,copy_isolation=copy_isolation,song_slot=slot,notes=len(ns),note_lengths_seconds=[1/6 if inverse and cleared and (not single or step==1) else 1/12 for step in range(4)],passed=True))
    finally:(c.out/'results.json').write_text(json.dumps(c.results,indent=2)+'\n')

def patch_channel_clear_isolation(c):
    from cases import assign_trig_parameter
    c.configure();c.tap(2,1)
    c.enc(3,1);c.enc(2,1);c.enc(3,1);c.enc(2,1);c.enc(3,1);c.key(3)
    c.tap(1,2);c.hold_tap((1,4),(4,4));c.enc(1,-3)
    for channel,values,octave in [(2,(40,80),-1),(1,(24,96),1)]:
        c.tap(channel,1);assign_trig_parameter(c,'CC 1')
        for step,value in zip((1,3),values):
            c.action(type='grid',x=step,y=4,state=1)
            try:
                c.elapse(.05);c.action(type='enc',n=3,delta=-126);c.enc(3,value+1)
            finally:c.action(type='grid',x=step,y=4,state=0)
        c.hold_tap((2,4),(10+octave,8))
    windows=[]
    for phase in range(3):
        if phase:
            c.tap(1,1);c.action(type='key',n=1,state=1)
            try:c.elapse(.3);c.key(2)
            finally:c.action(type='key',n=1,state=0)
        before=c.snapshot()['midi_count'];c.tap(1,8)
        def complete(s):
            return all(sum(e['index']>before and e['bytes'][0]==143+ch and e['bytes'][2]>0 for e in s['midi'])>=9 for ch in (1,2))
        c.wait(complete,timeout=5);c.tap(1,8);c.wait(lambda s:not s['midi_capture']['outstanding'])
        windows.append((phase,before,c.snapshot()['midi_count']))
    c.finish()
    try:
        events=[json.loads(line) for line in (c.out/'native/native-events.jsonl').read_text().splitlines()]
        midi=[e for e in events if e.get('kind') in (3,11)]
        assert [e['sequence'] for e in midi]==list(range(1,len(midi)+1))
        field='logical_ns' if c.clock_mode!='real-time' else 'monotonic_ns';tol=2e-9 if c.clock_mode!='real-time' else .01
        for phase,before,after in windows:
            window=midi[before:after];origins=[]
            allnotes=[e for e in window if len(e['bytes'])==3 and e['bytes'][0]&240==144 and e['bytes'][2]>0]
            assert all((e['port'],e['bytes'][0]) in [(1,144),(2,145)] for e in allnotes)
            for ch in (1,2):
                ns=[e for e in allnotes if e['bytes'][0]==143+ch];assert len(ns)>=9
                origins.append(ns[0][field])
                pitches=(60,50,64,65) if ch==2 else ((60,74,64,65) if phase==0 else (60,62,64,65))
                cc=[e for e in window if e['bytes'][0]==175+ch]
                for i,n in enumerate(ns):
                    assert (n['port'],n['bytes'])==(ch,[143+ch,pitches[i%4],(127,117,107,97)[i%4]])
                    assert abs((n[field]-ns[0][field])/1e9-i/6)<=tol
                    prior=ns[i-1]['sequence'] if i else 0
                    actual=[(e['port'],e['bytes']) for e in cc if prior<e['sequence']<n['sequence']]
                    value=(40,80)[(i%4)//2] if ch==2 else (24,96)[(i%4)//2]
                    expected=[] if i%2 or ch==1 and phase else [(ch,[175+ch,1,value])]
                    assert actual==expected,dict(phase=phase,channel=ch,step=i%4+1,actual=actual,expected=expected)
            assert (max(origins)-min(origins))/1e9<=tol
            c.results.append(dict(kind='cross-channel-lock-clear',phase=phase,cleared_channel=1 if phase else None,other_channel_unchanged=True,passed=True))
    finally:(c.out/'results.json').write_text(json.dumps(c.results,indent=2)+'\n')

def patch_ten_slot_slides(c,remove_middle=False):
    from cases import assign_trig_parameter
    c.configure();c.enc(1,-3)
    for slot in range(1,11):
        if slot>1:c.enc(2,1)
        assign_trig_parameter(c,'CC '+str(slot))
        for step,value in [(1,slot),(3,slot+16)]:
            c.action(type='grid',x=step,y=4,state=1)
            try:
                c.elapse(.05);c.action(type='enc',n=3,delta=-126);c.enc(3,value+1)
            finally:c.action(type='grid',x=step,y=4,state=0)
        c.key(3)
    if remove_middle:
        c.enc(2,-5);c.enc(1,2);c.enc(3,-8);c.key(3);c.enc(1,-2) # Slot5, /6.
    before=c.snapshot()['midi_count']
    if remove_middle:
        from cases import parameter_list_label
        c.tap(1,8)
        c.wait(lambda s:any(e['index']>before and e['bytes'][:2]==[176,5] and 5<e['bytes'][2]<12 for e in s['midi']))
        c.key(2);c.elapse(.05);c.action(type='enc',n=3,delta=-126);c.elapse(.15)
        parameter_list_label(c,'None');c.key(3);c.key(2)
        c.wait(lambda s:sum(e['index']>before and e['bytes'][0]==144 and e['bytes'][2]>0 for e in s['midi'])>=9,timeout=12)
        c.tap(1,8);c.wait(lambda s:not s['midi_capture']['outstanding'])
    else:c.playback([(1,[144,n,v]) for n,v in zip((60,62,64,65),(127,117,107,97))],cycles=2)
    after=c.snapshot()['midi_count'];c.finish()
    try:
        raw=[json.loads(line) for line in (c.out/'native/native-events.jsonl').read_text().splitlines()]
        midi=[e for e in raw if e.get('kind') in (3,11)]
        assert [e['sequence'] for e in midi]==list(range(1,len(midi)+1))
        window=midi[before:after];ns=[e for e in window if e['bytes'][0]==144 and e['bytes'][2]>0]
        cc=[e for e in window if e['bytes'][0]&240==176]
        assert all(e['port']==1 and e['bytes'][0]==176 and 1<=e['bytes'][1]<=10 for e in cc)
        field='logical_ns' if c.clock_mode!='real-time' else 'monotonic_ns';tol=2e-9 if c.clock_mode!='real-time' else .01
        gap=1 if remove_middle else 1/6
        for i,n in enumerate(ns):
            assert (n['port'],n['bytes'])==(1,[144,(60,62,64,65)[i%4],(127,117,107,97)[i%4]])
            assert abs((n[field]-ns[0][field])/1e9-i*gap)<=tol
        if remove_middle:
            confirmations=[e for e in raw if e.get('kind')=='input' and e.get('type')==1 and e['args']==[3,1] and e['monotonic_ns']>ns[0]['monotonic_ns']]
            assert len(confirmations)==1
            cutoff=confirmations[0]['monotonic_ns']
            assert cutoff<ns[2]['monotonic_ns']
            assert any(e['bytes'][1]==5 and 5<e['bytes'][2]<21 and e['monotonic_ns']<cutoff for e in cc)
            assert not [e for e in cc if e['bytes'][1]==5 and e['monotonic_ns']>cutoff], 'Removed slot kept emitting'
        initial=[e['bytes'] for e in cc if e['sequence']<ns[0]['sequence']]
        assert initial==[[176,slot,slot] for slot in range(1,11)],initial
        checks=[]
        for cycle in range(2):
            source,destination,next_source=ns[cycle*4],ns[cycle*4+2],ns[cycle*4+4]
            for slot in range(1,11):
                if remove_middle and slot==5:continue
                ramp=[e for e in cc if e['bytes'][1]==slot and source['sequence']<e['sequence']<destination['sequence']]
                assert len(ramp)>=3,dict(slot=slot,missing_slide=True)
                for e in ramp:
                    elapsed=(e[field]-source[field])/1e9;ideal=slot+16*max(0,min(1,elapsed/(2*gap)))
                    assert abs(e['bytes'][2]-ideal)<=1+16/(2*gap)*tol,dict(slot=slot,elapsed=elapsed,value=e['bytes'][2],ideal=ideal)
                    assert e['bytes'][2]!=slot,'Repeated initial slot value after note'
                assert ramp[-1]['bytes'][2]==slot+16
                assert abs((ramp[-1][field]-destination[field])/1e9)<=tol
                tail=[e for e in cc if e['bytes'][1]==slot and destination['sequence']<e['sequence']<next_source['sequence']]
                assert len(tail)==1 and tail[0]['bytes'][2]==slot
                assert abs((tail[0][field]-next_source[field])/1e9)<=tol
                checks.append(dict(cycle=cycle,slot=slot,values=[e['bytes'][2] for e in ramp]))
        c.results.append(dict(kind='all-ten-native-slide-slots',slots=10,removed_slot=5 if remove_middle else None,cycles=2,checks=checks,passed=True))
    finally:(c.out/'results.json').write_text(json.dumps(c.results,indent=2)+'\n')

def patch_sparse_slide(c,high=False):
    from cases import menu_label,menu_value,assign_trig_parameter
    open_patch_control(c,True);label='SparseHigh' if high else 'SparseLow';cc_number=3 if high else 2
    for _ in range(180):
        if selected_line(c.snapshot(),label):break
        c.enc(2,1)
    else:raise AssertionError('Sparse control not reachable')
    menu_label(c,label);menu_value(c,'X');turn(c,-1 if high else 1);turn(c,-14 if high else 13);menu_value(c,'113');c.key(1)
    c.enc(1,-3);assign_trig_parameter(c,label)
    for step,value in [(1,100),(3,127)]:
        c.action(type='grid',x=step,y=4,state=1)
        try:
            c.elapse(.05);c.action(type='enc',n=3,delta=126 if high else -126)
            c.enc(3,value-128 if high else value-99)
        finally:c.action(type='grid',x=step,y=4,state=0)
    c.key(3);before=c.snapshot()['midi_count']
    c.playback([(1,[144,n,v]) for n,v in zip((60,62,64,65),(127,117,107,97))],cycles=2)
    after=c.snapshot()['midi_count'];c.key(1);menu_value(c,'113');c.finish()
    try:
        raw=[json.loads(line) for line in (c.out/'native/native-events.jsonl').read_text().splitlines()]
        midi=[e for e in raw if e.get('kind') in (3,11)]
        assert [e['sequence'] for e in midi]==list(range(1,len(midi)+1))
        window=midi[before:after];ns=[e for e in window if e['bytes'][0]==144 and e['bytes'][2]>0]
        cc=[e for e in window if e['bytes'][0]&240==176]
        assert all(e['port']==1 and e['bytes'][:2]==[176,cc_number] and 100<=e['bytes'][2]<=127 for e in cc),'Emitted sparse Off gap or wrong route'
        field='logical_ns' if c.clock_mode!='real-time' else 'monotonic_ns';tol=2e-9 if c.clock_mode!='real-time' else .01
        for i,n in enumerate(ns):assert abs((n[field]-ns[0][field])/1e9-i/6)<=tol
        initial=[e for e in cc if e['sequence']<ns[0]['sequence']];assert initial[-1]['bytes'][2]==100
        checks=[]
        for cycle in range(2):
            source,dest=ns[cycle*4],ns[cycle*4+2]
            ramp=[e for e in cc if source['sequence']<e['sequence']<dest['sequence']]
            assert len(ramp)>=3
            for e in ramp:
                elapsed=(e[field]-source[field])/1e9;ideal=100+27*max(0,min(1,elapsed/(1/3)))
                assert abs(e['bytes'][2]-ideal)<=1+81*tol,dict(value=e['bytes'][2],ideal=ideal)
            assert ramp[-1]['bytes'][2]==127
            assert abs((ramp[-1][field]-dest[field])/1e9)<=tol
            tail=[e['bytes'][2] for e in cc if dest['sequence']<e['sequence']<ns[cycle*4+3]['sequence']]
            assert tail==[113],tail
            checks.append([e['bytes'][2] for e in ramp])
        c.results.append(dict(kind='sparse-domain-slide',off=200 if high else -1,active_range=[100,127],stored=113,checks=checks,passed=True))
    finally:(c.out/'results.json').write_text(json.dumps(c.results,indent=2)+'\n')


def patch_nrpn_restart(c,legacy=False,convert=False):
    """Native edits/autosave/reload; pre-policy seed removes only new metadata."""
    import re,shutil,subprocess
    from pathlib import Path
    historical_output=legacy and not convert
    from cases import menu_value,menu_label
    from driver import Driver,digest
    def locate(driver,setup):
        open_patch_control(driver,configured=True,setup=setup)
        for _ in range(180):
            if selected_line(driver.snapshot(),'NRPN14'):break
            driver.enc(2,1)
        else:raise AssertionError('NRPN14 not reachable')
        menu_label(driver,'NRPN14')
    def packets(value):
        hi,lo=divmod(value,128)
        if historical_output:lo=lo//2 if lo%2==0 else 0
        return [(1,[176,cc,v]) for cc,v in ((99,4),(98,5),(6,hi),(38,lo))]
    def captured(driver,before=0):
        return [(e['port'],e['bytes']) for e in driver.snapshot()['midi']
                if e['index']>before and e['bytes'][0]&240==176]
    def autosave(driver):
        driver.elapse(59);driver.elapse(2)
        driver.wait(lambda _:all((driver.data_directory/name).is_file() for name in ('autosave.ptn','autosave.pset')),timeout=3)
    locate(c,True);menu_value(c,'X');turn(c,1);menu_value(c,'126');c.key(1)
    autosave(c);c.finish()
    seed=c.data_directory
    if legacy:
        seed=c.out/'pre-policy-seed';shutil.copytree(c.data_directory,seed)
        path=seed/'autosave.ptn';text=path.read_text()
        text,n=re.subn(r'^ *\["nrpn_policy_version"\]=[^\n]+\n','',text,flags=re.M)
        assert n==1,'Seed must contain exactly one current project policy version'
        text,n=re.subn(r'^ *\["nrpn_stored_modes"\]=[^\n]+\n','',text,flags=re.M)
        assert n==1
        path.write_text(text)
        c.results.append(dict(kind='pre-policy-project-fixture',removed_fields=['nrpn_policy_version','nrpn_stored_modes'],sha256=digest(path),numeric_values_unchanged=True))
    if convert:
        assert legacy
        converted=c.out/'converted-seed'
        shutil.copytree(seed,converted,ignore=shutil.ignore_patterns('autosave.ptn','autosave.pset'))
        original_digest=digest(seed/'autosave.ptn')
        install=json.loads(Path(c.launch_options['experimental_install']).read_text())
        command=['python3',str(Path(__file__).resolve().parents[2]/'tools/nrpn-project-mode.py'),
          '--norns-source',install['source'],'--project',str(seed/'autosave.ptn'),
          '--output',str(converted/'autosave.ptn'),'--mode','standard']
        result=subprocess.run(command,capture_output=True,text=True)
        assert result.returncode==0,result.stderr
        assert digest(seed/'autosave.ptn')==original_digest,'Conversion changed the source project'
        assert digest(seed/'autosave.pset')==digest(converted/'autosave.pset'),'Conversion changed numeric params'
        output_digest=digest(converted/'autosave.ptn')
        refused=subprocess.run(command,capture_output=True,text=True)
        assert refused.returncode!=0 and digest(converted/'autosave.ptn')==output_digest,'Conversion overwrote existing output'
        c.results.append(dict(kind='explicit-nrpn-project-conversion',mode='standard',source_unchanged=True,pset_identical=True,overwrite_refused=True))
        seed=converted
    # First reload migrates if needed; second proves ordinary save persisted it.
    value=126
    for generation in (1,2):
        out=c.out/('nrpn-reload-'+str(generation));out.mkdir()
        loaded=Driver(out,project_seed=seed,**c.launch_options)
        try:
            assert captured(loaded)==packets(value),dict(stage='boot',value=value,expected=packets(value),actual=captured(loaded))
            locate(loaded,False);menu_value(loaded,str(value))
            if generation==1:
                before=loaded.snapshot()['midi_count'];turn(loaded,1);value=253;menu_value(loaded,'253')
                assert captured(loaded,before)==packets(value),dict(stage='edit',actual=captured(loaded,before),expected=packets(value))
            loaded.key(1);before=loaded.snapshot()['midi_count']
            loaded.playback([(1,[144,n,v]) for n,v in ((60,127),(62,117),(64,107),(65,97))],cycles=2)
            assert captured(loaded,before)==packets(value),dict(stage='play',actual=captured(loaded,before),expected=packets(value))
            if generation==1:autosave(loaded)
            loaded.results.append(dict(kind='nrpn-reload-compatibility',legacy=historical_output,converted=convert,generation=generation,value=value,expected=packets(value),passed=True))
        finally:
            loaded.finish();(out/'results.json').write_text(json.dumps(loaded.results,indent=2)+'\n')
        seed=loaded.data_directory
    c.results.append(dict(kind='nrpn-persisted-mode-native',legacy=legacy,passed=True))
    (c.out/'results.json').write_text(json.dumps(c.results,indent=2)+'\n')


def patch_nrpn_boundary_matrix(c):
    from cases import menu_label,menu_value
    open_patch_control(c,True)
    for _ in range(180):
        if selected_line(c.snapshot(),'NS0'):break
        c.enc(2,1)
    else:raise AssertionError('Boundary NRPN controls unreachable')
    checks=[]
    table=[(legacy,i,v) for legacy in (False,True) for i,v in enumerate((0,1,126,127,128,129,16383))]
    # Return to A after traversing standard and historical B parameters.
    for position,(legacy,index,value) in enumerate(table+[table[0]]):
        if position==14:c.enc(2,-13)
        elif position:c.enc(2,1)
        name=('NL' if legacy else 'NS')+str(index)
        menu_label(c,name);menu_value(c,'X')
        before=c.snapshot()['midi_count'];turn(c,1);menu_value(c,str(value))
        hi,lo=divmod(value,128)
        if legacy:lo=lo//2 if lo%2==0 else 0
        status=191 if legacy else 177
        expected=[(1,[status,cc,v]) for cc,v in ((99,7 if legacy else 6),(98,index),(6,hi),(38,lo))]
        actual=[(e['port'],e['bytes']) for e in c.snapshot()['midi'] if e['index']>before]
        assert actual==expected,dict(name=name,expected=expected,actual=actual)
        before=c.snapshot()['midi_count'];turn(c,-1);menu_value(c,'X')
        assert c.snapshot()['midi_count']==before,'Off emitted data'
        checks.append(dict(parameter=name,value=value,expected=expected))
    c.results.append(dict(kind='nrpn-native-boundary-mode-matrix',checks=checks,off_silence=True,aba=True,passed=True))


def patch_nrpn_slide(c,legacy=False,descending=False,default_off=False):
    from cases import menu_label,menu_value,assign_trig_parameter
    from frame_oracle import header,matches
    name='NRPNdef' if default_off else ('NRPNold' if legacy else 'NRPN14')
    open_patch_control(c,True)
    for _ in range(180):
        if selected_line(c.snapshot(),name):break
        c.enc(2,1)
    else:raise AssertionError('NRPN slide control unreachable')
    menu_label(c,name);menu_value(c,'X');c.key(1)
    c.enc(1,-3);assign_trig_parameter(c,name)
    source,target=(253,126) if descending else (126,253)
    for step,value in ((1,source),(3,target)):
        c.action(type='grid',x=step,y=4,state=1)
        try:
            c.elapse(.05);c.action(type='enc',n=3,delta=-126)
            c.enc(3,1 if value==126 else 2)
            c.action(type='key',n=1,state=1);c.elapse(.3)
            try:c.enc(3,-2 if value==126 else -4) # Fine edit: coarse128/257 ->126/253.
            finally:c.action(type='key',n=1,state=0)
        finally:c.action(type='grid',x=step,y=4,state=0)
    if default_off:
        c.action(type='grid',x=2,y=4,state=1)
        try:c.elapse(.05);c.action(type='enc',n=3,delta=-126);c.elapse(.15)
        finally:c.action(type='grid',x=2,y=4,state=0)
    c.key(3)
    c.enc(1,2);c.wait(lambda s:matches(s,header('Ch. 1 Clocks',selected=4)))
    c.enc(3,-23);c.key(3);c.enc(1,-2) # /24 gives4seconds/step at90BPM.
    before=c.snapshot()['midi_count']
    c.playback([(1,[144,n,v]) for n,v in ((60,127),(62,117),(64,107),(65,97))],cycles=2,timeout=36,settle_seconds=30)
    after=c.snapshot()['midi_count'];c.key(1);menu_value(c,'X');c.finish()
    try:
        events=[json.loads(line) for line in (c.out/'native/native-events.jsonl').read_text().splitlines()]
        midi=[e for e in events if e.get('kind') in (3,11)]
        assert [e['sequence'] for e in midi]==list(range(1,len(midi)+1))
        window=midi[before:after]
        notes=[e for e in window if e['bytes'][0]==144 and e['bytes'][2]>0]
        cc=[e for e in window if e['bytes'][0]&240==176]
        assert len(cc)%4==0
        packets=[]
        for index in range(0,len(cc),4):
            group=cc[index:index+4]
            assert all(e['port']==1 and e['bytes'][0]==176 for e in group)
            assert [e['bytes'][1] for e in group]==[99,98,6,38]
            assert [e['bytes'][2] for e in group[:2]]==([5,6] if default_off else [4,6 if legacy else 5])
            packets.append(dict(event=group[-1],hi=group[2]['bytes'][2],lo=group[3]['bytes'][2],first_sequence=group[0]['sequence']))
        field='monotonic_ns' if c.clock_mode=='real-time' else 'logical_ns'
        tolerance=.01 if c.clock_mode=='real-time' else 2e-9
        origin=notes[0][field]
        for i,note in enumerate(notes):assert abs((note[field]-origin)/1e9-i*4)<=tolerance
        def packed(value):
            hi,lo=divmod(value,128)
            if legacy:lo=lo//2 if lo%2==0 else 0
            return hi,lo
        checks=[]
        for cycle in range(2):
            first,last=notes[cycle*4],notes[cycle*4+2]
            initial=[p for p in packets if p['event']['sequence']<first['sequence']][-1]
            assert (initial['hi'],initial['lo'])==packed(source)
            ramp=[p for p in packets if first['sequence']<p['first_sequence'] and p['event']['sequence']<last['sequence']]
            assert len(ramp)>100,'Too few distinct values for slow127-unit slide'
            for packet in ramp:
                elapsed=(packet['event'][field]-first[field])/1e9
                ideal=source+(target-source)*max(0,min(1,elapsed/8))
                allowed=[v for v in range(min(source,target),max(source,target)+1) if abs(v-ideal)<=1+127/8*tolerance]
                assert (packet['hi'],packet['lo']) in [packed(v) for v in allowed],dict(elapsed=elapsed,ideal=ideal,packet=packet)
            assert (ramp[-1]['hi'],ramp[-1]['lo'])==packed(target)
            assert abs((ramp[-1]['event'][field]-last[field])/1e9)<=tolerance
            assert not [p for p in packets if last['sequence']<p['first_sequence']<notes[cycle*4+3]['sequence']], 'Stale slide tail or Off recall'
            if not legacy:
                values=[p['hi']*128+p['lo'] for p in ramp]
                assert 127 in values and 128 in values,'Rollover values not exercised'
                assert values==sorted(values,reverse=descending)
            checks.append(dict(cycle=cycle,samples=len(ramp),source=source,target=target))
        c.results.append(dict(kind='nrpn-musical-rollover-slide',legacy=legacy,descending=descending,default_off_middle=default_off,step_seconds=4,slide_seconds=8,checks=checks,passed=True))
    finally:(c.out/'results.json').write_text(json.dumps(c.results,indent=2)+'\n')



def patch_mixed_cc_nrpn_slides(c):
    """Run independent step-local CC and global NRPN slides concurrently."""
    from cases import assign_trig_parameter,assert_durations
    from note_accounting import note_pairs

    open_patch_control(c,True)
    c.key(1);c.enc(1,-3)

    def hold(step, action):
        c.action(type='grid',x=step,y=4,state=1)
        try:
            c.elapse(.05);action()
        finally:c.action(type='grid',x=step,y=4,state=0)
        c.elapse(.15)

    # Slot1: CC from24 to96, with only step1 marked as a slide source.
    assign_trig_parameter(c,'CCdefault')
    for step,value in ((1,24),(3,96)):
        hold(step,lambda value=value:(c.action(type='enc',n=3,delta=-126),c.enc(3,value+1)))
    hold(1,lambda:c.key(3))

    # Slot2: standard NRPN from126 to253, with the channel-wide slide flag.
    c.enc(2,1);assign_trig_parameter(c,'NRPN14')
    for step,value in ((1,126),(3,253)):
        def set_nrpn(value=value):
            c.action(type='enc',n=3,delta=-126)
            c.enc(3,1 if value==126 else 2)
            c.action(type='key',n=1,state=1);c.elapse(.3)
            try:c.enc(3,-2 if value==126 else -4)
            finally:c.action(type='key',n=1,state=0)
        hold(step,set_nrpn)
    c.key(3)

    before=c.snapshot()['midi_count']
    played=c.playback([(1,[144,n,v]) for n,v in ((60,127),(62,117),(64,107),(65,97))],cycles=2)
    events=[e for e in c.snapshot()['midi'] if e['index']>before]
    notes=[e for e in events if e['bytes'][0]==144 and e['bytes'][2]>0]
    assert notes==played and len(notes)>=9
    pairs=note_pairs(events);assert [on for on,off in pairs]==notes
    assert_durations(c,notes,[1]*(len(notes)-1),events=events)

    parameter_events=[e for e in events if len(e['bytes'])==3 and e['bytes'][0]&240==176]
    programs=[e for e in events if len(e['bytes'])==2 and e['bytes'][0]&240==192]
    releases=[e for e in events if len(e['bytes'])==3 and e['bytes'][0]&240==128]
    transport=[e for e in events if len(e['bytes'])==1]
    assert [(e['port'],e['bytes']) for e in transport]==[(1,[250]),(2,[250]),(3,[250]),(1,[252]),(2,[252]),(3,[252])]
    expected_program=[[192,0],[193,0],[194,3],[195,64]]*len(notes)
    assert all(e['port']==3 for e in programs) and [e['bytes'] for e in programs]==expected_program
    for ordinal,note in enumerate(notes):
        group=programs[ordinal*4:ordinal*4+4]
        assert all(e['index']<note['index'] for e in group)
        assert ordinal==0 or all(e['index']>notes[ordinal-1]['index'] for e in group)
    assert len(releases)==len(notes)
    assert len(events)==len(parameter_events)+len(programs)+len(notes)+len(releases)+len(transport),'Unclassified MIDI output'
    assert all(e['port']==1 and len(e['bytes'])==3 and e['bytes'][0]==176 and all(0<=v<=127 for v in e['bytes'][1:]) for e in parameter_events)
    assert all(e['bytes'][1] in (1,99,98,6,38) for e in parameter_events),'Unexpected parameter controller'

    # Parse the complete parameter stream. A standard NRPN packet must be four
    # consecutive captured MIDI messages; filtering cannot hide an interleave.
    cc=[];nrpn=[];offset=0
    while offset<len(parameter_events):
        event=parameter_events[offset]
        if event['bytes'][1]==1:
            cc.append(event);offset+=1;continue
        group=parameter_events[offset:offset+4]
        assert len(group)==4
        assert [e['bytes'][1] for e in group]==[99,98,6,38]
        assert [e['bytes'][2] for e in group[:2]]==[4,5]
        assert [e['index'] for e in group]==list(range(group[0]['index'],group[0]['index']+4))
        nrpn.append(dict(first=group[0],last=group[-1],value=group[2]['bytes'][2]*128+group[3]['bytes'][2]))
        offset+=4

    expected_cc=[24,36,48,60,72,84,96,24,36,48,60,72,84,96,24]
    expected_nrpn=[126,147,168,190,211,232,253,126,147,168,190,211,232,253,126]
    assert [e['bytes'][2] for e in cc]==expected_cc
    assert [p['value'] for p in nrpn]==expected_nrpn

    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    origin=notes[0][field]
    for ordinal,note in enumerate(notes):
        assert abs((note[field]-origin)/1e9-ordinal/6)<=tolerance

    checks=[]
    for cycle in range(2):
        note_base=cycle*4;event_base=cycle*7
        source,destination,following,next_source=notes[note_base],notes[note_base+2],notes[note_base+3],notes[note_base+4]
        initial_cc,initial_nrpn=cc[event_base],nrpn[event_base]
        cc_ramp=cc[event_base+1:event_base+7]
        nrpn_ramp=nrpn[event_base+1:event_base+7]
        next_cc,next_nrpn=cc[event_base+7],nrpn[event_base+7]
        assert initial_cc['bytes'][2]==24 and initial_nrpn['value']==126
        assert initial_cc['index']<source['index'] and initial_nrpn['last']['index']<source['index']
        assert abs((initial_cc[field]-source[field])/1e9)<=tolerance
        assert abs((initial_nrpn['last'][field]-source[field])/1e9)<=tolerance
        for sample,(cc_event,nrpn_packet) in enumerate(zip(cc_ramp,nrpn_ramp),1):
            expected_offset=sample/18
            assert source['index']<cc_event['index']<destination['index']
            assert source['index']<nrpn_packet['first']['index']<=nrpn_packet['last']['index']<destination['index']
            assert abs((cc_event[field]-source[field])/1e9-expected_offset)<=tolerance
            assert abs((nrpn_packet['last'][field]-source[field])/1e9-expected_offset)<=tolerance
            assert abs((cc_event[field]-nrpn_packet['last'][field])/1e9)<=tolerance
        assert len(set(e['bytes'][2] for e in cc_ramp[:-1]))==5
        assert len(set(p['value'] for p in nrpn_ramp[:-1]))==5
        assert cc_ramp[-1]['bytes'][2]==96 and nrpn_ramp[-1]['value']==253
        assert abs((cc_ramp[-1][field]-destination[field])/1e9)<=tolerance
        assert abs((nrpn_ramp[-1]['last'][field]-destination[field])/1e9)<=tolerance
        assert not [e for e in parameter_events if destination['index']<e['index']<following['index']]
        assert following['index']<next_cc['index']<next_source['index']
        assert following['index']<next_nrpn['first']['index']<=next_nrpn['last']['index']<next_source['index']
        assert abs((next_cc[field]-next_source[field])/1e9)<=tolerance
        assert abs((next_nrpn['last'][field]-next_source[field])/1e9)<=tolerance
        checks.append(dict(cycle=cycle,cc_samples=6,nrpn_samples=6,sample_period_seconds=1/18))
    c.results.append(dict(kind='mixed-cc-nrpn-slides',cc_mode='step-local',nrpn_mode='global',
                          encoding_independent=True,cycles=2,checks=checks,passed=True))


def patch_configured_off_lock(c,high=False,default_kind=None):
    from cases import assign_trig_parameter,menu_value
    name=default_kind or ('SparseHigh' if high else 'NRPN14')
    open_patch_control(c,True);c.key(1);c.enc(1,-3);assign_trig_parameter(c,name)
    c.action(type='grid',x=1,y=4,state=1)
    try:
        c.elapse(.05);c.action(type='enc',n=3,delta=126 if high else -126);c.elapse(.15)
    finally:c.action(type='grid',x=1,y=4,state=0)
    before=c.snapshot()['midi_count']
    c.playback([(1,[144,n,v]) for n,v in ((60,127),(62,117),(64,107),(65,97))],cycles=2)
    actual=[(e['port'],e['bytes']) for e in c.snapshot()['midi'] if e['index']>before and e['bytes'][0]&240==176]
    c.results.append(dict(kind='configured-step-lock-off',parameter=name,off=200 if high else -1,expected=[],actual=actual))
    assert actual==[],'Configured Off lock was clamped to an active value'
