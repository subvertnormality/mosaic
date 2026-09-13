"""Shared user-level PERF-002/003 workload and slide oracle."""

def build_project(d,channels,workload='dense',select_parameter=None):
    d.tap(5,8);d.tap(1,1)
    for x in range(1,17):d.tap(x,4)
    d.tap(3,8);d.enc(1,4)
    for channel in range(1,channels+1):
        d.tap(channel,1)
        d.enc(3,1);d.enc(2,1)
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

def validate_events(emitted,channels,workload):
    """Shared completeness, ordering, byte, release, and slide oracle."""
    assert emitted and [e['index'] for e in emitted]==list(range(1,len(emitted)+1)),'Non-contiguous native export'
    ons=[e for e in emitted if e['bytes'][0]&240==144 and e['bytes'][2]>0]
    offs=[e for e in emitted if e['bytes'][0]&240==128 or (e['bytes'][0]&240==144 and e['bytes'][2]==0)]
    assert ons and len(ons)%channels==0,('Incomplete step',len(ons))
    steps=[ons[i:i+channels] for i in range(0,len(ons),channels)]
    for index,group in enumerate(steps):
        assert sorted(e['bytes'][0] for e in group)==[144+c for c in range(channels)],('Channels at step',index,[e['bytes'] for e in group])
        assert all(e['bytes'][1:]==[60,100] and e['port']==1 for e in group),('Bytes at step',index,[e['bytes'] for e in group])
    assert len(offs)==len(ons),('Unbalanced releases',len(ons),len(offs))
    return {'ons':ons,'offs':offs,'steps':steps,'slide_cycles':check_slides(emitted,ons,channels) if workload=='slides' else None}
