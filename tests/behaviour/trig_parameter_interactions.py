"""Native stock-parameter precedence; literal MIDI and musical-time oracles."""

def fixed_note_domain(c,start=0,count=16):
    from cases import assert_durations
    assert 0<=start<128 and 1<=count<=16 and start+count<=128
    c.ui.configure();c.ui.channel_page('trig_locks',from_page='midi_config',confirm=False)
    c.ui.assign_trig_parameter_key('fixed_note')
    for parameter,value in [('quantised_fixed_note',7),('random_note',4),('twos_random_note',4)]:
        c.ui.turn(2,1);c.ui.assign_trig_parameter_key(parameter)
        c.ui.set_value(value+(1 if parameter=='quantised_fixed_note' else 0))
    c.ui.turn(2,-3);c.ui.set_value(start+1)
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
        if pitch>start:c.ui.set_value(1)
        phrase([pitch]*4,str(pitch))
    if start+count==128:
        c.ui.set_value(3);phrase([127]*4,'upper-clamp')
    # Disable all four sources using real encoder saturation, then require the
    # original four-note/velocity phrase. No inferred random-output golden.
    for slot in (1,2,3,4):
        if slot>1:c.ui.turn(2,1)
        c.elapse(.05);c.ui.encoder_event(3,-126);c.elapse(.15)
    phrase([60,62,64,65],'all-overrides-off')


def quantised_fixed_table(c,profile='major'):
    from cases import assert_durations
    # Literal musical tables, independent of Mosaic's quantiser. Root shifts
    # retain the scale's lower endpoint; ties choose the lower legal pitch.
    tables={
        'major':[(0,0),(1,0),(3,2),(6,5),(7,7),(11,11),(12,12),
                 (60,60),(61,60),(63,62),(66,65),(70,69),(126,125),(127,127)],
        'd-major':[(0,2),(1,2),(60,59),(61,61),(63,62),(127,127)],
        'a-harmonic-minor':[(125,125),(126,125),(127,125)],
    }
    assert profile in tables
    c.ui.configure()
    if profile!='major':
        c.ui.scale_editor()
        if profile=='a-harmonic-minor':c.ui.set_value(3) # Major -> Harmonic Minor
        c.ui.turn(2,-1);c.ui.set_value(9 if profile=='a-harmonic-minor' else 2)
        c.ui.press_key(3);c.ui.menu('channel_editor')
    c.ui.channel_page('trig_locks',from_page='midi_config',confirm=False);c.ui.assign_trig_parameter_key('quantised_fixed_note')
    previous=-1
    for value,pitch in tables[profile]:
        c.ui.set_value(value-previous);previous=value
        notes=c.playback([(1,[144,pitch,v]) for v in (127,117,107,97)],cycles=2)
        assert_durations(c,notes,[1]*(len(notes)-1))
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        errors=[(note[field]-notes[0][field])/1e9-i/6 for i,note in enumerate(notes)]
        assert all(abs(error)<=tolerance for error in errors),errors
        c.results.append(dict(kind='quantised-fixed-musical-table',profile=profile,input=value,pitch=pitch,timing_errors=errors,passed=True))


def stock_pitch_lock_inheritance(c,quantised=True):
    from cases import assert_durations
    c.ui.configure();c.ui.channel_page('trig_locks',from_page='midi_config',confirm=False)
    c.ui.assign_trig_parameter_key('quantised_fixed_note' if quantised else 'fixed_note')
    def phrase(pitches,phase):
        notes=c.playback([(1,[144,p,v]) for p,v in zip(pitches,(127,117,107,97))],cycles=2)
        assert_durations(c,notes,[1]*(len(notes)-1))
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        errors=[(n[field]-notes[0][field])/1e9-i/6 for i,n in enumerate(notes)]
        assert all(abs(e)<=tolerance for e in errors),errors
        c.results.append(dict(kind='stock-pitch-lock-inheritance',quantised=quantised,phase=phase,pitches=pitches,timing_errors=errors,passed=True))
    def lock(step,value):
        with c.ui.hold_step(step):
            c.elapse(.05);c.ui.encoder_event(3,-126);c.elapse(.15)
            if value>=0:c.ui.set_value(value+1)
        c.elapse(.15)
    def clear(step):
        with c.ui.hold_step(step):
            c.elapse(.05);c.ui.press_key(2)
        c.elapse(.15)
    c.ui.set_value(61);phrase([60]*4,'channel60')
    lock(2,63);locked=62 if quantised else 63
    phrase([60,locked,60,60],'step2-override')
    lock(1,0);phrase([0,locked,60,60],'zero-is-active')
    lock(4,-1);phrase([0,locked,60,60],'off-inherits')
    c.ui.set_value(5);phrase([0,locked,65,65],'default-edit-preserves-locks')
    clear(2);phrase([0,65,65,65],'clear-step2')
    c.ui.encoder_event(3,-126);c.elapse(.15)
    phrase([0,62,64,65],'channel-off-restores-pattern')
    clear(1);phrase([60,62,64,65],'clear-zero-restores-pattern')
    # Re-entering a cleared step must not reuse an old calculator/lock value.
    lock(2,0);phrase([60,0,64,65],'reenter-cleared-step-zero')
    clear(2);phrase([60,62,64,65],'second-clear-restores-pattern')


