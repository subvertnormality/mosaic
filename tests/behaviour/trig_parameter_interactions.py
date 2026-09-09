"""Native stock-parameter precedence; literal MIDI and musical-time oracles."""

def fixed_note_domain(c,start=0,count=16):
    from cases import assign_trig_parameter,assert_durations
    assert 0<=start<128 and 1<=count<=16 and start+count<=128
    c.configure();c.enc(1,-3)
    assign_trig_parameter(c,'Fixed Note')
    for label,value in [('Quantised Fixed Note',7),('Random Note',4),('Twos Random Note',4)]:
        c.enc(2,1);assign_trig_parameter(c,label)
        c.enc(3,value+(1 if label=='Quantised Fixed Note' else 0))
    c.enc(2,-3);c.enc(3,start+1)
    def phrase(pitches,label):
        notes=c.playback([(1,[144,pitch,velocity]) for pitch,velocity in zip(pitches,(127,117,107,97))],cycles=2)
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        origin=notes[0][field]
        errors=[(note[field]-origin)/1e9-i/6 for i,note in enumerate(notes)]
        assert all(abs(error)<=tolerance for error in errors),errors
        assert_durations(c,notes,[1]*(len(notes)-1))
        c.results.append(dict(kind='fixed-note-precedence',phase=label,pitches=pitches,other_sources=['pattern','quantised-fixed7','random4','twos4'],timing_errors=errors,passed=True))
    for pitch in range(start,start+count):
        if pitch>start:c.enc(3,1)
        phrase([pitch]*4,str(pitch))
    if start+count==128:
        c.enc(3,3);phrase([127]*4,'upper-clamp')
    # Disable all four sources using real encoder saturation, then require the
    # original four-note/velocity phrase. No inferred random-output golden.
    for slot in (1,2,3,4):
        if slot>1:c.enc(2,1)
        c.elapse(.05);c.action(type='enc',n=3,delta=-126);c.elapse(.15)
    phrase([60,62,64,65],'all-overrides-off')


def quantised_fixed_table(c,profile='major'):
    from cases import assign_trig_parameter,assert_durations
    # Literal musical tables, independent of Mosaic's quantiser. Root shifts
    # retain the scale's lower endpoint; ties choose the lower legal pitch.
    tables={
        'major':[(0,0),(1,0),(3,2),(6,5),(7,7),(11,11),(12,12),
                 (60,60),(61,60),(63,62),(66,65),(70,69),(126,125),(127,127)],
        'd-major':[(0,2),(1,2),(60,59),(61,61),(63,62),(127,127)],
        'a-harmonic-minor':[(125,125),(126,125),(127,125)],
    }
    assert profile in tables
    c.configure()
    if profile!='major':
        c.tap(4,8)
        if profile=='a-harmonic-minor':c.enc(3,3) # Major -> Harmonic Minor
        c.enc(2,-1);c.enc(3,9 if profile=='a-harmonic-minor' else 2)
        c.key(3);c.tap(3,8)
    c.enc(1,-3);assign_trig_parameter(c,'Quantised Fixed Note')
    previous=-1
    for value,pitch in tables[profile]:
        c.enc(3,value-previous);previous=value
        notes=c.playback([(1,[144,pitch,v]) for v in (127,117,107,97)],cycles=2)
        assert_durations(c,notes,[1]*(len(notes)-1))
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        errors=[(note[field]-notes[0][field])/1e9-i/6 for i,note in enumerate(notes)]
        assert all(abs(error)<=tolerance for error in errors),errors
        c.results.append(dict(kind='quantised-fixed-musical-table',profile=profile,input=value,pitch=pitch,timing_errors=errors,passed=True))


