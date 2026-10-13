"""Shared user-level PERF-002/003/009 workload and slide and parameter-lock oracles."""

# PERF-009 parameter locks: every channel assigns four CC trig parameters with
# distinct default values, and locks each on two steps without slides. Defaults
# are sent on every unlocked step (README "Default Parameter Values"); locked
# steps send their lock value (README "Trig Param Locks").
LOCK_PARAMETERS = (1, 2, 3, 4)
# The extreme probe sounds every other step, so its steps are this many apart.
EXTREME_STEP_STRIDE = 2
LOCK_DEFAULTS = {1: 20, 2: 40, 3: 60, 4: 80}
LOCK_STEPS = {1: ((1, 101), (9, 11)), 2: ((1, 102), (9, 12)), 3: ((1, 103), (9, 13)), 4: ((1, 104), (9, 14))}

def lock_values(parameter):
    """Expected CC value on steps 1..16 of the locks workload."""
    values = [LOCK_DEFAULTS[parameter]] * 16
    for step, value in LOCK_STEPS[parameter]: values[step - 1] = value
    return values

def set_step_value(d, step, value):
    with d.ui.hold_step(step):
        d.elapse(.05);d.ui.encoder_event(3, -126);d.elapse(.15);d.ui.set_value(value + 1)
    d.elapse(.1)

def build_project(d,channels,workload='dense',select_parameter=None,select_device=None):
    d.ui.pattern_editor();d.ui.select_channel(1)
    # Every channel plays this one pattern; the extreme probe trigs every other step.
    for step in range(1,17,EXTREME_STEP_STRIDE if workload=='extreme' else 1):d.ui.tap_step(step)
    d.ui.menu('channel_editor');d.ui.turn(1,4)
    for channel in range(1,channels+1):
        d.ui.select_channel(channel)
        if select_device:select_device(d,channel)
        else:d.ui.set_value(1)
        d.ui.turn(2,1)
        if channel>1:d.ui.set_value(channel-1)
        d.ui.press_key(3);d.ui.tap_control('pattern_slot',1);d.ui.set_range(1,16)
        # The pattern slot tap shows Merge detail (grid actions show what they changed):
        # return to Device, where the rest of this recipe (and the next channel) starts.
        d.ui.channel_page('midi_config',channel=channel,confirm=False)
        if workload=='slides':
            d.ui.turn(1,-3)
            if select_parameter:select_parameter(d,'CC 1')
            else:d.ui.assign_trig_parameter('CC 1')
            for step,value in ((1,0),(9,127)):
                with d.ui.hold_step(step):
                    d.elapse(.05);d.ui.encoder_event(3,-126);d.elapse(.15);d.ui.set_value(value+1)
                d.elapse(.1)
            d.ui.press_key(3);d.ui.turn(1,3)
        if workload=='extreme':
            # A busy project: a four-note chord on every other step of every
            # channel, three locked CC parameters and a sliding fourth. A trig on
            # every step of all sixteen channels is not a project anyone plays,
            # and over DIN MIDI it asks for more messages than the wire carries.
            # This is a stress probe, not a certified case: it exists to find
            # where a busy project stops keeping time, so its oracle checks
            # completeness, not exact notes.
            d.ui.turn(1,-4)
            for index,turns in enumerate((2,4,5,7)):
                d.ui.turn(2,1);d.ui.set_value(turns)
            d.ui.turn(2,-4);d.ui.turn(1,4)
            # The hardware fixture maps CC 1-4, so three locked parameters and a
            # slide on the fourth.
            locked=LOCK_PARAMETERS[:3]
            d.ui.turn(1,-3)
            for index,parameter in enumerate(locked):
                if index:d.ui.turn(2,1)
                label='CC %d'%parameter
                if select_parameter:select_parameter(d,label)
                else:d.ui.assign_trig_parameter(label)
                d.ui.set_value(LOCK_DEFAULTS[parameter]+1)
                for step,value in LOCK_STEPS[parameter]:set_step_value(d,step,value)
            d.ui.turn(2,1)
            if select_parameter:select_parameter(d,'CC 4')
            else:d.ui.assign_trig_parameter('CC 4')
            for step,value in ((1,0),(9,127)):set_step_value(d,step,value)
            d.ui.turn(2,-len(locked));d.ui.turn(1,3)
        if workload=='locks':
            d.ui.turn(1,-3)
            for index,parameter in enumerate(LOCK_PARAMETERS):
                if index:d.ui.turn(2,1)
                label='CC %d'%parameter
                if select_parameter:select_parameter(d,label)
                else:d.ui.assign_trig_parameter(label)
                d.ui.set_value(LOCK_DEFAULTS[parameter]+1)
                for step,value in LOCK_STEPS[parameter]:set_step_value(d,step,value)
            d.ui.turn(2,-(len(LOCK_PARAMETERS)-1));d.ui.turn(1,3)
    d.ui.select_channel(1)

