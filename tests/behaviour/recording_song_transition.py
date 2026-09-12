"""High-risk triple: live recording across a song transition (BEHAVIOUR_PLAN
"recording + lock edit + song transition").

Channel 1 has no trigs; slot 1 (global length 4) is copied to slot 2 and song
mode advances 1 -> 2 -> 1. Under a 100 BPM MIDI clock (24 PPQN, 150 ms steps,
step 1 from pulse 50 at 1.25 s, as M-REC-001), note A (72/90) lands on step 2
of slot 1 and note B (79/80) on step 2 of slot 2. Replay under the internal
clock must play each recorded note only in its own slot.
"""
import time

def recording_song_transition(c,held_across=False,release_length=False,chord=False):
    from cases import menu_label,menu_value
    c.configure()
    c.tap(5,8)
    for x in range(1,5):c.tap(x,4)                               # clear pattern 1 trigs
    c.tap(6,8);c.tap(2,7)
    for _ in range(3):c.tap(8,7)                                 # global length 4
    c.hold_tap((1,1),(2,1));c.tap(1,1);c.tap(3,8)                # slot 2 = copy of slot 1
    c.key(1);c.enc(1,4);c.key(3);menu_label(c,'LEVELS >')
    position=next(i for i,v in enumerate(c.snapshot()['diagnostics']['parameter_roots']) if v['name']=='CLOCK')
    c.enc(2,position);c.key(3);menu_label(c,'source');c.enc(3,1);menu_value(c,'midi');c.key(1)
    c.tap(2,8)                                                   # arm recording
    controlled=c.clock_mode=='controlled-experimental';domain='logical' if controlled else 'monotonic'
    origin=c.logical_ns+100000000 if controlled else time.monotonic_ns()+500000000
    a_on=1430000000;b_on=1430000000+4*150000000                  # slot 1 step 2; slot 2 step 2
    packets=[(i*25000000,[248]) for i in range(1,113)]
    packets+=[(1230000000,[250]),(a_on,[144,72,90]),(a_on+20000000,[128,72,0]),(b_on,[144,79,80]),(b_on+20000000,[128,79,0]),(2805000000,[252])]
    if held_across:
        # Note C pressed on slot 1 step 4 (1.73 s) and released after the 1.85 s transition.
        packets+=[(1730000000,[144,84,70]),
                  (1900000000 if chord or not release_length else 2030000000,[128,84,0])]
        if chord:
            packets+=[(1750000000,[144,88,70]),(2030000000,[128,88,0])]
    events=[dict(port=1,bytes=data,**{'at_'+domain+'_ns':origin+offset}) for offset,data in sorted(packets,key=lambda pair:pair[0])]
    request=dict(type='midi_schedule',schedule_id=1,events=events)
    if controlled:request['time_domain']='logical'
    c.action(**request)
    if controlled:c.elapse((origin+2820000000-c.logical_ns)/1e9)
    else:c.wait(lambda state:len(state['midi_input_schedule']['delivered'])==len(events),timeout=5)
    c.wait(lambda state:not state['midi_capture']['outstanding']);c.tap(2,8)  # disarm
    c.results.append(dict(kind='recording-across-transition',notes={'A':[72,90,'slot1-step2'],'B':[79,80,'slot2-step2']},passed=True))
    c.key(1);c.key(3);menu_label(c,'source');c.enc(3,-1);menu_value(c,'internal')
    c.enc(2,1);menu_label(c,'tempo');c.enc(3,-10);menu_value(c,'90');c.key(1)
    c.tap(6,8);c.tap(1,1);c.tap(3,8)                             # play the chain from slot 1
    # Current-active-step recording (user decision, LIVE_RECORDING_PLACEMENT.md): a note belongs
    # to the step, and so the slot, active at its first press.
    phrase=[(1,[144,72,90])]+([(1,[144,84,70])] if held_across else [])+([(1,[144,88,70])] if chord else [])+[(1,[144,79,80])]
    spacing=[2,0,2,4] if chord else ([2,2,4] if held_across else [4,4])                    # song-cycle steps between onsets
    notes=c.playback(phrase,cycles=3)
    field='logical_ns' if controlled else 'monotonic_ns';tolerance=2e-9 if controlled else .01
    gaps=[(b[field]-a[field])/1e9 for a,b in zip(notes,notes[1:])]
    assert all(abs(g-spacing[i%len(spacing)]/6)<=tolerance for i,g in enumerate(gaps)),dict(gaps=gaps,spacing=spacing)
    c.results.append(dict(kind='recording-across-transition-replay',gaps_seconds=gaps,passed=True))

    if release_length:
        # README 239: shared chord length runs from first press to final release.
        # 0.300 s at 100 BPM = two sixteenth-note steps. Replay at 90 BPM
        # must therefore hold each recorded voice for 2/6 seconds.
        events=c.snapshot()['midi']
        pitches=(84,88) if chord else (84,)
        durations=[]
        for onset in notes:
            if onset['bytes'][1] not in pitches:continue
            off=next(event for event in events if event['index']>onset['index']
                     and event['port']==onset['port']
                     and event['bytes'][0]==128 and event['bytes'][1]==onset['bytes'][1])
            duration=(off[field]-onset[field])/1e9
            durations.append(duration)
            assert abs(duration-2/6)<=tolerance, dict(pitch=onset['bytes'][1],duration=duration,expected=2/6)
        assert len(durations)>=3*len(pitches), durations
        c.results.append(dict(kind='cross-song-final-release-length',chord=chord,
                              expected_seconds=2/6,durations=durations,passed=True))
