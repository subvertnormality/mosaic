def panic_hold(c, button, source, repeats=1):
    ui=c.ui
    menus={'channel':[15,2,2,2], 'scale':[2,15,2,2],
           'trig':[2,2,5,2], 'note':[2,2,10,2],
           'velocity':[2,2,15,2], 'song':[2,2,2,15]}
    selected={'channel':3,'scale':4,'trig':5,'note':5,'velocity':5,'song':6}[source]
    ui.channel_editor()
    if source in ('trig','note','velocity'):
        for _ in range(('trig','note','velocity').index(source)+1):ui.pattern_editor()
    elif source!='channel':ui.tap_control(('channel_editor','scale_editor','pattern_editor','song_editor')[selected-3])
    menu=menus[source];c.led_values([(x,8) for x in (3,4,5,6)],menu)
    expected=[[128+channel,note,0] for note in range(128) for channel in range(16)] if button!=selected else []
    for repeat in range(repeats):
        after=c.snapshot()['midi_count'];start=len(c.observations)
        logical_start=c.logical_ns
        control=('channel_editor','scale_editor','pattern_editor','song_editor')[button-3]
        press_ack=ui.control_edge(control,True)
        c.elapse(.9);c.snapshot()
        # Live snapshots drive observation only; full exported MIDI is the oracle.
        for _ in range(10):
            c.elapse(.1);c.snapshot()
            if len(c.observations)>start+2:del c.observations[start+1:-1]
        ui.control_edge(control,False);c.elapse(.06);cursor=c.snapshot()['midi_count']
        c.led_values([(x,8) for x in (3,4,5,6)],menu)
        if not hasattr(c,'panic_windows'):c.panic_windows=[]
        c.panic_windows.append(dict(type='panic',after=after,cursor=cursor,source=source,
                                   button=button,repeat=repeat,logical_start=logical_start,press_ack=press_ack))


def panic_navigation(c, button):
    c.configure();panic_hold(c,button,'song');finish_panic_trace(c)


def panic_navigation_channel(c):
    return panic_navigation(c, 3)


def panic_navigation_pattern(c):
    return panic_navigation(c, 5)


def panic_hold_matrix(c):
    c.configure();pairs=[]
    for source in ('channel','scale','trig','note','velocity','song'):
        for button in (3,4,5,6):
            panic_hold(c,button,source,repeats=2)
            after=c.snapshot()['midi_count']
            c.playback([(1,[144,n,v]) for n,v in ((60,127),(62,117),(64,107),(65,97))],cycles=2)
            c.panic_windows.append(dict(type='melody',after=after,cursor=c.snapshot()['midi_count']))
            pairs.append([source,button])
    assert len(pairs)==24
    finish_panic_trace(c,dict(kind='panic-hold-matrix',pairs=pairs,holds=48,melody_checks=24,passed=True))


def finish_panic_trace(c, summary=None):
    import json
    from automation.input_origin import verified_input_origin
    from panic_trace import verify_panic_trace
    c.finish()
    try:
        events=[json.loads(line) for line in (c.out/'native/native-events.jsonl').read_text().splitlines()]
        actions=[json.loads(line) for line in (c.out/'native/actions.jsonl').read_text().splitlines()]
        controlled=c.clock_mode=='controlled-experimental'
        for window in c.panic_windows:
            if window['type']!='panic':continue
            ack=window['press_ack']
            submitted=[e for e in events if e.get('kind')=='input' and e['sequence']==ack['native']['sequence']]
            assert len(submitted)==1
            evidence=verified_input_origin(events,actions,session_id=c.runtime.id,action_id=ack['action_id'],
                expected_action=dict(type='grid',x=window['button'],y=8,state=1),declared_origin_ns=submitted[0]['monotonic_ns'])
            window['input_origin']=evidence
            window['minimum_ns']=window['logical_start']+1_000_000_000-2 if controlled else evidence['origin_ns']+900_000_000
        (c.out/'panic-windows.json').write_text(json.dumps(c.panic_windows,indent=2)+'\n')
        verify_panic_trace(events,c.panic_windows,11 if controlled else 3,c.results)
        if summary:c.results.append(summary)
    finally:
        (c.out/'results.json').write_text(json.dumps(c.results,indent=2)+'\n')


def panic_overlapping_holds(c, repeats):
    import json
    from panic_repeat_trace import verify_restarted_sweeps
    from panic_trace import verify_panic_trace
    ui=c.ui
    c.configure();ui.song_editor()
    before=c.snapshot()['midi_count'];held=[]
    try:
        for button in (3,4,5)[:repeats]:
            control=('channel_editor','scale_editor','pattern_editor')[button-3]
            ui.control_edge(control,True);held.append(button);c.elapse(.12)
        c.elapse(1.9)
    finally:
        for button in held:
            ui.control_edge(('channel_editor','scale_editor','pattern_editor')[button-3],False)
    c.elapse(.1);after=c.snapshot()['midi_count']
    c.led_values([(x,8) for x in (3,4,5,6)],[2,2,2,15])
    melody_before=c.snapshot()['midi_count']
    c.playback([(1,[144,n,v]) for n,v in ((60,127),(62,117),(64,107),(65,97))],cycles=2)
    melody_after=c.snapshot()['midi_count'];c.finish()
    try:
        events=[json.loads(line) for line in (c.out/'native/native-events.jsonl').read_text().splitlines()]
        midi=[e for e in events if e.get('kind') in (3,11)]
        assert [e['sequence'] for e in midi]==list(range(1,len(midi)+1))
        kind=11 if c.clock_mode=='controlled-experimental' else 3
        assert all(e['kind']==kind for e in midi)
        c.results.append(verify_restarted_sweeps(midi[before:after],repeats))
        # Reuse the independent melody oracle on a reindexed copy of that window.
        melody=[dict(e,sequence=i+1,index=i+1) for i,e in enumerate(midi[melody_before:melody_after])]
        verify_panic_trace(melody,[dict(type='melody',after=0,cursor=len(melody))],kind,c.results)
        outside=midi[:before]+midi[after:melody_before]+midi[melody_after:]
        assert not [e for e in outside if e['bytes'][0]&240 in (128,144)],'Notes outside panic/melody windows'
        c.results.append(dict(kind='panic-overlap-complete-stream',repeats=repeats,passed=True))
    finally:
        (c.out/'results.json').write_text(json.dumps(c.results,indent=2)+'\n')


def panic_overlapping_holds_two(c):
    return panic_overlapping_holds(c, 2)


def panic_overlapping_holds_three(c):
    return panic_overlapping_holds(c, 3)
