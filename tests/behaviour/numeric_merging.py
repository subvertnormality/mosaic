def numeric_note_merge(c,foreign_velocity=False,pentatonic=False,all_scales=False,harmony=False,
                       blink_observer=None):
    from cases import assert_durations
    c.ui.configure();c.ui.set_mosaic_options([('Lock merged to pent.',pentatonic)])
    sources=[(0,2,4,6),(2,4,6,0),(6,6,6,6)]
    c.ui.menu('pattern_editor')
    for slot,values in enumerate(sources,1):
        c.ui.tap_control('pattern_select',slot)
        if slot>1:
            for step in range(1,5):c.ui.tap_step(step)
        c.ui.menu('pattern_editor')
        for x,degree in enumerate(values,1):c.ui.tap_control('pattern_note_degree',(x,degree))
        steady=[(x,7-degree) for x,degree in enumerate(values,1) if not (x==slot and degree==6)]
        c.ui.expect_leds({('pattern_note_fader',cell):'active' for cell in steady})
        if values[slot-1]==6 and blink_observer:
            blink_observer(c,slot)
        c.ui.menu('channel_editor');c.ui.menu('pattern_editor')
    c.ui.menu('channel_editor');c.ui.tap_control('pattern_slot',2) # Only patterns1/2 are assigned.
    c.ui.tap_control('trig_merge_mode');c.ui.tap_control('trig_merge_mode')
    c.ui.expect_leds({('trig_merge_mode',None):'medium'}) # All trigs.
    c.ui.hold_control_tap('velocity_merge_mode','pattern_slot',target_index=3 if foreign_velocity else 1)
    c.ui.expect_leds({('pattern_slot',1):'selected',('pattern_slot',2):'selected',('pattern_slot',3):'off'})
    velocity=[100]*4 if foreign_velocity else [127,117,107,97]
    # Degree means [1,3,5,3]; Higher = mean+(max-min)=[3,5,7,9].
    # Independently map these zero-based degrees through C major.
    for mode,level,pitches in [('average',2,[62,64,69,64] if pentatonic else [62,65,69,65]),('higher',5,[64,69,72,76] if pentatonic else [65,69,72,76])]:
        if mode=='higher':c.ui.tap_control('note_merge_mode')
        c.ui.expect_leds({('note_merge_mode',None):{2:'off',5:'in_range',8:'medium'}[level]})
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
            c.ui.menu('scale_editor')
            # Normalize the selected field to scale type after each edit.
            if degree_delta:
                c.ui.turn(2,1);c.ui.set_value(degree_delta);c.ui.press_key(3);c.ui.turn(2,-1)
            if rotation_delta:
                c.ui.turn(2,3);c.ui.set_value(rotation_delta);c.ui.press_key(3);c.ui.turn(2,-3)
            if root_delta:
                c.ui.turn(2,-1);c.ui.set_value(root_delta);c.ui.press_key(3);c.ui.turn(2,1)
            c.ui.menu('channel_editor')
            for index,(mode,level) in enumerate([('higher',5),('lower',8),('average',2)]):
                if index:c.ui.tap_control('note_merge_mode')
                c.ui.expect_leds({('note_merge_mode',None):{2:'off',5:'in_range',8:'medium'}[level]})
                pitches=(pent if pentatonic else plain)[index]
                notes=c.playback([(1,[144,n,v]) for n,v in zip(pitches,velocity)],cycles=2,timeout=4)
                assert_durations(c,notes,[1]*8)
                for i,note in enumerate(notes):assert abs((note[field]-notes[0][field])/1e9-i/6)<=tolerance
                c.results.append(dict(kind='merge-harmony-transition',stage=label,mode=mode,pentatonic=pentatonic,pitches=pitches,passed=True))
            c.ui.tap_control('note_merge_mode')
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
                c.ui.menu('scale_editor');c.ui.set_value(1);c.ui.press_key(3);c.ui.menu('channel_editor')
            # Enter with Higher selected. Cycle through Lower/Average and back.
            for mode,level,degrees in [('higher',5,[3,5,7,9]),('lower',8,[-1,1,3,-3]),('average',2,[1,3,5,3])]:
                if mode!='higher':c.ui.tap_control('note_merge_mode')
                c.ui.expect_leds({('note_merge_mode',None):{2:'off',5:'in_range',8:'medium'}[level]})
                pitches=pent_tables[number][{'higher':0,'lower':1,'average':2}[mode]] if pentatonic else [60+12*(d//7)+intervals[d%7] for d in degrees]
                notes=c.playback([(1,[144,n,v]) for n,v in zip(pitches,velocity)],cycles=2,timeout=4)
                assert_durations(c,notes,[1]*8)
                for i,note in enumerate(notes):assert abs((note[field]-notes[0][field])/1e9-i/6)<=tolerance
                c.results.append(dict(kind='numeric-merge-all-scales',scale=scale,mode=mode,degrees=degrees,pitches=pitches,passed=True))
            c.ui.tap_control('note_merge_mode')
    if pentatonic and not all_scales:
        def verify(label,pitches):
            notes=c.playback([(1,[144,n,v]) for n,v in zip(pitches,velocity)],cycles=2,timeout=4)
            assert_durations(c,notes,[1]*8)
            for i,note in enumerate(notes):assert abs((note[field]-notes[0][field])/1e9-i/6)<=tolerance
            c.results.append(dict(kind='numeric-merge-scale-transition',label=label,pitches=pitches,passed=True))
        c.ui.menu('scale_editor');c.ui.turn(2,-1);c.ui.set_value(2);c.ui.press_key(3) # Root C -> D.
        verify('D-major-pentatonic-higher',[66,71,74,78])
        c.ui.turn(2,1);c.ui.set_value(2);c.ui.press_key(3) # Major -> natural minor.
        verify('D-minor-pentatonic-higher',[67,69,74,77])
        c.ui.menu('channel_editor');c.ui.tap_control('note_merge_mode');c.ui.tap_control('note_merge_mode')
        c.ui.expect_leds({('note_merge_mode',None):'off'})
        verify('D-minor-pentatonic-average',[65,67,69,67])
        c.ui.menu('scale_editor');c.ui.set_value(-2);c.ui.press_key(3);c.ui.turn(2,-1);c.ui.set_value(-2);c.ui.press_key(3)
        verify('restored-C-major-pentatonic-average',[62,64,69,64])


def merge_transpose_scale_lock(c):
    """Merge degrees before independent scale-lock and transpose composition."""
    from cases import assert_durations
    from midi_window import MidiWindow
    from note_accounting import note_pairs
    # Include Mosaic's script-start output as well as the subsequent user run.
    capture=MidiWindow(0)
    c.ui.configure(); c.ui.set_mosaic_options([('Lock merged to pent.',False)])
    sources=[(0,2,4,6),(2,4,6,0)]
    c.ui.menu('pattern_editor')
    for slot,values in enumerate(sources,1):
        c.ui.tap_control('pattern_select',slot)
        if slot>1:
            for step in range(1,5): c.ui.tap_step(step)
        c.ui.menu('pattern_editor')
        for x,degree in enumerate(values,1): c.ui.tap_control('pattern_note_degree',(x,degree))
        c.ui.menu('channel_editor'); c.ui.menu('pattern_editor')
    c.ui.menu('channel_editor'); c.ui.tap_control('pattern_slot',2)
    c.ui.tap_control('trig_merge_mode'); c.ui.tap_control('trig_merge_mode')
    c.ui.hold_control_tap('velocity_merge_mode','pattern_slot',target_index=1)

    # Edit-only scale slot2: D natural minor, transpose +3.
    c.ui.menu('scale_editor')
    with c.ui.hold_keys(1):
        c.elapse(.3); c.ui.tap_control('scale_slot',2)
    c.ui.set_value(2); c.ui.press_key(3)      # Major -> Minor.
    c.ui.turn(2,-1); c.ui.set_value(2); c.ui.press_key(3)  # Root C -> D.
    c.ui.turn(2,3); c.ui.set_value(3); c.ui.press_key(3)   # Transpose 0 -> +3.

    # Make the independent global scale track four steps long, then change
    # to slot2 at step3. It must reset at step1 of every loop. Step transpose
    # +12 persists from step3 through step4 on the same track.
    c.ui.set_range(1,4)
    c.ui.hold_control_tap('step','channel_scale_slot',held_index=3,target_index=2)
    c.ui.hold_control_tap('step','global_transpose_minimum',held_index=1)
    c.ui.hold_control_tap('step','cell',held_index=2,target_index=(12,8))
    c.ui.hold_control_tap('step','cell',held_index=3,target_index=(15,8))
    c.ui.menu('channel_editor')

    # Average degrees are [1,3,5,3]. Steps1/2 use C major: D62/F65.
    # Steps3/4 use D minor: Bb70/G67. Apply locks [-12,0,+12,+12]
    # and slot2's saved +3 only where the slot2 scale lock is active.
    expected_pitches=(50,65,85,82); expected_velocities=(127,117,107,97)
    c.ui.gesture((('play_stop',None),),(('play_stop',None),))
    c.elapse(1.9)
    c.wait(lambda state:capture.extend(state) and len(capture.note_ons())>=13,timeout=5)
    c.ui.gesture((('play_stop',None),),())
    stop_lower=c.logical_ns if c.clock_mode=='controlled-experimental' else __import__('time').monotonic_ns()
    c.ui.gesture((),(('play_stop',None),))
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
    c.ui.configure(); c.ui.menu('pattern_editor')
    for slot,values in enumerate(sources,1):
        c.ui.tap_control('pattern_select',slot)
        if slot>1:
            for step in range(1,5): c.ui.tap_step(step)
        c.ui.menu('pattern_editor')
        for x,degree in enumerate(values,1):
            control='pattern_note_octave_down' if degree<0 else 'pattern_note_octave_up'
            with c.ui.hold_control(control): c.elapse(1.2)
            c.elapse(.06)
            note_degree=7-(-degree if degree<0 else 14-degree)
            c.ui.tap_control('pattern_note_degree',(x,note_degree))
        c.ui.menu('channel_editor'); c.ui.menu('pattern_editor')
    c.ui.menu('channel_editor'); c.ui.tap_control('pattern_slot',2)
    c.ui.tap_control('trig_merge_mode'); c.ui.tap_control('trig_merge_mode')
    c.ui.hold_control_tap('velocity_merge_mode','pattern_slot',target_index=1)
    c.ui.tap_control('note_merge_mode')  # Average -> Higher.

    def set_scale_transpose(delta,lock=False):
        c.ui.menu('scale_editor')
        with c.ui.hold_keys(1):
            c.elapse(.3); c.ui.tap_control('scale_slot',1)
        c.ui.turn(2,2); c.ui.set_value(delta); c.ui.press_key(3); c.ui.turn(2,-2)
        if lock: c.ui.hold_control_tap('step','scale_slot',held_index=1,target_index=1)

    def play(mode,pitches,unbounded):
        velocities=(127,117,107,97); before=c.snapshot()
        if mode=='higher':
            startup=[(3,[192,0]),(3,[193,0]),(3,[194,0]),(3,[195,64]),(3,[196,0]),
                     (3,[197,0]),(3,[198,0]),(3,[199,0]),(3,[200,64]),(3,[201,11])]
            assert before['midi_count']==10
            assert [(e['port'],e['bytes']) for e in before['midi']]==startup
        capture=MidiWindow(before['midi_count'])
        c.ui.gesture((('play_stop',None),),(('play_stop',None),))
        c.elapse(4/3-.1)
        c.wait(lambda state:capture.extend(state) and len(capture.note_ons())>=9,timeout=4)
        c.ui.gesture((('play_stop',None),),())
        stop_lower=c.logical_ns if c.clock_mode=='controlled-experimental' else __import__('time').monotonic_ns()
        c.ui.gesture((),(('play_stop',None),))
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
    c.ui.tap_control('channel_octave',2); set_scale_transpose(12,lock=True)
    c.ui.hold_control_tap('step','cell',held_index=1,target_index=(15,8)); c.ui.menu('channel_editor')
    play('higher',(127,127,96,96),(148,148,96,96))

    # Lower degrees [-17,-17,-7,-7] map to [31,31,48,48]. Reversing
    # octave, scale and step transpose subtracts 48 semitones.
    c.ui.tap_control('channel_octave',-2); set_scale_transpose(-24)
    c.ui.hold_control_tap('step','global_transpose_minimum',held_index=1); c.ui.menu('channel_editor')
    c.ui.tap_control('note_merge_mode')
    play('lower',(0,0,0,0),(-17,-17,0,0))


def merge_mode_cycle(c,field):
    from cases import assert_durations
    assert field in ('velocity','length')
    c.ui.configure();c.ui.pattern_editor()
    for step in (2,3,4):c.ui.tap_step(step)
    if field=='length':c.ui.hold_control_tap('step','step',held_index=1,target_index=2)
    c.ui.tap_control('pattern_select',2);c.ui.tap_step(1)
    if field=='length':c.ui.hold_control_tap('step','step',held_index=1,target_index=4)
    c.ui.menu('channel_editor');c.ui.tap_control('pattern_slot',2)
    c.ui.tap_control('trig_merge_mode');c.ui.tap_control('trig_merge_mode')
    c.ui.hold_control_tap('note_merge_mode','pattern_slot',target_index=1)
    if field=='length':c.ui.hold_control_tap('velocity_merge_mode','pattern_slot',target_index=1)
    def verify(stage):
        notes=c.playback([(1,[144,60,127 if field=='length' else 114])],cycles=2,timeout=4)
        assert_durations(c,notes,[3 if field=='length' else 1]*2)
        key='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        for i,note in enumerate(notes):assert abs((note[key]-notes[0][key])/1e9-i*4/6)<=tolerance
        c.results.append(dict(kind='merge-mode-cycle',field=field,stage=stage,passed=True))
    verify('initial-average')
    for cycle in range(2):
        def cycle_modes():
            for level in (5,8,2):
                c.ui.tap_control('velocity_merge_mode')
                c.ui.expect_leds({('velocity_merge_mode',None):{2:'off',5:'in_range',8:'medium'}[level]})
        if field=='length':
            with c.ui.hold_keys(1):
                c.elapse(.3)
                cycle_modes()
        else:
            cycle_modes()
        verify('returned-average-'+str(cycle+1))


def merge_rounding(c,three=False,extreme=False,pentatonic=False):
    from cases import assert_durations
    c.ui.configure();c.ui.set_mosaic_options([('Lock merged to pent.',pentatonic)])
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
    c.ui.menu('pattern_editor')
    for slot,values in enumerate(sources,1):
        c.ui.tap_control('pattern_select',slot)
        if slot>1:
            for step in range(1,5):c.ui.tap_step(step)
        c.ui.menu('pattern_editor')
        for x,degree in enumerate(values,1):
            if 0<=degree<=6:c.ui.tap_control('pattern_note_octave_reset');y=7-degree
            else:
                control='pattern_note_octave_down' if degree<0 else 'pattern_note_octave_up'
                with c.ui.hold_control(control):c.elapse(1.2)
                c.elapse(.06);y=-degree if degree<0 else 14-degree
            note_degree=7-y
            c.ui.tap_control('pattern_note_degree',(x,note_degree))
            if not (y==1 and x==slot):c.ui.expect_leds({('pattern_note_fader',(x,y)):'active'})
        c.ui.menu('channel_editor');c.ui.menu('pattern_editor')
    c.ui.menu('channel_editor')
    for slot in range(2,len(sources)+1):c.ui.tap_control('pattern_slot',slot)
    c.ui.tap_control('trig_merge_mode');c.ui.tap_control('trig_merge_mode')
    c.ui.hold_control_tap('velocity_merge_mode','pattern_slot',target_index=1)
    key='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    for index,(mode,level,pitches) in enumerate(expected+[expected[0]]):
        if index:c.ui.tap_control('note_merge_mode')
        c.ui.expect_leds({('note_merge_mode',None):{2:'off',5:'in_range',8:'medium'}[level]})
        for reversed_order in (False,True):
            if reversed_order:
                for slot in range(1,len(sources)+1):c.ui.tap_control('pattern_slot',slot)
                for slot in range(len(sources),0,-1):c.ui.tap_control('pattern_slot',slot)
            notes=c.playback([(1,[144,n,v]) for n,v in zip(pitches,[127,117,107,97])],cycles=2,timeout=4)
            assert_durations(c,notes,[1]*8)
            for i,note in enumerate(notes):assert abs((note[key]-notes[0][key])/1e9-i/6)<=tolerance
            c.results.append(dict(kind='merge-rounded-mean-native',contributors=sources,mode=mode,reversed_assignment=reversed_order,pitches=pitches,passed=True))


def numeric_velocity_merge(c,three=False):
    from cases import assert_durations
    c.ui.configure();c.ui.pattern_editor()
    for slot in ([2,3,4] if three else [2,4]):
        c.ui.tap_control('pattern_select',slot)
        for x in range(1,5):c.ui.tap_step(x)
    c.ui.pattern_editor('note',from_view='trigger')
    for x in range(1,5):c.ui.tap_control('pattern_note_degree',(x,4)) # Unassigned pattern4 supplies G only.
    c.ui.expect_leds({('pattern_note_degree',(x,4)):'active' for x in range(1,5)})
    c.ui.menu('channel_editor');c.ui.tap_control('pattern_slot',2)
    if three:c.ui.tap_control('pattern_slot',3)
    c.ui.tap_control('trig_merge_mode');c.ui.tap_control('trig_merge_mode');c.ui.hold_control_tap('note_merge_mode','pattern_slot',target_index=4)
    c.ui.expect_leds({('pattern_slot',4):'off'})
    # Sources127/117/107/97 and one or two100s. Round the mean first;
    # apply mode arithmetic, then enforce MIDI velocity's upper bound127.
    expected=([('average',2,[109,106,102,99]),('higher',5,[127,123,109,102]),('lower',8,[91,94,98,95])] if three else
              [('average',2,[114,109,104,99]),('higher',5,[127,126,111,102]),('lower',8,[86,91,96,95])])
    key='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    for index,(mode,level,velocities) in enumerate(expected+[expected[0]]):
        if index:c.ui.tap_control('velocity_merge_mode')
        c.ui.expect_leds({('velocity_merge_mode',None):{2:'off',5:'in_range',8:'medium'}[level]})
        notes=c.playback([(1,[144,67,v]) for v in velocities],cycles=2,timeout=4)
        assert_durations(c,notes,[1]*8)
        for i,note in enumerate(notes):assert abs((note[key]-notes[0][key])/1e9-i/6)<=tolerance
        c.results.append(dict(kind='numeric-velocity-merge',contributors=3 if three else 2,mode=mode,velocities=velocities,note_priority_unassigned=4,passed=True))


def lydian_octave_boundary(c):
    from cases import assert_durations
    c.ui.configure();c.ui.menu('pattern_editor')
    for slot in (1,2):
        c.ui.tap_control('pattern_select',slot)
        if slot==2:
            for step in range(1,5):c.ui.tap_step(step)
        c.ui.menu('pattern_editor')
        for x,degree in enumerate((-7,0,7,0),1):
            if degree==0:c.ui.tap_control('pattern_note_octave_reset')
            else:
                control='pattern_note_octave_down' if degree<0 else 'pattern_note_octave_up'
                with c.ui.hold_control(control):c.elapse(1.2)
                c.elapse(.06)
            c.ui.tap_control('pattern_note_degree',(x,0))
            c.ui.expect_leds({('pattern_note_degree',(x,0)):'active'})
        c.ui.menu('channel_editor');c.ui.menu('pattern_editor')
    c.ui.menu('channel_editor');c.ui.tap_control('pattern_slot',2)
    c.ui.tap_control('trig_merge_mode');c.ui.tap_control('trig_merge_mode')
    c.ui.hold_control_tap('velocity_merge_mode','pattern_slot',target_index=1)
    c.ui.menu('scale_editor');c.ui.turn(3,7);c.ui.press_key(3)
    # Lydian selection D/E/G/A/B repeats across octaves. C48/60/72
    # has B47/59/71 nearer than D50/62/74. Equal source values still merge.
    notes=c.playback([(1,[144,n,v]) for n,v in zip([47,59,71,59],[127,117,107,97])],cycles=2,timeout=4)
    assert_durations(c,notes,[1]*8)
    key='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    for i,note in enumerate(notes):assert abs((note[key]-notes[0][key])/1e9-i/6)<=tolerance
    c.results.append(dict(kind='lydian-pentatonic-octave-equivalence',degrees=[-7,0,7,0],pitches=[47,59,71,59],passed=True))


def velocity_zero_boundary(c):
    c.ui.configure();c.ui.menu('pattern_editor')
    for slot in (1,2):
        c.ui.tap_control('pattern_select',slot)
        if slot==2:
            for step in range(1,5):c.ui.tap_step(step)
        c.ui.menu('pattern_editor')
        if slot==1:c.ui.tap_control('cell',(4,3)) # G remains G under the enabled Major pentatonic lock.
        c.ui.menu('pattern_editor')
        # The manual's 14-position velocity fader spans 127..0.
        # Literal source vectors: [0,0,19,58], [127,0,58,58].
        if slot==2:
            with c.ui.hold_control('cell',(15,8)):c.elapse(1.2)
            c.elapse(.06);c.ui.tap_control('pattern_select',1)
        with c.ui.hold_control('cell',(16,8)):c.elapse(1.2)
        c.elapse(.06)
        cells=([(1,7),(2,7),(3,5),(4,1)] if slot==1 else [(2,7),(3,1),(4,1)])
        for cell in cells:c.ui.tap_control('pattern_note_fader',cell)
        c.ui.expect_leds({('pattern_note_fader',cell):'active' for cell in cells})
        c.ui.menu('channel_editor');c.ui.menu('pattern_editor')
    c.ui.menu('channel_editor');c.ui.tap_control('pattern_slot',2)
    c.ui.tap_control('trig_merge_mode');c.ui.tap_control('trig_merge_mode')
    c.ui.hold_control_tap('note_merge_mode','pattern_slot',target_index=1)
    key='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    # Rounded mean, then mode arithmetic, then MIDI 0..127 clamp.
    # Lower raw results [-64,0,-1,58] must not wrap into loud notes.
    expected=[('average',2,[64,0,39,58]),('higher',5,[127,0,78,58]),('lower',8,[0,0,0,58])]
    for index,(mode,level,velocities) in enumerate(expected+[expected[0]]):
        if index:c.ui.tap_control('velocity_merge_mode')
        c.ui.expect_leds({('velocity_merge_mode',None):{2:'off',5:'in_range',8:'medium'}[level]})
        before=c.snapshot()['midi_count'];c.ui.tap_control('play_stop')
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
        c.ui.tap_control('play_stop');c.wait(lambda state:state['midi_capture']['outstanding']==[])
        c.results.append(dict(kind='numeric-velocity-zero-boundary',mode=mode,velocities=velocities,raw_events_checked=len(events),passed=True))


def numeric_length_merge(c,variant=0,arp=False,strum=False,simultaneous=False,same_pitch=False):
    from cases import assert_durations
    sources,expected=[([2,4],[3,5,1]),([3,4],[4,5,2]),([2,2,5],[3,6,1]),([1,2],[2,3,0]),([1,4],[3,6,0]),([2,2,8],[4,10,0])][variant]
    cycle_steps=16 if variant>=3 else 8
    c.ui.configure();c.ui.set_range(1,cycle_steps);c.ui.menu('pattern_editor')
    for step in (2,3,4):c.ui.tap_step(step)
    for slot,length in enumerate(sources,1):
        c.ui.tap_control('pattern_select',slot)
        if slot>1:c.ui.tap_step(1)
        if length>1:c.ui.set_range(1,length)
        c.ui.expect_steps({step:('selected' if step==1 else 'in_range' if step<=length else 'off')
                           for step in range(1,cycle_steps+1)})
    c.ui.menu('channel_editor')
    for slot in range(2,len(sources)+1):c.ui.tap_control('pattern_slot',slot)
    c.ui.tap_control('trig_merge_mode');c.ui.tap_control('trig_merge_mode')
    c.ui.hold_control_tap('note_merge_mode','pattern_slot',target_index=1)
    c.ui.hold_control_tap('velocity_merge_mode','pattern_slot',target_index=1)
    key='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    if arp or strum:
        from cases import assign_trig_parameter
        assert variant in (3,4)
        with c.ui.hold_keys(1):
            c.elapse(.3);c.ui.tap_control('velocity_merge_mode');c.ui.tap_control('velocity_merge_mode')
            c.ui.expect_leds({('velocity_merge_mode',None):'medium'})
        if strum:
            c.ui.turn(1,-4);c.ui.turn(2,3);c.ui.set_value(2) # First chord mask from X: degree2, E64.
            c.ui.turn(1,1);c.ui.assign_trig_parameter('Chord Note Strum');c.ui.set_value(0 if simultaneous else 8)
            if same_pitch:
                c.ui.turn(2,1);c.ui.assign_trig_parameter('Fixed Note');c.ui.set_value(65) # Fixed root E64 equals the chord E64.
        else:
            c.ui.turn(1,-3);c.ui.assign_trig_parameter('Chord Note Arpeggio');c.ui.set_value(8)
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
            with c.ui.hold_keys(1):
                c.elapse(.3);c.ui.tap_control('velocity_merge_mode')
                c.ui.expect_leds({('velocity_merge_mode',None):{2:'off',5:'in_range',8:'medium'}[level]})
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
    from cases import assert_durations
    sources,merged,detents,label,mask=[([2,4],[3,5,1],8,'1/2',.5),([1,4],[3,6,0],1,'1/24',1/24),([2,4],[3,5,1],15,'1.25',1.25)][variant]
    c.ui.configure();c.ui.set_range(1,8);c.ui.menu('pattern_editor')
    for step in (2,3,4):c.ui.tap_step(step)
    for slot,length in enumerate(sources,1):
        c.ui.tap_control('pattern_select',slot)
        if slot>1:c.ui.tap_step(1)
        if length>1:c.ui.set_range(1,length)
        c.ui.expect_steps({step:('selected' if step==1 else 'in_range' if step<=length else 'off')
                           for step in range(1,9)})
    c.ui.menu('channel_editor');c.ui.tap_control('pattern_slot',2)
    c.ui.tap_control('trig_merge_mode');c.ui.tap_control('trig_merge_mode')
    c.ui.hold_control_tap('note_merge_mode','pattern_slot',target_index=1)
    c.ui.hold_control_tap('velocity_merge_mode','pattern_slot',target_index=1)
    c.ui.turn(1,-4);c.ui.turn(2,2);c.ui.expect_field_value('length','X')
    c.ui.set_value(detents);c.ui.expect_field_value('length',label)
    key='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    modes=list(zip(['average','longer','shorter'],[2,5,8],merged))+[('average',2,merged[0])]
    for index,(mode,level,unmasked) in enumerate(modes):
        if index:
            with c.ui.hold_keys(1):
                c.elapse(.3);c.ui.tap_control('velocity_merge_mode')
                c.ui.expect_leds({('velocity_merge_mode',None):{2:'off',5:'in_range',8:'medium'}[level]})
        if hierarchy:
            assert variant==0
            with c.ui.hold_step(1):
                c.ui.expect_field_value('length',label);c.ui.set_value(15-detents);c.ui.expect_field_value('length','1.25')
            c.elapse(.06);c.ui.expect_field_value('length',label)
            # An explicit step mask remains in force whether or not the
            # channel default exists. Clearing it later must reveal that default.
            for channel_active in (True,False):
                if not channel_active:c.ui.set_value(-detents);c.ui.expect_field_value('length','X')
                marker=c.snapshot()['midi_count']
                notes=c.playback([(1,[144,60,127])],cycles=2,timeout=5)
                assert_durations(c,notes,[1.25]*2)
                for i,note in enumerate(notes):assert abs((note[key]-notes[0][key])/1e9-i*8/6)<=tolerance
                events=[m for m in c.snapshot()['midi'] if m['index']>marker and 128<=m['bytes'][0]<=159]
                assert [(m['port'],m['bytes']) for m in events]==[(1,msg) for _ in notes for msg in ([144,60,127],[128,60,127])],events
                c.results.append(dict(kind='step-length-mask-precedence',mode=mode,channel_active=channel_active,expected_steps=1.25,passed=True))
            c.ui.set_value(detents);c.ui.expect_field_value('length',label)
            with c.ui.hold_step(1):c.ui.press_key(2)
            c.elapse(.06);c.ui.expect_field_value('length',label)
        # Change merge mode while the mask is active, then remove the mask.
        for masked,duration in [(True,mask),(False,unmasked)]:
            if not masked:c.ui.set_value(-detents);c.ui.expect_field_value('length','X')
            else:c.ui.expect_field_value('length',label)
            marker=c.snapshot()['midi_count']
            notes=c.playback([(1,[144,60,127])],cycles=2,timeout=5)
            assert_durations(c,notes,[duration]*2)
            for i,note in enumerate(notes):assert abs((note[key]-notes[0][key])/1e9-i*8/6)<=tolerance
            events=[m for m in c.snapshot()['midi'] if m['index']>marker and 128<=m['bytes'][0]<=159]
            assert [(m['port'],m['bytes']) for m in events]==[(1,msg) for _ in notes for msg in ([144,60,127],[128,60,127])],events
            c.results.append(dict(kind='fractional-length-mask-merge',sources=sources,mode=mode,masked=masked,expected_steps=duration,passed=True))
        c.ui.set_value(detents);c.ui.expect_field_value('length',label)
