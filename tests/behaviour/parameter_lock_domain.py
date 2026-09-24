"""User-visible parameter-lock coverage across all steps and slots."""

def parameter_lock_all_steps_slots(c):
    from cases import assert_durations
    from note_accounting import note_pairs
    c.ui.configure();c.ui.set_mosaic_options([('Trigless locks',True)])
    c.ui.set_range(1,64);c.ui.channel_page('trig_locks','midi_config',confirm=False)
    selected=1
    for slot in range(1,11):
        if slot>1:c.ui.turn(2,1)
        c.ui.assign_trig_parameter('CC '+str(slot))
    selected=10
    def select(slot):
        nonlocal selected
        if slot!=selected:c.ui.turn(2,slot-selected);selected=slot
    def lock(step,value):
        select((step-1)%10+1)
        with c.ui.hold_step(step):
            c.elapse(.05);c.ui.encoder_event(3,-126);c.elapse(.15)
            if value>=0:c.ui.turn(3,value+1)
        c.elapse(.15)
    values={step:(step-1)//10 for step in range(1,65)}
    for step,value in values.items():lock(step,value)
    # Overwrite the first, middle and last rows, including one explicit Off.
    for step,value in ((1,7),(32,9),(33,-1),(64,8)):
        lock(step,value);values[step]=value
    c.ui.expect_steps({step:'selected' if step<=4 else 'off' for step in range(1,65)})
    c.ui.expect_steps({step:'active' if step<=4 else 'trace' for step in range(1,65)})
    before=c.snapshot()['midi_count'];c.ui.tap_control('play_stop')
    def ons(state):return [e for e in state['midi'] if e['index']>before and e['bytes'][0]&240==144 and e['bytes'][2]>0]
    state=c.wait(lambda state:len(ons(state))>=5,timeout=15)
    c.ui.tap_control('play_stop');c.wait(lambda state:not state['midi_capture']['outstanding'])
    events=[e for e in c.snapshot()['midi'] if e['index']>before]
    notes=[e for e in events if e['bytes'][0]&240==144 and e['bytes'][2]>0]
    assert [(e['port'],e['bytes']) for e in notes]==[(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107),(65,97),(60,127)]]
    pairs=note_pairs(events);assert [on for on,off in pairs]==notes
    assert_durations(c,notes,[1]*4,events=events)
    expected=[]
    for ordinal in range(65):
        step=ordinal%64+1;value=values[step]
        if value>=0:expected.append((ordinal,(1,[176,(step-1)%10+1,value])))
    cc=[e for e in events if e['bytes'][0]&240==176]
    assert [(e['port'],e['bytes']) for e in cc]==[payload for ordinal,payload in expected]
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns';tol=2e-9 if c.clock_mode=='controlled-experimental' else .01
    origin=notes[0][field]
    for event,(ordinal,payload) in zip(cc,expected):
        assert abs((event[field]-origin)/1e9-ordinal/6)<=tol
    by_ordinal={ordinal:event for event,(ordinal,payload) in zip(cc,expected)}
    for note,ordinal in zip(notes,(0,1,2,3,64)):
        control=by_ordinal[ordinal]
        assert control['index']<note['index'] and abs((control[field]-note[field])/1e9)<=tol
    c.results.append(dict(kind='parameter-lock-all-steps-slots',steps=64,slots=10,off_step=33,
                          overwritten={1:7,32:9,33:'X',64:8},emitted_controls=len(cc),passed=True))


