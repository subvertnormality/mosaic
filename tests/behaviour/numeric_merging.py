def numeric_note_merge(c,foreign_velocity=False,pentatonic=False,all_scales=False,harmony=False):
    from cases import set_mosaic_options,assert_durations
    c.configure();set_mosaic_options(c,[('Lock merged to pent.',pentatonic)])
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
    for mode,level,pitches in [('average',2,[62,64,69,64] if pentatonic else [62,65,69,65]),('higher',5,[64,69,72,76] if pentatonic else [65,69,72,76])]:
        if mode=='higher':c.tap(15,8)
        c.led_values([(15,8)],[level])
        notes=c.playback([(1,[144,n,v]) for n,v in zip(pitches,velocity)],cycles=2,timeout=4)
        assert_durations(c,notes,[1]*8)
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        for i,note in enumerate(notes):assert abs((note[field]-notes[0][field])/1e9-i/6)<=tolerance
        c.results.append(dict(kind='numeric-note-merge',mode=mode,assigned_patterns=[1,2],velocity_source=3 if foreign_velocity else 1,pitches=pitches,passed=True))

    if harmony:
        # Independent literal phrases: degree II maps C-major degrees through
        # D/E/F/G/A/B/C. Rotation two lowers the final two positions by an
        # octave; pentatonic snapping still uses the root scale C/D/E/G/A.
        # Negative degree -3 remains in the preceding octave (A57 at degree II).
        # Root D adds two semitones after those operations.
        stages=[
            ('degree-II',1,0,0,[[67,71,74,77],[60,64,67,57],[64,67,71,67]],[[67,72,74,76],[60,64,67,57],[64,67,72,67]]),
            ('degree-II-rotation-two',0,2,0,[[67,59,74,77],[48,64,67,57],[64,67,59,67]],[[67,60,74,76],[48,64,67,57],[64,67,60,67]]),
            ('D-root-degree-II-rotation-two',0,0,2,[[69,61,76,79],[50,66,69,59],[66,69,61,69]],[[69,62,76,78],[50,66,69,59],[66,69,62,69]]),
            ('restored-C-major',-1,-2,-2,[[65,69,72,76],[59,62,65,55],[62,65,69,65]],[[64,69,72,76],[60,62,64,55],[62,64,69,64]])]
        for label,degree_delta,rotation_delta,root_delta,plain,pent in stages:
            c.tap(4,8)
            # Normalize the selected field to scale type after each edit.
            if degree_delta:
                c.enc(2,1);c.enc(3,degree_delta);c.key(3);c.enc(2,-1)
            if rotation_delta:
                c.enc(2,3);c.enc(3,rotation_delta);c.key(3);c.enc(2,-3)
            if root_delta:
                c.enc(2,-1);c.enc(3,root_delta);c.key(3);c.enc(2,1)
            c.tap(3,8)
            for index,(mode,level) in enumerate([('higher',5),('lower',8),('average',2)]):
                if index:c.tap(15,8)
                c.led_values([(15,8)],[level])
                pitches=(pent if pentatonic else plain)[index]
                notes=c.playback([(1,[144,n,v]) for n,v in zip(pitches,velocity)],cycles=2,timeout=4)
                assert_durations(c,notes,[1]*8)
                for i,note in enumerate(notes):assert abs((note[field]-notes[0][field])/1e9-i/6)<=tolerance
                c.results.append(dict(kind='merge-harmony-transition',stage=label,mode=mode,pentatonic=pentatonic,pitches=pitches,passed=True))
            c.tap(15,8)
        return

    if all_scales:
        # Musical interval fixtures, independent of Mosaic/official quantiser code.
        scales=[('major',[0,2,4,5,7,9,11]),('harmonic-major',[0,2,4,5,7,8,11]),
                ('minor',[0,2,3,5,7,8,10]),('harmonic-minor',[0,2,3,5,7,8,11]),
                ('melodic-minor',[0,2,3,5,7,9,11]),('dorian',[0,2,3,5,7,9,10]),
                ('phrygian',[0,1,3,5,7,8,10]),('lydian',[0,2,4,6,7,9,11]),
                ('mixolydian',[0,2,4,5,7,9,10]),('locrian',[0,1,3,5,6,8,10])]
        # Literal H/L/A tables from reviewed modal selections, independently
        # derived from interval fixtures; never call the runtime quantiser.
        pent_tables=[
          [[64,69,72,76],[60,62,64,55],[62,64,69,64]],
          [[64,68,72,76],[60,62,64,55],[62,64,68,64]],
          [[65,67,72,75],[58,63,65,55],[63,65,67,65]],
          [[65,67,72,75],[59,63,65,55],[63,65,67,65]],
          [[65,67,72,75],[59,63,65,55],[63,65,67,65]],
          [[65,70,72,74],[58,62,65,55],[62,65,70,65]],
          [[65,68,72,75],[58,60,65,56],[60,65,68,65]],
          [[67,69,71,76],[59,62,67,55],[62,67,69,67]],
          [[65,69,72,77],[57,62,65,55],[62,65,69,65]],
          [[65,68,73,75],[58,61,65,53],[61,65,68,65]]]
        for number,(scale,intervals) in enumerate(scales):
            if number:
                c.tap(4,8);c.enc(3,1);c.key(3);c.tap(3,8)
            # Enter with Higher selected. Cycle through Lower/Average and back.
            for mode,level,degrees in [('higher',5,[3,5,7,9]),('lower',8,[-1,1,3,-3]),('average',2,[1,3,5,3])]:
                if mode!='higher':c.tap(15,8)
                c.led_values([(15,8)],[level])
                pitches=pent_tables[number][{'higher':0,'lower':1,'average':2}[mode]] if pentatonic else [60+12*(d//7)+intervals[d%7] for d in degrees]
                notes=c.playback([(1,[144,n,v]) for n,v in zip(pitches,velocity)],cycles=2,timeout=4)
                assert_durations(c,notes,[1]*8)
                for i,note in enumerate(notes):assert abs((note[field]-notes[0][field])/1e9-i/6)<=tolerance
                c.results.append(dict(kind='numeric-merge-all-scales',scale=scale,mode=mode,degrees=degrees,pitches=pitches,passed=True))
            c.tap(15,8)
    if pentatonic and not all_scales:
        def verify(label,pitches):
            notes=c.playback([(1,[144,n,v]) for n,v in zip(pitches,velocity)],cycles=2,timeout=4)
            assert_durations(c,notes,[1]*8)
            for i,note in enumerate(notes):assert abs((note[field]-notes[0][field])/1e9-i/6)<=tolerance
            c.results.append(dict(kind='numeric-merge-scale-transition',label=label,pitches=pitches,passed=True))
        c.tap(4,8);c.enc(2,-1);c.enc(3,2);c.key(3) # Root C -> D.
        verify('D-major-pentatonic-higher',[66,71,74,78])
        c.enc(2,1);c.enc(3,2);c.key(3) # Major -> natural minor.
        verify('D-minor-pentatonic-higher',[67,69,74,77])
        c.tap(3,8);c.tap(15,8);c.tap(15,8);c.led_values([(15,8)],[2])
        verify('D-minor-pentatonic-average',[65,67,69,67])
        c.tap(4,8);c.enc(3,-2);c.key(3);c.enc(2,-1);c.enc(3,-2);c.key(3)
        verify('restored-C-major-pentatonic-average',[62,64,69,64])


def merge_transpose_scale_lock(c):
    """Merge degrees before independent scale-lock and transpose composition."""
    from cases import set_mosaic_options,assert_durations
    from midi_window import MidiWindow
    from note_accounting import note_pairs
    # Include Mosaic's script-start output as well as the subsequent user run.
    capture=MidiWindow(0)
    c.configure(); set_mosaic_options(c,[('Lock merged to pent.',False)])
    sources=[(0,2,4,6),(2,4,6,0)]
    c.tap(5,8)
    for slot,values in enumerate(sources,1):
        c.tap(slot,1)
        if slot>1:
            for x in range(1,5): c.tap(x,4)
        c.tap(5,8)
        for x,degree in enumerate(values,1): c.tap(x,7-degree)
        c.tap(3,8); c.tap(5,8)
    c.tap(3,8); c.tap(2,2)
    c.tap(14,8); c.tap(14,8)  # All trigs; Average notes is the default.
    c.hold_tap((16,8),(1,2))  # Velocity remains owned by pattern1.

    # Edit-only scale slot2: D natural minor, transpose +3.
    c.tap(4,8)
    c.action(type='key',n=1,state=1)
    try: c.elapse(.3); c.tap(2,3)
    finally: c.action(type='key',n=1,state=0)
    c.enc(3,2); c.key(3)      # Major -> Minor.
    c.enc(2,-1); c.enc(3,2); c.key(3)  # Root C -> D.
    c.enc(2,3); c.enc(3,3); c.key(3)   # Transpose 0 -> +3.

    # Make the independent global scale track four steps long, then change
    # to slot2 at step3. It must reset at step1 of every loop. Step transpose
    # +12 persists from step3 through step4 on the same track.
    c.hold_tap((1,4),(4,4))
    c.hold_tap((3,4),(2,3))
    c.hold_tap((1,4),(9,8))
    c.hold_tap((2,4),(12,8))
    c.hold_tap((3,4),(15,8))
    c.tap(3,8)

    # Average degrees are [1,3,5,3]. Steps1/2 use C major: D62/F65.
    # Steps3/4 use D minor: Bb70/G67. Apply locks [-12,0,+12,+12]
    # and slot2's saved +3 only where the slot2 scale lock is active.
    expected_pitches=(50,65,85,82); expected_velocities=(127,117,107,97)
    c.action(type='grid',x=1,y=8,state=1); c.action(type='grid',x=1,y=8,state=0)
    c.elapse(1.9)
    c.wait(lambda state:capture.extend(state) and len(capture.note_ons())>=13,timeout=5)
    c.action(type='grid',x=1,y=8,state=1)
    stop_lower=c.logical_ns if c.clock_mode=='controlled-experimental' else __import__('time').monotonic_ns()
    c.action(type='grid',x=1,y=8,state=0)
    stop_upper=c.logical_ns if c.clock_mode=='controlled-experimental' else __import__('time').monotonic_ns()
    c.wait(lambda state:capture.extend(state) and not state['midi_capture']['outstanding'])

    notes=capture.note_ons(); assert len(notes)==13,('Unexpected onset count',len(notes))
    expected_notes=[(1,[144,expected_pitches[i%4],expected_velocities[i%4]]) for i in range(13)]
    assert [(event['port'],event['bytes']) for event in notes]==expected_notes
    pairs=note_pairs(capture.events); assert len(pairs)==len(notes)==13
    assert [on for on,off in pairs]==notes,'Release pairing changed onset order'
    assert all((off['port'],off['bytes'])==(on['port'],[128+(on['bytes'][0]&15),on['bytes'][1],on['bytes'][2]])
               for on,off in pairs),'Release bytes differ from their onset'
    assert_durations(c,notes[:12],[1]*12,events=capture.events)

    # The remaining non-note output is an exact part of this user-visible run:
    # Mosaic initializes ten Elektron program channels, sends transport on the
    # three configured outputs, then sends four program changes per played step.
    startup=[(3,[192,0]),(3,[193,0]),(3,[194,0]),(3,[195,64]),(3,[196,0]),
             (3,[197,0]),(3,[198,0]),(3,[199,0]),(3,[200,64]),(3,[201,11])]
    programs=[[(3,[192,0]),(3,[193,0]),(3,[194,3]),(3,[195,52])],
              [(3,[192,0]),(3,[193,0]),(3,[194,3]),(3,[195,64])],
              [(3,[192,2]),(3,[193,0]),(3,[194,4]),(3,[195,79])],
              [(3,[192,2]),(3,[193,0]),(3,[194,4]),(3,[195,79])]]
    wanted_nonnotes=(startup+[(p,[250]) for p in (1,2,3)]+
                     [event for i in range(13) for event in programs[i%4]]+
                     [(p,[252]) for p in (1,2,3)])
    actual_nonnotes=[(event['port'],event['bytes']) for event in capture.events
                     if event['bytes'][0]&240 not in (128,144)]
    assert actual_nonnotes==wanted_nonnotes,dict(expected=wanted_nonnotes,actual=actual_nonnotes)
    assert len(capture.events)==len(wanted_nonnotes)+2*len(notes),'Unaccounted MIDI event'

    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    errors=[(note[field]-notes[0][field])/1e9-i/6 for i,note in enumerate(notes)]
    assert max(abs(error) for error in errors)<=tolerance,errors
    boundary_release=pairs[-1][1][field]
    assert stop_lower<=boundary_release<=stop_upper+int(tolerance*1e9),(stop_lower,boundary_release,stop_upper)
    c.results.append(dict(kind='merge-transpose-scale-lock',source_degrees=sources,
                          merged_average_degrees=[1,3,5,3],scale_lock_step=3,
                          scale2=dict(type='minor',root='D',transpose=3),
                          step_transposes=[-12,0,12,None],expected_pitches=list(expected_pitches),
                          complete_onsets=len(notes),complete_releases=len(pairs),
                          accounted_non_note_events=len(actual_nonnotes),
                          maximum_phase_error_seconds=max(abs(error) for error in errors),passed=True))


def transpose_midi_boundaries(c):
    """Clamp composed musical pitch to the MIDI 0..127 wire domain."""
    from cases import assert_durations
    from midi_window import MidiWindow
    from note_accounting import note_pairs
    sources=[(-7,13,-7,-7),(13,-7,-7,-7)]
    c.configure(); c.tap(5,8)
    for slot,values in enumerate(sources,1):
        c.tap(slot,1)
        if slot>1:
            for x in range(1,5): c.tap(x,4)
        c.tap(5,8)
        for x,degree in enumerate(values,1):
            button=16 if degree<0 else 14
            c.action(type='grid',x=button,y=8,state=1)
            try: c.elapse(1.2)
            finally: c.action(type='grid',x=button,y=8,state=0)
            c.elapse(.06)
            c.tap(x,-degree if degree<0 else 14-degree)
        c.tap(3,8); c.tap(5,8)
    c.tap(3,8); c.tap(2,2)
    c.tap(14,8); c.tap(14,8); c.hold_tap((16,8),(1,2))
    c.tap(15,8)  # Average -> Higher.

    def set_scale_transpose(delta,lock=False):
        c.tap(4,8)
        c.action(type='key',n=1,state=1)
        try: c.elapse(.3); c.tap(1,3)
        finally: c.action(type='key',n=1,state=0)
        c.enc(2,2); c.enc(3,delta); c.key(3); c.enc(2,-2)
        if lock: c.hold_tap((1,4),(1,3))

    def play(mode,pitches,unbounded):
        velocities=(127,117,107,97); before=c.snapshot()
        if mode=='higher':
            startup=[(3,[192,0]),(3,[193,0]),(3,[194,0]),(3,[195,64]),(3,[196,0]),
                     (3,[197,0]),(3,[198,0]),(3,[199,0]),(3,[200,64]),(3,[201,11])]
            assert before['midi_count']==10
            assert [(e['port'],e['bytes']) for e in before['midi']]==startup
        capture=MidiWindow(before['midi_count'])
        c.action(type='grid',x=1,y=8,state=1); c.action(type='grid',x=1,y=8,state=0)
        c.elapse(4/3-.1)
        c.wait(lambda state:capture.extend(state) and len(capture.note_ons())>=9,timeout=4)
        c.action(type='grid',x=1,y=8,state=1)
        stop_lower=c.logical_ns if c.clock_mode=='controlled-experimental' else __import__('time').monotonic_ns()
        c.action(type='grid',x=1,y=8,state=0)
        stop_upper=c.logical_ns if c.clock_mode=='controlled-experimental' else __import__('time').monotonic_ns()
        c.wait(lambda state:capture.extend(state) and not state['midi_capture']['outstanding'])
        notes=capture.note_ons(); assert len(notes)==9
        wanted=[(1,[144,pitches[i%4],velocities[i%4]]) for i in range(9)]
        assert [(event['port'],event['bytes']) for event in notes]==wanted
        pairs=note_pairs(capture.events); assert len(pairs)==len(notes)==9
        assert [on for on,off in pairs]==notes
        assert all((off['port'],off['bytes'])==(1,[128,on['bytes'][1],on['bytes'][2]]) for on,off in pairs)
        assert_durations(c,notes[:8],[1]*8,events=capture.events)
        nonnotes=[event for event in capture.events if event['bytes'][0]&240 not in (128,144)]
        assert [(e['port'],e['bytes']) for e in nonnotes[:3]]==[(1,[250]),(2,[250]),(3,[250])]
        assert [(e['port'],e['bytes']) for e in nonnotes[-3:]]==[(1,[252]),(2,[252]),(3,[252])]
        programs=nonnotes[3:-3]
        program_value=88 if mode=='higher' else 40
        program_group=[(3,[192,0]),(3,[193,0]),(3,[194,3]),(3,[195,program_value])]
        assert [(e['port'],e['bytes']) for e in programs]==program_group*9
        assert len(capture.events)==60,'Extra or missing note/program/transport event'
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        errors=[(note[field]-notes[0][field])/1e9-i/6 for i,note in enumerate(notes)]
        assert max(abs(error) for error in errors)<=tolerance,errors
        assert stop_lower<=pairs[-1][1][field]<=stop_upper+int(tolerance*1e9)
        c.results.append(dict(kind='transpose-midi-boundary',mode=mode,sources=sources,
                              unbounded=list(unbounded),expected=list(pitches),onsets=9,releases=9,
                              program_changes=36,program_group=program_group,
                              excluded_script_start_events=10 if mode=='higher' else 0,
                              transport_events=6,total_events=60,
                              maximum_phase_error_seconds=max(abs(error) for error in errors),passed=True))

    # Higher degrees [23,23,-7,-7] map to [100,100,48,48]. Channel
    # octave +2, scale +12 and step +12 add 48 semitones.
    c.tap(12,8); set_scale_transpose(12,lock=True); c.hold_tap((1,4),(15,8)); c.tap(3,8)
    play('higher',(127,127,96,96),(148,148,96,96))

    # Lower degrees [-17,-17,-7,-7] map to [31,31,48,48]. Reversing
    # octave, scale and step transpose subtracts 48 semitones.
    c.tap(8,8); set_scale_transpose(-24); c.hold_tap((1,4),(9,8)); c.tap(3,8); c.tap(15,8)
    play('lower',(0,0,0,0),(-17,-17,0,0))


def merge_mode_cycle(c,field):
    from cases import assert_durations
    assert field in ('velocity','length')
    c.configure();c.tap(5,8)
    for x in (2,3,4):c.tap(x,4)
    if field=='length':c.hold_tap((1,4),(2,4))
    c.tap(2,1);c.tap(1,4)
    if field=='length':c.hold_tap((1,4),(4,4))
    c.tap(3,8);c.tap(2,2);c.tap(14,8);c.tap(14,8)
    c.hold_tap((15,8),(1,2))
    if field=='length':c.hold_tap((16,8),(1,2))
    def verify(stage):
        notes=c.playback([(1,[144,60,127 if field=='length' else 114])],cycles=2,timeout=4)
        assert_durations(c,notes,[3 if field=='length' else 1]*2)
        key='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        for i,note in enumerate(notes):assert abs((note[key]-notes[0][key])/1e9-i*4/6)<=tolerance
        c.results.append(dict(kind='merge-mode-cycle',field=field,stage=stage,passed=True))
    verify('initial-average')
    for cycle in range(2):
        if field=='length':c.action(type='key',n=1,state=1);c.elapse(.3)
        try:
            for level in (5,8,2):c.tap(16,8);c.led_values([(16,8)],[level])
        finally:
            if field=='length':c.action(type='key',n=1,state=0)
        verify('returned-average-'+str(cycle+1))


def merge_rounding(c,three=False,extreme=False,pentatonic=False):
    from cases import set_mosaic_options,assert_durations
    c.configure();set_mosaic_options(c,[('Lock merged to pent.',pentatonic)])
    sources=[(0,-1,2,6),(1,0,2,6),(1,0,8,6)] if three else [(1,-2,-1,6),(2,-1,0,6)]
    # Literal arithmetic before pitch mapping:
    # two: A=[2,-1,0,6], H=[3,0,1,6], L=[0,-3,-2,6].
    # three: A=[1,0,4,6], H=[2,1,10,6], L=[-1,-2,0,6].
    expected=([('average',2,[62,60,67,71]),('higher',5,[64,62,77,71]),('lower',8,[59,57,60,71])] if three else
              [('average',2,[64,59,60,71]),('higher',5,[65,60,62,71]),('lower',8,[60,55,57,71])])
    assert not (three and (extreme or pentatonic))
    if extreme:
        sources=[(-7,13,-7,13),(13,-7,-7,13)]
        # A=[3,3,-7,13], H=[23,23,-7,13], L=[-17,-17,-7,13].
        # Major pentatonic snaps F down to E and B up to next-octave C.
        expected=[('average',2,[64,64,48,84] if pentatonic else [65,65,48,83]),
                  ('higher',5,[100,100,48,84] if pentatonic else [100,100,48,83]),
                  ('lower',8,[31,31,48,84] if pentatonic else [31,31,48,83])]
    elif pentatonic:
        expected=[('average',2,[64,60,60,72]),('higher',5,[64,60,62,72]),('lower',8,[60,55,57,72])]
    c.tap(5,8)
    for slot,values in enumerate(sources,1):
        c.tap(slot,1)
        if slot>1:
            for x in range(1,5):c.tap(x,4)
        c.tap(5,8)
        for x,degree in enumerate(values,1):
            if 0<=degree<=6:c.tap(15,8);y=7-degree
            else:
                button=16 if degree<0 else 14
                c.action(type='grid',x=button,y=8,state=1)
                try:c.elapse(1.2)
                finally:c.action(type='grid',x=button,y=8,state=0)
                c.elapse(.06);y=-degree if degree<0 else 14-degree
            c.tap(x,y)
            if not (y==1 and x==slot):c.led_values([(x,y)],[12])
        c.tap(3,8);c.tap(5,8)
    c.tap(3,8)
    for slot in range(2,len(sources)+1):c.tap(slot,2)
    c.tap(14,8);c.tap(14,8);c.hold_tap((16,8),(1,2))
    key='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    for index,(mode,level,pitches) in enumerate(expected+[expected[0]]):
        if index:c.tap(15,8)
        c.led_values([(15,8)],[level])
        for reversed_order in (False,True):
            if reversed_order:
                for slot in range(1,len(sources)+1):c.tap(slot,2)
                for slot in range(len(sources),0,-1):c.tap(slot,2)
            notes=c.playback([(1,[144,n,v]) for n,v in zip(pitches,[127,117,107,97])],cycles=2,timeout=4)
            assert_durations(c,notes,[1]*8)
            for i,note in enumerate(notes):assert abs((note[key]-notes[0][key])/1e9-i/6)<=tolerance
            c.results.append(dict(kind='merge-rounded-mean-native',contributors=sources,mode=mode,reversed_assignment=reversed_order,pitches=pitches,passed=True))


def numeric_velocity_merge(c,three=False):
    from cases import assert_durations
    c.configure();c.tap(5,8)
    for slot in ([2,3,4] if three else [2,4]):
        c.tap(slot,1)
        for x in range(1,5):c.tap(x,4)
    c.tap(5,8)
    for x in range(1,5):c.tap(x,3) # Unassigned pattern4 supplies G only.
    c.led_values([(x,3) for x in range(1,5)],[12]*4)
    c.tap(3,8);c.tap(2,2)
    if three:c.tap(3,2)
    c.tap(14,8);c.tap(14,8);c.hold_tap((15,8),(4,2))
    c.led_values([(4,2)],[2])
    # Sources127/117/107/97 and one or two100s. Round the mean first;
    # apply mode arithmetic, then enforce MIDI velocity's upper bound127.
    expected=([('average',2,[109,106,102,99]),('higher',5,[127,123,109,102]),('lower',8,[91,94,98,95])] if three else
              [('average',2,[114,109,104,99]),('higher',5,[127,126,111,102]),('lower',8,[86,91,96,95])])
    key='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    for index,(mode,level,velocities) in enumerate(expected+[expected[0]]):
        if index:c.tap(16,8)
        c.led_values([(16,8)],[level])
        notes=c.playback([(1,[144,67,v]) for v in velocities],cycles=2,timeout=4)
        assert_durations(c,notes,[1]*8)
        for i,note in enumerate(notes):assert abs((note[key]-notes[0][key])/1e9-i/6)<=tolerance
        c.results.append(dict(kind='numeric-velocity-merge',contributors=3 if three else 2,mode=mode,velocities=velocities,note_priority_unassigned=4,passed=True))


def lydian_octave_boundary(c):
    from cases import assert_durations
    c.configure();c.tap(5,8)
    for slot in (1,2):
        c.tap(slot,1)
        if slot==2:
            for x in range(1,5):c.tap(x,4)
        c.tap(5,8)
        for x,degree in enumerate((-7,0,7,0),1):
            if degree==0:c.tap(15,8);y=7
            else:
                button=16 if degree<0 else 14
                c.action(type='grid',x=button,y=8,state=1)
                try:c.elapse(1.2)
                finally:c.action(type='grid',x=button,y=8,state=0)
                c.elapse(.06);y=7
            c.tap(x,y);c.led_values([(x,y)],[12])
        c.tap(3,8);c.tap(5,8)
    c.tap(3,8);c.tap(2,2);c.tap(14,8);c.tap(14,8)
    c.hold_tap((16,8),(1,2));c.tap(4,8);c.enc(3,7);c.key(3)
    # Lydian selection D/E/G/A/B repeats across octaves. C48/60/72
    # has B47/59/71 nearer than D50/62/74. Equal source values still merge.
    notes=c.playback([(1,[144,n,v]) for n,v in zip([47,59,71,59],[127,117,107,97])],cycles=2,timeout=4)
    assert_durations(c,notes,[1]*8)
    key='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    for i,note in enumerate(notes):assert abs((note[key]-notes[0][key])/1e9-i/6)<=tolerance
    c.results.append(dict(kind='lydian-pentatonic-octave-equivalence',degrees=[-7,0,7,0],pitches=[47,59,71,59],passed=True))


def velocity_zero_boundary(c):
    c.configure();c.tap(5,8)
    for slot in (1,2):
        c.tap(slot,1)
        if slot==2:
            for x in range(1,5):c.tap(x,4)
        c.tap(5,8)
        if slot==1:c.tap(4,3) # G remains G under the enabled Major pentatonic lock.
        c.tap(5,8)
        # The manual's 14-position velocity fader spans 127..0.
        # Literal source vectors: [0,0,19,58], [127,0,58,58].
        if slot==2:
            c.action(type='grid',x=15,y=8,state=1);c.elapse(1.2)
            c.action(type='grid',x=15,y=8,state=0);c.elapse(.06);c.tap(1,1)
        c.action(type='grid',x=16,y=8,state=1);c.elapse(1.2)
        c.action(type='grid',x=16,y=8,state=0);c.elapse(.06)
        cells=([(1,7),(2,7),(3,5),(4,1)] if slot==1 else [(2,7),(3,1),(4,1)])
        for cell in cells:c.tap(*cell)
        c.led_values(cells,[12]*len(cells))
        c.tap(3,8);c.tap(5,8)
    c.tap(3,8);c.tap(2,2);c.tap(14,8);c.tap(14,8)
    c.hold_tap((15,8),(1,2))
    key='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    # Rounded mean, then mode arithmetic, then MIDI 0..127 clamp.
    # Lower raw results [-64,0,-1,58] must not wrap into loud notes.
    expected=[('average',2,[64,0,39,58]),('higher',5,[127,0,78,58]),('lower',8,[0,0,0,58])]
    for index,(mode,level,velocities) in enumerate(expected+[expected[0]]):
        if index:c.tap(16,8)
        c.led_values([(16,8)],[level]);before=c.snapshot()['midi_count'];c.tap(1,8)
        def onsets(state):
            return [m for m in state['midi'] if m['index']>before and 144<=m['bytes'][0]<=159]
        state=c.wait(lambda state:len(onsets(state))>=9,4)
        events=onsets(state);wanted=[(1,[144,[60,62,64,67][i%4],velocities[i%4]]) for i in range(len(events))]
        assert [(m['port'],m['bytes']) for m in events]==wanted, dict(expected=wanted,actual=[(m['port'],m['bytes']) for m in events])
        for i,event in enumerate(events):assert abs((event[key]-events[0][key])/1e9-i/6)<=tolerance
        # Zero Note On is a release, not an audible onset. Check every positive
        # note's scheduled release across both complete cycles independently.
        for event in events[:8]:
            if event['bytes'][2]==0:continue
            offs=[m for m in state['midi'] if m['index']>event['index'] and m['port']==1 and m['bytes'][:2]==[128,event['bytes'][1]]]
            assert offs and abs((offs[0][key]-event[key])/1e9-1/6)<=tolerance
        c.tap(1,8);c.wait(lambda state:state['midi_capture']['outstanding']==[])
        c.results.append(dict(kind='numeric-velocity-zero-boundary',mode=mode,velocities=velocities,raw_events_checked=len(events),passed=True))


def numeric_length_merge(c,variant=0,arp=False,strum=False,simultaneous=False,same_pitch=False):
    from cases import assert_durations
    sources,expected=[([2,4],[3,5,1]),([3,4],[4,5,2]),([2,2,5],[3,6,1]),([1,2],[2,3,0]),([1,4],[3,6,0]),([2,2,8],[4,10,0])][variant]
    cycle_steps=16 if variant>=3 else 8
    c.configure();c.hold_tap((1,4),(cycle_steps,4));c.tap(5,8)
    for x in (2,3,4):c.tap(x,4)
    for slot,length in enumerate(sources,1):
        c.tap(slot,1)
        if slot>1:c.tap(1,4)
        if length>1:c.hold_tap((1,4),(length,4))
        c.led_values([(x,4) for x in range(1,cycle_steps+1)],[15]+[5]*(length-1)+[2]*(cycle_steps-length))
    c.tap(3,8)
    for slot in range(2,len(sources)+1):c.tap(slot,2)
    c.tap(14,8);c.tap(14,8)
    c.hold_tap((15,8),(1,2));c.hold_tap((16,8),(1,2))
    key='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    if arp or strum:
        from cases import assign_trig_parameter
        assert variant in (3,4)
        c.action(type='key',n=1,state=1);c.elapse(.3)
        try:
            c.tap(16,8);c.tap(16,8);c.led_values([(16,8)],[8])
        finally:c.action(type='key',n=1,state=0)
        if strum:
            c.enc(1,-4);c.enc(2,3);c.enc(3,3) # First chord mask: degree2, E64.
            c.enc(1,1);assign_trig_parameter(c,'Chord Note Strum');c.enc(3,0 if simultaneous else 8)
            if same_pitch:
                c.enc(2,1);assign_trig_parameter(c,'Fixed Note');c.enc(3,65) # Fixed root E64 equals the chord E64.
        else:
            c.enc(1,-3);assign_trig_parameter(c,'Chord Note Arpeggio');c.enc(3,8)
        # Half-step ratchet selected, but nonpositive parent gate ends at onset.
        # Repeat transport to expose retained arp jobs and duplicate releases.
        for trial in range(2):
            marker=c.snapshot()['midi_count']
            expected_notes=[(1,[144,64 if same_pitch else 60,127])]+([(1,[144,64,127])] if strum else [])
            notes=c.playback(expected_notes,cycles=2,timeout=8)
            assert_durations(c,notes,[0]*(4 if strum else 2))
            for i,note in enumerate(notes):
                expected_time=((i//2)*cycle_steps+(i%2)*(0 if simultaneous else .5))/6 if strum else i*cycle_steps/6
                assert abs((note[key]-notes[0][key])/1e9-expected_time)<=tolerance
            c.elapse(.3)
            events=[m for m in c.snapshot()['midi'] if m['index']>marker and 128<=m['bytes'][0]<=159]
            assert [(m['port'],m['bytes']) for m in events]==[(1,msg) for note in notes for msg in (note['bytes'],[128,note['bytes'][1],127])],events
            assert not c.snapshot()['midi_capture']['outstanding']
            c.results.append(dict(kind='nonpositive-strum-release' if strum else 'nonpositive-arp-endpoint',source_lengths=sources,trial=trial,onsets=len(notes),simultaneous=simultaneous,same_pitch=same_pitch,passed=True))
        return
    for index,(mode,level,length) in enumerate(list(zip(['average','longer','shorter'],[2,5,8],expected))+[('average',2,expected[0])]):
        if index:
            c.action(type='key',n=1,state=1);c.elapse(.3)
            try:c.tap(16,8);c.led_values([(16,8)],[level])
            finally:c.action(type='key',n=1,state=0)
        marker=c.snapshot()['midi_count']
        notes=c.playback([(1,[144,60,127])],cycles=2,timeout=8)
        assert_durations(c,notes,[length]*2)
        for i,note in enumerate(notes):assert abs((note[key]-notes[0][key])/1e9-i*cycle_steps/6)<=tolerance
        if variant>=3:
            events=[m for m in c.snapshot()['midi'] if m['index']>marker and 128<=m['bytes'][0]<=159]
            assert len(events)==2*len(notes),events
            assert [(m['port'],m['bytes']) for m in events]==[(1,msg) for note in notes for msg in (note['bytes'],[128,note['bytes'][1],127])],events
        c.results.append(dict(kind='numeric-length-merge',source_steps=sources,mode=mode,expected_steps=length,passed=True))


def fractional_length_mask_merge(c,variant=0,hierarchy=False):
    from cases import assert_durations,length_mask_display
    sources,merged,detents,label,mask=[([2,4],[3,5,1],8,'1/2',.5),([1,4],[3,6,0],1,'1/24',1/24),([2,4],[3,5,1],15,'1.25',1.25)][variant]
    c.configure();c.hold_tap((1,4),(8,4));c.tap(5,8)
    for x in (2,3,4):c.tap(x,4)
    for slot,length in enumerate(sources,1):
        c.tap(slot,1)
        if slot>1:c.tap(1,4)
        if length>1:c.hold_tap((1,4),(length,4))
        c.led_values([(x,4) for x in range(1,9)],[15]+[5]*(length-1)+[2]*(8-length))
    c.tap(3,8);c.tap(2,2);c.tap(14,8);c.tap(14,8)
    c.hold_tap((15,8),(1,2));c.hold_tap((16,8),(1,2))
    c.enc(1,-4);c.enc(2,2);length_mask_display(c,'X')
    c.enc(3,detents);length_mask_display(c,label)
    key='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    modes=list(zip(['average','longer','shorter'],[2,5,8],merged))+[('average',2,merged[0])]
    for index,(mode,level,unmasked) in enumerate(modes):
        if index:
            c.action(type='key',n=1,state=1);c.elapse(.3)
            try:c.tap(16,8);c.led_values([(16,8)],[level])
            finally:c.action(type='key',n=1,state=0)
        if hierarchy:
            assert variant==0
            c.action(type='grid',x=1,y=4,state=1)
            try:
                length_mask_display(c,label);c.enc(3,15-detents);length_mask_display(c,'1.25')
            finally:c.action(type='grid',x=1,y=4,state=0)
            c.elapse(.06);length_mask_display(c,label)
            # An explicit step mask remains in force whether or not the
            # channel default exists. Clearing it later must reveal that default.
            for channel_active in (True,False):
                if not channel_active:c.enc(3,-detents);length_mask_display(c,'X')
                marker=c.snapshot()['midi_count']
                notes=c.playback([(1,[144,60,127])],cycles=2,timeout=5)
                assert_durations(c,notes,[1.25]*2)
                for i,note in enumerate(notes):assert abs((note[key]-notes[0][key])/1e9-i*8/6)<=tolerance
                events=[m for m in c.snapshot()['midi'] if m['index']>marker and 128<=m['bytes'][0]<=159]
                assert [(m['port'],m['bytes']) for m in events]==[(1,msg) for _ in notes for msg in ([144,60,127],[128,60,127])],events
                c.results.append(dict(kind='step-length-mask-precedence',mode=mode,channel_active=channel_active,expected_steps=1.25,passed=True))
            c.enc(3,detents);length_mask_display(c,label)
            c.action(type='grid',x=1,y=4,state=1)
            try:c.key(2)
            finally:c.action(type='grid',x=1,y=4,state=0)
            c.elapse(.06);length_mask_display(c,label)
        # Change merge mode while the mask is active, then remove the mask.
        for masked,duration in [(True,mask),(False,unmasked)]:
            if not masked:c.enc(3,-detents);length_mask_display(c,'X')
            else:length_mask_display(c,label)
            marker=c.snapshot()['midi_count']
            notes=c.playback([(1,[144,60,127])],cycles=2,timeout=5)
            assert_durations(c,notes,[duration]*2)
            for i,note in enumerate(notes):assert abs((note[key]-notes[0][key])/1e9-i*8/6)<=tolerance
            events=[m for m in c.snapshot()['midi'] if m['index']>marker and 128<=m['bytes'][0]<=159]
            assert [(m['port'],m['bytes']) for m in events]==[(1,msg) for _ in notes for msg in ([144,60,127],[128,60,127])],events
            c.results.append(dict(kind='fractional-length-mask-merge',sources=sources,mode=mode,masked=masked,expected_steps=duration,passed=True))
        c.enc(3,detents);length_mask_display(c,label)
