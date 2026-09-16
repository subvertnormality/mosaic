"""Shared user-level PERF-002/003/009 workload and slide and parameter-lock oracles."""

# PERF-009 parameter locks: every channel assigns four CC trig parameters with
# distinct default values, and locks each on two steps without slides. Defaults
# are sent on every unlocked step (README "Default Parameter Values"); locked
# steps send their lock value (README "Trig Param Locks").
LOCK_PARAMETERS = (1, 2, 3, 4)
LOCK_DEFAULTS = {1: 20, 2: 40, 3: 60, 4: 80}
LOCK_STEPS = {1: ((1, 101), (9, 11)), 2: ((1, 102), (9, 12)), 3: ((1, 103), (9, 13)), 4: ((1, 104), (9, 14))}

def lock_values(parameter):
    """Expected CC value on steps 1..16 of the locks workload."""
    values = [LOCK_DEFAULTS[parameter]] * 16
    for step, value in LOCK_STEPS[parameter]: values[step - 1] = value
    return values

def set_step_value(d, step, value):
    d.action(type='grid', x=step, y=4, state=1)
    try:d.elapse(.05);d.action(type='enc', n=3, delta=-126);d.elapse(.15);d.enc(3, value + 1)
    finally:d.action(type='grid', x=step, y=4, state=0)
    d.elapse(.1)

def build_project(d,channels,workload='dense',select_parameter=None,select_device=None):
    d.tap(5,8);d.tap(1,1)
    for x in range(1,17):d.tap(x,4)
    d.tap(3,8);d.enc(1,4)
    for channel in range(1,channels+1):
        d.tap(channel,1)
        if select_device:select_device(d,channel)
        else:d.enc(3,1)
        d.enc(2,1)
        if channel>1:d.enc(3,channel-1)
        d.key(3);d.tap(1,2);d.hold_tap((1,4),(16,4))
        if workload=='slides':
            d.enc(1,-3)
            if select_parameter:select_parameter(d,'CC 1')
            else:
                from cases import assign_trig_parameter
                assign_trig_parameter(d,'CC 1')
            for step,value in ((1,0),(9,127)):
                d.action(type='grid',x=step,y=4,state=1)
                try:d.elapse(.05);d.action(type='enc',n=3,delta=-126);d.elapse(.15);d.enc(3,value+1)
                finally:d.action(type='grid',x=step,y=4,state=0)
                d.elapse(.1)
            d.key(3);d.enc(1,3)
        if workload=='extreme':
            # Everything at once: a four-note chord on every step, four locked CC
            # parameters, and a sliding fifth. This is a stress probe, not a
            # certified case: it exists to find where a busy project stops
            # keeping time, so its oracle checks completeness, not exact notes.
            d.enc(1,-4)
            for index,turns in enumerate((2,4,5,7)):
                d.enc(2,1);d.enc(3,turns)
            d.enc(2,-4);d.enc(1,4)
            # The hardware fixture maps CC 1-4, so three locked parameters and a
            # slide on the fourth.
            locked=LOCK_PARAMETERS[:3]
            d.enc(1,-3)
            for index,parameter in enumerate(locked):
                if index:d.enc(2,1)
                label='CC %d'%parameter
                if select_parameter:select_parameter(d,label)
                else:
                    from cases import assign_trig_parameter
                    assign_trig_parameter(d,label)
                d.enc(3,LOCK_DEFAULTS[parameter]+1)
                for step,value in LOCK_STEPS[parameter]:set_step_value(d,step,value)
            d.enc(2,1)
            if select_parameter:select_parameter(d,'CC 4')
            else:
                from cases import assign_trig_parameter
                assign_trig_parameter(d,'CC 4')
            for step,value in ((1,0),(9,127)):set_step_value(d,step,value)
            d.enc(2,-len(locked));d.enc(1,3)
        if workload=='locks':
            d.enc(1,-3)
            for index,parameter in enumerate(LOCK_PARAMETERS):
                if index:d.enc(2,1)
                label='CC %d'%parameter
                if select_parameter:select_parameter(d,label)
                else:
                    from cases import assign_trig_parameter
                    assign_trig_parameter(d,label)
                d.enc(3,LOCK_DEFAULTS[parameter]+1)
                for step,value in LOCK_STEPS[parameter]:set_step_value(d,step,value)
            d.enc(2,-(len(LOCK_PARAMETERS)-1));d.enc(1,3)
    d.tap(1,1)

