"""Native scale-slot ownership and highest-slot lock precedence."""
def scale_slot_matrix(c):
    from cases import assert_durations
    from frame_oracle import header,matches
    c.configure();c.tap(4,8);c.enc(2,-1)
    def selected(slot,applied):
        expected=header('Scale slot '+str(slot)+' ',selected=1,tabs=3)
        c.wait(lambda state:matches(state,expected))
        c.led_values([(n,3) for n in range(1,17)],[15 if n==applied else 4 if n==slot else 2 for n in range(1,17)])
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    def verify(pitches,label):
        notes=c.playback([(1,[144,p,v]) for p,v in zip(pitches,[127,117,107,97])],cycles=2,timeout=4)
        assert_durations(c,notes,[1]*8)
        for i,note in enumerate(notes):assert abs((note[field]-notes[0][field])/1e9-i/6)<=tolerance
        c.results.append(dict(kind='scale-slot-matrix',stage=label,pitches=pitches,passed=True))
    # Adjacent slots use distinct chromatic roots; slots 13..16 repeat roots
    # but are edited and read independently in reverse order as well.
    roots=[0,1,2,3,4,5,6,7,8,9,10,11,0,1,2,3]
    for slot,root in enumerate(roots,1):
        c.action(type='key',n=1,state=1)
        try:c.elapse(.3);c.tap(slot,3)
        finally:c.action(type='key',n=1,state=0)
        selected(slot,1)
        if root:c.enc(3,root)
        c.key(3);selected(slot,1)
        verify([60,62,64,65],'edit-only-slot-'+str(slot))
    applied=1
    for order in [list(range(1,17)),list(range(16,0,-1))]:
        for slot in order:
            if slot==applied:
                c.tap(slot,3);selected(slot,0)
                verify([60,61,62,63],'short-reselect-disables-slot-'+str(slot))
            c.tap(slot,3);selected(slot,slot);applied=slot
            root=roots[slot-1]
            verify([60+root,62+root,64+root,65+root],'apply-slot-'+str(slot))
    # Highest global and channel scale references must use their own saved
    # settings, persist for the stated lifetime, and clear independently.
    c.hold_tap((1,4),(16,3));c.tap(3,8)
    c.hold_tap((2,4),(15,3))
    verify([63,64,66,67],'global16-channel15-precedence')
    c.hold_tap((2,4),(15,3))
    verify([63,65,67,68],'clear-channel15-reveals-global16')
    c.tap(4,8);c.hold_tap((1,4),(16,3))
    verify([60,62,64,65],'clear-global16-restores-default1')
    selected(1,1)
