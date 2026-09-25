"""Exact range feedback and clipping contracts."""


def rejected_range(c,scale_page=False):
    from cases import assert_durations
    from frame_oracle import footer_matches
    c.configure()
    if scale_page:c.tap(4,8)
    c.hold_tap((2,4),(4,4));c.elapse(.15)
    def verify(start,stage):
        pitches=[60,62,64,65] if scale_page else [60,62,64,65][start-1:]
        velocities=[127,117,107,97] if scale_page else [127,117,107,97][start-1:]
        notes=c.playback([(1,[144,p,v]) for p,v in zip(pitches,velocities)],cycles=2,timeout=4)
        assert_durations(c,notes,[1]*(len(pitches)*2))
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        for i,note in enumerate(notes):assert abs((note[field]-notes[0][field])/1e9-i/6)<=tolerance
        c.results.append(dict(kind='range-rejection-playback',scale_page=scale_page,stage=stage,pitches=pitches,passed=True))
    verify(2,'valid-before-rejection')
    for sequence in ['held4-release2','press2-press4-release2']:
        before=c.snapshot()['grid'][48:112]
        events=[(4,1),(2,1),(2,0),(4,0)] if sequence=='held4-release2' else [(2,1),(4,1),(2,0),(4,0)]
        for x,z in events:c.action(type='grid',x=x,y=4,state=z)
        # Live footer tooltip (frame_oracle.footer): exact text, whole footer line.
        def feedback(state):return footer_matches(state,'End must follow start')
        c.wait(feedback);c.wait(lambda state:state['grid'][48:112]==before)
        c.results.append(dict(kind='range-rejection-feedback',scale_page=scale_page,sequence=sequence,prior_grid=before,passed=True))
        verify(2,sequence)
    c.hold_tap((3,4),(4,4));c.elapse(.15)
    c.led_values([(1,4),(2,4),(5,4)],[0,0,0]);verify(3,'valid-recovery')


def rejected_range_while_playing(c,scale_page=False):
    from cases import assert_durations
    from frame_oracle import footer_matches
    c.configure()
    if scale_page:c.tap(4,8)
    marker=c.snapshot()['midi_count'];c.tap(1,8)
    def notes(state):return [m for m in state['midi'] if m['index']>marker and 144<=m['bytes'][0]<=159 and m['bytes'][2]>0]
    c.wait(lambda state:len(notes(state))>=5)
    for events in [[(4,1),(2,1),(2,0),(4,0)],[(2,1),(4,1),(2,0),(4,0)]]:
        for x,z in events:c.action(type='grid',x=x,y=4,state=z)
        # Live footer tooltip (frame_oracle.footer): exact text, whole footer line.
        def feedback(state):return footer_matches(state,'End must follow start')
        c.wait(feedback);c.elapse(.3)
    state=c.wait(lambda state:len(notes(state))>=17);emitted=notes(state)
    phrase=[[144,60,127],[144,62,117],[144,64,107],[144,65,97]]
    assert [(m['port'],m['bytes']) for m in emitted]==[(1,phrase[i%4]) for i in range(len(emitted))]
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    for i,note in enumerate(emitted):assert abs((note[field]-emitted[0][field])/1e9-i/6)<=tolerance
    c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])
    assert_durations(c,emitted,[1]*16)
    c.results.append(dict(kind='live-range-rejection',scale_page=scale_page,onsets=len(emitted),passed=True))


