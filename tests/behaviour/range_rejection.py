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


def rejected_range_channel_isolation(c):
    from cases import assert_durations
    c.configure()
    c.tap(2,1);c.enc(3,1);c.enc(2,1);c.enc(3,1);c.enc(2,1);c.enc(3,1);c.key(3)
    c.tap(1,2);c.hold_tap((1,4),(3,4));c.enc(1,-4)
    for index,(global_turns,local_turns) in enumerate([(80,2),(41,20),(8,7)]):
        if index:c.enc(2,1)
        c.enc(3,global_turns);c.action(type='grid',x=2,y=4,state=1)
        try:c.enc(3,local_turns)
        finally:c.action(type='grid',x=2,y=4,state=0)
        c.elapse(.06)
    c.tap(1,1)
    marker=c.snapshot()['midi_count'];c.tap(1,8)
    def emitted(state):return [m for m in state['midi'] if m['index']>marker and 144<=m['bytes'][0]<=159 and m['bytes'][2]>0]
    c.wait(lambda state:len(emitted(state))>=10)
    c.hold_tap((4,4),(2,4))
    state=c.wait(lambda state:sum(m['port']==1 for m in emitted(state))>=17 and sum(m['port']==2 for m in emitted(state))>=17,5)
    all_notes=emitted(state);assert all((m['port'],m['bytes'][0]) in [(1,144),(2,145)] for m in all_notes)
    c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    phrases={1:[[144,60,127],[144,62,117],[144,64,107],[144,65,97]],2:[[145,79,40],[145,81,60],[145,79,40]]}
    for port,phrase in phrases.items():
        notes=[m for m in all_notes if m['port']==port]
        assert [m['bytes'] for m in notes]==[phrase[i%len(phrase)] for i in range(len(notes))]
        for i,note in enumerate(notes):assert abs((note[field]-notes[0][field])/1e9-i/6)<=tolerance
        assert_durations(c,notes,[1]*12 if port==1 else [.5,1.25,.5]*4)
    first=[next(m[field] for m in all_notes if m['port']==port) for port in [1,2]]
    assert abs(first[0]-first[1])/1e9<=tolerance
    c.results.append(dict(kind='rejected-range-channel-isolation',ranges=[[1,4],[1,3]],phrases=phrases,passed=True))


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


def offset_range_clipping(c):
    from cases import assert_durations
    c.configure();c.hold_tap((2,4),(4,4));c.tap(6,8);c.tap(2,7);c.tap(8,7);c.tap(3,8)
    c.led_values([(1,4),(2,4),(3,4),(4,4)],[0,15,15,0])
    notes=c.playback([(1,[144,62,117]),(1,[144,64,107])],cycles=3,timeout=4)
    assert_durations(c,notes,[1]*6)
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    for i,note in enumerate(notes):assert abs((note[field]-notes[0][field])/1e9-i/6)<=tolerance
    c.results.append(dict(kind='offset-channel-global-cap',start=2,end=4,global_length=2,passed=True))


def offset_range_rates(c):
    from cases import assert_durations
    c.configure();c.hold_tap((2,4),(4,4));c.tap(6,8);c.tap(2,7);c.tap(8,7);c.tap(3,8)
    c.enc(1,-1);selected=13
    for index,label,factor in [(8,'x3',1/3),(10,'x2',.5),(13,'/1',1),(15,'/2',2),(17,'/3',3)]:
        c.enc(3,selected-index);c.key(3);selected=index
        notes=c.playback([(1,[144,62,117]),(1,[144,64,107])],cycles=10,timeout=12)
        assert_durations(c,notes,[factor]*18)
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        for i,note in enumerate(notes):assert abs((note[field]-notes[0][field])/1e9-i*factor/6)<=tolerance
        c.results.append(dict(kind='offset-global-range-clock-rate',label=label,completed_loops=10,passed=True))

def offset_scale_range_clipping(c):
    from cases import assert_durations
    c.configure();c.tap(4,8);c.enc(2,-1)
    for slot,semitones in [(2,2),(3,4)]:
        c.action(type='key',n=1,state=1)
        try:c.elapse(.3);c.tap(slot,3)
        finally:c.action(type='key',n=1,state=0)
        c.enc(3,semitones);c.key(3)
    # Scale track starts beyond step1, with independent D/E/C locks.
    for step,slot in [(2,2),(3,3),(4,1)]:c.hold_tap((step,4),(slot,3))
    c.hold_tap((2,4),(4,4))
    for length,pitches in [(1,[62]),(2,[62,66]),(3,[62,66,64]),(2,[62,66])]:
        c.tap(6,8);c.tap(2,7)
        for _ in range(length-1):c.tap(8,7)
        c.tap(4,8)
        notes=c.playback([(1,[144,p,v]) for p,v in zip(pitches,[127,117,107])],cycles=4,timeout=5)
        assert_durations(c,notes,[1]*(len(pitches)*3))
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        for i,note in enumerate(notes):assert abs((note[field]-notes[0][field])/1e9-i/6)<=tolerance
        c.results.append(dict(kind='offset-scale-global-cap',length=length,pitches=pitches,passed=True))
