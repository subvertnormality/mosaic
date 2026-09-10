"""Channel versus global scale locks and "Scales lock until ptn end" (README Scale Locks, MAN option).

Slots: 2 D major (applied), 3 E major, 4 G major. Channel 1 plays degrees
I..IV on steps 1-4; the scale track is also 4 steps, so every cycle repeats.
A global lock sets slot 4 on scale-track step 2; a channel lock sets slot 3
on step 1. Pitches come from these independent interval tables.
"""
MAJOR=[0,2,4,5,7,9,11]
ROOT={2:62,3:64,4:67} # slot -> middle-C-octave root

def pitch(slot,degree):return ROOT[slot]+MAJOR[degree]
VELOCITY=[127,117,107,97]

def scale_lock_precedence(c):
    from cases import set_mosaic_options,assign_trig_parameter
    def edit_root(semitones):c.enc(2,-1);c.enc(3,semitones);c.key(3);c.enc(2,1)
    def hold_slot(step,slot):
        c.action(type='grid',x=step,y=4,state=1)
        try:c.tap(slot,3)
        finally:c.action(type='grid',x=step,y=4,state=0)
        c.elapse(.1)
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    def phrase(stage,slots):
        """slots[i] is the active slot for step i+1, or None for a silent step."""
        steps=[i+1 for i,s in enumerate(slots) if s]
        expected=[(1,[144,pitch(slots[s-1],s-1),VELOCITY[s-1]]) for s in steps]
        notes=c.playback(expected,cycles=2)
        for i,(a,b) in enumerate(zip(notes,notes[1:])):
            left=steps[i%len(steps)];right=steps[(i+1)%len(steps)]
            assert abs((b[field]-a[field])/1e9-((right-left)%4 or 4)/6)<=tolerance,(stage,i)
        c.results.append(dict(kind='scale-lock-precedence',stage=stage,slots=slots,pitches=[e[1][1] for e in expected],passed=True))
    c.configure()
    c.tap(4,8);c.hold_tap((1,4),(4,4))                       # scale track steps 1-4
    c.tap(3,3);edit_root(4);c.tap(4,3);edit_root(7);c.tap(2,3);edit_root(2)
    hold_slot(2,4)                                           # global lock: step 2 -> G major
    c.tap(3,8);hold_slot(1,3)                                # channel lock: step 1 -> E major
    phrase('hold-on-channel-over-global',[3,3,3,3])
    set_mosaic_options(c,[('Scales lock until ptn end',False)])
    phrase('hold-off-next-trig-clears',[3,4,4,4])
    # A probability-rejected trig does not clear the channel lock.
    c.enc(1,-3);assign_trig_parameter(c,'Trig Probability')
    c.action(type='grid',x=2,y=4,state=1)
    try:c.elapse(.05);c.action(type='enc',n=3,delta=-126);c.elapse(.15);c.enc(3,1) # step 2 probability 0
    finally:c.action(type='grid',x=2,y=4,state=0)
    c.elapse(.15)
    phrase('hold-off-rejected-trig-keeps-lock',[3,None,4,4])
    c.action(type='grid',x=2,y=4,state=1)
    try:c.elapse(.05);c.key(2)                               # clear step-2 trig locks
    finally:c.action(type='grid',x=2,y=4,state=0)
    c.elapse(.15)
    phrase('hold-off-probability-cleared',[3,4,4,4])
    # A rest (no trig on step 2) does not clear it either.
    c.tap(5,8);c.tap(1,1);c.tap(2,4);c.tap(3,8)
    phrase('hold-off-rest-keeps-lock',[3,None,4,4])
    c.tap(5,8);c.tap(1,1);c.tap(2,4);c.tap(3,8)
    # A new channel lock on step 3 replaces the old one and applies normally.
    hold_slot(3,2)
    phrase('hold-off-replacement',[3,4,2,4])
    set_mosaic_options(c,[('Scales lock until ptn end',True)])
    phrase('hold-on-replacement',[3,3,2,2])
