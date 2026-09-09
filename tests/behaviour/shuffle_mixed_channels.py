"""Simultaneous MIDI lanes distinguish inheritance from local clock overrides."""
def mixed_shuffle_inheritance(c):
    from note_accounting import note_pairs
    from midi_window import MidiWindow
    c.configure()
    # Channel2 uses port2/channel2 and the same four-step pattern as channel1.
    c.tap(2,1);c.enc(3,1);c.enc(2,1);c.enc(3,1);c.enc(2,1);c.enc(3,1);c.key(3)
    c.tap(1,2);c.hold_tap((1,4),(4,4))
    c.enc(1,-1);c.enc(2,1);c.enc(3,1);c.key(3) # Explicit Swing only on channel2.
    c.tap(6,8);c.enc(1,1)
    c.enc(2,1);c.enc(3,1);c.key(3) # Global Shuffle.
    c.enc(2,1);c.enc(3,2);c.key(3) # Heavy.
    c.enc(2,1);c.enc(3,3);c.key(3) # Basis6.
    c.enc(2,1);c.enc(3,-101);c.key(3);c.enc(3,100);c.key(3)
    c.enc(2,-3) # Global type selector.
    for label,delta,shuffled in [('global-Shuffle',None,True),('global-Swing',-1,False),('restored-global-Shuffle',1,True)]:
        if delta is not None:c.enc(3,delta);c.key(3)
        capture=MidiWindow(c.snapshot()['midi_count']);c.tap(1,8)
        c.wait(lambda state:capture.extend(state) and all(sum(n['port']==port for n in capture.note_ons())>=17 for port in (1,2)),timeout=8)
        c.tap(1,8);c.wait(lambda state:capture.extend(state) and not state['midi_capture']['outstanding'])
        notes=capture.note_ons();pairs=note_pairs(capture.events)
        assert len(pairs)==len(notes)
        assert all((n['port'],n['bytes'][0]) in [(1,144),(2,145)] for n in notes)
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        origins=[];lanes=[]
        for port in (1,2):
            lane=[n for n in notes if n['port']==port];origins.append(lane[0][field])
            assert len(lane)>=17
            for i,n in enumerate(lane):
                assert n['bytes']==[143+port,(60,62,64,65)[i%4],(127,117,107,97)[i%4]],dict(stage=label,port=port,index=i,note=n)
                pulse=96*(i//4)+(0,16,32,48)[i%4] if port==1 and shuffled else 24*i
                error=(n[field]-lane[0][field])/1e9-pulse/144
                assert abs(error)<=tolerance,dict(stage=label,port=port,index=i,expected_pulse=pulse,error=error)
            for n,nxt in zip(lane,lane[1:]):
                off=next(e for e in capture.events if e['index']>n['index'] and e['port']==port and e['bytes']==[127+port,n['bytes'][1],n['bytes'][2]])
                assert abs(off[field]-nxt[field])/1e9<=tolerance
            lanes.append(dict(port=port,onsets=len(lane),shuffled=port==1 and shuffled))
        assert abs(origins[1]-origins[0])/1e9<=tolerance
        c.results.append(dict(kind='mixed-channel-shuffle-inheritance',stage=label,lanes=lanes,release_pairs=len(pairs),passed=True))
