"""Native recording lifetime tests; literal MIDI expectations, physical controls."""

def recording_lifetime(c,ending,scale_page=False):
    from cases import assign_trig_parameter,menu_value,parameter_list_label
    from patch_params import open_patch_control,turn
    assert ending in ('selected-wrap','nonselected-wrap','disarm','stop','reassign','same-assignment','configuration','slide-active','slide-off','pending-assignment','pending-configuration','mute')
    slide=ending.startswith('slide-')
    value=-1 if ending=='slide-off' else 64
    open_patch_control(c);turn(c,63);turn(c,1);menu_value(c,'63');c.key(1)
    c.enc(1,-3);assign_trig_parameter(c,'CC 1')
    for step,lock in [(1,24),(3,96)]:
        c.action(type='grid',x=step,y=4,state=1)
        try:c.elapse(.05);c.action(type='enc',n=3,delta=-126);c.enc(3,lock+1)
        finally:c.action(type='grid',x=step,y=4,state=0)
    if slide:c.key(3)
    c.enc(1,2);c.enc(3,-23);c.key(3);c.enc(1,-2)
    c.tap(2,8);before=c.snapshot()['midi_count'];c.tap(1,8)
    def notes(state):return [e for e in state['midi'] if e['index']>before and e['bytes'][0]&240==144 and e['bytes'][2]>0]
    c.wait(lambda state:len(notes(state))==1);c.elapse(.5)
    edit=c.snapshot()['midi_count']
    if value==-1:c.action(type='enc',n=3,delta=-126);c.elapse(.15)
    else:c.enc(3,1)
    wanted_steps=4;replay=[24,64,64,64];port=1;channel=0;cc_number=1
    if ending=='mute':
        def shift_mute():
            c.action(type='key',n=1,state=1)
            try:c.elapse(.3);c.tap(1,1)
            finally:c.action(type='key',n=1,state=0)
        shift_mute();c.led_values([(1,1)],[7])
        marker=c.snapshot()['midi_count'];c.elapse(8)
        quiet=c.snapshot()
        assert not [e for e in quiet['midi'] if e['index']>marker and (e['bytes'][0]&240==176 or (e['bytes'][0]&240==144 and e['bytes'][2]>0))],quiet['midi']
        assert not quiet['midi_capture']['outstanding']
        shift_mute();c.led_values([(1,1)],[15]);wanted_steps=2
    elif ending=='selected-wrap':wanted_steps=5
    elif ending=='nonselected-wrap':
        c.tap(4,8) if scale_page else c.tap(2,1)
        c.wait(lambda state:len(notes(state))>=5,timeout=18)
        c.elapse(.3)
        c.tap(3,8) if scale_page else c.tap(1,1)
        wanted_steps=8
    elif ending in ('pending-assignment','pending-configuration'):
        c.wait(lambda state:len(notes(state))>=2,timeout=5)
        if ending=='pending-assignment':
            c.key(2);c.enc(3,1);parameter_list_label(c,'CC 2')
        else:
            c.enc(1,3);c.enc(2,1);c.enc(3,1);c.enc(2,1);c.enc(3,1)
        # An eligible step occurs with the proposed edit still unconfirmed.
        c.wait(lambda state:len(notes(state))>=3,timeout=5)
        c.key(2) # Cancel through the real UI.
        if ending=='pending-configuration':c.enc(1,-3)
    elif ending in ('disarm','stop','reassign','same-assignment','configuration'):
        c.wait(lambda state:len(notes(state))>=2,timeout=5)
        replay=[24,64,96,65]
        if ending=='disarm':c.tap(2,8);c.tap(2,8)
        elif ending=='stop':
            c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])
            before=c.snapshot()['midi_count'];edit=before;c.tap(1,8)
        elif ending in ('reassign','same-assignment'):
            c.key(2)
            if ending=='reassign':c.enc(3,1);cc_number=2
            else:c.enc(3,1);c.enc(3,-1) # Enqueue actual same-assignment confirmation.
            parameter_list_label(c,'CC '+str(cc_number));c.key(3);c.key(2)
            if ending=='same-assignment':replay=[24,64,64,64]
        else:
            c.enc(1,3);c.enc(2,1);c.enc(3,1);c.enc(2,1);c.enc(3,1);c.key(3);c.enc(1,-3)
            port=2;channel=1;replay=[65]*4
            # Confirmation clears device locks and resets assignments, including
            # route-only changes. Reassign before wrap to expose latent dirty state.
            assign_trig_parameter(c,'CC 1')
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
    elif ending in ('same-assignment','pending-assignment','pending-configuration'):wanted=[(1,[176,1,64])]*4
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
    c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding']);c.tap(2,8)
    if slide:c.key(3) # Disable slide through the same UI before lock replay.
    current=-1 if ending in ('reassign','configuration','slide-off') else 64
    c.enc(3,65-current)
    # Use the native patch menu to prove the new default is independent.
    c.key(1)
    if ending=='reassign':c.enc(2,1)
    menu_value(c,'65');c.key(1)
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


