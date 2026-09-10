"""User-level Matrix/toolkit interactions with Mosaic MIDI parameters."""
import math


def modulated_cc_lock_precedence(c):
    from cases import assign_trig_parameter,assert_durations,menu_label,menu_value
    from note_accounting import note_pairs
    from patch_params import open_patch_control,turn

    assert c.profile=='midi-modulation'
    open_patch_control(c,configured=True)
    menu_label(c,'Control 1');menu_value(c,'X');turn(c,33);menu_value(c,'32');c.key(1)

    # Assign the same configured parameter as a trig-lock slot and author two
    # explicit locks. The routed/default value must fill only the other steps.
    c.enc(1,-3);assign_trig_parameter(c,'Control 1')
    for step,value in ((1,24),(3,48)):
        c.action(type='grid',x=step,y=4,state=1)
        try:c.elapse(.05);c.action(type='enc',n=3,delta=-126);c.enc(3,value+1)
        finally:c.action(type='grid',x=step,y=4,state=0)
        c.elapse(.15)
    c.enc(1,3)

    # Route toolkit macro1 through the actual Matrix menu to Control1 at +0.50.
    c.key(1);c.enc(1,-4);c.enc(2,1);c.key(3);menu_label(c,'DEVICES > ')
    c.enc(2,2);menu_label(c,'MODS >');c.key(3);menu_label(c,'MATRIX >',4)
    c.key(3);menu_label(c,'LEVELS >')
    roots=c.snapshot()['diagnostics']['parameter_roots']
    position=next(i for i,v in enumerate(roots) if v['id']=='midi_device_params_group_channel_1')
    c.enc(2,position);c.key(3);menu_label(c,'Fixed Note')
    from frame_oracle import selected_line
    for _ in range(180):
        if selected_line(c.snapshot(),'Control 1'):break
        c.enc(2,1)
    else:raise AssertionError('Configured Control 1 unavailable in Matrix target group')
    menu_label(c,'Control 1');c.key(3);menu_label(c,'rhythm 1')
    c.enc(2,12);menu_label(c,'macro 1')
    c.enc(3,50);menu_value(c,'0.50')

    c.enc(1,4);c.key(2)
    c.action(type='enc',n=2,delta=-126);c.elapse(.15)
    menu_label(c,'LEVELS >')
    roots=c.snapshot()['diagnostics']['parameter_roots']
    position=next(i for i,v in enumerate(roots) if v['name']=='macro 1')
    c.enc(2,position);c.key(3);menu_label(c,'active')
    c.enc(2,1);menu_label(c,'value')
    def detent_sweep(steps,expected,label):
        before=c.snapshot()['midi_count'];direction=2 if steps>0 else -2
        for ordinal,wanted in enumerate(expected,1):
            c.elapse(.05)
            prior=c.snapshot();prior_events=[e for e in prior['midi'] if e['index']>before]
            assert [(e['port'],e['bytes']) for e in prior_events]==[(1,[176,1,v]) for v in expected[:ordinal-1]]
            prior_count=prior['midi_count'];c.action(type='enc',n=3,delta=direction)
            state=c.wait(lambda s:s['midi_count']>=prior_count+1,timeout=.04)
            emitted=[e for e in state['midi'] if e['index']>before]
            new_events=[e for e in state['midi'] if e['index']>prior_count]
            assert [(e['port'],e['bytes']) for e in new_events]==[(1,[176,1,wanted])]
            assert [(e['port'],e['bytes']) for e in emitted]==[(1,[176,1,v]) for v in expected[:ordinal]]
        c.elapse(.15);settled=c.snapshot()
        emitted=[e for e in settled['midi'] if e['index']>before]
        assert [(e['port'],e['bytes']) for e in emitted]==[(1,[176,1,v]) for v in expected]
        c.results.append(dict(kind='modulation-detent-causality',label=label,count=len(expected),
                              maximum_observation_latency_seconds=.04,
                              one_complete_cc_before_next_input=True,passed=True))
        return emitted

    # Control1's configured selectable domain is Off plus0..127: modulation
    # therefore spans128 normalized intervals. Every detent must synchronously
    # expose exactly one complete CC before the next physical input is sent.
    expected_positive=[math.floor(32+.64*i+.5) for i in range(1,101)]
    positive=detent_sweep(100,expected_positive,'positive-source-sweep')
    menu_value(c,'1.0');c.key(1)

    def phase(default,label):
        start=c.snapshot()['midi_count']
        notes=c.playback([(1,[144,n,v]) for n,v in ((60,127),(62,117),(64,107),(65,97))],cycles=2)
        events=[e for e in c.snapshot()['midi'] if e['index']>start]
        cc=[e for e in events if e['bytes'] and e['bytes'][0]&240==176]
        expected=[default]+[24 if i%4==0 else 48 if i%4==2 else default for i in range(len(notes))]
        assert [(e['port'],e['bytes']) for e in cc]==[(1,[176,1,v]) for v in expected]
        realtime=[e for e in events if e['bytes'] and e['bytes'][0]>=248]
        assert [(e['port'],e['bytes']) for e in realtime]==[
            (1,[250]),(2,[250]),(3,[250]),(1,[252]),(2,[252]),(3,[252])]
        starts=realtime[:3];stops=realtime[3:]
        assert cc[0]['index']<starts[0]['index']<notes[0]['index']
        assert notes[-1]['index']<stops[0]['index']
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        for ordinal,note in enumerate(notes):
            event=cc[ordinal+1]
            assert event['index']<note['index'] and (ordinal==0 or event['index']>notes[ordinal-1]['index'])
            assert abs((event[field]-note[field])/1e9)<=tolerance
            assert abs((note[field]-notes[0][field])/1e9-ordinal/6)<=tolerance
        pairs=note_pairs(events);assert [on for on,off in pairs]==notes
        assert_durations(c,notes,[1]*(len(notes)-1),events=events)
        c.results.append(dict(kind='modulated-cc-lock-phase',phase=label,default=default,
                              locks={1:24,3:48},cc_values=expected,passed=True))

    phase(96,'positive-depth')

    # Editing the unmodulated base32 to33 while +0.50 remains active yields97.
    c.key(1);c.enc(1,4);c.key(2)
    c.action(type='enc',n=2,delta=-126);c.elapse(.15);menu_label(c,'LEVELS >')
    roots=c.snapshot()['diagnostics']['parameter_roots']
    position=next(i for i,v in enumerate(roots) if v['id']=='midi_device_params_group_channel_1')
    c.enc(2,position);c.key(3);menu_label(c,'Fixed Note')
    for _ in range(180):
        if selected_line(c.snapshot(),'Control 1'):break
        c.enc(2,1)
    else:raise AssertionError('Configured Control 1 unavailable after modulation playback')
    menu_label(c,'Control 1');menu_value(c,'96')
    before=c.snapshot()['midi_count'];turn(c,1);menu_value(c,'97')
    edited=[e for e in c.snapshot()['midi'] if e['index']>before]
    assert [(e['port'],e['bytes']) for e in edited]==[(1,[176,1,97])]
    c.key(1);phase(97,'manual-edit-under-modulation')

    # Clear depth through Matrix. The candidate dependency must reapply raw33.
    c.key(1);c.enc(1,-4);c.key(3);c.key(3);c.key(3);menu_label(c,'macro 1')
    before=c.snapshot()['midi_count'];c.key(3);menu_value(c,'-')
    cleared=[e for e in c.snapshot()['midi'] if e['index']>before]
    assert [(e['port'],e['bytes']) for e in cleared]==[(1,[176,1,33])]
    c.key(1);phase(33,'cleared-depth')

    # Rebind the still-held macro at -0.25. No source edit is needed; each
    # native depth detent must emit the independently mapped descending value.
    c.key(1);menu_label(c,'macro 1')
    expected_negative=[max(0,math.floor(33-1.28*i+.5)) for i in range(1,26)]
    negative=detent_sweep(-25,expected_negative,'negative-depth-rebind');menu_value(c,'-0.25')
    c.key(1);phase(1,'held-source-negative-rebind')
    c.results.append(dict(kind='modulated-device-parameter-lock-precedence',target='Control 1',
                          depths=[.5,0,-.25],base_values=[32,33],locks=[24,48],passed=True))
