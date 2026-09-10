"""User-visible parameter-lock coverage across all steps and slots."""

def _cell(step):
    return ((step-1)%16+1,(step-1)//16+4)


def parameter_lock_all_steps_slots(c):
    from cases import assign_trig_parameter,assert_durations,set_mosaic_options
    from note_accounting import note_pairs
    c.configure();set_mosaic_options(c,[('Trigless locks',True)])
    c.hold_tap(_cell(1),_cell(64));c.enc(1,-3)
    selected=1
    for slot in range(1,11):
        if slot>1:c.enc(2,1)
        assign_trig_parameter(c,'CC '+str(slot))
    selected=10
    def select(slot):
        nonlocal selected
        if slot!=selected:c.enc(2,slot-selected);selected=slot
    def lock(step,value):
        select((step-1)%10+1)
        x,y=_cell(step);c.action(type='grid',x=x,y=y,state=1)
        try:
            c.elapse(.05);c.action(type='enc',n=3,delta=-126);c.elapse(.15)
            if value>=0:c.enc(3,value+1)
        finally:c.action(type='grid',x=x,y=y,state=0)
        c.elapse(.15)
    values={step:(step-1)//10 for step in range(1,65)}
    for step,value in values.items():lock(step,value)
    # Overwrite the first, middle and last rows, including one explicit Off.
    for step,value in ((1,7),(32,9),(33,-1),(64,8)):
        lock(step,value);values[step]=value
    cells=[_cell(step) for step in range(1,65)]
    c.led_values(cells,[15]*4+[2]*60);c.led_values(cells,[12]*4+[1]*60)
    before=c.snapshot()['midi_count'];c.tap(1,8)
    def ons(state):return [e for e in state['midi'] if e['index']>before and e['bytes'][0]&240==144 and e['bytes'][2]>0]
    state=c.wait(lambda state:len(ons(state))>=5,timeout=15)
    c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])
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
    from cases import assign_trig_parameter,assert_durations
    from note_accounting import note_pairs
    c.configure();c.enc(1,-3)
    assign_trig_parameter(c,'CC 1');c.enc(2,1);assign_trig_parameter(c,'CC 2')
    selected=2
    def lock(slot,step,value):
        nonlocal selected
        if slot!=selected:c.enc(2,slot-selected);selected=slot
        x,y=_cell(step);c.action(type='grid',x=x,y=y,state=1)
        try:
            c.elapse(.05);c.action(type='enc',n=3,delta=-126);c.elapse(.15);c.enc(3,value+1)
        finally:c.action(type='grid',x=x,y=y,state=0)
        c.elapse(.15)
    lock(1,1,24);lock(2,2,48)
    c.enc(1,2);c.enc(3,-23);c.key(3);c.enc(1,-2) # /24: four seconds per step.
    before=c.snapshot()['midi_count'];c.tap(1,8)
    def ons(state):return [e for e in state['midi'] if e['index']>before and e['bytes'][0]&240==144 and e['bytes'][2]>0]
    first=c.wait(lambda state:len(ons(state))==1)
    assert [(e['port'],e['bytes']) for e in first['midi'] if e['index']>before and e['bytes'][0]&240==176]==[(1,[176,1,24])]
    c.elapse(.5)
    x,y=_cell(2);c.action(type='grid',x=x,y=y,state=1)
    try:c.enc(3,1)
    finally:c.action(type='grid',x=x,y=y,state=0)
    c.elapse(.15)
    state=c.wait(lambda state:len(ons(state))>=3,timeout=10)
    c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])
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
    replay_before=c.snapshot()['midi_count'];c.tap(1,8)
    def replay_ons(state):return [e for e in state['midi'] if e['index']>replay_before and e['bytes'][0]&240==144 and e['bytes'][2]>0]
    c.wait(lambda state:len(replay_ons(state))>=3,timeout=10)
    c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])
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
