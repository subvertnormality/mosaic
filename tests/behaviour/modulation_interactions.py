"""User-level Matrix/toolkit interactions with Mosaic MIDI parameters."""
import math


def modulated_cc_lock_precedence(c):
    from cases import assert_durations
    from note_accounting import note_pairs

    def label(key):
        c.ui.expect_native_menu_label(key)

    def value(key):
        c.ui.expect_native_menu_value('modulation_control_1',key)

    assert c.profile=='midi-modulation'
    c.ui.open_patch_control(configured=True)
    label('patch_control_configured');value('off');c.ui.turn_patch_control(33);value('base_32');c.ui.press_key(1)

    # Assign the same configured parameter as a trig-lock slot and author two
    # explicit locks. The routed/default value must fill only the other steps.
    c.ui.turn(1,-3);c.ui.assign_trig_parameter('Control 1')
    for step,value in ((1,24),(3,48)):
        with c.ui.hold_step(step):
            c.elapse(.05);c.ui.encoder_event(3,-126);c.ui.turn(3,value+1)
        c.elapse(.15)
    c.ui.turn(1,3)

    # Route toolkit macro1 through the actual Matrix menu to Control1 at +0.50.
    c.ui.press_key(1);c.ui.turn(1,-4);c.ui.turn(2,1);c.ui.press_key(3);label('mod_devices_root')
    c.ui.turn(2,2);label('mod_mods_root');c.ui.press_key(3);label('mod_matrix_root')
    c.ui.press_key(3);label('levels_root')
    c.ui.seek_native_parameter_root('channel_1_device_parameters')
    c.ui.press_key(3);c.ui.expect_trig_parameter('fixed_note')
    c.ui.seek_native_menu_parameter('configured_control_1',attempts=180)
    label('patch_control_configured');c.ui.press_key(3);label('mod_rhythm_1')
    c.ui.turn(2,12);label('mod_macro_1')
    c.ui.turn(3,50);value('positive_half')

    c.ui.turn(1,4);c.ui.press_key(2)
    c.ui.encoder_event(2,-126);c.elapse(.15)
    label('levels_root')
    c.ui.seek_native_parameter_root('macro_1')
    c.ui.press_key(3);label('mod_active')
    c.ui.turn(2,1);label('mod_value')
    def detent_sweep(steps,expected,label):
        before=c.snapshot()['midi_count'];direction=2 if steps>0 else -2
        for ordinal,wanted in enumerate(expected,1):
            c.elapse(.05)
            prior=c.snapshot();prior_events=[e for e in prior['midi'] if e['index']>before]
            assert [(e['port'],e['bytes']) for e in prior_events]==[(1,[176,1,v]) for v in expected[:ordinal-1]]
            prior_count=prior['midi_count'];c.ui.encoder_event(3,direction)
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
    value('full_depth');c.ui.press_key(1)

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
    c.ui.press_key(1);c.ui.turn(1,4);c.ui.press_key(2)
    c.ui.encoder_event(2,-126);c.elapse(.15);label('levels_root')
    c.ui.seek_native_parameter_root('channel_1_device_parameters')
    c.ui.press_key(3);c.ui.expect_trig_parameter('fixed_note')
    c.ui.seek_native_menu_parameter(
        'configured_control_1', attempts=180,
        failure='Configured Control 1 unavailable after modulation playback',
    )
    label('patch_control_configured');value('base_96')
    before=c.snapshot()['midi_count'];c.ui.turn_patch_control(1);value('base_97')
    edited=[e for e in c.snapshot()['midi'] if e['index']>before]
    assert [(e['port'],e['bytes']) for e in edited]==[(1,[176,1,97])]
    c.ui.press_key(1);phase(97,'manual-edit-under-modulation')

    # Clear depth through Matrix. The candidate dependency must reapply raw33.
    c.ui.press_key(1);c.ui.turn(1,-4);c.ui.press_key(3);c.ui.press_key(3);c.ui.press_key(3);label('mod_macro_1')
    before=c.snapshot()['midi_count'];c.ui.press_key(3);value('clear_depth')
    cleared=[e for e in c.snapshot()['midi'] if e['index']>before]
    assert [(e['port'],e['bytes']) for e in cleared]==[(1,[176,1,33])]
    c.ui.press_key(1);phase(33,'cleared-depth')

    # Rebind the still-held macro at -0.25. No source edit is needed; each
    # native depth detent must emit the independently mapped descending value.
    c.ui.press_key(1);label('mod_macro_1')
    expected_negative=[max(0,math.floor(33-1.28*i+.5)) for i in range(1,26)]
    negative=detent_sweep(-25,expected_negative,'negative-depth-rebind');value('negative_quarter')
    c.ui.press_key(1);phase(1,'held-source-negative-rebind')
    c.results.append(dict(kind='modulated-device-parameter-lock-precedence',target='Control 1',
                          depths=[.5,0,-.25],base_values=[32,33],locks=[24,48],passed=True))