def check_slides(emitted,ons,channels):
    """Each channel has a complete ordered CC 1 ramp from step 1 to step 9."""
    checked=0
    for channel in range(channels):
        cc=[e for e in emitted if e['bytes'][:2]==[176+channel,1]]
        notes=[e for e in ons if e['bytes'][0]==144+channel]
        for cycle in range(len(notes)//16):
            first,ninth=notes[16*cycle],notes[16*cycle+8]
            ramp=[e['bytes'][2] for e in cc if first['index']-channels*2<e['index']<ninth['index']]
            assert ramp and ramp[0]==0 and ramp[-1]==127 and ramp==sorted(ramp) and len(set(ramp))>=4,(channel+1,cycle,ramp)
            checked+=1
    assert checked>=channels,('No complete slide cycle',checked)
    return checked

def check_locks(emitted,ons,channels):
    """Before each note, a channel has sent every locks-workload CC with that step's value.

    Play first recalls current parameter values (patch recall); later values in the
    same step replace them, so only the last value sent before each note counts.
    """
    pending={channel:{} for channel in range(channels)};counts={channel:0 for channel in range(channels)};checked=0
    for e in emitted:
        status=e['bytes'][0]&240;channel=e['bytes'][0]&15
        if channel>=channels or len(e['bytes'])<3:continue
        if status==176 and e['bytes'][1] in LOCK_PARAMETERS:pending[channel][e['bytes'][1]]=e['bytes'][2]
        elif status==144 and e['bytes'][2]>0:
            step=counts[channel]%16
            for parameter in LOCK_PARAMETERS:
                assert pending[channel].get(parameter)==lock_values(parameter)[step],('Lock value',channel+1,parameter,step+1,pending[channel].get(parameter))
                checked+=1
            pending[channel]={};counts[channel]+=1
    assert all(count>=16 for count in counts.values()),('Lock cycle incomplete',counts)
    return checked

def validate_events(emitted,channels,workload):
    """Shared completeness, ordering, byte, release, and slide oracle."""
    assert emitted and [e['index'] for e in emitted]==list(range(1,len(emitted)+1)),'Non-contiguous native export'
    ons=[e for e in emitted if e['bytes'][0]&240==144 and e['bytes'][2]>0]
    offs=[e for e in emitted if e['bytes'][0]&240==128 or (e['bytes'][0]&240==144 and e['bytes'][2]==0)]
    if workload=='extreme':
        # Chord voices make a step's note count vary, so group by the gap between
        # bursts and require every channel in every step rather than a fixed size.
        steps=[];current=[]
        for event in ons:
            if current and event['monotonic_seconds']-current[-1]['monotonic_seconds']>0.02:steps.append(current);current=[]
            current.append(event)
        if current:steps.append(current)
        steps=[g for g in steps if len(g)>=channels]
        assert len(steps)>=4,('Too few complete steps',len(steps))
        for index,group in enumerate(steps):
            present={e['bytes'][0]&15 for e in group}
            assert present=={c for c in range(channels)},('Channels at step',index,sorted(present))
        assert len(offs)>=len(ons)-channels*8,('Unbalanced releases',len(ons),len(offs))
        return {'ons':ons,'offs':offs,'steps':steps,'slide_cycles':None,'lock_values_checked':None}
    assert ons and len(ons)%channels==0,('Incomplete step',len(ons))
    steps=[ons[i:i+channels] for i in range(0,len(ons),channels)]
    for index,group in enumerate(steps):
        assert sorted(e['bytes'][0] for e in group)==[144+c for c in range(channels)],('Channels at step',index,[e['bytes'] for e in group])
        assert all(e['bytes'][1:]==[60,100] and e['port']==1 for e in group),('Bytes at step',index,[(e['port'],e['bytes']) for e in group])
    assert len(offs)==len(ons),('Unbalanced releases',len(ons),len(offs))
    return {'ons':ons,'offs':offs,'steps':steps,'slide_cycles':check_slides(emitted,ons,channels) if workload=='slides' else None,
            'lock_values_checked':check_locks(emitted,ons,channels) if workload=='locks' else None}
