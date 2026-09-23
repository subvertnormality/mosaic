"""Exact range feedback and clipping contracts."""
import base64


def rejected_range(c,scale_page=False):
    from cases import assert_durations
    from frame_oracle import render
    c.configure()
    if scale_page:c.tap(4,8)
    c.hold_tap((2,4),(4,4));c.elapse(.15)
    def verify(start,stage):
        pitches=[60,62,64,65] if scale_page else [60,62,64,65][start-1:]
        velocities=[127,117,107,97] if scale_page else [127,117,107,97][start-1:]
        notes=c.playback([(1,[144,p,v]) for p,v in zip(pitches,velocities)],cycles=2,timeout=4)
        assert_durations(c,notes,[1]*(len(pitches)*2))
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        for i,note in enumerate(notes):assert abs((note[field]-notes[0][field])/1e9-i/6)<=tolerance
        c.results.append(dict(kind='range-rejection-playback',scale_page=scale_page,stage=stage,pitches=pitches,passed=True))
    verify(2,'valid-before-rejection')
    for sequence in ['held4-release2','press2-press4-release2']:
        before=c.snapshot()['grid'][48:112]
        events=[(4,1),(2,1),(2,0),(4,0)] if sequence=='held4-release2' else [(2,1),(4,1),(2,0),(4,0)]
        for x,z in events:c.action(type='grid',x=x,y=4,state=z)
        expected=render([(0,62,10,'End must follow start')])
        def feedback(state):
            actual=base64.b64decode(state['frame']['pixels_base64'])
            return all(actual[(y*128+x)*4+k]==expected[(y*128+x)*4+k] for y in range(55,64) for x in range(128) for k in range(3))
        c.wait(feedback);c.wait(lambda state:state['grid'][48:112]==before)
        c.results.append(dict(kind='range-rejection-feedback',scale_page=scale_page,sequence=sequence,prior_grid=before,passed=True))
        verify(2,sequence)
    c.hold_tap((3,4),(4,4));c.elapse(.15)
    c.led_values([(1,4),(2,4),(5,4)],[0,0,0]);verify(3,'valid-recovery')


def rejected_range_while_playing(c,scale_page=False):
    from cases import assert_durations
    from frame_oracle import render
    c.configure()
    if scale_page:c.tap(4,8)
    marker=c.snapshot()['midi_count'];c.tap(1,8)
    def notes(state):return [m for m in state['midi'] if m['index']>marker and 144<=m['bytes'][0]<=159 and m['bytes'][2]>0]
    c.wait(lambda state:len(notes(state))>=5)
    for events in [[(4,1),(2,1),(2,0),(4,0)],[(2,1),(4,1),(2,0),(4,0)]]:
        for x,z in events:c.action(type='grid',x=x,y=4,state=z)
        expected=render([(0,62,10,'End must follow start')])
        def feedback(state):
            actual=base64.b64decode(state['frame']['pixels_base64'])
            return all(actual[(y*128+x)*4+k]==expected[(y*128+x)*4+k] for y in range(55,64) for x in range(128) for k in range(3))
        c.wait(feedback);c.elapse(.3)
    state=c.wait(lambda state:len(notes(state))>=17);emitted=notes(state)
    phrase=[[144,60,127],[144,62,117],[144,64,107],[144,65,97]]
    assert [(m['port'],m['bytes']) for m in emitted]==[(1,phrase[i%4]) for i in range(len(emitted))]
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    for i,note in enumerate(emitted):assert abs((note[field]-emitted[0][field])/1e9-i/6)<=tolerance
    c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])
    assert_durations(c,emitted,[1]*16)
    c.results.append(dict(kind='live-range-rejection',scale_page=scale_page,onsets=len(emitted),passed=True))