def stock_pitch_lock_inheritance(c,quantised=True):
    from cases import assign_trig_parameter,assert_durations
    c.configure();c.enc(1,-3)
    assign_trig_parameter(c,'Quantised Fixed Note' if quantised else 'Fixed Note')
    def phrase(pitches,phase):
        notes=c.playback([(1,[144,p,v]) for p,v in zip(pitches,(127,117,107,97))],cycles=2)
        assert_durations(c,notes,[1]*(len(notes)-1))
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        errors=[(n[field]-notes[0][field])/1e9-i/6 for i,n in enumerate(notes)]
        assert all(abs(e)<=tolerance for e in errors),errors
        c.results.append(dict(kind='stock-pitch-lock-inheritance',quantised=quantised,phase=phase,pitches=pitches,timing_errors=errors,passed=True))
    def lock(step,value):
        c.action(type='grid',x=step,y=4,state=1)
        try:
            c.elapse(.05);c.action(type='enc',n=3,delta=-126);c.elapse(.15)
            if value>=0:c.enc(3,value+1)
        finally:c.action(type='grid',x=step,y=4,state=0)
        c.elapse(.15)
    def clear(step):
        c.action(type='grid',x=step,y=4,state=1)
        try:c.elapse(.05);c.key(2)
        finally:c.action(type='grid',x=step,y=4,state=0)
        c.elapse(.15)
    c.enc(3,61);phrase([60]*4,'channel60')
    lock(2,63);locked=62 if quantised else 63
    phrase([60,locked,60,60],'step2-override')
    lock(1,0);phrase([0,locked,60,60],'zero-is-active')
    lock(4,-1);phrase([0,locked,60,60],'off-inherits')
    c.enc(3,5);phrase([0,locked,65,65],'default-edit-preserves-locks')
    clear(2);phrase([0,65,65,65],'clear-step2')
    c.action(type='enc',n=3,delta=-126);c.elapse(.15)
    phrase([0,62,64,65],'channel-off-restores-pattern')
    clear(1);phrase([60,62,64,65],'clear-zero-restores-pattern')
    # Re-entering a cleared step must not reuse an old calculator/lock value.
    lock(2,0);phrase([60,0,64,65],'reenter-cleared-step-zero')
    clear(2);phrase([60,62,64,65],'second-clear-restores-pattern')


def competing_pitch_locks(c):
    from cases import assign_trig_parameter,assert_durations
    c.configure();c.enc(1,-3)
    assign_trig_parameter(c,'Quantised Fixed Note');c.enc(3,66)
    c.enc(2,1);assign_trig_parameter(c,'Fixed Note');c.enc(3,61)
    def phrase(pitches,phase):
        notes=c.playback([(1,[144,p,v]) for p,v in zip(pitches,(127,117,107,97))],cycles=2)
        assert_durations(c,notes,[1]*(len(notes)-1))
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        errors=[(n[field]-notes[0][field])/1e9-i/6 for i,n in enumerate(notes)]
        assert all(abs(e)<=tolerance for e in errors),errors
        c.results.append(dict(kind='competing-stock-pitch-locks',phase=phase,pitches=pitches,timing_errors=errors,passed=True))
    def lock(step,value):
        c.action(type='grid',x=step,y=4,state=1)
        try:
            c.elapse(.05);c.action(type='enc',n=3,delta=-126);c.elapse(.15)
            if value>=0:c.enc(3,value+1)
        finally:c.action(type='grid',x=step,y=4,state=0)
        c.elapse(.15)
    def clear(step):
        c.action(type='grid',x=step,y=4,state=1)
        try:c.elapse(.05);c.key(2)
        finally:c.action(type='grid',x=step,y=4,state=0)
        c.elapse(.15)
    phrase([60]*4,'fixed-default-beats-quantised')
    c.enc(2,-1);lock(1,63)
    phrase([60]*4,'fixed-default-beats-quantised-lock')
    c.enc(2,1);lock(2,0);lock(3,-1)
    phrase([60,0,60,60],'fixed-zero-lock-and-off-inheritance')
    c.action(type='enc',n=3,delta=-126);c.elapse(.15)
    phrase([62,0,65,65],'fixed-off-reveals-quantised-default-and-lock')
    c.enc(2,-1);lock(4,0)
    phrase([62,0,65,0],'independent-zero-locks-on-two-slots')
    c.action(type='enc',n=3,delta=-126);c.elapse(.15)
    phrase([62,0,64,0],'both-defaults-off-preserve-local-locks')
    clear(2);phrase([62,62,64,0],'clear-fixed-lock-only-step2')
    clear(1);phrase([60,62,64,0],'clear-quantised-lock-only-step1')
    clear(4);phrase([60,62,64,65],'full-original-phrase-restored')


