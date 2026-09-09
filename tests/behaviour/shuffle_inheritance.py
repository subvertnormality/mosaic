"""Native global/local clock inheritance round trips with independent pulse expectations."""
def shuffle_type_inheritance(c):
    from frame_oracle import header,matches
    from note_accounting import note_pairs
    c.configure()
    c.tap(6,8);c.enc(1,1) # Song Global settings.
    c.enc(2,1);c.enc(3,1);c.key(3) # Global Swing -> Shuffle.
    c.enc(2,1);c.enc(3,2);c.key(3) # Drunk -> Heavy.
    c.enc(2,1);c.enc(3,3);c.key(3) # Basis9 -> Basis6.
    c.enc(2,1);c.enc(3,-101);c.key(3);c.enc(3,100);c.key(3)
    c.tap(3,8);c.enc(1,-1)
    c.wait(lambda state:matches(state,header('Ch. 1 Clocks',selected=4)))
    c.enc(2,1) # Local Swing Type, initially X.
    stages=[('untouched-X',None,True),('local-Swing',1,False),
            ('explicit-X-from-Swing',-1,True),('local-Shuffle',2,True),
            ('explicit-X-from-Shuffle',-2,True)]
    for label,delta,shuffled in stages:
        if delta is not None:c.enc(3,delta);c.key(3)
        before=c.snapshot()['midi_count']
        notes=c.playback([(1,[144,n,v]) for n,v in ((60,127),(62,117),(64,107),(65,97))],cycles=4,timeout=8)
        events=[e for e in c.snapshot()['midi'] if e['index']>before]
        pairs=note_pairs(events)
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        planned=[96*(i//4)+(0,16,32,48)[i%4] if shuffled else 24*i for i in range(len(notes))]
        errors=[(note[field]-notes[0][field])/1e9-pulse/144 for note,pulse in zip(notes,planned)]
        assert max(map(abs,errors))<=tolerance,dict(stage=label,expected_pulses=planned,errors=errors)
        for note,nxt in zip(notes,notes[1:]):
            off=next(e for e in events if e['index']>note['index'] and e['bytes']==[128,note['bytes'][1],note['bytes'][2]])
            assert abs(off[field]-nxt[field])/1e9<=tolerance
        c.results.append(dict(kind='shuffle-type-inheritance',stage=label,expected_pulses=planned,onsets=len(notes),release_pairs=len(pairs),passed=True))
