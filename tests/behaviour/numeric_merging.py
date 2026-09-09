def numeric_note_merge(c,foreign_velocity=False):
    from cases import set_mosaic_options,assert_durations
    c.configure();set_mosaic_options(c,[('Lock merged to pent.',False)])
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
    for mode,level,pitches in [('average',2,[62,65,69,65]),('higher',5,[65,69,72,76])]:
        if mode=='higher':c.tap(15,8)
        c.led_values([(15,8)],[level])
        notes=c.playback([(1,[144,n,v]) for n,v in zip(pitches,velocity)],cycles=2,timeout=4)
        assert_durations(c,notes,[1]*8)
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        for i,note in enumerate(notes):assert abs((note[field]-notes[0][field])/1e9-i/6)<=tolerance
        c.results.append(dict(kind='numeric-note-merge',mode=mode,assigned_patterns=[1,2],velocity_source=3 if foreign_velocity else 1,pitches=pitches,passed=True))
