"""Native recording lifetime tests; literal MIDI expectations, physical controls."""

def recording_lifetime(c,ending,scale_page=False):
    ui = c.ui
    assert ending in ('selected-wrap','nonselected-wrap','disarm','stop','reassign','same-assignment','configuration','slide-active','slide-off','pending-assignment','pending-configuration','mute','memory','memory-branch','persistence')
    slide=ending.startswith('slide-')
    value=-1 if ending=='slide-off' else 64
    ui.open_patch_control();ui.turn_patch_control(63);ui.turn_patch_control(1);ui.expect_patch_value(63);ui.leave_native_menu()
    ui.turn(1,-3);cc1_offset=ui.assign_trig_parameter_key('stored_patch_cc1')
    for step,lock in [(1,24),(3,96)]:
        ui.control_edge('step',True,index=step)
        try:c.elapse(.05);ui.encoder_event(3,-126);ui.set_value(lock+1)
        finally:ui.control_edge('step',False,index=step)
    if slide:ui.press_key(3)
    ui.turn(1,2);ui.set_value(-23);ui.press_key(3);ui.turn(1,-2)
    ui.tap_control('record');before=c.snapshot()['midi_count'];ui.tap_control('play_stop')
    def notes(state):return [e for e in state['midi'] if e['index']>before and e['bytes'][0]&240==144 and e['bytes'][2]>0]
    c.wait(lambda state:len(notes(state))==1);c.elapse(.5)
    edit=c.snapshot()['midi_count']
    if value==-1:ui.encoder_event(3,-126);c.elapse(.15)
    else:ui.set_value(1)
    wanted_steps=4;replay=[24,64,64,64];port=1;channel=0;cc_number=1
    if ending=='mute':
        def shift_mute():
            ui.key_edge(1,True)
            try:c.elapse(.3);ui.tap_control('channel',1)
            finally:ui.key_edge(1,False)
        shift_mute();ui.expect_leds({('channel',1):'alternate'})
        marker=c.snapshot()['midi_count'];c.elapse(8)
        quiet=c.snapshot()
        assert not [e for e in quiet['midi'] if e['index']>marker and (e['bytes'][0]&240==176 or (e['bytes'][0]&240==144 and e['bytes'][2]>0))],quiet['midi']
        assert not quiet['midi_capture']['outstanding']
        shift_mute();ui.expect_leds({('channel',1):'selected'});wanted_steps=2
    elif ending=='selected-wrap':wanted_steps=5
    elif ending=='nonselected-wrap':
        ui.tap_control('scale_editor') if scale_page else ui.select_channel(2)
        c.wait(lambda state:len(notes(state))>=5,timeout=18)
        c.elapse(.3)
        ui.tap_control('channel_editor') if scale_page else ui.select_channel(1)
        wanted_steps=8
    elif ending in ('pending-assignment','pending-configuration'):
        c.wait(lambda state:len(notes(state))>=2,timeout=5)
        if ending=='pending-assignment':
            ui.press_key(2);ui.set_value(1);ui.expect_trig_parameter_visible('stored_patch_cc2')
        else:
            ui.turn(1,3);ui.turn(2,1);ui.set_value(1);ui.turn(2,1);ui.set_value(1)
        # An eligible step occurs with the proposed edit still unconfirmed.
        c.wait(lambda state:len(notes(state))>=3,timeout=5)
        ui.press_key(2) # Cancel through the real UI.
        if ending=='pending-configuration':ui.turn(1,-3)
    elif ending in ('disarm','stop','reassign','same-assignment','configuration'):
        c.wait(lambda state:len(notes(state))>=2,timeout=5)
        replay=[24,64,96,65]
        if ending=='disarm':ui.tap_control('record');ui.tap_control('record')
        elif ending=='stop':
            ui.tap_control('play_stop');c.wait(lambda state:not state['midi_capture']['outstanding'])
            before=c.snapshot()['midi_count'];edit=before;ui.tap_control('play_stop')
        elif ending in ('reassign','same-assignment'):
            ui.press_key(2)
            if ending=='reassign':ui.set_value(1);cc_number=2
            else:ui.set_value(1);ui.set_value(-1) # Enqueue actual same-assignment confirmation.
            ui.expect_trig_parameter_visible('stored_patch_cc%d' % cc_number);ui.press_key(3);ui.press_key(2)
            if ending=='same-assignment':replay=[24,64,64,64]
        else:
            ui.turn(1,3);ui.turn(2,1);ui.set_value(1);ui.turn(2,1);ui.set_value(1);ui.press_key(3);ui.turn(1,-3)
            port=2;channel=1;replay=[65]*4
            # Confirmation clears device locks and resets assignments, including
            # route-only changes. Reassign before wrap to expose latent dirty state.
            # Reuse the offset found at setup: scanning the parameter list
            # again here takes longer than the two steps this must fit inside.
            ui.assign_trig_parameter_key('stored_patch_cc1',offset=cc1_offset)
            assert len(notes(c.snapshot()))<4,'Reassignment missed pre-wrap step4'
    state=c.wait(lambda state:len(notes(state))>=wanted_steps,timeout=18)
    ons=notes(state);assert len(ons)==wanted_steps,ons
    if ending=='mute':
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        resumed_seconds=(ons[1][field]-ons[0][field])/1e9
        assert abs(resumed_seconds-12)<=tolerance,dict(resumed_seconds=resumed_seconds,expected=12)
    for i,note in enumerate(ons):
        expected_port=port if ending=='configuration' and i>=2 else 1
        expected_channel=channel if ending=='configuration' and i>=2 else 0
        position=(0,3)[i] if ending=='mute' else i%4
        assert (note['port'],note['bytes'])==(expected_port,[144+expected_channel,(60,62,64,65)[position],(127,117,107,97)[position]])
    emitted=[e for e in state['midi'] if e['index']>edit and e['bytes'][0]&240==176]
    actual=[(e['port'],e['bytes']) for e in emitted]
    if ending=='mute':wanted=[(1,[176,1,64])]*2 # Manual edit and resumed step4 only.
    elif ending=='selected-wrap':wanted=[(1,[176,1,v]) for v in [64,64,64,64,24]]
    elif ending=='nonselected-wrap':wanted=[(1,[176,1,v]) for v in [64,64,96,64,24,64,64,64]]
    elif ending=='disarm':wanted=[(1,[176,1,v]) for v in [64,64,96,64]]
    elif ending=='stop':wanted=[(1,[176,1,v]) for v in [64,24,64,96,64]]
    elif ending=='reassign':wanted=[(1,[176,1,64]),(1,[176,1,64]),(1,[176,2,96])]
    elif ending=='configuration':wanted=[(1,[176,1,64]),(1,[176,1,64])]
    elif ending in ('same-assignment','pending-assignment','pending-configuration','memory','memory-branch','persistence'):wanted=[(1,[176,1,64])]*4
    elif ending=='slide-active':
        # The encoder's established silent update during a slide is separate
        # from step-boundary restoration. No stale callback may follow it.
        after_boundary=[e for e in emitted if e['index']>ons[1]['index']]
        assert [(e['port'],e['bytes']) for e in after_boundary]==[(1,[176,1,64])]*2,after_boundary
        second=[e for e in emitted if e['index']<ons[1]['index']][-1]
        assert second['bytes']==[176,1,64]
        prior=[e for e in state['midi'] if before<e['index']<edit and e['bytes'][0]==176]
        assert any(24<e['bytes'][2]<64 for e in prior),prior
        wanted=None
    else:
        # Off must not cancel the original 24->96 ramp over eight seconds.
        ramp=[e for e in state['midi'] if e['index']>before and e['bytes'][0]==176]
        assert [(e['port'],e['bytes']) for e in ramp]==[(1,[176,1,v]) for v in [63]+list(range(24,97))]
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        # Eight seconds at90BPM/96ppqn =1152 pulses. The 1/48-beat
        # slide service samples every2 pulses, rounded to nearest CC integer.
        # Off suppresses the destination lock, so no explicit endpoint repeat
        # is expected when rounding already reached96 at pulse1144.
        planned=[(0,24)];previous=24
        for pulse in range(2,1153,2):
            quantised=24+(72*pulse+576)//1152
            if quantised!=previous:planned.append((pulse,quantised));previous=quantised
        assert len(planned)==len(ramp)-1
        for event,(pulse,quantised) in zip(ramp[1:],planned):
            actual_seconds=(event[field]-ons[0][field])/1e9
            assert event['bytes']==[176,1,quantised]
            assert abs(actual_seconds-pulse/144)<=tolerance,dict(pulse=pulse,value=quantised,actual=actual_seconds,expected=pulse/144)
        assert any(e['index']>ons[1]['index'] and e['bytes'][2]<96 for e in ramp)
        wanted=None;replay=[24,-1,-1,-1]
    if wanted is not None:assert actual==wanted,dict(ending=ending,expected=wanted,actual=actual)
    c.results.append(dict(kind='recording-lifetime-live-output',ending=ending,actual=actual,passed=True))
    ui.tap_control('play_stop');c.wait(lambda state:not state['midi_capture']['outstanding']);ui.tap_control('record')
    if slide:ui.press_key(3) # Disable slide through the same UI before lock replay.
    current=-1 if ending in ('reassign','configuration','slide-off') else 64
    ui.set_value(65-current)
    # Use the native patch menu to prove the new default is independent.
    ui.enter_native_menu()
    if ending=='reassign':ui.turn(2,1)
    ui.expect_patch_value(65);ui.leave_native_menu()
    start=c.snapshot()['midi_count']
    played=c.playback([(port,[144+channel,n,v]) for n,v in [(60,127),(62,117),(64,107),(65,97)]],cycles=2,timeout=36,settle_seconds=30)
    cc=[e for e in c.snapshot()['midi'] if e['index']>start and e['bytes'][0]&240==176]
    table=replay*2+[replay[0]]
    prefix=([(1,[176,1,64])] if ending=='reassign' else [])+[(port,[176+channel,cc_number,65])]
    expected=prefix+[(port,[176+channel,cc_number,v]) for v in table if v!=-1]
    assert [(e['port'],e['bytes']) for e in cc]==expected,dict(ending=ending,expected=expected,actual=cc)
    cc=cc[len(prefix):]
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    for i,control in zip([i for i,v in enumerate(table) if v!=-1],cc):
        assert control['index']<played[i]['index']
        assert abs((control[field]-played[0][field])/1e9-i*4)<=tolerance
    c.results.append(dict(kind='recording-lifetime-disarmed-replay',ending=ending,values=table,distinct_default=65,passed=True))
    if ending=='persistence':
        import json
        import shutil
        from driver import Driver,digest
        ui.turn(1,2);ui.turn(3,15);ui.press_key(3) # /6 for fresh-process replay.
        def save(driver):
            driver.elapse(59);driver.elapse(2)
            driver.wait(lambda _:all((driver.data_directory/name).is_file() for name in ('autosave.ptn','autosave.pset')),timeout=3)
            captured=driver.out/'generated-project';captured.mkdir(exist_ok=True)
            shutil.copy2(driver.data_directory/'autosave.ptn',captured/'autosave.ptn')
            driver.results.append(dict(kind='recording-autosave-files',files={name:digest(driver.data_directory/name) for name in ('autosave.ptn','autosave.pset')}))
        save(c);c.finish();seed=c.data_directory
        for generation in (1,2):
            out=c.out/('recording-reload-'+str(generation));out.mkdir()
            loaded=Driver(out,project_seed=seed,**c.launch_options)
            try:
                loaded.ui.tap_control('channel_editor');loaded.ui.turn(1,-10);loaded.ui.turn(1,2);loaded.ui.expect_header('memory',channel=1)
                def replay(values,stage):
                    start=loaded.snapshot()['midi_count']
                    played=loaded.playback([(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107),(65,97)]],cycles=2,timeout=12)
                    cc=[e for e in loaded.snapshot()['midi'] if e['index']>start and e['bytes'][0]&240==176]
                    expected=[65]+values*2+[values[0]]
                    assert [(e['port'],e['bytes']) for e in cc]==[(1,[176,1,v]) for v in expected],dict(generation=generation,stage=stage,expected=expected,actual=cc)
                    for i,event in enumerate(cc[1:]):
                        assert event['index']<played[i]['index']
                        assert abs((event[field]-played[0][field])/1e9-i)<=tolerance
                    loaded.results.append(dict(kind='recording-fresh-process-replay',generation=generation,stage=stage,values=values,passed=True))
                replay([24,64,64,64] if generation==1 else [24,64,64,65],'restored')
                loaded.ui.turn(3,-1 if generation==1 else 1)
                replay([24,64,64,65] if generation==1 else [24,64,64,64],'undo' if generation==1 else 'redo')
                if generation==1:save(loaded)
            finally:loaded.finish()
            seed=loaded.data_directory
        c.results.append(dict(kind='recorded-lock-and-history-persistence',fresh_processes=2,undone_position_preserved=True,passed=True))
        (c.out/'results.json').write_text(json.dumps(c.results,indent=2)+'\n')

    if ending in ('memory','memory-branch'):
        # Recorded steps2/3/4 are the last three memory actions. Step3
        # overwrote an authored96; steps2/4 were previously unbound.
        ui.turn(1,2);ui.turn(3,15);ui.press_key(3);ui.turn(1,-1) # /6, Memory page.
        ui.expect_header('memory',channel=1)
        stages=[(-1,[24,64,64,65]),(-1,[24,64,96,65]),(-1,[24,65,96,65]),
                (1,[24,64,96,65]),(1,[24,64,64,65]),(1,[24,64,64,64])]
        for direction,values in stages:
            ui.turn(3,direction);start=c.snapshot()['midi_count']
            played=c.playback([(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107),(65,97)]],cycles=2,timeout=12)
            cc=[e for e in c.snapshot()['midi'] if e['index']>start and e['bytes'][0]&240==176]
            expected=[65]+values*2+[values[0]]
            assert [(e['port'],e['bytes']) for e in cc]==[(1,[176,1,v]) for v in expected],dict(direction=direction,values=values,actual=cc)
            for i,event in enumerate(cc[1:]):
                assert event['index']<played[i]['index']
                assert abs((event[field]-played[0][field])/1e9-i)<=tolerance
            c.results.append(dict(kind='recording-memory-step-replay',direction=direction,values=values,passed=True))
        if ending=='memory-branch':
            ui.turn(3,-2) # Keep recorded step2; undo recorded steps3/4.
            ui.turn(1,-1) # Trig Parameters.
            ui.control_edge('step',True,index=3)
            try:c.elapse(.05);ui.set_value(1) # Existing96 -> new97, one memory action.
            finally:ui.control_edge('step',False,index=3)
            ui.turn(1,1);ui.expect_header('memory',channel=1)
            for action,values in [('latest',[24,64,97,65]),('undo',[24,64,96,65]),('redo',[24,64,97,65]),('past-end',[24,64,97,65])]:
                if action=='latest':ui.press_key(3)
                else:ui.turn(3,-1 if action=='undo' else (1 if action=='redo' else 3))
                start=c.snapshot()['midi_count']
                played=c.playback([(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107),(65,97)]],cycles=2,timeout=12)
                cc=[e for e in c.snapshot()['midi'] if e['index']>start and e['bytes'][0]&240==176]
                expected=[65]+values*2+[values[0]]
                assert [(e['port'],e['bytes']) for e in cc]==[(1,[176,1,v]) for v in expected],dict(action=action,expected=expected,actual=cc)
                for i,event in enumerate(cc[1:]):
                    assert event['index']<played[i]['index']
                    assert abs((event[field]-played[0][field])/1e9-i)<=tolerance
                c.results.append(dict(kind='recording-memory-branch-replay',action=action,values=values,passed=True))