def competing_pitch_locks(c):
    from cases import assert_durations
    c.ui.configure();c.ui.channel_page('trig_locks',from_page='midi_config',confirm=False)
    c.ui.assign_trig_parameter_key('quantised_fixed_note');c.ui.set_value(66)
    c.ui.turn(2,1);c.ui.assign_trig_parameter_key('fixed_note');c.ui.set_value(61)
    def phrase(pitches,phase):
        notes=c.playback([(1,[144,p,v]) for p,v in zip(pitches,(127,117,107,97))],cycles=2)
        assert_durations(c,notes,[1]*(len(notes)-1))
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        errors=[(n[field]-notes[0][field])/1e9-i/6 for i,n in enumerate(notes)]
        assert all(abs(e)<=tolerance for e in errors),errors
        c.results.append(dict(kind='competing-stock-pitch-locks',phase=phase,pitches=pitches,timing_errors=errors,passed=True))
    def lock(step,value):
        c.ui.gesture([('step',step)],[])
        try:
            c.elapse(.05);c.ui.encoder_event(3,-126);c.elapse(.15)
            if value>=0:c.ui.set_value(value+1)
        finally:c.ui.gesture([],[('step',step)])
        c.elapse(.15)
    def clear(step):
        c.ui.gesture([('step',step)],[])
        try:c.elapse(.05);c.ui.press_key(2)
        finally:c.ui.gesture([],[('step',step)])
        c.elapse(.15)
    phrase([60]*4,'fixed-default-beats-quantised')
    c.ui.turn(2,-1);lock(1,63)
    phrase([60]*4,'fixed-default-beats-quantised-lock')
    c.ui.turn(2,1);lock(2,0);lock(3,-1)
    phrase([60,0,60,60],'fixed-zero-lock-and-off-inheritance')
    c.ui.encoder_event(3,-126);c.elapse(.15)
    phrase([62,0,65,65],'fixed-off-reveals-quantised-default-and-lock')
    c.ui.turn(2,-1);lock(4,0)
    phrase([62,0,65,0],'independent-zero-locks-on-two-slots')
    c.ui.encoder_event(3,-126);c.elapse(.15)
    phrase([62,0,64,0],'both-defaults-off-preserve-local-locks')
    clear(2);phrase([62,62,64,0],'clear-fixed-lock-only-step2')
    clear(1);phrase([60,62,64,0],'clear-quantised-lock-only-step1')
    clear(4);phrase([60,62,64,65],'full-original-phrase-restored')


def probability_endpoint_locks(c):
    from cases import assert_durations
    c.ui.configure();c.ui.channel_page('trig_locks',from_page='midi_config',confirm=False)
    c.ui.assign_trig_parameter_key('fixed_note');c.ui.set_value(66)
    c.ui.turn(2,1);c.ui.assign_trig_parameter_key('trig_probability')
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
        c.ui.gesture([('step',step)],[])
        try:
            c.elapse(.05);c.ui.encoder_event(3,-126);c.elapse(.15)
            c.ui.set_value(value+1)
        finally:c.ui.gesture([],[('step',step)])
        c.elapse(.15)
    def clear(step):
        c.ui.gesture([('step',step)],[])
        try:c.elapse(.05);c.ui.press_key(2)
        finally:c.ui.gesture([],[('step',step)])
        c.elapse(.15)
    c.ui.set_value(101);phrase([1,2,3,4],'100-always')
    c.ui.set_value(3);phrase([1,2,3,4],'upper-clamp100')
    c.ui.encoder_event(3,-126);c.elapse(.15);c.ui.set_value(1)
    # Include the very first onset opportunity in the silence window.
    before=c.snapshot()['midi_count'];c.ui.play();c.elapse(2.8)
    state=c.snapshot()
    notes=[e for e in state['midi'] if e['index']>before and e['bytes'][0]&240==144 and e['bytes'][2]>0]
    assert notes==[],notes
    assert state['midi_capture']['outstanding']==[]
    c.ui.stop()
    c.results.append(dict(kind='probability-zero-silence',seconds=2.8,note_ons=notes,fixed_pitch=65,passed=True))
    lock(2,100);phrase([2],'step100-overrides-channel0')
    c.ui.set_value(100);lock(1,0);phrase([2,3,4],'step0-overrides-channel100')
    lock(4,0);phrase([2,3],'first-and-wrap-step0')
    clear(1);phrase([1,2,3],'clear-first-zero')
    clear(4);phrase([1,2,3,4],'clear-wrap-zero')


