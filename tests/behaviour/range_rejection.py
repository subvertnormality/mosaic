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
