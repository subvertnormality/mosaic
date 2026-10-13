"""Ordinary range isolation and scale clipping behaviour."""

def four_against_three_setup(c):
    """Channel 1 plays 60,62,64,65 over steps 1-4 on port 1; channel 2 plays 79,81,79 over steps 1-3 on port 2."""
    c.ui.configure()
    c.ui.select_channel_on_page(2,'midi_config');c.ui.turn(3,1);c.ui.turn(2,1);c.ui.turn(3,1);c.ui.turn(2,1);c.ui.turn(3,1);c.ui.press_key(3)
    c.ui.tap_control('pattern_slot',1);c.ui.set_range(1,3);c.ui.channel_page('masks','midi_config',confirm=False)
    for index,(global_turns,local_turns) in enumerate([(80,2),(41,20),(8,7)]):
        if index:c.ui.turn(2,1)
        c.ui.turn(3,global_turns)
        with c.ui.hold_step(2):c.ui.turn(3,local_turns)
        c.elapse(.06)
    c.ui.select_channel(1)

def rejected_range_channel_isolation(c,offset_step4=False):
    from cases import assert_durations
    four_against_three_setup(c)
    marker=c.snapshot()['midi_count'];c.ui.tap_control('play_stop')
    def emitted(state):return [m for m in state['midi'] if m['index']>marker and 144<=m['bytes'][0]<=159 and m['bytes'][2]>0]
    if offset_step4:
        # README.md#channel-length: the 4-step and 3-step loops started together on step 1; on
        # step 4 channel 1 plays its fourth note, 65, while the 3-step loop has wrapped and
        # channel 2 begins again with 79 (derived arithmetic, label: characterisation of the LCM claim).
        field4='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance4=2e-9 if c.clock_mode=='controlled-experimental' else .01
        state=c.wait(lambda state:sum(m['port']==1 for m in emitted(state))>=4 and sum(m['port']==2 for m in emitted(state))>=4)
        fourth=[[m for m in emitted(state) if m['port']==port][3] for port in (1,2)]
        assert [m['bytes'] for m in fourth]==[[144,65,97],[145,79,40]],'step 4: channel 1 has not wrapped, channel 2 has'
        assert abs(fourth[0][field4]-fourth[1][field4])/1e9<=tolerance4,'both fourth-step notes start together'
        c.results.append(dict(kind='loops-offset-step-4',port1_note=65,port2_note=79,passed=True))
    state=c.wait(lambda state:len(emitted(state))>=10)
    assert {m['port'] for m in emitted(state)}=={1,2},'both channels must be sounding before the range gesture'
    c.results.append(dict(kind='polymeter-playing',ports=[1,2],passed=True))
    c.ui.set_range(4,2)
    state=c.wait(lambda state:sum(m['port']==1 for m in emitted(state))>=17 and sum(m['port']==2 for m in emitted(state))>=17,5)
    all_notes=emitted(state);assert all((m['port'],m['bytes'][0]) in [(1,144),(2,145)] for m in all_notes)
    # README Channel Length: a 4-step and a 3-step loop start together on step 1 and again after
    # 12 steps, the first count both divide into. Step 13 is the 13th note of each port, 2 s later
    # at 6 steps per second; the refused reversed range left both loops running.
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    ports={port:[m for m in all_notes if m['port']==port] for port in (1,2)}
    meeting=[ports[port][12] for port in (1,2)]
    assert [m['bytes'] for m in meeting]==[[144,60,127],[145,79,40]],'step 13 is the first step of both phrases'
    delta=abs(meeting[0][field]-meeting[1][field])/1e9
    assert delta<=tolerance,delta
    for port in (1,2):
        assert abs((ports[port][12][field]-ports[port][0][field])/1e9-12/6)<=tolerance
    c.results.append(dict(kind='loops-meet-at-step-13',port1_note=60,port2_note=79,onset_delta_s=delta,passed=True))
    c.ui.tap_control('play_stop');c.wait(lambda state:not state['midi_capture']['outstanding'])
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    phrases={1:[[144,60,127],[144,62,117],[144,64,107],[144,65,97]],2:[[145,79,40],[145,81,60],[145,79,40]]}
    for port,phrase in phrases.items():
        notes=[m for m in all_notes if m['port']==port]
        assert [m['bytes'] for m in notes]==[phrase[i%len(phrase)] for i in range(len(notes))]
        for i,note in enumerate(notes):
            phase_error=(note[field]-notes[0][field])/1e9-i/6
            assert abs(phase_error)<=tolerance, dict(
                port=port, note_index=i, phase_error_seconds=phase_error,
                tolerance_seconds=tolerance, first_ns=notes[0][field], note_ns=note[field])
        assert_durations(c,notes,[1]*12 if port==1 else [.5,1.25,.5]*4)
    first=[next(m[field] for m in all_notes if m['port']==port) for port in [1,2]]
    assert abs(first[0]-first[1])/1e9<=tolerance
    c.results.append(dict(kind='rejected-range-channel-isolation',ranges=[[1,4],[1,3]],phrases=phrases,passed=True))

def rejected_range_offset_step4(c):
    """M-RANGE-REJECT-006: the four-against-three polymeter with a step-4 offset checkpoint."""
    return rejected_range_channel_isolation(c,offset_step4=True)

def offset_scale_range_clipping(c):
    from cases import assert_durations
    c.ui.configure();c.ui.scale_editor();c.ui.turn(2,-1)
    for slot,semitones in [(2,2),(3,4)]:
        with c.ui.hold_keys(1):c.elapse(.3);c.ui.tap_control('scale_slot',slot)
        c.ui.turn(3,semitones);c.ui.press_key(3)
    # Scale track starts beyond step1, with independent D/E/C locks.
    for step,slot in [(2,2),(3,3),(4,1)]:c.ui.hold_control_tap('step','scale_slot',step,slot)
    c.ui.set_range(2,4)
    for length,pitches in [(1,[62]),(2,[62,66]),(3,[62,66,64]),(2,[62,66])]:
        c.ui.song_editor();c.ui.tap_control('global_pattern_length',2)
        for _ in range(length-1):c.ui.tap_control('global_pattern_length',8)
        c.ui.scale_editor()
        notes=c.playback([(1,[144,p,v]) for p,v in zip(pitches,[127,117,107])],cycles=4,timeout=5)
        assert_durations(c,notes,[1]*(len(pitches)*3))
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        for i,note in enumerate(notes):assert abs((note[field]-notes[0][field])/1e9-i/6)<=tolerance
        c.results.append(dict(kind='offset-scale-global-cap',length=length,pitches=pitches,passed=True))