def seeded_probability(c,probability=50,opportunities=64):
    from cases import assert_durations
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

    c.ui.configure()
    # A second channel carries the same authored four-step phrase at100%.
    # Its raw MIDI output independently exposes every opportunity, including
    # the first accepted note's position and the complete rejected tail.
    c.ui.select_channel(2);c.ui.expect_header('midi_config',channel=2)
    c.ui.set_value(1);c.ui.turn(2,1);c.ui.set_value(1);c.ui.turn(2,1);c.ui.set_value(1);c.ui.press_key(3)
    c.ui.tap_control('pattern_slot',1);c.ui.set_range(1,4);c.ui.expect_leds({('channel',2):'selected',('pattern_slot',1):'selected'})
    c.ui.select_channel(1);c.ui.channel_page('trig_locks',from_page='midi_config',confirm=False);c.ui.assign_trig_parameter_key('trig_probability');c.ui.set_value(probability+1)
    before=c.snapshot()['midi_count'];c.ui.play()
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
    c.ui.stop();c.wait(lambda state:state['midi_capture']['outstanding']==[])
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
    from cases import assert_durations
    c.ui.configure()
    if nrpn:c.ui.set_value(1);c.ui.press_key(3) # Generic CC -> existing configured NRPN fixture.
    c.ui.set_mosaic_option_keys([('trigless_locks',trigless)])
    c.ui.select_channel(2);c.ui.expect_header('midi_config',channel=2)
    c.ui.set_value(1);c.ui.turn(2,1);c.ui.set_value(1);c.ui.turn(2,1);c.ui.set_value(1);c.ui.press_key(3)
    c.ui.tap_control('pattern_slot',1);c.ui.set_range(1,4);c.ui.select_channel(1);c.ui.channel_page('trig_locks',from_page='midi_config',confirm=False)
    c.ui.assign_trig_parameter_key('nrpn14' if nrpn else 'stored_patch_cc1')
    values=[126,253,126,253] if nrpn else [24,48,72,96]
    for step,value in enumerate(values,1):
        c.ui.gesture([('step',step)],[])
        try:
            c.elapse(.05);c.ui.encoder_event(3,-126)
            c.ui.set_value((1 if value==126 else 2) if nrpn else value+1)
            if nrpn:
                with c.ui.hold_keys(1):
                    c.elapse(.3)
                    c.ui.set_value(-2 if value==126 else -4)
        finally:c.ui.gesture([],[('step',step)])
    c.ui.turn(2,1);c.ui.assign_trig_parameter_key('trig_probability');c.ui.set_value(1)
    def phase(active,accepted,label):
        before=c.snapshot()['midi_count'];c.ui.play()
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
        c.ui.stop();c.wait(lambda state:state['midi_capture']['outstanding']==[])
        assert_durations(c,ref,[1]*(len(ref)-1))
        if selected:assert_durations(c,selected,[1]*len(selected))
        c.results.append(dict(kind='probability-trigless-midi-locks',nrpn=nrpn,trigless=trigless,phase=label,active_steps=active,accepted_steps=accepted,lock_opportunities=lock_steps,passed=True))
    phase([1,2,3,4],[],'probability0-active-trigs-retain-locks')
    c.ui.pattern_editor();c.ui.tap_step(3);c.ui.menu('channel_editor')
    phase([1,2,4],[],'removed-trig-respects-trigless')
    c.ui.gesture([('step',4)],[])
    try:c.elapse(.05);c.ui.encoder_event(3,-126);c.elapse(.15);c.ui.set_value(101)
    finally:c.ui.gesture([],[('step',4)])
    c.elapse(.15)
    phase([1,2,4],[4],'step-probability100-keeps-lock-before-note')


def recorded_edit_receipt(c):
    """One normal encoder detent, retaining its public applied-input receipt."""
    c.elapse(.05)
    receipt=c.ui.encoder_event(3,2)
    c.elapse(.15)
    return receipt


def assert_immediate_cc_on_edit(control,receipt):
    """Require the audible MIDI response at the applied encoder input."""
    assert isinstance(receipt,dict) and receipt.get('status')=='applied',receipt
    native=receipt.get('native')
    assert isinstance(native,dict) and type(native.get('monotonic_ns')) is int,receipt
    applied_ns=native['monotonic_ns']
    assert type(control.get('monotonic_ns')) is int,control
    delay_ns=control['monotonic_ns']-applied_ns
    assert abs(delay_ns)<=10_000_000,dict(delay_ns=delay_ns,applied_ns=applied_ns,control=control)
    return delay_ns