def parameter_lock_during_playback(c):
    from cases import assert_durations
    from note_accounting import note_pairs
    c.ui.configure();c.ui.channel_page('trig_locks','midi_config',confirm=False)
    c.ui.assign_trig_parameter('CC 1');c.ui.turn(2,1);c.ui.assign_trig_parameter('CC 2')
    selected=2
    def lock(slot,step,value):
        nonlocal selected
        if slot!=selected:c.ui.turn(2,slot-selected);selected=slot
        with c.ui.hold_step(step):
            c.elapse(.05);c.ui.encoder_event(3,-126);c.elapse(.15);c.ui.turn(3,value+1)
        c.elapse(.15)
    lock(1,1,24);lock(2,2,48)
    c.ui.channel_page('clock_mods','trig_locks',confirm=False);c.ui.turn(3,-23);c.ui.press_key(3);c.ui.channel_page('trig_locks','clock_mods',confirm=False) # /24: four seconds per step.
    before=c.snapshot()['midi_count'];c.ui.tap_control('play_stop')
    def ons(state):return [e for e in state['midi'] if e['index']>before and e['bytes'][0]&240==144 and e['bytes'][2]>0]
    first=c.wait(lambda state:len(ons(state))==1)
    assert [(e['port'],e['bytes']) for e in first['midi'] if e['index']>before and e['bytes'][0]&240==176]==[(1,[176,1,24])]
    c.elapse(.5)
    with c.ui.hold_step(2):c.ui.turn(3,1)
    c.elapse(.15)
    state=c.wait(lambda state:len(ons(state))>=3,timeout=10)
    c.ui.tap_control('play_stop');c.wait(lambda state:not state['midi_capture']['outstanding'])
    events=[e for e in c.snapshot()['midi'] if e['index']>before]
    notes=[e for e in events if e['bytes'][0]&240==144 and e['bytes'][2]>0]
    assert [(e['port'],e['bytes']) for e in notes]==[(1,[144,60,127]),(1,[144,62,117]),(1,[144,64,107])]
    pairs=note_pairs(events);assert [on for on,off in pairs]==notes
    assert_durations(c,notes[:2],[24,24],events=events)
    cc=[e for e in events if e['bytes'][0]&240==176]
    assert [(e['port'],e['bytes']) for e in cc]==[(1,[176,1,24]),(1,[176,2,49])]
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns';tol=2e-9 if c.clock_mode=='controlled-experimental' else .01
    assert abs((cc[0][field]-notes[0][field])/1e9)<=tol and cc[0]['index']<notes[0]['index']
    assert abs((cc[1][field]-notes[1][field])/1e9)<=tol and cc[1]['index']<notes[1]['index']
    assert abs((notes[1][field]-notes[0][field])/1e9-4)<=tol
    # A fresh transport pass proves the held-step edit committed persistently;
    # a transient value consumed at the first step2 boundary cannot satisfy it.
    replay_before=c.snapshot()['midi_count'];c.ui.tap_control('play_stop')
    def replay_ons(state):return [e for e in state['midi'] if e['index']>replay_before and e['bytes'][0]&240==144 and e['bytes'][2]>0]
    c.wait(lambda state:len(replay_ons(state))>=3,timeout=10)
    c.ui.tap_control('play_stop');c.wait(lambda state:not state['midi_capture']['outstanding'])
    replay_events=[e for e in c.snapshot()['midi'] if e['index']>replay_before]
    replay_notes=[e for e in replay_events if e['bytes'][0]&240==144 and e['bytes'][2]>0]
    assert [(e['port'],e['bytes']) for e in replay_notes]==[(1,[144,60,127]),(1,[144,62,117]),(1,[144,64,107])]
    replay_pairs=note_pairs(replay_events);assert [on for on,off in replay_pairs]==replay_notes
    assert_durations(c,replay_notes[:2],[24,24],events=replay_events)
    replay_cc=[e for e in replay_events if e['bytes'][0]&240==176]
    assert [(e['port'],e['bytes']) for e in replay_cc]==[(1,[176,1,24]),(1,[176,2,49])]
    for control,note in zip(replay_cc,replay_notes[:2]):
        assert control['index']<note['index'] and abs((control[field]-note[field])/1e9)<=tol
    assert abs((replay_notes[1][field]-replay_notes[0][field])/1e9-4)<=tol
    c.results.append(dict(kind='parameter-lock-live-future-overwrite',old_value=48,new_value=49,
                          edit_during_step=1,applied_step=2,current_gate_seconds=4,persistent_replay=True,passed=True))


def parameter_slot_limit(c):
    """E2 clamps at the ten real slots; endpoint locks keep their routes."""
    from cases import assert_durations
    from note_accounting import continuation_onsets,note_pairs,window_onsets
    c.ui.configure();c.ui.channel_page('trig_locks','midi_config',confirm=False)
    for slot in range(1,11):
        if slot>1:c.ui.turn(2,1)
        c.ui.assign_trig_parameter('CC '+str(slot))
    def lock(step,value):
        with c.ui.hold_step(step):c.elapse(.05);c.ui.encoder_event(3,-126);c.elapse(.15);c.ui.turn(3,value+1)
        c.elapse(.15)
    c.ui.turn(2,20);lock(1,0)   # Must remain slot10; no slot11 exists.
    c.ui.turn(2,-20);lock(2,1)  # Must clamp back to slot1; no slot0 exists.
    before=c.snapshot()['midi_count']
    phrase=[(1,[144,n,v]) for n,v in ((60,127),(62,117),(64,107),(65,97))]
    notes=c.playback(phrase,cycles=2)
    events=[e for e in c.snapshot()['midi'] if e['index']>before]
    # The window runs until Stop takes effect. In real time a further step may
    # sound first: it must continue the phrase on the 1/6 s lattice, with its
    # own step lock, timing and release.
    played=window_onsets(events)
    late=continuation_onsets(c,notes,played,phrase,lambda i:i/6)
    cc=[e for e in events if e['bytes'][0]&240==176]
    expected=[(ordinal,(1,[176,10,0]) if ordinal%4==0 else (1,[176,1,1])) for ordinal in range(len(played)) if ordinal%4<2]
    assert [(e['port'],e['bytes']) for e in cc]==[payload for ordinal,payload in expected]
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns';tol=2e-9 if c.clock_mode=='controlled-experimental' else .01
    origin=played[0][field]
    for event,(ordinal,payload) in zip(cc,expected):assert abs((event[field]-origin)/1e9-ordinal/6)<=tol
    for event,(ordinal,payload) in zip(cc,expected):
        note=played[ordinal]
        assert event['index']<note['index'] and abs((event[field]-note[field])/1e9)<=tol
    pairs=note_pairs(events);assert [on for on,off in pairs]==played
    assert_durations(c,played,[1]*(len(played)-1),events=events)
    c.results.append(dict(kind='parameter-slot-limit',assigned_slots=10,upper_route_cc=10,lower_route_cc=1,
                          upper_and_lower_clamped=True,passed=True,
                          **({'late_window_onsets':len(late)} if late else {})))