def recording_nrpn(c,value):
    ui = c.ui
    assert value in (253,0,-1)
    ui.configure();ui.set_value(1);ui.turn(2,1);ui.set_value(1);ui.turn(2,1);ui.set_value(1);ui.press_key(3)
    ui.open_patch_control(configured=True,setup=False)
    ui.seek_patch_parameter('nrpn14',configured=True,open_control=False)
    ui.turn_patch_control(1);ui.expect_patch_value(126);ui.leave_native_menu()
    ui.turn(1,-3);ui.assign_trig_parameter_key('stored_patch_nrpn14')
    for step,lock in [(1,126),(3,253)]:
        ui.control_edge('step',True,index=step)
        try:
            c.elapse(.05);ui.encoder_event(3,-126);ui.set_value(1 if lock==126 else 2)
            ui.key_edge(1,True);c.elapse(.3)
            try:ui.set_value(-2 if lock==126 else -4)
            finally:ui.key_edge(1,False)
        finally:ui.control_edge('step',False,index=step)
    ui.turn(2,1);ui.assign_trig_parameter_key('stored_patch_control1')
    ui.control_edge('step',True,index=3)
    try:c.elapse(.05);ui.encoder_event(3,-126);ui.set_value(97)
    finally:ui.control_edge('step',False,index=3)
    ui.turn(2,-1);ui.turn(1,2);ui.set_value(-23);ui.press_key(3);ui.turn(1,-2)
    ui.tap_control('record');before=c.snapshot()['midi_count'];ui.tap_control('play_stop')
    def notes(state):return [e for e in state['midi'] if e['index']>before and e['bytes'][0]&240==144 and e['bytes'][2]>0]
    c.wait(lambda state:len(notes(state))==1);c.elapse(.5)
    edit=c.snapshot()['midi_count'];ui.encoder_event(3,-126);c.elapse(.15)
    if value!=-1:
        if value==253:ui.set_value(2)
        ui.key_edge(1,True);c.elapse(.3)
        try:ui.set_value(-4 if value==253 else 1)
        finally:ui.key_edge(1,False)
    state=c.wait(lambda state:len(notes(state))>=4,timeout=14)
    ons=notes(state)
    assert [(e['port'],e['bytes']) for e in ons]==[(2,[145,n,v]) for n,v in [(60,127),(62,117),(64,107),(65,97)]]
    def packet(v):return [(2,[177,99,4]),(2,[177,98,5]),(2,[177,6,v//128]),(2,[177,38,v%128])]
    cc=[e for e in state['midi'] if e['index']>edit and e['bytes'][0]&240==176]
    manual=[128,257,256,255,254,253] if value==253 else ([0] if value==0 else [])
    expected=[event for v in manual for event in packet(v)]
    for step in (2,3,4):
        if value!=-1:expected+=packet(value)
        if step==3:expected.append((2,[177,1,96]))
    assert [(e['port'],e['bytes']) for e in cc]==expected,dict(value=value,expected=expected,actual=cc)
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    scheduled=cc[4*len(manual):];offset=0
    for step in (2,3,4):
        count=(4 if value!=-1 else 0)+(1 if step==3 else 0)
        for event in scheduled[offset:offset+count]:
            assert event['index']<ons[step-1]['index']
            assert abs((event[field]-ons[step-1][field])/1e9)<=tolerance
        offset+=count
    ui.tap_control('play_stop');c.wait(lambda state:not state['midi_capture']['outstanding']);ui.tap_control('record')
    ui.enter_native_menu();ui.expect_patch_value('off' if value==-1 else value);ui.turn_patch_control(1)
    default=value+127;ui.expect_patch_value(default);ui.leave_native_menu()
    start=c.snapshot()['midi_count']
    played=c.playback([(2,[145,n,v]) for n,v in [(60,127),(62,117),(64,107),(65,97)]],cycles=2,timeout=36,settle_seconds=30)
    cc=[e for e in c.snapshot()['midi'] if e['index']>start and e['bytes'][0]&240==176]
    expected=packet(default);schedule=[]
    for i,v in enumerate([126,value,value,value]*2+[126]):
        events=(packet(v) if v!=-1 else [])+([(2,[177,1,96])] if i%4==2 else [])
        expected+=events;schedule.extend([i]*len(events))
    assert [(e['port'],e['bytes']) for e in cc]==expected,dict(value=value,expected=expected,actual=cc)
    for i,event in zip(schedule,cc[4:]):
        assert event['index']<played[i]['index']
        assert abs((event[field]-played[0][field])/1e9-i*4)<=tolerance
    c.results.append(dict(kind='recording-nrpn-route-and-clean-slot',value=value,port=2,channel=2,distinct_default=default,manual_values=manual,clean_CC1_step3=96,passed=True))


def recording_ten_slots_trigless(c):
    """All ten slots record on one rest without changing later locks."""
    import time
    from cases import assert_durations
    from midi_window import MidiWindow
    from note_accounting import note_pairs
    ui=c.ui
    ui.configure();ui.set_mosaic_option_keys([('trigless_locks',True)]);ui.turn(1,-3)
    for slot in range(1,11):
        if slot>1:ui.turn(2,1)
        ui.assign_stored_patch_control(slot)
        for step,value in enumerate((1,2,3,4),1):
            ui.control_edge('step',True,index=step)
            try:c.elapse(.05);ui.encoder_event(3,-126);ui.set_value(value+1)
            finally:ui.control_edge('step',False,index=step)
    ui.turn(2,-9);ui.tap_control('pattern_editor');ui.tap_step(2);ui.tap_control('channel_editor')
    ui.turn(1,2);ui.set_value(-29);ui.press_key(3);ui.turn(1,-2) # /48: eight seconds per step.
    ui.tap_control('record');capture=MidiWindow(c.snapshot()['midi_count'])
    ui.control_edge('play_stop',True);ui.control_edge('play_stop',False)
    def now():return c.logical_ns if c.clock_mode=='controlled-experimental' else time.monotonic_ns()
    origin=now();selected=1
    for slot in range(1,11):
        if slot!=selected:ui.turn(2,slot-selected);selected=slot
        ui.set_value(1) # Off to zero.
    assert now()<origin+7_500_000_000
    remaining=origin+8_200_000_000-now();assert remaining>0;c.elapse(remaining/1e9)
    capture.extend(c.snapshot());ui.control_edge('play_stop',True);ui.control_edge('play_stop',False)
    c.wait(lambda state:capture.extend(state) and not state['midi_capture']['outstanding'])
    notes=capture.note_ons();assert [(e['port'],e['bytes']) for e in notes]==[(1,[144,60,127])]
    pairs=note_pairs(capture.events);assert len(pairs)==1 and pairs[0][0]==notes[0]
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns';tol=2e-9 if c.clock_mode=='controlled-experimental' else .01
    assert abs((pairs[0][1][field]-notes[0][field])/1e9-8)<=tol
    cc=[e for e in capture.events if e['bytes'][0]&240==176]
    expected=[(1,[176,slot,1]) for slot in range(1,11)]
    expected += [(1,[176,slot,0]) for slot in range(1,11)]*2
    assert [(e['port'],e['bytes']) for e in cc]==expected
    for event in cc[:20]:assert abs((event[field]-notes[0][field])/1e9)<=7.5
    for event in cc[20:]:assert abs((event[field]-notes[0][field])/1e9-8)<=tol
    ui.tap_control('record');ui.turn(1,2);ui.set_value(29);ui.press_key(3);ui.turn(1,-2)
    for slot in range(1,11):
        if slot!=selected:ui.turn(2,slot-selected);selected=slot
        ui.encoder_event(3,-126);c.elapse(.15);ui.set_value(6) # Default5.
    before=c.snapshot()['midi_count']
    played=c.playback([(1,[144,60,127]),(1,[144,64,107]),(1,[144,65,97])],cycles=2,timeout=6)
    events=[e for e in c.snapshot()['midi'] if e['index']>before];cc=[e for e in events if e['bytes'][0]&240==176]
    expected=[(1,[176,slot,5]) for slot in range(1,11)]
    for step in (1,2,3,4,1,2,3,4,1):
        value=(1,0,3,4)[step-1];expected += [(1,[176,slot,value]) for slot in range(1,11)]
    assert [(e['port'],e['bytes']) for e in cc]==expected
    origin2=played[0][field]
    for index,event in enumerate(cc[10:]):
        assert abs((event[field]-origin2)/1e9-(index//10)/6)<=tol
    note_steps=(0,2,3,4,6,7,8)
    for note,step in zip(played,note_steps):
        assert abs((note[field]-origin2)/1e9-step/6)<=tol
        group=cc[10+step*10:20+step*10]
        assert len(group)==10 and all(control['index']<note['index'] for control in group)
        assert all(abs((control[field]-note[field])/1e9)<=tol for control in group)
    replay_pairs=note_pairs(events);assert [on for on,off in replay_pairs]==played
    assert_durations(c,played,[1]*(len(played)-1),events=events)
    c.results.append(dict(kind='recording-ten-slot-trigless-rest',slots=10,recorded_step=2,
                          live_zero_packets=20,replay_values=[1,0,3,4],distinct_default=5,passed=True))


def recording_ten_slots(c):
    ui=c.ui
    ui.configure();ui.turn(1,-3)
    for slot in range(1,11):
        if slot>1:ui.turn(2,1)
        ui.assign_stored_patch_control(slot)
        for step,value in [(1,slot),(3,slot+16)]:
            ui.control_edge('step',True,index=step)
            try:c.elapse(.05);ui.encoder_event(3,-126);ui.set_value(value+1)
            finally:ui.control_edge('step',False,index=step)
    ui.turn(2,-9);ui.turn(1,2);ui.set_value(-23);ui.press_key(3);ui.turn(1,-2)
    ui.tap_control('record');before=c.snapshot()['midi_count'];ui.tap_control('play_stop')
    def notes(s):return [e for e in s['midi'] if e['index']>before and e['bytes'][0]==144 and e['bytes'][2]>0]
    def controls(s,marker):return [e for e in s['midi'] if e['index']>marker and e['bytes'][0]&240==176]
    first=c.wait(lambda s:len(notes(s))==1)
    assert [(e['port'],e['bytes']) for e in controls(first,before)]==[(1,[176,slot,slot]) for slot in range(1,11)]
    selected=1
    def edit_slots(slots,value):
        nonlocal selected
        for slot in slots:
            if slot!=selected:ui.turn(2,slot-selected);selected=slot
            ui.set_value(value+1) # Each previously unedited default starts at Off=-1.
    edit_slots(range(1,11,2),0)
    assert len(notes(c.snapshot()))==1,'Odd-slot edit batch missed step2 deadline'
    marker=c.snapshot()['midi_count'];second=c.wait(lambda s:len(notes(s))>=2,timeout=5)
    second_cc=controls(second,marker)
    assert [(e['port'],e['bytes']) for e in second_cc]==[(1,[176,slot,0]) for slot in range(1,11,2)]
    edit_slots(range(2,11,2),1)
    assert len(notes(c.snapshot()))==2,'Even-slot edit batch missed step3 deadline'
    marker=c.snapshot()['midi_count'];state=c.wait(lambda s:len(notes(s))>=4,timeout=9)
    ons=notes(state);assert [(e['port'],e['bytes']) for e in ons]==[(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107),(65,97)]]
    cc=controls(state,marker)
    expected=[(1,[176,slot,0 if slot%2 else 1]) for _ in (3,4) for slot in range(1,11)]
    assert [(e['port'],e['bytes']) for e in cc]==expected,dict(actual=cc,expected=expected)
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    for i,note in enumerate(ons):assert abs((note[field]-ons[0][field])/1e9-4*i)<=tolerance
    for event,i in [(e,1) for e in second_cc]+[(e,2+j//10) for j,e in enumerate(cc)]:
        assert event['index']<ons[i]['index']
        assert abs((event[field]-ons[0][field])/1e9-4*i)<=tolerance
    ui.tap_control('play_stop');c.wait(lambda s:not s['midi_capture']['outstanding']);ui.tap_control('record')
    # Give every patch default a distinct value2, proving replay uses stored locks.
    for slot in range(1,11):
        if slot!=selected:ui.turn(2,slot-selected);selected=slot
        ui.set_value(2 if slot%2 else 1)
    start=c.snapshot()['midi_count']
    played=c.playback([(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107),(65,97)]],cycles=2,timeout=36,settle_seconds=30)
    cc=controls(c.snapshot(),start)
    expected=[(1,[176,slot,2]) for slot in range(1,11)]
    for step in [1,2,3,4]*2+[1]:
        for slot in range(1,11):
            value=slot if step==1 else (0 if slot%2 else (2 if step==2 else 1))
            expected.append((1,[176,slot,value]))
    assert [(e['port'],e['bytes']) for e in cc]==expected,dict(actual=cc,expected=expected)
    for j,event in enumerate(cc[10:]):
        i=j//10;assert event['index']<played[i]['index']
        assert abs((event[field]-played[0][field])/1e9-4*i)<=tolerance
    c.results.append(dict(kind='ten-slot-recording-staggered-zero-one',slots=10,odd_edit_before_step=2,even_edit_before_step=3,distinct_default=2,cycles=2,passed=True))