def live_parameter_recording(c,switch_return=False,empty_step=False,scale_page=False,edit_value=64,trigless=True,probability_zero=False):
    c.ui.configure()
    assert not (empty_step and probability_zero)
    if empty_step or probability_zero:c.ui.set_mosaic_option_keys([('trigless_locks',trigless)])
    c.ui.open_patch_control(setup=False);c.ui.turn_patch_control(63);c.ui.turn_patch_control(1);c.ui.expect_patch_value(63);c.ui.press_key(1)
    c.ui.channel_page('trig_locks',from_page='midi_config',confirm=False);c.ui.assign_trig_parameter_key('stored_patch_cc1')
    for step,value in [(1,24),(3,96)]:
        c.ui.gesture([('step',step)],[])
        try:c.elapse(.05);c.ui.encoder_event(3,-126);c.ui.set_value(value+1)
        finally:c.ui.gesture([],[('step',step)])
    if probability_zero:
        c.ui.turn(2,1);c.ui.assign_trig_parameter_key('trig_probability')
        c.ui.gesture([('step',3)],[])
        try:c.elapse(.05);c.ui.encoder_event(3,-126);c.ui.set_value(1)
        finally:c.ui.gesture([],[('step',3)])
        c.ui.turn(2,-1)
    if empty_step:
        c.ui.pattern_editor();c.ui.tap_step(3);c.ui.menu('channel_editor') # Remove note3 through pattern editor.
    c.ui.channel_page('clock_mods',from_page='trig_locks',confirm=False);c.ui.set_value(-23);c.ui.press_key(3);c.ui.channel_page('trig_locks',from_page='clock_mods',confirm=False) # Four seconds per step.
    c.ui.tap_control('record') # Native recording arm.
    before=c.snapshot()['midi_count'];c.ui.play()
    def notes(state):return [e for e in state['midi'] if e['index']>before and e['bytes'][0]==144 and e['bytes'][2]>0]
    first=c.wait(lambda state:len(notes(state))==1)
    assert notes(first)[0]['bytes']==[144,60,127]
    cc=[e['bytes'] for e in first['midi'] if e['index']>before and e['bytes'][0]==176]
    assert cc==[[176,1,63],[176,1,24]],cc # Stored patch recall precedes first lock.
    c.elapse(.5)
    edited_after=c.snapshot()['midi_count']
    edit_receipt=None
    if edit_value==64:edit_receipt=recorded_edit_receipt(c)
    else:
        assert edit_value in (-1,0)
        c.ui.encoder_event(3,-126);c.elapse(.15) # Saturate to Off.
        if edit_value==0:edit_receipt=recorded_edit_receipt(c)
    if switch_return:
        c.ui.scale_editor() if scale_page else c.ui.select_channel(2) # Pause via global scale editor or channel2.
        paused=c.wait(lambda state:len(notes(state))>=3,timeout=10)
        old=[e for e in paused['midi'] if e['index']>edited_after and e['bytes'][0]==176]
        assert old[-1]['bytes']==[176,1,96],old
        c.elapse(.3)
        c.ui.menu('channel_editor') if scale_page else c.ui.select_channel(1)
    silent_step=empty_step or probability_zero
    state=c.wait(lambda state:len(notes(state))>=(3 if silent_step else 4),timeout=14)
    captured=[e for e in state['midi'] if e['index']>edited_after and e['bytes'][0]==176]
    actual=[(e['port'],e['bytes']) for e in captured]
    live_repetitions=3 if empty_step and not trigless else 4
    wanted=[] if edit_value==-1 else [(1,[176,1,edit_value])]*live_repetitions
    c.results.append(dict(kind='live-parameter-recording-dirty-value',expected=wanted if not switch_return else None,actual=actual,meaning='Active edited values emit immediately and on eligible steps; Off remains silent.'))
    live_value=actual[-1][1][2] if actual else None
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    if not switch_return:
        assert actual==wanted,dict(expected=wanted,actual=actual)
        # Separate the immediate encoder emission from later step dispatches.
        # The edit lands .61 seconds after step1; eligible future boundaries are
        # steps2/3/4 at 4/8/12 seconds. A removed rest is skipped only when the
        # option is Off; an authored probability-zero trig remains eligible.
        boundary_offsets=[4,12] if empty_step and not trigless else [4,8,12]
        actual_offsets=[(e[field]-notes(state)[0][field])/1e9 for e in captured]
        immediate_offset=.76 if edit_value==0 else .61
        expected_offsets=[] if edit_value==-1 else [immediate_offset]+boundary_offsets
        assert len(actual_offsets)==len(expected_offsets)
        if expected_offsets:
            if c.clock_mode=='controlled-experimental':
                assert abs(actual_offsets[0]-expected_offsets[0])<=2e-9,dict(actual=actual_offsets,expected=expected_offsets)
            else:
                # Host-side sleeps, polling and RPCs do not determine when the
                # encoder is applied. Retain the same 10 ms MIDI response bound
                # against the public input acknowledgement instead.
                delay_ns=assert_immediate_cc_on_edit(captured[0],edit_receipt)
                c.results.append(dict(kind='live-parameter-immediate-input',delay_ns=delay_ns,
                                      max_abs_delay_ns=10_000_000,passed=True))
            assert all(abs(actual-wanted)<=tolerance for actual,wanted in zip(actual_offsets[1:],expected_offsets[1:])),dict(actual=actual_offsets,expected=expected_offsets)
    else:
        assert actual==[(1,[176,1,v]) for v in [64,64,96,64]],actual
        assert captured[-1]['index']<notes(state)[-1]['index']
        assert abs(captured[-1][field]-notes(state)[-1][field])<=(2 if c.clock_mode=='controlled-experimental' else 10000000)
    phrase=[(60,127),(62,117)]+([] if silent_step else [(64,107)])+[(65,97)]
    live_notes=notes(state);assert [e['bytes'] for e in live_notes]==[[144,n,v] for n,v in phrase]
    if not switch_return:
        note_offsets=[0,4,12] if silent_step else [0,4,8,12]
        notes_by_offset=dict(zip(note_offsets,live_notes))
        for control,offset in zip(captured[1:],boundary_offsets):
            if offset in notes_by_offset:
                note=notes_by_offset[offset]
                assert control['index']<note['index'],'Recorded control must precede its audible note'
                assert abs((control[field]-note[field])/1e9)<=tolerance
    # Disarm just before wrap, then observe the final intended gate complete
    # naturally. Stop only the extra wrap onset, which cannot alter stored locks.
    import time
    origin_live=live_notes[0][field]
    now=lambda:c.logical_ns if c.clock_mode=='controlled-experimental' else time.monotonic_ns()
    remaining=origin_live+15_800_000_000-now();assert remaining>0;c.elapse(remaining/1e9)
    c.ui.tap_control('record')
    remaining=origin_live+16_200_000_000-now();assert remaining>0;c.elapse(remaining/1e9)
    c.ui.stop();c.wait(lambda state:state['midi_capture']['outstanding']==[])
    live_events=[e for e in c.snapshot()['midi'] if e['index']>before]
    from note_accounting import note_pairs
    pairs=note_pairs(live_events);assert [on for on,off in pairs[:len(live_notes)]]==live_notes
    assert len(pairs)==len(live_notes)+1 and pairs[-1][0]['bytes']==[144,60,127]
    from cases import assert_durations
    assert_durations(c,live_notes,[24]*len(live_notes),events=live_events)
    c.ui.press_key(1);c.ui.expect_patch_value('off' if edit_value==-1 else edit_value);c.ui.press_key(1)
    c.ui.set_value(65-edit_value) # Distinct default proves stored locks independently.
    c.ui.press_key(1);c.ui.expect_patch_value(65);c.ui.press_key(1)
    if empty_step and not trigless:
        # Native params reopens at the prior device control. Return through its
        # group list to a stable root before selecting Mosaic options.
        c.ui.press_key(1);c.ui.press_key(2);c.ui.turn(2,-60);c.ui.expect_native_menu_label('levels_root');c.ui.press_key(2);c.ui.press_key(1)
        # Reveal the silent step's stored value during replay. If recording while
        # disabled overwrote it, the expected96 below becomes64 and fails.
        c.ui.set_mosaic_option_keys([('trigless_locks',True)])
    # Disarmed playback proves the future steps were actually recorded, not
    # merely suppressed during the recording pass. Step1 already sounded before
    # the edit; steps2..4 receive64 through the end of this channel cycle.
    before=c.snapshot()['midi_count']
    played=c.playback([(1,[144,n,v]) for n,v in phrase],cycles=2,timeout=36,settle_seconds=30)
    cc=[e for e in c.snapshot()['midi'] if e['index']>before and e['bytes'][0]==176]
    values=([24,65,96,64] if switch_return else [24,edit_value,96,edit_value] if empty_step and not trigless else [24,edit_value,edit_value,edit_value])
    expected=values*2+[24]
    emitted_steps=[i for i,value in enumerate(expected) if value!=-1]
    assert [(e['port'],e['bytes']) for e in cc]==[(1,[176,1,v]) for v in [65]+expected if v!=-1]
    cc=cc[1:] # Stored patch recall is separate from per-step lock dispatch.
    assert len(cc)==len(emitted_steps)
    assert len(played)==(7 if silent_step else 9)
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    replay_events=[e for e in c.snapshot()['midi'] if e['index']>before]
    replay_pairs=note_pairs(replay_events);assert [on for on,off in replay_pairs]==played
    assert_durations(c,played,[24]*(len(played)-1),events=replay_events)
    origin=played[0][field]
    for i,control in zip(emitted_steps,cc):
        assert abs((control[field]-origin)/1e9-i*4)<=tolerance,dict(step=i,control=control,origin=origin)
    note_steps=[i for i in range(9) if not silent_step or i%4!=2]
    notes_by_step=dict(zip(note_steps,played))
    for i,control in zip(emitted_steps,cc):
        if i not in notes_by_step:continue
        note=notes_by_step[i]
        assert control['index']<note['index']
        assert abs((control[field]-note[field])/1e9)<=tolerance
    c.results.append(dict(kind='recorded-parameter-disarmed-replay',values=expected,distinct_patch_default=65,passed=True))
    if switch_return:
        c.results.append(dict(kind='recording-switch-return-live-replay',live_step4_value=live_value,recorded_step4_value=expected[3],passed=live_value==expected[3]))
        assert live_value==expected[3],dict(live_step4=live_value,recorded_step4=expected[3],meaning='Resumed recorded value must match the value heard at that step')


