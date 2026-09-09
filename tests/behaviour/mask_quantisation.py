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
