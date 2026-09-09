"""Manual mask-clear gestures, neighbouring-step isolation and MIDI oracles."""

def mask_clear_attributes(c,attribute,defaults=False):
    from cases import assert_durations
    selection,turns={'note':(0,[73,75]),'velocity':(1,[91,81]),'length':(2,[8,15]),'trig':(-1,[1,1]),'chord':(3,[2,4])}[attribute]
    c.configure();c.enc(1,-4);c.enc(2,selection)
    if defaults:
        default_turns,turns={"note":(68,[5,7]),"velocity":(51,[40,30]),"length":(18,[-10,-3]),"chord":(3,[2,3])}[attribute]
        c.enc(3,default_turns)
    for step,amount in enumerate(turns,1):
        c.action(type='grid',x=step,y=4,state=1)
        try:c.enc(3,amount)
        finally:c.action(type='grid',x=step,y=4,state=0)
        c.elapse(.06)
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    def verify(active,stage):
        phrase=[];lengths=[];positions=[]
        for step,(note,velocity) in enumerate(zip([60,62,64,65],[127,117,107,97]),1):
            overridden=step in active
            if attribute=='trig' and overridden:continue
            if defaults and attribute=='note':note=67
            if defaults and attribute=='velocity':velocity=50
            if attribute=='note' and overridden:note=[72,74][step-1]
            if attribute=='velocity' and overridden:velocity=[90,80][step-1]
            length=([.5,1.25][step-1] if overridden else (2 if defaults else 1)) if attribute=='length' else 1
            phrase.append((1,[144,note,velocity]));lengths.append(length);positions.append(step-1)
            if attribute=='chord' and (overridden or defaults):
                # Default offset2: E/F/G/A. Override offsets4/5: G/B.
                chord=([67,71][step-1] if overridden else [64,65,67,69][step-1]) if defaults else [64,69][step-1]
                phrase.append((1,[144,chord,velocity]));lengths.append(length);positions.append(step-1)
        notes=c.playback(phrase,cycles=3 if defaults else 2,timeout=5)
        assert_durations(c,notes,lengths*2)
        for i,note in enumerate(notes):
            elapsed=((i//len(phrase))*4+positions[i%len(phrase)]-positions[0])/6
            assert abs((note[field]-notes[0][field])/1e9-elapsed)<=tolerance
        c.results.append(dict(kind='mask-clear-attribute',attribute=attribute,defaults=defaults,stage=stage,active_step_overrides=sorted(active),expected_phrase=phrase,expected_lengths=lengths,passed=True))
    verify({1,2},'both-step-overrides')
    for stage in ('clear-first-step','repeat-clear-first-step'):
        c.action(type='grid',x=1,y=4,state=1)
        shifted=stage=='repeat-clear-first-step'
        if shifted:c.action(type='key',n=1,state=1);c.elapse(.3)
        try:c.key(2)
        finally:
            if shifted:c.action(type='key',n=1,state=0)
            c.action(type='grid',x=1,y=4,state=0)
        c.elapse(.06);verify({2},stage)
    c.action(type='key',n=1,state=1);c.elapse(.3)
    try:c.key(2)
    finally:c.action(type='key',n=1,state=0)
    c.elapse(.06);verify(set(),'clear-channel-step-overrides')