def recording_trigless_toggle(c):
    """Mid-recording option changes use authored-trigger eligibility immediately."""
    import time
    from cases import assert_durations,menu_label,menu_option_row,set_mosaic_options
    from midi_window import MidiWindow
    from note_accounting import note_pairs
    c.ui.configure();c.ui.set_mosaic_option_keys([('trigless_locks',False)])
    c.ui.channel_page('trig_locks',from_page='midi_config',confirm=False);c.ui.assign_trig_parameter_key('stored_patch_cc1')
    for step,value in enumerate((24,48,96,120),1):
        c.ui.gesture([('step',step)],[])
        try:c.elapse(.05);c.ui.encoder_event(3,-126);c.ui.set_value(value+1)
        finally:c.ui.gesture([],[('step',step)])
    c.ui.encoder_event(3,-126);c.elapse(.15);c.ui.set_value(65) # Explicit default64.
    c.ui.pattern_editor();c.ui.tap_step(2);c.ui.tap_step(3);c.ui.menu('channel_editor')
    c.ui.channel_page('clock_mods',from_page='trig_locks',confirm=False);c.ui.set_value(-29);c.ui.press_key(3);c.ui.channel_page('trig_locks',from_page='clock_mods',confirm=False) # /48: eight seconds per step.
    c.ui.tap_control('record');capture=MidiWindow(c.snapshot()['midi_count'])
    c.ui.gesture([('play_stop',None)],[('play_stop',None)])
    def now():return c.logical_ns if c.clock_mode=='controlled-experimental' else time.monotonic_ns()
    origin=now();c.elapse(.5)
    edit_receipt=c.ui.set_value(1) # Timed live edit64 to65.
    def reach(seconds):
        remaining=origin+round(seconds*1e9)-now();assert remaining>0
        c.elapse(remaining/1e9)
    # Open Trigless locks once and leave it selected for both live transitions.
    reach(1);c.ui.open_native_parameters(observe_entry=False)
    c.ui.seek_native_parameter_root('mosaic');c.ui.press_key(3)
    c.ui.seek_mosaic_option('trigless_locks',failure='Trigless option not reached during recording')
    assert now()<origin+7_000_000_000
    reach(8.2);c.ui.set_value(3);c.ui.expect_mosaic_option('trigless_locks',True)
    reach(16.2);c.ui.set_value(-3);c.ui.expect_mosaic_option('trigless_locks',False)
    # Disarm before wrap so step4 can complete its natural eight-second gate
    # without recording the next step1. Observe that wrap, then Stop the new gate.
    reach(31.8);c.ui.tap_control('record');reach(32.2);capture.extend(c.snapshot())
    c.ui.gesture([('play_stop',None)],[('play_stop',None)])
    c.wait(lambda state:capture.extend(state) and not state['midi_capture']['outstanding'])
    notes=capture.note_ons();assert [(e['port'],e['bytes']) for e in notes]==[(1,[144,60,127]),(1,[144,65,97]),(1,[144,60,127])]
    pairs=note_pairs(capture.events);assert len(pairs)==3 and [on for on,off in pairs]==notes
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns';tol=2e-9 if c.clock_mode=='controlled-experimental' else .01
    for on,off in pairs[:2]:assert abs((off[field]-on[field])/1e9-8)<=tol
    assert .19<=(pairs[2][1][field]-pairs[2][0][field])/1e9<=.31,'Stop must release the wrap note promptly'
    live_cc=[e for e in capture.events if e['bytes'][0]&240==176]
    assert [(e['port'],e['bytes']) for e in live_cc]==[(1,[176,1,v]) for v in (64,24,65,65,65,24)]
    offsets=[(e[field]-notes[0][field])/1e9 for e in live_cc]
    for index,(actual,wanted) in enumerate(zip(offsets,(0,0,.55,16,24,32))):
        if index==2 and c.clock_mode!='controlled-experimental':
            assert_immediate_cc_on_edit(live_cc[index],edit_receipt)
        else:
            assert abs(actual-wanted)<=tol,(offsets,wanted)
    for control,note in ((live_cc[1],notes[0]),(live_cc[4],notes[1]),(live_cc[5],notes[2])):
        assert control['index']<note['index'] and abs((control[field]-note[field])/1e9)<=tol
    c.ui.set_value(3);c.ui.expect_mosaic_option('trigless_locks',True)
    c.ui.press_key(2);c.ui.encoder_event(2,-126);c.elapse(.15);c.ui.expect_native_menu_label('levels_root');c.ui.press_key(2);c.ui.press_key(1)
    c.ui.set_value(1)
    before=c.snapshot()['midi_count']
    played=c.playback([(1,[144,60,127]),(1,[144,65,97])],cycles=2,timeout=80,settle_seconds=60)
    events=[e for e in c.snapshot()['midi'] if e['index']>before]
    cc=[e for e in events if e['bytes'][0]&240==176]
    values=[66]+[24,48,65,65,24,48,65,65,24]
    assert [(e['port'],e['bytes']) for e in cc]==[(1,[176,1,v]) for v in values]
    steps=(0,1,2,3,4,5,6,7,8);origin2=played[0][field]
    for event,step in zip(cc[1:],steps):assert abs((event[field]-origin2)/1e9-step*8)<=tol
    note_steps=(0,3,4,7,8)
    for note,step in zip(played,note_steps):
        assert abs((note[field]-origin2)/1e9-step*8)<=tol
        control=cc[1+step];assert control['index']<note['index'] and abs((control[field]-note[field])/1e9)<=tol
    replay_pairs=note_pairs(events);assert [on for on,off in replay_pairs]==played
    assert_durations(c,played,[48]*(len(played)-1),events=events)
    c.results.append(dict(kind='recording-trigless-live-toggle',live_values=[64,24,65,65,65,24],
                          replay_values=values[1:],transitions=['off','on','off','on-for-replay'],passed=True))

