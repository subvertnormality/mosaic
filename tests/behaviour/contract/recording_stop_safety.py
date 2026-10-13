def long_stop(c):
    with c.ui.hold_control("play_stop"):
        c.elapse(1.2)
    c.elapse(.06)


def recording_stop_safety(c):
    c.ui.configure();c.ui.set_mosaic_options([('Shift press to stop',True)])
    c.ui.open_patch_control(setup=False)
    c.ui.turn_patch_control(63);c.ui.turn_patch_control(1)
    c.ui.expect_menu_value('63');c.ui.press_key(1)
    c.ui.turn(1,-3);c.ui.assign_trig_parameter('CC 1')
    for step,value in [(1,24),(3,96)]:
        with c.ui.hold_step(step):
            c.elapse(.05);c.ui.encoder_event(3,-126);c.ui.turn(3,value+1)
    c.ui.turn(1,2);c.ui.turn(3,-23);c.ui.press_key(3);c.ui.turn(1,-2)
    c.ui.tap_control("record");before=c.snapshot()['midi_count'];c.ui.play()
    def notes(state):return [e for e in state['midi'] if e['index']>before and e['bytes'][0]==144 and e['bytes'][2]>0]
    c.wait(lambda state:len(notes(state))==1);c.elapse(.5);c.ui.turn(3,1)
    c.wait(lambda state:len(notes(state))>=2,timeout=5)
    def stop_and_drain():
        long_stop(c);c.wait(lambda state:not state['midi_capture']['outstanding'])
    stop_and_drain()
    before=c.snapshot()['midi_count'];c.ui.play()
    first=c.wait(lambda state:len(notes(state))>=1)
    actual=[(e['port'],e['bytes']) for e in first['midi'] if e['index']>before and e['bytes'][0]&240==176]
    expected=[(1,[176,1,64]),(1,[176,1,24])] # Patch recall then unchanged first lock.
    assert actual==expected,dict(expected=expected,actual=actual,meaning='Long Stop must clear pending recording while arm remains enabled')
    state=c.wait(lambda state:len(notes(state))>=4,timeout=14)
    assert [e['bytes'] for e in notes(state)]==[[144,n,v] for n,v in [(60,127),(62,117),(64,107),(65,97)]]
    cc=[(e['port'],e['bytes']) for e in state['midi'] if e['index']>before and e['bytes'][0]&240==176]
    assert cc==[(1,[176,1,v]) for v in [64,24,64,96,64]],cc
    stop_and_drain()
    # Prove retained arm through a new recorded edit and distinct-default replay.
    # A Stop implementation which disarms would leave step 2 at its old 64.
    before=c.snapshot()['midi_count'];c.ui.play()
    c.wait(lambda state:len(notes(state))==1);c.elapse(.5);c.ui.turn(3,1)
    c.wait(lambda state:len(notes(state))>=2,timeout=5)
    stop_and_drain();c.ui.tap_control("record") # Explicitly disarm only after the new edit is recorded.
    c.ui.turn(3,1) # Default 66 differs from recorded 65 and original lock 64.
    before=c.snapshot()['midi_count'];c.ui.play()
    state=c.wait(lambda state:len(notes(state))>=2,timeout=5)
    cc=[(e['port'],e['bytes']) for e in state['midi'] if e['index']>before and e['bytes'][0]&240==176]
    assert cc==[(1,[176,1,v]) for v in [66,24,65]],dict(actual=cc,meaning='Stop retains arm: new step-2 edit survives disarmed replay with a different default')
    stop_and_drain()
    c.results.append(dict(kind='recording-stop-safety-long-press-restart',record_arm_retained=True,first_lock=24,recorded_step2=64,untouched_step3=96,new_recorded_step2=65,replay_default=66,passed=True))