def recording_nrpn(c,value):
    from cases import assign_trig_parameter,menu_value,menu_label
    from patch_params import open_patch_control,turn
    from frame_oracle import selected_line
    assert value in (253,0,-1)
    c.configure();c.enc(3,1);c.enc(2,1);c.enc(3,1);c.enc(2,1);c.enc(3,1);c.key(3)
    open_patch_control(c,configured=True,setup=False)
    for _ in range(180):
        if selected_line(c.snapshot(),'NRPN14'):break
        c.enc(2,1)
    else:raise AssertionError('NRPN14 patch control not reached')
    menu_label(c,'NRPN14');turn(c,1);menu_value(c,'126');c.key(1)
    c.enc(1,-3);assign_trig_parameter(c,'NRPN14')
    for step,lock in [(1,126),(3,253)]:
        c.action(type='grid',x=step,y=4,state=1)
        try:
            c.elapse(.05);c.action(type='enc',n=3,delta=-126);c.enc(3,1 if lock==126 else 2)
            c.action(type='key',n=1,state=1);c.elapse(.3)
            try:c.enc(3,-2 if lock==126 else -4)
            finally:c.action(type='key',n=1,state=0)
        finally:c.action(type='grid',x=step,y=4,state=0)
    c.enc(2,1);assign_trig_parameter(c,'Control 1')
    c.action(type='grid',x=3,y=4,state=1)
    try:c.elapse(.05);c.action(type='enc',n=3,delta=-126);c.enc(3,97)
    finally:c.action(type='grid',x=3,y=4,state=0)
    c.enc(2,-1);c.enc(1,2);c.enc(3,-23);c.key(3);c.enc(1,-2)
    c.tap(2,8);before=c.snapshot()['midi_count'];c.tap(1,8)
    def notes(state):return [e for e in state['midi'] if e['index']>before and e['bytes'][0]&240==144 and e['bytes'][2]>0]
    c.wait(lambda state:len(notes(state))==1);c.elapse(.5)
    edit=c.snapshot()['midi_count'];c.action(type='enc',n=3,delta=-126);c.elapse(.15)
    if value!=-1:
        if value==253:c.enc(3,2)
        c.action(type='key',n=1,state=1);c.elapse(.3)
        try:c.enc(3,-4 if value==253 else 1)
        finally:c.action(type='key',n=1,state=0)
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
    c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding']);c.tap(2,8)
    c.key(1);menu_value(c,'X' if value==-1 else str(value));turn(c,1)
    default=value+127;menu_value(c,str(default));c.key(1)
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