def cc_encoder_domain(c,configured=True):
    c.ui.configure()
    if configured:c.ui.set_value(1);c.ui.press_key(3)
    c.ui.channel_page('trig_locks',from_page='midi_config',confirm=False);c.ui.assign_trig_parameter_key('configured_control_1' if configured else 'stored_patch_cc1')
    c.ui.channel_page('clock_mods',from_page='trig_locks',confirm=False);c.ui.set_value(-8);c.ui.press_key(3);c.ui.channel_page('trig_locks',from_page='clock_mods',confirm=False) # One-second step avoids host input latency overlap.
    tested=[]
    for expected in list(range(128))+[127,-1,0]:
        c.ui.gesture([('step',1)],[])
        try:
            if expected==-1:c.elapse(.05);c.ui.encoder_event(3,-126);c.elapse(.15)
            else:c.ui.set_value(1)
        finally:c.ui.gesture([],[('step',1)])
        before=c.snapshot()['midi_count'];c.ui.play()
        def notes(state):return [e for e in state['midi'] if e['index']>before and e['bytes'][0]&240==144 and e['bytes'][2]>0]
        state=c.wait(lambda state:len(notes(state))>=1)
        assert [(e['port'],e['bytes']) for e in notes(state)]==[(1,[144,60,127])]
        cc=[e for e in state['midi'] if e['index']>before and e['bytes'][0]&240==176]
        wanted=[] if expected==-1 else [(1,[176,1,expected])]
        actual=[(e['port'],e['bytes']) for e in cc]
        assert actual==wanted,dict(configured=configured,encoder_detent=len(tested)+1,expected=wanted,actual=actual)
        if cc:assert cc[0]['index']<notes(state)[0]['index']
        c.ui.stop();c.wait(lambda state:not state['midi_capture']['outstanding'])
        tested.append(expected)
    c.results.append(dict(kind='CC-editor-every-detent-native-MIDI',configured=configured,values=tested,includes_clamp_Off_reentry=True,passed=True))


