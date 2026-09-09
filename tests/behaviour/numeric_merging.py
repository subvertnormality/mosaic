def numeric_note_merge(c,foreign_velocity=False,pentatonic=False):
    from cases import set_mosaic_options,assert_durations
    c.configure();set_mosaic_options(c,[('Lock merged to pent.',pentatonic)])
    sources=[(0,2,4,6),(2,4,6,0),(6,6,6,6)]
    c.tap(5,8)
    for slot,values in enumerate(sources,1):
        c.tap(slot,1)
        if slot>1:
            for x in range(1,5):c.tap(x,4)
        c.tap(5,8)
        for x,degree in enumerate(values,1):c.tap(x,7-degree)
        steady=[(x,7-degree) for x,degree in enumerate(values,1) if not (x==slot and degree==6)]
        c.led_values(steady,[12]*len(steady))
        if values[slot-1]==6:
            c.wait(lambda state:state['grid'][slot-1] in (11,13))
            c.results.append(dict(kind='selected-pattern-top-note-blink',slot=slot,levels=[11,13],passed=True))
        c.tap(3,8);c.tap(5,8)
    c.tap(3,8);c.tap(2,2) # Only patterns1/2 are assigned.
    c.tap(14,8);c.tap(14,8);c.led_values([(14,8)],[8]) # All trigs.
    c.hold_tap((16,8),(3 if foreign_velocity else 1,2))
    c.led_values([(1,2),(2,2),(3,2)],[15,15,2])
    velocity=[100]*4 if foreign_velocity else [127,117,107,97]
    # Degree means [1,3,5,3]; Higher = mean+(max-min)=[3,5,7,9].
    # Independently map these zero-based degrees through C major.
    for mode,level,pitches in [('average',2,[62,64,69,64] if pentatonic else [62,65,69,65]),('higher',5,[64,69,72,76] if pentatonic else [65,69,72,76])]:
        if mode=='higher':c.tap(15,8)
        c.led_values([(15,8)],[level])
        notes=c.playback([(1,[144,n,v]) for n,v in zip(pitches,velocity)],cycles=2,timeout=4)
        assert_durations(c,notes,[1]*8)
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        for i,note in enumerate(notes):assert abs((note[field]-notes[0][field])/1e9-i/6)<=tolerance
        c.results.append(dict(kind='numeric-note-merge',mode=mode,assigned_patterns=[1,2],velocity_source=3 if foreign_velocity else 1,pitches=pitches,passed=True))

    if pentatonic:
        def verify(label,pitches):
            notes=c.playback([(1,[144,n,v]) for n,v in zip(pitches,velocity)],cycles=2,timeout=4)
            assert_durations(c,notes,[1]*8)
            for i,note in enumerate(notes):assert abs((note[field]-notes[0][field])/1e9-i/6)<=tolerance
            c.results.append(dict(kind='numeric-merge-scale-transition',label=label,pitches=pitches,passed=True))
        c.tap(4,8);c.enc(2,-1);c.enc(3,2);c.key(3) # Root C -> D.
        verify('D-major-pentatonic-higher',[66,71,74,78])
        c.enc(2,1);c.enc(3,2);c.key(3) # Major -> natural minor.
        verify('D-minor-pentatonic-higher',[67,69,74,77])
        c.tap(3,8);c.tap(15,8);c.tap(15,8);c.led_values([(15,8)],[2])
        verify('D-minor-pentatonic-average',[65,67,69,67])
        c.tap(4,8);c.enc(3,-2);c.key(3);c.enc(2,-1);c.enc(3,-2);c.key(3)
        verify('restored-C-major-pentatonic-average',[62,64,69,64])


def merge_mode_cycle(c,field):
    from cases import assert_durations
    assert field in ('velocity','length')
    c.configure();c.tap(5,8)
    for x in (2,3,4):c.tap(x,4)
    if field=='length':c.hold_tap((1,4),(2,4))
    c.tap(2,1);c.tap(1,4)
    if field=='length':c.hold_tap((1,4),(4,4))
    c.tap(3,8);c.tap(2,2);c.tap(14,8);c.tap(14,8)
    c.hold_tap((15,8),(1,2))
    if field=='length':c.hold_tap((16,8),(1,2))
    def verify(stage):
        notes=c.playback([(1,[144,60,127 if field=='length' else 114])],cycles=2,timeout=4)
        assert_durations(c,notes,[3 if field=='length' else 1]*2)
        key='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        for i,note in enumerate(notes):assert abs((note[key]-notes[0][key])/1e9-i*4/6)<=tolerance
        c.results.append(dict(kind='merge-mode-cycle',field=field,stage=stage,passed=True))
    verify('initial-average')
    for cycle in range(2):
        if field=='length':c.action(type='key',n=1,state=1);c.elapse(.3)
        try:
            for level in (5,8,2):c.tap(16,8);c.led_values([(16,8)],[level])
        finally:
            if field=='length':c.action(type='key',n=1,state=0)
        verify('returned-average-'+str(cycle+1))


def merge_rounding(c,three=False):
    from cases import set_mosaic_options,assert_durations
    c.configure();set_mosaic_options(c,[('Lock merged to pent.',False)])
    sources=[(0,-1,2,6),(1,0,2,6),(1,0,8,6)] if three else [(1,-2,-1,6),(2,-1,0,6)]
    # Literal arithmetic before pitch mapping:
    # two: A=[2,-1,0,6], H=[3,0,1,6], L=[0,-3,-2,6].
    # three: A=[1,0,4,6], H=[2,1,10,6], L=[-1,-2,0,6].
    expected=([('average',2,[62,60,67,71]),('higher',5,[64,62,77,71]),('lower',8,[59,57,60,71])] if three else
              [('average',2,[64,59,60,71]),('higher',5,[65,60,62,71]),('lower',8,[60,55,57,71])])
    c.tap(5,8)
    for slot,values in enumerate(sources,1):
        c.tap(slot,1)
        if slot>1:
            for x in range(1,5):c.tap(x,4)
        c.tap(5,8)
        for x,degree in enumerate(values,1):
            if 0<=degree<=6:c.tap(15,8);y=7-degree
            else:
                button=16 if degree<0 else 14
                c.action(type='grid',x=button,y=8,state=1)
                try:c.elapse(1.2)
                finally:c.action(type='grid',x=button,y=8,state=0)
                c.elapse(.06);y=-degree if degree<0 else 14-degree
            c.tap(x,y)
            if not (y==1 and x==slot):c.led_values([(x,y)],[12])
        c.tap(3,8);c.tap(5,8)
    c.tap(3,8)
    for slot in range(2,len(sources)+1):c.tap(slot,2)
    c.tap(14,8);c.tap(14,8);c.hold_tap((16,8),(1,2))
    key='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    for index,(mode,level,pitches) in enumerate(expected+[expected[0]]):
        if index:c.tap(15,8)
        c.led_values([(15,8)],[level])
        for reversed_order in (False,True):
            if reversed_order:
                for slot in range(1,len(sources)+1):c.tap(slot,2)
                for slot in range(len(sources),0,-1):c.tap(slot,2)
            notes=c.playback([(1,[144,n,v]) for n,v in zip(pitches,[127,117,107,97])],cycles=2,timeout=4)
            assert_durations(c,notes,[1]*8)
            for i,note in enumerate(notes):assert abs((note[key]-notes[0][key])/1e9-i/6)<=tolerance
            c.results.append(dict(kind='merge-rounded-mean-native',contributors=sources,mode=mode,reversed_assignment=reversed_order,pitches=pitches,passed=True))
