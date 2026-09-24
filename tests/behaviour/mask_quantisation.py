"""Independent scale pitch expectations, exercised through physical inputs."""

def mask_scale_snap(c,root=0):
    from cases import assert_durations
    c.configure();c.ui.set_mosaic_options([('Lock merged to pent.',False),('Quantise note masks',False),('Snap note masks to scale',True)])
    c.ui.channel_page('masks',from_page='midi_config',confirm=False)
    masked=[61,63,66,70]
    for step,pitch in enumerate(masked,1):
        with c.ui.hold_step(step):c.ui.set_value(pitch+1)
        c.elapse(.06)
    scales=[('major',[0,2,4,5,7,9,11]),('harmonic-major',[0,2,4,5,7,8,11]),
            ('minor',[0,2,3,5,7,8,10]),('harmonic-minor',[0,2,3,5,7,8,11]),
            ('melodic-minor',[0,2,3,5,7,9,11]),('dorian',[0,2,3,5,7,9,10]),
            ('phrygian',[0,1,3,5,7,8,10]),('lydian',[0,2,4,6,7,9,11]),
            ('mixolydian',[0,2,4,5,7,9,10]),('locrian',[0,1,3,5,6,8,10])]
    c.ui.scale_editor()
    if root:c.ui.turn(2,-1);c.ui.set_value(root);c.ui.press_key(3);c.ui.turn(2,1)
    for enabled in [True,False,True]:
        if enabled is False:c.ui.set_mosaic_options([('Snap note masks to scale',False)])
        elif len(c.results) and getattr(c,'mask_snap_disabled',False):c.ui.set_mosaic_options([('Snap note masks to scale',True)])
        c.mask_snap_disabled=not enabled
        c.ui.set_value(-20);c.ui.press_key(3)
        for number,(name,intervals) in enumerate(scales):
            if number:c.ui.set_value(1);c.ui.press_key(3)
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
    from cases import assert_durations
    c.configure();c.ui.set_mosaic_options([('Lock merged to pent.',False),('Quantise note masks',False),('Snap note masks to scale',True)])
    c.ui.channel_page('masks',from_page='midi_config',confirm=False)
    for step,pitch in enumerate([60,64,69,71],1):
        with c.ui.hold_step(step):c.ui.set_value(pitch+1)
        c.elapse(.06)
    c.ui.scale_editor();c.ui.turn(2,1);c.ui.set_value(1);c.ui.press_key(3) # C-major degreeII.
    c.ui.turn(2,2);c.ui.set_value(1);c.ui.press_key(3) # Rotation1: final scale tone drops an octave.
    def verify(pitches,stage):
        notes=c.playback([(1,[144,p,v]) for p,v in zip(pitches,[127,117,107,97])],cycles=2,timeout=4)
        assert_durations(c,notes,[1]*8)
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        for i,note in enumerate(notes):assert abs((note[field]-notes[0][field])/1e9-i/6)<=tolerance
        c.results.append(dict(kind='full-mask-quantisation',stage=stage,pitches=pitches,passed=True))
    verify([60,64,69,71],'snap-ignores-degree-and-rotation')
    c.ui.set_mosaic_options([('Quantise note masks',True)])
    # Input degrees C/E/A/B become D/F/B/C under degreeII; rotation lowers C.
    verify([62,65,71,60],'global-full-degree-and-rotation')
    c.ui.menu('channel_editor');c.ui.channel_page('trig_locks',from_page='masks',confirm=False);c.ui.assign_trig_parameter('Quantise Note Mask')
    c.ui.set_value(1);verify([60,64,69,71],'channel-off-overrides-global-on')
    def lock(step,delta):
        with c.ui.hold_step(step):
            c.elapse(.05);c.ui.encoder_event(3,-126);c.elapse(.15);c.ui.set_value(delta)
        c.elapse(.06)
    lock(2,2);verify([60,65,69,71],'step-on-overrides-channel-off')
    c.ui.set_value(-1);verify([62,65,71,60],'channel-unset-inherits-global')
    lock(1,1);verify([60,65,71,60],'step-off-overrides-global-on')
    c.ui.set_mosaic_options([('Quantise note masks',False)])
    verify([60,65,69,71],'global-off-preserves-step-on')
    c.ui.set_value(2);verify([60,65,71,60],'channel-on-overrides-global-off')
    with c.ui.hold_step(1):c.ui.press_key(2)
    c.elapse(.06);verify([62,65,71,60],'clear-step-off-restores-channel-on')
    lock(1,0);verify([60,65,71,60],'explicit-step-X-uses-global-off')
    with c.ui.hold_step(1):c.ui.press_key(2)
    c.elapse(.06);verify([62,65,71,60],'clear-X-restores-channel-on')
    c.ui.set_mosaic_options([('Quantise note masks',True)])
    c.ui.encoder_event(3,-126);c.elapse(.15);c.ui.set_value(1)
    lock(3,0);verify([60,65,71,71],'explicit-step-X-uses-global-on-over-channel-off')
    with c.ui.hold_step(3):c.ui.press_key(2)
    c.elapse(.06);verify([60,65,69,71],'clear-X-restores-channel-off')



def mask_full_chord_inheritance(c):
    from cases import assert_durations
    c.configure();c.ui.set_mosaic_options([('Lock merged to pent.',False),('Quantise note masks',True)])
    c.ui.channel_page('masks',from_page='midi_config',confirm=False);c.ui.set_value(61);c.ui.turn(2,3);c.ui.set_value(2)  # unset chord masks start from X (bugs.json chord-mask-unset-start-x)
    c.ui.scale_editor();c.ui.turn(2,1);c.ui.set_value(1);c.ui.press_key(3)
    c.ui.menu('channel_editor');c.ui.channel_page('trig_locks',from_page='masks',confirm=False);c.ui.assign_trig_parameter('Quantise Note Mask')
    def verify(pitches,stage):
        phrase=[(1,[144,p,v]) for v in [127,117,107,97] for p in pitches]
        notes=c.playback(phrase,cycles=2,timeout=4);assert_durations(c,notes,[1]*16)
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        for i,note in enumerate(notes):assert abs((note[field]-notes[0][field])/1e9-(i//2)/6)<=tolerance
        c.results.append(dict(kind='full-mask-chord-inheritance',stage=stage,pitches=pitches,passed=True))
    verify([62,65],'fresh-assigned-X-inherits-global-for-root-and-chord')
    c.ui.set_value(1);verify([60,64],'explicit-off-root-and-chord')
    c.ui.set_value(1);verify([62,65],'explicit-on-root-and-chord')
    c.ui.set_value(-2);verify([62,65],'on-to-X-retains-global-root-and-chord')