def sparse_editor_domain(c,domain):
    assert domain in ('SparseLow','SparseHigh','NS0','NS6')
    c.ui.configure();c.ui.set_value(1);c.ui.press_key(3);c.ui.channel_page('trig_locks',from_page='midi_config',confirm=False);c.ui.assign_trig_parameter_key({'SparseLow':'sparse_low','SparseHigh':'sparse_high','NS0':'ns0','NS6':'ns6'}[domain])
    c.ui.channel_page('clock_mods',from_page='trig_locks',confirm=False);c.ui.set_value(-8);c.ui.press_key(3);c.ui.channel_page('trig_locks',from_page='clock_mods',confirm=False)
    if domain=='SparseLow':
        operations=[(1,v) for v in range(100,128)]+[(1,127)]+[(-1,v) for v in range(126,99,-1)]+[(-1,None),(-1,None),(1,100)]
    elif domain=='SparseHigh':
        operations=[(1,None)]+[(-1,v) for v in range(127,99,-1)]+[(-1,100)]+[(1,v) for v in range(101,128)]+[(1,None),(1,None),(-1,127)]
    else:
        value=0 if domain=='NS0' else 16383
        operations=[(1,value),(1,value),(-1,None),(-1,None),(1,value)]*2
    checked=[]
    for i,(direction,value) in enumerate(operations):
        fine=i%2==0
        c.ui.gesture([('step',1)],[])
        try:
            if fine:
                with c.ui.hold_keys(1):
                    c.elapse(.3)
                    c.ui.set_value(direction)
            else:c.ui.set_value(direction)
        finally:c.ui.gesture([],[('step',1)])
        start=c.snapshot()['midi_count'];c.ui.play()
        def notes(state):return [e for e in state['midi'] if e['index']>start and e['bytes'][0]&240==144 and e['bytes'][2]>0]
        state=c.wait(lambda state:len(notes(state))>=1)
        assert [(e['port'],e['bytes']) for e in notes(state)]==[(1,[144,60,127])]
        cc=[e for e in state['midi'] if e['index']>start and e['bytes'][0]&240==176]
        if value is None:wanted=[]
        elif domain.startswith('NS'):
            address=0 if domain=='NS0' else 6
            wanted=[(1,[177,99,6]),(1,[177,98,address]),(1,[177,6,value//128]),(1,[177,38,value%128])]
        else:wanted=[(1,[176,2 if domain=='SparseLow' else 3,value])]
        actual=[(e['port'],e['bytes']) for e in cc]
        assert actual==wanted,dict(domain=domain,operation=i,direction=direction,fine=fine,expected=wanted,actual=actual)
        assert all(e['index']<notes(state)[0]['index'] for e in cc)
        c.ui.stop();c.wait(lambda state:not state['midi_capture']['outstanding'])
        checked.append(dict(direction=direction,value=value,fine=fine))
    c.results.append(dict(kind='native-sparse-singleton-editor-domain',domain=domain,operations=checked,clamp_and_Off=True,passed=True))


def pending_parameter_lock_song_transition(c):
    """A held parameter edit belongs to the song slot active at first press."""
    c.ui.configure()
    c.ui.open_patch_control(setup=False);c.ui.turn_patch_control(63);c.ui.turn_patch_control(1);c.ui.expect_patch_value(63);c.ui.press_key(1)
    c.ui.channel_page('trig_locks',from_page='midi_config',confirm=False);c.ui.assign_trig_parameter_key('stored_patch_cc1')
    def lock(step,value):
        c.ui.gesture([('step',step)],[])
        try:
            c.elapse(.05);c.ui.encoder_event(3,-126);c.ui.set_value(value+1)
        finally:c.ui.gesture([],[('step',step)])
    lock(2,24)
    # Slot 2 is a copy with a distinct octave and step-2 lock.
    c.ui.song_editor();c.ui.tap_control('global_pattern_length',2)
    for _ in range(7):c.ui.tap_control('global_pattern_length',8)
    c.ui.copy_slot(1,2,control='song_pattern_slot');c.ui.tap_control('song_pattern_slot',2);c.ui.expect_leds({('song_pattern_slot',1):'alternate',('song_pattern_slot',2):'selected'})
    c.ui.menu('channel_editor');c.ui.tap_control('channel_octave',1);lock(2,96)
    c.ui.song_editor();c.ui.tap_control('song_pattern_slot',1);c.ui.expect_leds({('song_pattern_slot',1):'selected',('song_pattern_slot',2):'alternate'})
    c.ui.menu('channel_editor');c.ui.expect_header('trig_locks',channel=1)

    marker=c.snapshot()['midi_count'];c.ui.play()
    def onsets(state,after=marker):
        return [e for e in state['midi'] if e['index']>after and e['bytes'][0]==144 and e['bytes'][2]>0]
    first=c.wait(lambda state:len(onsets(state))>=1,timeout=3)
    assert onsets(first)[0]['bytes']==[144,60,127]
    c.ui.gesture([('step',2)],[])
    try:
        c.elapse(.05);c.ui.encoder_event(3,-126);c.elapse(.15);c.ui.set_value(1)
        # Value zero is queued while slot 1 owns the gesture. Keep it held
        # across the actual boundary, whose octave proves slot 2 is live.
        crossed=c.wait(lambda state:any(e['bytes']==[144,72,127] for e in onsets(state)),timeout=12)
        assert any(e['bytes']==[144,72,127] for e in onsets(crossed))
    finally:c.ui.gesture([],[('step',2)])
    c.ui.stop();c.wait(lambda state:not state['midi_capture']['outstanding'])
    c.ui.song_editor();c.ui.expect_leds({('song_pattern_slot',1):'alternate',('song_pattern_slot',2):'selected'})
    c.ui.menu('channel_editor')

    def select_slot(slot):
        c.ui.song_editor();c.ui.tap_control('song_pattern_slot',slot);c.ui.menu('channel_editor');c.ui.expect_header('trig_locks',channel=1)
    # A distinct unheld default separates locks from ordinary values in both slots.
    for slot in (1,2):
        select_slot(slot)
        c.ui.encoder_event(3,-126);c.elapse(.15);c.ui.set_value(66)

    def replay(slot,pitches,step_two):
        select_slot(slot);start=c.snapshot()['midi_count'];c.ui.play()
        state=c.wait(lambda current:len(onsets(current,start))>=4,timeout=8)
        notes=onsets(state,start)[:4];cutoff=notes[-1]['index']
        cc=[e for e in state['midi'] if start<e['index']<=cutoff and e['bytes'][:2]==[176,1]]
        expected_notes=[[144,pitch,velocity] for pitch,velocity in zip(pitches,(127,117,107,97))]
        expected_cc=[[176,1,value] for value in (65,65,step_two,65,65)]
        assert [e['bytes'] for e in notes]==expected_notes,(slot,notes,expected_notes)
        assert [e['bytes'] for e in cc]==expected_cc,(slot,cc,expected_cc)
        for control,note in zip(cc[1:],notes):assert control['index']<note['index']
        c.ui.stop();c.wait(lambda current:not current['midi_capture']['outstanding'])
        return dict(slot=slot,pitches=pitches,controls=expected_cc,passed=True)
    slot1=replay(1,[60,62,64,65],0)
    slot2=replay(2,[72,74,76,77],96)
    c.results.append(dict(kind='pending-parameter-lock-song-transition',slot1=slot1,slot2=slot2,held_value=0,passed=True))
