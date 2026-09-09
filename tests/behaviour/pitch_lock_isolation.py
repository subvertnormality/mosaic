"""Independent MIDI oracles for pitch-lock ownership across channels/song copies."""

def pitch_lock_isolation(c,song_copy=False):
    from cases import assign_trig_parameter,assert_durations
    c.configure()
    c.tap(2,1);c.enc(3,1);c.enc(2,1);c.enc(3,1);c.enc(2,1);c.enc(3,1);c.key(3)
    c.tap(1,2);c.hold_tap((1,4),(4,4));c.enc(1,-3)
    def lock(step,value):
        c.action(type='grid',x=step,y=4,state=1)
        try:
            c.elapse(.05);c.action(type='enc',n=3,delta=-126);c.elapse(.15)
            if value>=0:c.enc(3,value+1)
        finally:c.action(type='grid',x=step,y=4,state=0)
        c.elapse(.15)
    def clear(step):
        c.action(type='grid',x=step,y=4,state=1)
        try:c.elapse(.05);c.key(2)
        finally:c.action(type='grid',x=step,y=4,state=0)
        c.elapse(.15)
    def verify(one,two,label):
        before=c.snapshot()['midi_count'];c.tap(1,8)
        def emitted(state):return [m for m in state['midi'] if m['index']>before and 144<=m['bytes'][0]<=159 and m['bytes'][2]>0]
        state=c.wait(lambda state:all(sum(m['port']==port for m in emitted(state))>=9 for port in [1,2]),4)
        notes=emitted(state);c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])
        assert all((m['port'],m['bytes'][0]) in [(1,144),(2,145)] for m in notes)
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        origins=[]
        for port,pitches in [(1,one),(2,two)]:
            lane=[m for m in notes if m['port']==port]
            phrase=[[143+port,p,v] for p,v in zip(pitches,[127,117,107,97])]
            assert [m['bytes'] for m in lane]==[phrase[i%4] for i in range(len(lane))],dict(stage=label,port=port,expected=phrase,actual=[m['bytes'] for m in lane])
            origins.append(lane[0][field])
            for i,note in enumerate(lane):assert abs((note[field]-lane[0][field])/1e9-i/6)<=tolerance
            assert_durations(c,lane,[1]*8)
        assert abs(origins[1]-origins[0])/1e9<=tolerance
        c.results.append(dict(kind='pitch-lock-channel-song-isolation',stage=label,pitches=[one,two],routes=2,passed=True))
    assign_trig_parameter(c,'Quantised Fixed Note');c.enc(3,66)
    lock(1,63);lock(3,0)
    c.tap(1,1);assign_trig_parameter(c,'Fixed Note');c.enc(3,61)
    lock(2,0);lock(4,127)
    one=[60,0,60,127];two=[62,65,0,65]
    verify(one,two,'independent-fixed-and-quantised-locks')
    if song_copy:
        c.tap(6,8);c.hold_tap((1,1),(2,1));c.tap(2,1)
        c.led_values([(1,1),(2,1)],[7,15]);c.tap(3,8)
        verify(one,two,'copied-song-retains-both-channels')
        c.tap(1,1);lock(2,72)
        c.tap(2,1);lock(1,67)
        verify([60,72,60,127],[67,65,0,65],'copy-edits-isolated-between-channels')
        c.tap(6,8);c.tap(1,1);c.led_values([(1,1),(2,1)],[15,7]);c.tap(3,8)
        verify(one,two,'source-song-unchanged-after-copy-edits')
        c.tap(6,8);c.tap(2,1);c.tap(3,8)
        c.tap(1,1);clear(4);c.tap(2,1);clear(3)
        verify([60,72,60,60],[67,65,65,65],'clear-only-copied-extreme-locks')
        c.tap(6,8);c.tap(1,1);c.tap(3,8)
        verify(one,two,'source-zero-and-upper-locks-retained')
        return
    c.tap(2,1);clear(1);verify(one,[65,65,0,65],'clear-second-channel-only')
    c.tap(1,1);c.enc(3,10);verify([70,0,70,127],[65,65,0,65],'default-edit-retains-other-channel-and-local-locks')
    clear(2);verify([70,70,70,127],[65,65,0,65],'clear-first-channel-zero-only')
    c.action(type='enc',n=3,delta=-126);c.elapse(.15)
    verify([60,62,64,127],[65,65,0,65],'fixed-default-off-restores-own-pattern')
    c.tap(2,1);c.action(type='enc',n=3,delta=-126);c.elapse(.15)
    verify([60,62,64,127],[60,62,0,65],'quantised-default-off-preserves-own-zero')
    clear(3);c.tap(1,1);clear(4)
    verify([60,62,64,65],[60,62,64,65],'both-original-phrases-restored')
