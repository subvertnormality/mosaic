"""Unchanged NAV-PAGES recording contract; README recording and page controls."""

def recorded_edit_receipt(c):
    """One normal encoder detent, retaining its public applied-input receipt."""
    c.elapse(.05)
    receipt=c.action(type='enc',n=3,delta=2)
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
    from cases import assign_trig_parameter,menu_label,menu_value
    from patch_params import open_patch_control,turn
    c.configure()
    assert not (empty_step and probability_zero)
    if empty_step or probability_zero:c.ui.set_mosaic_options([('Trigless locks',trigless)])
    open_patch_control(c,setup=False);turn(c,63);turn(c,1);menu_value(c,'63');c.key(1)
    c.enc(1,-3);assign_trig_parameter(c,'CC 1')
    for step,value in [(1,24),(3,96)]:
        c.action(type='grid',x=step,y=4,state=1)
        try:c.elapse(.05);c.action(type='enc',n=3,delta=-126);c.enc(3,value+1)
        finally:c.action(type='grid',x=step,y=4,state=0)
    if probability_zero:
        c.enc(2,1);assign_trig_parameter(c,'Trig Probability')
        c.action(type='grid',x=3,y=4,state=1)
        try:c.elapse(.05);c.action(type='enc',n=3,delta=-126);c.enc(3,1)
        finally:c.action(type='grid',x=3,y=4,state=0)
        c.enc(2,-1)
    if empty_step:
        c.tap(5,8);c.tap(3,4);c.tap(3,8) # Remove note3 through pattern editor.
    c.enc(1,2);c.enc(3,-23);c.key(3);c.enc(1,-2) # Four seconds per step.
    c.tap(2,8) # Native recording arm.
    before=c.snapshot()['midi_count'];c.tap(1,8)
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
        c.action(type='enc',n=3,delta=-126);c.elapse(.15) # Saturate to Off.
        if edit_value==0:edit_receipt=recorded_edit_receipt(c)
    if switch_return:
        c.tap(4,8) if scale_page else c.tap(2,1) # Pause via global scale editor or channel2.
        paused=c.wait(lambda state:len(notes(state))>=3,timeout=10)
        old=[e for e in paused['midi'] if e['index']>edited_after and e['bytes'][0]==176]
        assert old[-1]['bytes']==[176,1,96],old
        c.elapse(.3)
        c.tap(3,8) if scale_page else c.tap(1,1)
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
    c.tap(2,8)
    remaining=origin_live+16_200_000_000-now();assert remaining>0;c.elapse(remaining/1e9)
    c.tap(1,8);c.wait(lambda state:state['midi_capture']['outstanding']==[])
    live_events=[e for e in c.snapshot()['midi'] if e['index']>before]
    from note_accounting import note_pairs
    pairs=note_pairs(live_events);assert [on for on,off in pairs[:len(live_notes)]]==live_notes
    assert len(pairs)==len(live_notes)+1 and pairs[-1][0]['bytes']==[144,60,127]
    from cases import assert_durations
    assert_durations(c,live_notes,[24]*len(live_notes),events=live_events)
    c.key(1);menu_value(c,'X' if edit_value==-1 else str(edit_value));c.key(1)
    c.enc(3,65-edit_value) # Distinct default proves stored locks independently.
    c.key(1);menu_value(c,'65');c.key(1)
    if empty_step and not trigless:
        # Native params reopens at the prior device control. Return through its
        # group list to a stable root before selecting Mosaic options.
        c.key(1);c.key(2);c.enc(2,-60);menu_label(c,'LEVELS >');c.key(2);c.key(1)
        # Reveal the silent step's stored value during replay. If recording while
        # disabled overwrote it, the expected96 below becomes64 and fails.
        c.ui.set_mosaic_options([('Trigless locks',True)])
    # Disarmed playback proves the future steps were actually recorded, not
    # merely suppressed during the recording pass. Step1 already sounded before
    # the edit; steps2..4 receive64 through the end of this channel cycle.
    before=c.snapshot()['midi_count']
    returned=c.playback([(1,[144,n,v]) for n,v in phrase],cycles=2,timeout=36,settle_seconds=30)
    replay_events=[e for e in c.snapshot()['midi'] if e['index']>before]
    cc=[e for e in replay_events if e['bytes'][0]==176]
    values=([24,65,96,64] if switch_return else [24,edit_value,96,edit_value] if empty_step and not trigless else [24,edit_value,edit_value,edit_value])
    expected=values*2+[24]
    assert len(returned)==(7 if silent_step else 9)
    # The window runs until Stop takes effect. In real time a further step may
    # land first: an onset must continue the phrase on the 4 s step lattice
    # (a silent pattern step3 has none), and only a silent step's lock may
    # follow the last onset. Controlled time admits neither.
    from note_accounting import continuation_onsets,window_onsets
    def note_step(i):return 4*(i//3)+(0,1,3)[i%3] if silent_step else i
    played=window_onsets(replay_events)
    late=continuation_onsets(c,returned,played,[(1,[144,n,v]) for n,v in phrase],lambda i:note_step(i)*4)
    def stream(steps):return [values[i%4] for i in range(steps)]
    steps=note_step(len(played)-1)+1
    if (c.clock_mode=='real-time' and silent_step and steps%4==2
            and len(cc)>1+len([v for v in stream(steps) if v!=-1])):steps+=1
    emitted_steps=[i for i,value in enumerate(stream(steps)) if value!=-1]
    assert [(e['port'],e['bytes']) for e in cc]==[(1,[176,1,v]) for v in [65]+stream(steps) if v!=-1]
    cc=cc[1:] # Stored patch recall is separate from per-step lock dispatch.
    assert len(cc)==len(emitted_steps)
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    replay_pairs=note_pairs(replay_events);assert [on for on,off in replay_pairs]==played
    assert_durations(c,played,[24]*(len(played)-1),events=replay_events)
    origin=played[0][field]
    for i,control in zip(emitted_steps,cc):
        assert abs((control[field]-origin)/1e9-i*4)<=tolerance,dict(step=i,control=control,origin=origin)
    note_steps=[note_step(i) for i in range(len(played))]
    notes_by_step=dict(zip(note_steps,played))
    for i,control in zip(emitted_steps,cc):
        if i not in notes_by_step:continue
        note=notes_by_step[i]
        assert control['index']<note['index']
        assert abs((control[field]-note[field])/1e9)<=tolerance
    c.results.append(dict(kind='recorded-parameter-disarmed-replay',values=expected,distinct_patch_default=65,passed=True,
                          **({'late_window_onsets':len(late)} if late else {}),
                          **({'late_window_silent_locks':steps-note_step(len(played)-1)-1} if steps>note_step(len(played)-1)+1 else {})))
    if switch_return:
        c.results.append(dict(kind='recording-switch-return-live-replay',live_step4_value=live_value,recorded_step4_value=expected[3],passed=live_value==expected[3]))
        assert live_value==expected[3],dict(live_step4=live_value,recorded_step4=expected[3],meaning='Resumed recorded value must match the value heard at that step')


def live_parameter_recording_scale_page(c):
    return live_parameter_recording(c, switch_return=True, scale_page=True)