def global_range_clipping(c):
    from cases import assert_durations
    from frame_oracle import footer_matches
    c.configure();c.tap(5,8)
    c.tap(15,7);c.tap(16,7);c.tap(3,8)
    # Distinguish the last two steps through held-step note masks.
    c.ui.turn(1, -4)
    for x,turns in [(15,73),(16,75)]:
        c.action(type='grid',x=x,y=7,state=1)
        try:c.enc(3,turns)
        finally:c.action(type='grid',x=x,y=7,state=0)
    cell=lambda step:((step-1)%16+1,(step-1)//16+4)
    values={1:(60,127),2:(62,117),3:(64,107),4:(65,97),63:(72,100),64:(74,100)}
    for start,end in [(1,4),(2,4),(63,64)]:
        c.hold_tap(cell(start),cell(end))
        for length in [1,2,3,4,64]:
            c.tap(6,8)
            # Song fader inner-left/right select absolute 1/64; rightmost
            # increments by one. This also exercises the fine adjustment.
            c.tap(7 if length==64 else 2,7)
            if length!=64:
                for _ in range(length-1):c.tap(8,7)
            # Live footer tooltip (frame_oracle.footer): exact text, whole footer line.
            def feedback(state):return footer_matches(state,'Global pattern length: '+str(length))
            c.wait(feedback);c.tap(3,8)
            # LEDs show the playable range, capped by global length. Restoring
            # global length must expose the previously selected endpoints again.
            steps=list(range(start,min(end,start+length-1)+1))
            c.led_values([cell(i) for i in range(1,65)],[15 if i in steps else 0 for i in range(1,65)])
            phrase=[(1,[144,*values[i]]) for i in steps]
            notes=c.playback(phrase,cycles=3,timeout=5)
            assert_durations(c,notes,[1]*(len(steps)*2))
            field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
            tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
            for i,note in enumerate(notes):assert abs((note[field]-notes[0][field])/1e9-i/6)<=tolerance
            c.results.append(dict(kind='global-channel-range-clipping',start=start,end=end,global_length=length,played_steps=steps,passed=True))


def queued_global_length_transitions(c):
    from cases import assert_durations
    from frame_oracle import footer_matches
    c.configure();c.hold_tap((2,4),(4,4));c.tap(6,8)
    c.tap(2,7)
    for _ in range(3):c.tap(8,7)
    marker=[c.snapshot()['midi_count']];c.tap(1,8)
    def emitted(state):return [m for m in state['midi'] if m['index']>marker[0] and 144<=m['bytes'][0]<=159 and m['bytes'][2]>0]
    def shown(text):
        # Live footer tooltip (frame_oracle.footer): exact text, whole footer line.
        def feedback(state):return footer_matches(state,text)
        return feedback
    def queued(length,before_count):
        c.tap(2,7)
        for _ in range(length-1):c.tap(8,7)
        state=c.wait(shown("Q'd: Global pattern length: "+str(length)))
        return len(emitted(state))<before_count
    attempts=None
    if c.clock_mode=='real-time':attempts=queued_growth_real_time(c,marker,emitted,shown,queued)
    else:
        # Global4 finishes at onset index4. The capped offset phrase becomes
        # steps2/3 there, without resetting its clock or its still-valid playhead.
        assert queued(2,5),'Fixture queue missed the intended boundary'
        state=c.wait(lambda state:len(emitted(state))>=13,4)
        assert len(emitted(state))==13,'Fixture missed growth scheduling window'
        # The new global2 cycles end at indices6,8,10,12,14. Queue after12;
        # growth to3 must apply at14 and expose step4 again on index15.
        assert queued(3,15),'Fixture queue missed the intended boundary'
    steps=[2,3,4,2]+[3,2]*5+[3,4,2]*4
    try:
        state=c.wait(lambda state:len(emitted(state))>=25,5);notes=emitted(state)
        assert len(notes)<=len(steps)
        values={2:(62,117),3:(64,107),4:(65,97)}
        expected=[(1,[144,*values[step]]) for step in steps[:len(notes)]]
        actual=[(m['port'],m['bytes']) for m in notes]
        assert actual==expected,dict(expected=expected,actual=actual)
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        for i,note in enumerate(notes):assert abs((note[field]-notes[0][field])/1e9-i/6)<=tolerance
        c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])
        assert_durations(c,notes,[1]*24);c.tap(3,8)
        c.led_values([(1,4),(2,4),(3,4),(4,4),(5,4)],[0,15,15,15,0])
    except BaseException:
        # A decided in-window placement with the wrong outcome fails at once,
        # with every placement attempt already recorded.
        if attempts is not None:c.results.append(dict(kind='queued-global-shrink-grow',passed=False,placement_attempts=attempts))
        raise
    result=dict(kind='queued-global-shrink-grow',caps=[4,2,3],application_onset_indices=[4,14],expected_steps=steps[:len(notes)],passed=True)
    if attempts is not None:result['placement_attempts']=attempts
    c.results.append(result)