def global_range_clipping(c):
    from cases import assert_durations
    from frame_oracle import render
    c.configure();c.tap(5,8)
    c.tap(15,7);c.tap(16,7);c.tap(3,8)
    # Distinguish the last two steps through held-step note masks.
    c.enc(1,-4)
    for x,turns in [(15,73),(16,75)]:
        c.action(type='grid',x=x,y=7,state=1)
        try:c.enc(3,turns)
        finally:c.action(type='grid',x=x,y=7,state=0)
    cell=lambda step:((step-1)%16+1,(step-1)//16+4)
    values={1:(60,127),2:(62,117),3:(64,107),4:(65,97),63:(72,100),64:(74,100)}
    for start,end in [(1,4),(2,4),(63,64)]:
        c.hold_tap(cell(start),cell(end))
        for length in [1,2,3,4,64]:
            c.tap(6,8)
            # Song fader inner-left/right select absolute 1/64; rightmost
            # increments by one. This also exercises the fine adjustment.
            c.tap(7 if length==64 else 2,7)
            if length!=64:
                for _ in range(length-1):c.tap(8,7)
            expected=render([(0,62,10,'Global pattern length: '+str(length))])
            def feedback(state):
                actual=base64.b64decode(state['frame']['pixels_base64'])
                return all(actual[(y*128+x)*4+k]==expected[(y*128+x)*4+k] for y in range(55,64) for x in range(128) for k in range(3))
            c.wait(feedback);c.tap(3,8)
            # LEDs show the playable range, capped by global length. Restoring
            # global length must expose the previously selected endpoints again.
            steps=list(range(start,min(end,start+length-1)+1))
            c.led_values([cell(i) for i in range(1,65)],[15 if i in steps else 0 for i in range(1,65)])
            phrase=[(1,[144,*values[i]]) for i in steps]
            notes=c.playback(phrase,cycles=3,timeout=5)
            assert_durations(c,notes,[1]*(len(steps)*2))
            field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
            tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
            for i,note in enumerate(notes):assert abs((note[field]-notes[0][field])/1e9-i/6)<=tolerance
            c.results.append(dict(kind='global-channel-range-clipping',start=start,end=end,global_length=length,played_steps=steps,passed=True))


def queued_global_length_transitions(c):
    from cases import assert_durations
    from frame_oracle import render
    c.configure();c.hold_tap((2,4),(4,4));c.tap(6,8)
    c.tap(2,7)
    for _ in range(3):c.tap(8,7)
    marker=c.snapshot()['midi_count'];c.tap(1,8)
    def emitted(state):return [m for m in state['midi'] if m['index']>marker and 144<=m['bytes'][0]<=159 and m['bytes'][2]>0]
    def queued(length,before_count):
        c.tap(2,7)
        for _ in range(length-1):c.tap(8,7)
        expected=render([(0,62,10,"Q'd: Global pattern length: "+str(length))])
        def feedback(state):
            actual=base64.b64decode(state['frame']['pixels_base64'])
            return all(actual[(y*128+x)*4+k]==expected[(y*128+x)*4+k] for y in range(55,64) for x in range(128) for k in range(3))
        state=c.wait(feedback)
        assert len(emitted(state))<before_count,'Fixture queue missed the intended boundary'
    # Global4 finishes at onset index4. The capped offset phrase becomes
    # steps2/3 there, without resetting its clock or its still-valid playhead.
    queued(2,5)
    state=c.wait(lambda state:len(emitted(state))>=13,4)
    assert len(emitted(state))==13,'Fixture missed growth scheduling window'
    # The new global2 cycles end at indices6,8,10,12,14. Queue after12;
    # growth to3 must apply at14 and expose step4 again on index15.
    queued(3,15)
    state=c.wait(lambda state:len(emitted(state))>=25,5);notes=emitted(state)
    steps=[2,3,4,2]+[3,2]*5+[3,4,2]*4
    assert len(notes)<=len(steps)
    values={2:(62,117),3:(64,107),4:(65,97)}
    expected=[(1,[144,*values[step]]) for step in steps[:len(notes)]]
    actual=[(m['port'],m['bytes']) for m in notes]
    assert actual==expected,dict(expected=expected,actual=actual)
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    for i,note in enumerate(notes):assert abs((note[field]-notes[0][field])/1e9-i/6)<=tolerance
    c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])
    assert_durations(c,notes,[1]*24);c.tap(3,8)
    c.led_values([(1,4),(2,4),(3,4),(4,4),(5,4)],[0,15,15,15,0])
    c.results.append(dict(kind='queued-global-shrink-grow',caps=[4,2,3],application_onset_indices=[4,14],expected_steps=steps[:len(notes)],passed=True))

def range_reject_001(c):
    return rejected_range(c, False)


def range_reject_002(c):
    return rejected_range(c, True)


def range_reject_003(c):
    return rejected_range_while_playing(c, False)


def range_reject_004(c):
    return rejected_range_while_playing(c, True)