def check_slides(emitted,ons,channels,lead_ms=0):
    """Each channel has a complete ordered CC 1 ramp from step 1 to step 9.

    With a lock lead a ramp value leaves before the step it belongs to, so the
    cycle's first value precedes its own note. How far ahead is not a fixed
    figure: the value leaves on a clock pulse a lead before the step's pulse,
    while the note is dispatched once that step's channels have all been
    resolved, so a busy step widens the gap beyond the lead itself.

    The cycle is therefore bounded by the notes around it rather than by a time
    guard. A value for this cycle cannot precede the previous note, because the
    scheduling rule holds it to at least halfway between that note and its own
    step, and it cannot follow the ninth. That bound is exact at any lead and any
    step occupancy, where a time guard has to be guessed and then widened."""
    checked=0
    for channel in range(channels):
        cc=[e for e in emitted if e['bytes'][:2]==[176+channel,1]]
        notes=[e for e in ons if e['bytes'][0]==144+channel]
        for cycle in range(len(notes)//16):
            first,ninth=notes[16*cycle],notes[16*cycle+8]
            floor=notes[16*cycle-1]['index'] if cycle else -1
            ramp=[e['bytes'][2] for e in cc if floor<e['index']<ninth['index']]
            assert ramp and ramp[0]==0 and ramp[-1]==127 and ramp==sorted(ramp) and len(set(ramp))>=4,(channel+1,cycle,ramp)
            # The ramp is a glide across the cycle, not a burst before it. Its
            # samples are produced as the steps play, so most of them land after
            # the cycle's first note, and its destination arrives with the ninth.
            after=[e for e in cc if first['index']<e['index']<ninth['index']]
            assert len(after)>=len(ramp)-2,('Ramp bunched before its cycle',channel+1,cycle,len(after),len(ramp))
            assert after and after[-1]['bytes'][2]==127,('Ramp does not reach its destination in the cycle',channel+1,cycle)
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

def validate_events(emitted,channels,workload,lead_ms=0):
    """Shared completeness, ordering, byte, release, and slide oracle."""
    assert emitted and [e['index'] for e in emitted]==list(range(1,len(emitted)+1)),'Non-contiguous native export'
    ons=[e for e in emitted if e['bytes'][0]&240==144 and e['bytes'][2]>0]
    offs=[e for e in emitted if e['bytes'][0]&240==128 or (e['bytes'][0]&240==144 and e['bytes'][2]==0)]
    if workload=='extreme':
        # Chord voices make a step's note count vary, so group by the gap between
        # bursts and require every channel in every step rather than a fixed size.
        steps=[];current=[]
        for event in ons:
            if current and event['monotonic_ns']-current[-1]['monotonic_ns']>20_000_000:steps.append(current);current=[]
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
    return {'ons':ons,'offs':offs,'steps':steps,'slide_cycles':check_slides(emitted,ons,channels,lead_ms) if workload=='slides' else None,
            'lock_values_checked':check_locks(emitted,ons,channels) if workload=='locks' else None}