# Real-time growth placement (M-RANGE-LIVE-002). The growth edits must be
# callback-complete between onset12 (a global2 boundary) and onset14 (the next
# one). Sequential taps after a polled observation of onset12 spent most of that
# 333ms window in unmeasured poll lag, round trips and fixed 60ms tap pacing.
# Mosaic acts on grid release and its fader press has no timing, so the pacing
# is not a device hold. Instead submit the same six edges, in the same order, as
# one native input schedule at fixed native times 80ms after onset12. The native
# scheduler needs >=100ms admission lead and polling observes an onset 40-130ms
# late, so the times are projected from an earlier observed onset on the 1/6s
# lattice (itself asserted to 10ms below). Placement is then DECIDED only from
# measurements: every edge's native callback-completion timestamp must lie at
# least 10ms after onset12's and 10ms before onset14's native MIDI timestamp.
# Undecided or missed placements stop (Stop discards queued length edits),
# restore global4 while stopped and re-place; at most three attempts, all
# recorded before any assertion.
GROWTH_PLACE_NS=80_000_000       # first edge after onset12
GROWTH_EDGE_SPACING_NS=2_000_000 # ordered edges; no hold/debounce is required
GROWTH_ADMIT_NS=150_000_000      # native admission needs >=100ms lead
GROWTH_MARGIN_NS=10_000_000
GROWTH_EDGES=[(2,1),(2,0),(8,1),(8,0),(8,1),(8,0)]  # tap(2,7); tap(8,7) x2 -> 3


def queued_growth_real_time(c,marker,emitted,shown,queued):
    import time
    attempts=[]
    try:
        for attempt in range(3):
            if attempt:
                c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])
                c.tap(2,7)
                for _ in range(3):c.tap(8,7)
                c.wait(shown('Global pattern length: 4'))
                marker[0]=c.snapshot()['midi_count'];c.tap(1,8)
            row=dict(attempt=attempt+1,decided=False)
            attempts.append(row)
            row['shrink_queued_before_onset4']=queued(2,5)
            if not row['shrink_queued_before_onset4']:
                row['reason']='shrink-queue-missed-onset4';continue
            onsets=emitted(c.wait(lambda state:len(emitted(state))>=11,4));now=time.monotonic_ns()
            last=len(onsets)-1;projected=onsets[last]['monotonic_ns']+round((12-last)*1e9/6)
            planned=[projected+GROWTH_PLACE_NS+i*GROWTH_EDGE_SPACING_NS for i in range(len(GROWTH_EDGES))]
            row.update(projection_onset_index=last,projected_onset12_ns=projected,host_submit_ns=now,planned_ns=planned)
            if last>=12 or planned[0]-now<GROWTH_ADMIT_NS:
                row['reason']='observed-too-late-to-schedule';continue
            schedule_id=attempt+1
            ack=c.action(type='native_input_schedule',schedule_id=schedule_id,
                         events=[dict(type='grid',x=x,y=7,state=z,at_monotonic_ns=at) for (x,z),at in zip(GROWTH_EDGES,planned)])
            row['ack']=ack
            def settled(state):
                record=state.get('native_input_schedule') or {}
                return record.get('schedule_id')==schedule_id and record.get('status') in ('completed','failed','cancelled')
            record=c.wait(settled,3)['native_input_schedule']
            completions=[d.get('callback_completed_monotonic_ns') for d in record['delivered']]
            row.update(schedule_status=record['status'],callback_completed_ns=completions)
            if record['status']!='completed' or len(completions)!=len(GROWTH_EDGES) or None in completions:
                row['reason']='missing-native-edge-evidence';continue
            # Display oracle, as before: the growth edit is shown as queued.
            c.wait(shown("Q'd: Global pattern length: 3"))
            onsets=emitted(c.wait(lambda state:len(emitted(state))>=15,3))
            anchor=onsets[12]['monotonic_ns'];boundary=onsets[14]['monotonic_ns']
            row.update(anchor_onset_index=12,anchor_ns=anchor,boundary_onset_index=14,boundary_ns=boundary,
                       first_edge_after_anchor_ns=min(completions)-anchor,last_edge_before_boundary_ns=boundary-max(completions))
            if min(completions)>=anchor+GROWTH_MARGIN_NS and max(completions)<=boundary-GROWTH_MARGIN_NS:
                row['decided']=True;row['reason']='all-edges-inside-onset12-onset14';return attempts
            row['reason']='edges-not-clearly-inside-onset12-onset14'
    except BaseException:
        c.results.append(dict(kind='queued-global-shrink-grow',passed=False,placement_attempts=attempts))
        raise
    c.results.append(dict(kind='queued-global-shrink-grow',passed=False,placement_attempts=attempts))
    raise AssertionError('Three real-time growth placements were not decidably inside the onset12-onset14 window')


def range_reject_001(c):
    return rejected_range(c, False)


def range_reject_002(c):
    return rejected_range(c, True)


def range_reject_003(c):
    return rejected_range_while_playing(c, False)


def range_reject_004(c):
    return rejected_range_while_playing(c, True)
