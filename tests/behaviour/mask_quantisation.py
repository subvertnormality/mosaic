"""Independent scale pitch expectations, exercised through physical inputs."""

def mask_scale_snap(c,root=0):
    from cases import set_mosaic_options,assert_durations
    c.configure();set_mosaic_options(c,[('Lock merged to pent.',False),('Quantise note masks',False),('Snap note masks to scale',True)])
    c.enc(1,-4)
    masked=[61,63,66,70]
    for step,pitch in enumerate(masked,1):
        c.action(type='grid',x=step,y=4,state=1)
        try:c.enc(3,pitch+1)
        finally:c.action(type='grid',x=step,y=4,state=0)
        c.elapse(.06)
    scales=[('major',[0,2,4,5,7,9,11]),('harmonic-major',[0,2,4,5,7,8,11]),
            ('minor',[0,2,3,5,7,8,10]),('harmonic-minor',[0,2,3,5,7,8,11]),
            ('melodic-minor',[0,2,3,5,7,9,11]),('dorian',[0,2,3,5,7,9,10]),
            ('phrygian',[0,1,3,5,7,8,10]),('lydian',[0,2,4,6,7,9,11]),
            ('mixolydian',[0,2,4,5,7,9,10]),('locrian',[0,1,3,5,6,8,10])]
    c.tap(4,8)
    if root:c.enc(2,-1);c.enc(3,root);c.key(3);c.enc(2,1)
    for enabled in [True,False,True]:
        if enabled is False:set_mosaic_options(c,[('Snap note masks to scale',False)])
        elif len(c.results) and getattr(c,'mask_snap_disabled',False):set_mosaic_options(c,[('Snap note masks to scale',True)])
        c.mask_snap_disabled=not enabled
        c.enc(3,-20);c.key(3)
        for number,(name,intervals) in enumerate(scales):
            if number:c.enc(3,1);c.key(3)
            # Nearest chromatic pitch in a literal scale; equal distances choose
            # the lower note, the pinned musicutil snapping contract.
            available=[root+12*octave+interval for octave in range(0,11) for interval in intervals]
            pitches=[min(available,key=lambda n:(abs(n-pitch),n)) for pitch in masked] if enabled else masked
            notes=c.playback([(1,[144,p,v]) for p,v in zip(pitches,[127,117,107,97])],cycles=2,timeout=4)
            assert_durations(c,notes,[1]*8)
            field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
            tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
            for i,note in enumerate(notes):assert abs((note[field]-notes[0][field])/1e9-i/6)<=tolerance
            c.results.append(dict(kind='mask-scale-snap',root=root,scale=name,snap=enabled,raw=masked,pitches=pitches,passed=True))


def mask_full_quantisation(c):
    from cases import set_mosaic_options,assign_trig_parameter,assert_durations
    c.configure();set_mosaic_options(c,[('Lock merged to pent.',False),('Quantise note masks',False),('Snap note masks to scale',True)])
    c.enc(1,-4)
    for step,pitch in enumerate([60,64,69,71],1):
        c.action(type='grid',x=step,y=4,state=1)
        try:c.enc(3,pitch+1)
        finally:c.action(type='grid',x=step,y=4,state=0)
        c.elapse(.06)
    c.tap(4,8);c.enc(2,1);c.enc(3,1);c.key(3) # C-major degreeII.
    c.enc(2,2);c.enc(3,1);c.key(3) # Rotation1: final scale tone drops an octave.
    def verify(pitches,stage):
        notes=c.playback([(1,[144,p,v]) for p,v in zip(pitches,[127,117,107,97])],cycles=2,timeout=4)
        assert_durations(c,notes,[1]*8)
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        for i,note in enumerate(notes):assert abs((note[field]-notes[0][field])/1e9-i/6)<=tolerance
        c.results.append(dict(kind='full-mask-quantisation',stage=stage,pitches=pitches,passed=True))
    verify([60,64,69,71],'snap-ignores-degree-and-rotation')
    set_mosaic_options(c,[('Quantise note masks',True)])
    # Input degrees C/E/A/B become D/F/B/C under degreeII; rotation lowers C.
    verify([62,65,71,60],'global-full-degree-and-rotation')
    c.tap(3,8);c.enc(1,1);assign_trig_parameter(c,'Quantise Note Mask')
    c.enc(3,1);verify([60,64,69,71],'channel-off-overrides-global-on')
    def lock(step,delta):
        c.action(type='grid',x=step,y=4,state=1)
        try:
            c.elapse(.05);c.action(type='enc',n=3,delta=-126);c.elapse(.15);c.enc(3,delta)
        finally:c.action(type='grid',x=step,y=4,state=0)
        c.elapse(.06)
    lock(2,2);verify([60,65,69,71],'step-on-overrides-channel-off')
    c.enc(3,-1);verify([62,65,71,60],'channel-unset-inherits-global')
    lock(1,1);verify([60,65,71,60],'step-off-overrides-global-on')
    set_mosaic_options(c,[('Quantise note masks',False)])
    verify([60,65,69,71],'global-off-preserves-step-on')
    c.enc(3,2);verify([60,65,71,60],'channel-on-overrides-global-off')
    c.action(type='grid',x=1,y=4,state=1)
    try:c.key(2)
    finally:c.action(type='grid',x=1,y=4,state=0)
    c.elapse(.06);verify([62,65,71,60],'clear-step-off-restores-channel-on')
    lock(1,0);verify([60,65,71,60],'explicit-step-X-uses-global-off')
    c.action(type='grid',x=1,y=4,state=1)
    try:c.key(2)
    finally:c.action(type='grid',x=1,y=4,state=0)
    c.elapse(.06);verify([62,65,71,60],'clear-X-restores-channel-on')
    set_mosaic_options(c,[('Quantise note masks',True)])
    c.action(type='enc',n=3,delta=-126);c.elapse(.15);c.enc(3,1)
    lock(3,0);verify([60,65,71,71],'explicit-step-X-uses-global-on-over-channel-off')
    c.action(type='grid',x=3,y=4,state=1)
    try:c.key(2)
    finally:c.action(type='grid',x=3,y=4,state=0)
    c.elapse(.06);verify([60,65,69,71],'clear-X-restores-channel-off')



def mask_full_chord_inheritance(c):
    from cases import set_mosaic_options,assign_trig_parameter,assert_durations
    c.configure();set_mosaic_options(c,[('Lock merged to pent.',False),('Quantise note masks',True)])
    c.enc(1,-4);c.enc(3,61);c.enc(2,3);c.enc(3,2)  # unset chord masks start from X (bugs.json chord-mask-unset-start-x)
    c.tap(4,8);c.enc(2,1);c.enc(3,1);c.key(3)
    c.tap(3,8);c.enc(1,1);assign_trig_parameter(c,'Quantise Note Mask')
    def verify(pitches,stage):
        phrase=[(1,[144,p,v]) for v in [127,117,107,97] for p in pitches]
        notes=c.playback(phrase,cycles=2,timeout=4);assert_durations(c,notes,[1]*16)
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        for i,note in enumerate(notes):assert abs((note[field]-notes[0][field])/1e9-(i//2)/6)<=tolerance
        c.results.append(dict(kind='full-mask-chord-inheritance',stage=stage,pitches=pitches,passed=True))
    verify([62,65],'fresh-assigned-X-inherits-global-for-root-and-chord')
    c.enc(3,1);verify([60,64],'explicit-off-root-and-chord')
    c.enc(3,1);verify([62,65],'explicit-on-root-and-chord')
    c.enc(3,-2);verify([62,65],'on-to-X-retains-global-root-and-chord')