def recording_stop_safety(c):
    from cases import assign_trig_parameter,set_mosaic_options,menu_value
    from patch_params import open_patch_control,turn
    c.configure();set_mosaic_options(c,[('Shift press to stop',True)])
    open_patch_control(c,setup=False);turn(c,63);turn(c,1);menu_value(c,'63');c.key(1)
    c.enc(1,-3);assign_trig_parameter(c,'CC 1')
    for step,value in [(1,24),(3,96)]:
        c.action(type='grid',x=step,y=4,state=1)
        try:c.elapse(.05);c.action(type='enc',n=3,delta=-126);c.enc(3,value+1)
        finally:c.action(type='grid',x=step,y=4,state=0)
    c.enc(1,2);c.enc(3,-23);c.key(3);c.enc(1,-2)
    c.tap(2,8);before=c.snapshot()['midi_count'];c.tap(1,8)
    def notes(state):return [e for e in state['midi'] if e['index']>before and e['bytes'][0]==144 and e['bytes'][2]>0]
    c.wait(lambda state:len(notes(state))==1);c.elapse(.5);c.enc(3,1)
    c.wait(lambda state:len(notes(state))>=2,timeout=5)
    def long_stop():
        c.action(type='grid',x=1,y=8,state=1)
        try:c.elapse(1.2)
        finally:c.action(type='grid',x=1,y=8,state=0)
        c.elapse(.06);c.wait(lambda state:not state['midi_capture']['outstanding'])
    long_stop()
    before=c.snapshot()['midi_count'];c.tap(1,8)
    first=c.wait(lambda state:len(notes(state))>=1)
    actual=[(e['port'],e['bytes']) for e in first['midi'] if e['index']>before and e['bytes'][0]&240==176]
    expected=[(1,[176,1,64]),(1,[176,1,24])] # Patch recall then unchanged first lock.
    assert actual==expected,dict(expected=expected,actual=actual,meaning='Long Stop must clear pending recording while arm remains enabled')
    state=c.wait(lambda state:len(notes(state))>=4,timeout=14)
    assert [e['bytes'] for e in notes(state)]==[[144,n,v] for n,v in [(60,127),(62,117),(64,107),(65,97)]]
    cc=[(e['port'],e['bytes']) for e in state['midi'] if e['index']>before and e['bytes'][0]&240==176]
    assert cc==[(1,[176,1,v]) for v in [64,24,64,96,64]],cc
    long_stop()
    # Prove retained arm through a new recorded edit and distinct-default replay.
    # A Stop implementation which disarms would leave step 2 at its old 64.
    before=c.snapshot()['midi_count'];c.tap(1,8)
    c.wait(lambda state:len(notes(state))==1);c.elapse(.5);c.enc(3,1)
    c.wait(lambda state:len(notes(state))>=2,timeout=5)
    long_stop();c.tap(2,8) # Explicitly disarm only after the new edit is recorded.
    c.enc(3,1) # Default 66 differs from recorded 65 and original lock 64.
    before=c.snapshot()['midi_count'];c.tap(1,8)
    state=c.wait(lambda state:len(notes(state))>=2,timeout=5)
    cc=[(e['port'],e['bytes']) for e in state['midi'] if e['index']>before and e['bytes'][0]&240==176]
    assert cc==[(1,[176,1,v]) for v in [66,24,65]],dict(actual=cc,meaning='Stop retains arm: new step-2 edit survives disarmed replay with a different default')
    long_stop()
    c.results.append(dict(kind='recording-stop-safety-long-press-restart',record_arm_retained=True,first_lock=24,recorded_step2=64,untouched_step3=96,new_recorded_step2=65,replay_default=66,passed=True))


def recording_ten_slots(c):
    from cases import assign_trig_parameter
    c.configure();c.enc(1,-3)
    for slot in range(1,11):
        if slot>1:c.enc(2,1)
        assign_trig_parameter(c,'CC '+str(slot))
        for step,value in [(1,slot),(3,slot+16)]:
            c.action(type='grid',x=step,y=4,state=1)
            try:c.elapse(.05);c.action(type='enc',n=3,delta=-126);c.enc(3,value+1)
            finally:c.action(type='grid',x=step,y=4,state=0)
    c.enc(2,-9);c.enc(1,2);c.enc(3,-23);c.key(3);c.enc(1,-2)
    c.tap(2,8);before=c.snapshot()['midi_count'];c.tap(1,8)
    def notes(s):return [e for e in s['midi'] if e['index']>before and e['bytes'][0]==144 and e['bytes'][2]>0]
    def controls(s,marker):return [e for e in s['midi'] if e['index']>marker and e['bytes'][0]&240==176]
    first=c.wait(lambda s:len(notes(s))==1)
    assert [(e['port'],e['bytes']) for e in controls(first,before)]==[(1,[176,slot,slot]) for slot in range(1,11)]
    selected=1
    def edit_slots(slots,value):
        nonlocal selected
        for slot in slots:
            if slot!=selected:c.enc(2,slot-selected);selected=slot
            c.enc(3,value+1) # Each previously unedited default starts at Off=-1.
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
    c.tap(1,8);c.wait(lambda s:not s['midi_capture']['outstanding']);c.tap(2,8)
    # Give every patch default a distinct value2, proving replay uses stored locks.
    for slot in range(1,11):
        if slot!=selected:c.enc(2,slot-selected);selected=slot
        c.enc(3,2 if slot%2 else 1)
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