def probability_endpoint_locks(c):
    from cases import assign_trig_parameter,assert_durations
    c.configure();c.enc(1,-3)
    assign_trig_parameter(c,'Fixed Note');c.enc(3,66)
    c.enc(2,1);assign_trig_parameter(c,'Trig Probability')
    def phrase(steps,phase):
        velocities=(127,117,107,97)
        notes=c.playback([(1,[144,65,velocities[step-1]]) for step in steps],cycles=3)
        assert_durations(c,notes,[1]*(len(notes)-1))
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        expected=[((i//len(steps))*4+steps[i%len(steps)]-steps[0])/6 for i in range(len(notes))]
        errors=[(n[field]-notes[0][field])/1e9-t for n,t in zip(notes,expected)]
        assert all(abs(e)<=tolerance for e in errors),errors
        c.results.append(dict(kind='probability-endpoint-locked-phrase',phase=phase,active_steps=steps,expected_offsets=expected,timing_errors=errors,passed=True))
    def lock(step,value):
        c.action(type='grid',x=step,y=4,state=1)
        try:
            c.elapse(.05);c.action(type='enc',n=3,delta=-126);c.elapse(.15)
            c.enc(3,value+1)
        finally:c.action(type='grid',x=step,y=4,state=0)
        c.elapse(.15)
    def clear(step):
        c.action(type='grid',x=step,y=4,state=1)
        try:c.elapse(.05);c.key(2)
        finally:c.action(type='grid',x=step,y=4,state=0)
        c.elapse(.15)
    c.enc(3,101);phrase([1,2,3,4],'100-always')
    c.enc(3,3);phrase([1,2,3,4],'upper-clamp100')
    c.action(type='enc',n=3,delta=-126);c.elapse(.15);c.enc(3,1)
    # Include the very first onset opportunity in the silence window.
    before=c.snapshot()['midi_count'];c.tap(1,8);c.elapse(2.8)
    state=c.snapshot()
    notes=[e for e in state['midi'] if e['index']>before and e['bytes'][0]&240==144 and e['bytes'][2]>0]
    assert notes==[],notes
    assert state['midi_capture']['outstanding']==[]
    c.tap(1,8)
    c.results.append(dict(kind='probability-zero-silence',seconds=2.8,note_ons=notes,fixed_pitch=65,passed=True))
    lock(2,100);phrase([2],'step100-overrides-channel0')
    c.enc(3,100);lock(1,0);phrase([2,3,4],'step0-overrides-channel100')
    lock(4,0);phrase([2,3],'first-and-wrap-step0')
    clear(1);phrase([1,2,3],'clear-first-zero')
    clear(4);phrase([1,2,3,4],'clear-wrap-zero')


def seeded_probability(c,probability=50,opportunities=64):
    from cases import assign_trig_parameter,assert_durations
    import subprocess
    assert probability in (1,50,99)
    # Separate Lua process uses the native PRNG interface, not Mosaic's
    # sequencer, probability logic, capture output or private state.
    code='math.randomseed(42); for i=1,'+str(opportunities+1)+' do print(math.random(0,99)) end'
    proc=subprocess.run(['lua5.3','-e',code],capture_output=True,text=True,check=True)
    draws=[int(line) for line in proc.stdout.splitlines()]
    assert len(draws)==opportunities+1 and all(0<=n<=99 for n in draws)
    assert probability-1 in draws and probability in draws,'Seeded fixture must exercise both comparison boundaries'
    accepted=[i for i,n in enumerate(draws) if n<probability]
    assert len(accepted)>=3
    expected=[(1,[144,(60,62,64,65)[i%4],(127,117,107,97)[i%4]]) for i in accepted]
    c.results.append(dict(kind='independent-probability-oracle',seed=42,probability=probability,draws=draws,accepted_zero_based_steps=accepted,expected=expected,source='Separate lua5.3 native math.random; no startup draws expected from non-yielding Mosaic init. Never fit a draw offset to MIDI.'))

    c.configure()
    # A second channel carries the same authored four-step phrase at100%.
    # Its raw MIDI output independently exposes every opportunity, including
    # the first accepted note's position and the complete rejected tail.
    c.tap(2,1);c.screen_header('Ch. 2 Device Config',selected=5)
    c.enc(3,1);c.enc(2,1);c.enc(3,1);c.enc(2,1);c.enc(3,1);c.key(3)
    c.tap(1,2);c.hold_tap((1,4),(4,4));c.led_values([(2,1),(1,2)],[15,15])
    c.tap(1,1);c.enc(1,-3);assign_trig_parameter(c,'Trig Probability');c.enc(3,probability+1)
    before=c.snapshot()['midi_count'];c.tap(1,8)
    def notes(state):
        return [e for e in state['midi'] if e['index']>before and e['bytes'][0]&240==144 and e['bytes'][2]>0]
    def reference(state):return [e for e in notes(state) if e['port']==2 and e['bytes'][0]==145]
    state=c.wait(lambda state:len(reference(state))>=opportunities+1,timeout=opportunities/6+3)
    all_notes=notes(state);ref=reference(state)
    assert len(ref)==opportunities+1,len(ref)
    events=[e for e in all_notes if e['port']==1 and e['bytes'][0]==144]
    assert len(all_notes)==len(ref)+len(events),'Unexpected MIDI route'
    actual=[(e['port'],e['bytes']) for e in events]
    assert actual==expected,dict(expected=expected,actual=actual)
    ref_expected=[(2,[145,(60,62,64,65)[i%4],(127,117,107,97)[i%4]]) for i in range(opportunities+1)]
    assert [(e['port'],e['bytes']) for e in ref]==ref_expected
    c.tap(1,8);c.wait(lambda state:state['midi_capture']['outstanding']==[])
    # The closing reference onset can be cut by Stop. Every earlier planned
    # reference note and accepted probability note must get its full duration.
    assert_durations(c,ref,[1]*opportunities)
    completed=sum(i<opportunities for i in accepted)
    assert_durations(c,events,[1]*completed)
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    reference_errors=[(e[field]-ref[0][field])/1e9-i/6 for i,e in enumerate(ref)]
    errors=[(e[field]-ref[i][field])/1e9 for e,i in zip(events,accepted)]
    assert all(abs(e)<=tolerance for e in reference_errors),reference_errors
    assert all(abs(e)<=tolerance for e in errors),errors
    c.results.append(dict(kind='seeded-probability-reference-midi',probability=probability,actual=actual,accepted_zero_based_steps=accepted,reference_count=len(ref),reference_timing_errors=reference_errors,accepted_alignment_errors=errors,passed=True,scope='Every native reference opportunity through closing onset; first acceptance and rejected tail are checked.'))


def probability_midi_locks(c,trigless=True,nrpn=False):
    from cases import assign_trig_parameter,set_mosaic_options,assert_durations
    c.configure()
    if nrpn:c.enc(3,1);c.key(3) # Generic CC -> existing configured NRPN fixture.
    set_mosaic_options(c,[('Trigless locks',trigless)])
    c.tap(2,1);c.screen_header('Ch. 2 Device Config',selected=5)
    c.enc(3,1);c.enc(2,1);c.enc(3,1);c.enc(2,1);c.enc(3,1);c.key(3)
    c.tap(1,2);c.hold_tap((1,4),(4,4));c.tap(1,1);c.enc(1,-3)
    assign_trig_parameter(c,'NRPN14' if nrpn else 'CC 1')
    values=[126,253,126,253] if nrpn else [24,48,72,96]
    for step,value in enumerate(values,1):
        c.action(type='grid',x=step,y=4,state=1)
        try:
            c.elapse(.05);c.action(type='enc',n=3,delta=-126)
            c.enc(3,(1 if value==126 else 2) if nrpn else value+1)
            if nrpn:
                c.action(type='key',n=1,state=1);c.elapse(.3)
                try:c.enc(3,-2 if value==126 else -4)
                finally:c.action(type='key',n=1,state=0)
        finally:c.action(type='grid',x=step,y=4,state=0)
    c.enc(2,1);assign_trig_parameter(c,'Trig Probability');c.enc(3,1)
    def phase(active,accepted,label):
        before=c.snapshot()['midi_count'];c.tap(1,8)
        def ons(state):return [e for e in state['midi'] if e['index']>before and e['bytes'][0]&240==144 and e['bytes'][2]>0]
        def refs(state):return [e for e in ons(state) if e['port']==2 and e['bytes'][0]==145]
        state=c.wait(lambda state:len(refs(state))>=2*len(active)+1)
        ref=refs(state);assert len(ref)==2*len(active)+1
        opportunities=[4*cycle+step-1 for cycle in range(2) for step in active]+[0+8]
        assert [(e['port'],e['bytes']) for e in ref]==[(2,[145,(60,62,64,65)[i%4],(127,117,107,97)[i%4]]) for i in opportunities]
        selected=[e for e in ons(state) if e['port']==1 and e['bytes'][0]==144]
        target_steps=[4*cycle+step-1 for cycle in range(2) for step in accepted]
        assert [(e['port'],e['bytes']) for e in selected]==[(1,[144,(60,62,64,65)[i%4],(127,117,107,97)[i%4]]) for i in target_steps]
        assert len(ons(state))==len(ref)+len(selected)
        cc=[e for e in state['midi'] if e['index']>before and e['bytes'][0]&240==176]
        lock_steps=[i for i in range(9) if i%4+1 in active or trigless]
        packets=[]
        if nrpn:
            assert len(cc)==4*len(lock_steps)
            for i,step in enumerate(lock_steps):
                group=cc[4*i:4*i+4];v=values[step%4]
                assert [(e['port'],e['bytes']) for e in group]==[(1,[176,99,4]),(1,[176,98,5]),(1,[176,6,v//128]),(1,[176,38,v%128])]
                packets.append(group[-1])
        else:
            assert [(e['port'],e['bytes']) for e in cc]==[(1,[176,1,values[i%4]]) for i in lock_steps]
            packets=cc
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        origin=ref[0][field]
        for events,indexes in [(ref,opportunities),(selected,target_steps),(packets,lock_steps)]:
            errors=[(e[field]-origin)/1e9-i/6 for e,i in zip(events,indexes)]
            assert all(abs(e)<=tolerance for e in errors),errors
        for note,step in zip(selected,target_steps):
            packet=packets[lock_steps.index(step)]
            assert packet['index']<note['index'],'MIDI lock must precede accepted note'
        c.tap(1,8);c.wait(lambda state:state['midi_capture']['outstanding']==[])
        assert_durations(c,ref,[1]*(len(ref)-1))
        if selected:assert_durations(c,selected,[1]*len(selected))
        c.results.append(dict(kind='probability-trigless-midi-locks',nrpn=nrpn,trigless=trigless,phase=label,active_steps=active,accepted_steps=accepted,lock_opportunities=lock_steps,passed=True))
    phase([1,2,3,4],[],'probability0-active-trigs-retain-locks')
    c.tap(5,8);c.tap(3,4);c.tap(3,8)
    phase([1,2,4],[],'removed-trig-respects-trigless')
    c.action(type='grid',x=4,y=4,state=1)
    try:c.elapse(.05);c.action(type='enc',n=3,delta=-126);c.elapse(.15);c.enc(3,101)
    finally:c.action(type='grid',x=4,y=4,state=0)
    c.elapse(.15)
    phase([1,2,4],[4],'step-probability100-keeps-lock-before-note')


def live_parameter_recording(c):
    from cases import assign_trig_parameter,menu_value
    from patch_params import open_patch_control,turn
    open_patch_control(c);turn(c,63);turn(c,1);menu_value(c,'63');c.key(1)
    c.enc(1,-3);assign_trig_parameter(c,'CC 1')
    for step,value in [(1,24),(3,96)]:
        c.action(type='grid',x=step,y=4,state=1)
        try:c.elapse(.05);c.action(type='enc',n=3,delta=-126);c.enc(3,value+1)
        finally:c.action(type='grid',x=step,y=4,state=0)
    c.enc(1,2);c.enc(3,-23);c.key(3);c.enc(1,-2) # Four seconds per step.
    c.tap(2,8) # Native recording arm.
    before=c.snapshot()['midi_count'];c.tap(1,8)
    def notes(state):return [e for e in state['midi'] if e['index']>before and e['bytes'][0]==144 and e['bytes'][2]>0]
    first=c.wait(lambda state:len(notes(state))==1)
    assert notes(first)[0]['bytes']==[144,60,127]
    cc=[e['bytes'] for e in first['midi'] if e['index']>before and e['bytes'][0]==176]
    assert cc==[[176,1,63],[176,1,24]],cc # Stored patch recall precedes first lock.
    c.elapse(.5)
    edited_after=c.snapshot()['midi_count'];c.enc(3,1) # Authored default63 ->64.
    state=c.wait(lambda state:len(notes(state))>=4,timeout=14)
    captured=[e for e in state['midi'] if e['index']>edited_after and e['bytes'][0]==176]
    actual=[(e['port'],e['bytes']) for e in captured]
    c.results.append(dict(kind='live-parameter-recording-dirty-value',expected=[(1,[176,1,64])],actual=actual,meaning='Manual edit is sent immediately; old locks cannot overwrite it while recording their replacements.'))
    assert actual==[(1,[176,1,64])],dict(expected=[(1,[176,1,64])],actual=actual)
    assert [e['bytes'] for e in notes(state)]==[[144,n,v] for n,v in [(60,127),(62,117),(64,107),(65,97)]]
    c.tap(1,8);c.wait(lambda state:state['midi_capture']['outstanding']==[]);c.tap(2,8)
    c.key(1);menu_value(c,'64');c.key(1)
    c.enc(3,1) # Change default to65: output64 must now come from stored locks.
    c.key(1);menu_value(c,'65');c.key(1)
    # Disarmed playback proves the future steps were actually recorded, not
    # merely suppressed during the recording pass. Step1 already sounded before
    # the edit; steps2..4 receive64 through the end of this channel cycle.
    before=c.snapshot()['midi_count']
    played=c.playback([(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107),(65,97)]],cycles=2,timeout=36,settle_seconds=30)
    cc=[e for e in c.snapshot()['midi'] if e['index']>before and e['bytes'][0]==176]
    expected=[24,64,64,64]*2+[24]
    assert [(e['port'],e['bytes']) for e in cc]==[(1,[176,1,v]) for v in [65]+expected]
    cc=cc[1:] # Stored patch recall is separate from per-step lock dispatch.
    assert len(cc)==len(played)
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    for control,note in zip(cc,played):
        assert control['index']<note['index']
        assert abs((control[field]-note[field])/1e9)<=tolerance
    c.results.append(dict(kind='recorded-parameter-disarmed-replay',values=expected,distinct_patch_default=65,passed=True))
