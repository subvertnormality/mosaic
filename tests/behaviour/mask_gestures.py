"""Shift-grid trig mask gestures with independent whole-grid and MIDI oracles."""

def trig_gesture_all_steps(c):
    from cases import assert_durations
    c.configure();c.tap(1,2);c.hold_tap((1,4),(16,7));c.enc(1,-4)
    # No assigned pattern. Required defaults make newly added trigs audible.
    c.enc(3,61);c.enc(2,1);c.enc(3,101);c.enc(2,1);c.enc(3,14)
    def toggle(steps):
        c.action(type='key',n=1,state=1);c.elapse(.3)
        try:
            for step in steps:c.tap((step-1)%16+1,(step-1)//16+4)
        finally:c.action(type='key',n=1,state=0)
        c.elapse(.1)
    def verify(active,stage):
        def grid_matches(state):
            for step in range(1,65):
                level=state['grid'][(step-1)//16*16+(step-1)%16+48]
                if level not in ((12,15) if step in active else (1,2)):return False
            return True
        c.wait(grid_matches)
        phrase=[(1,[144,60,100]) for _ in active]
        notes=c.playback(phrase,cycles=2,timeout=26)
        assert_durations(c,notes,[1]*(len(active)*2))
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        for i,note in enumerate(notes):
            steps=(i//len(active))*64+active[i%len(active)]-active[0]
            assert abs((note[field]-notes[0][field])/1e9-steps/6)<=tolerance
        c.results.append(dict(kind='trig-mask-all64-gesture',stage=stage,active_steps=active,grid_cells=64,passed=True))
    all_steps=list(range(1,65));odd=list(range(1,65,2));even=list(range(2,65,2))
    toggle(all_steps);verify(all_steps,'all64-added-without-pattern')
    toggle(odd);verify(even,'odd-steps-removed-even-preserved')
    toggle(all_steps);verify(odd,'all64-toggled-odd-only')
    toggle(even);verify(all_steps,'even-restored-all64')
