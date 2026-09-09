"""External transport origin must not fast-forward when source epochs differ."""
def external_started_handoff(c):
    import time
    from cases import menu_label,menu_value
    from midi_window import MidiWindow
    c.configure();c.key(1);c.enc(1,4);c.key(3);menu_label(c,'LEVELS >')
    position=next(i for i,v in enumerate(c.snapshot()['diagnostics']['parameter_roots']) if v['name']=='CLOCK')
    c.enc(2,position);c.key(3);menu_label(c,'source');menu_value(c,'internal')
    c.enc(3,1);menu_value(c,'midi')
    controlled=c.clock_mode=='controlled-experimental';domain='logical' if controlled else 'monotonic'
    origin=(c.logical_ns if controlled else time.monotonic_ns())+500000000
    first=origin+1250000000
    packets=[(origin+i*25000000,248) for i in range(1,50)]
    packets += [(first,250)]+[(first+i*25000000,248) for i in range(80)]
    packets.sort(key=lambda x:x[0])
    events=[dict(port=1,bytes=[value],**{'at_'+domain+'_ns':at}) for at,value in packets]
    capture=MidiWindow(c.snapshot()['midi_count'])
    request=dict(type='midi_schedule',schedule_id=1,events=events)
    if controlled:request['time_domain']='logical'
    c.action(**request)
    c.wait(lambda state:capture.extend(state) and len(capture.note_ons())==1,timeout=3)
    c.elapse(.1);capture.extend(c.snapshot())
    assert c.snapshot()['midi_capture']['outstanding'],'No held note before source handoff'
    switch=c.action(type='enc',n=3,delta=-2)
    c.elapse(.5);capture.extend(c.snapshot());menu_value(c,'internal')
    c.tap(1,8)
    c.wait(lambda state:capture.extend(state) and not state['midi_capture']['outstanding'] and len(state['midi_input_schedule']['delivered'])==len(events),timeout=3)
    notes=capture.note_ons();field='logical_ns' if controlled else 'monotonic_ns'
    c.results.append(dict(kind='external-start-handoff-diagnostic',switch=switch,note_count=len(notes),notes=notes))
    # At90/100BPM sixteenth notes, this subsecond window cannot contain more
    # than six onsets. A source epoch change must not replay historical beats.
    assert 3<=len(notes)<=6,('Source handoff jumped through steps',len(notes))
    expected=[(60,127),(62,117),(64,107),(65,97)]
    assert [(m['port'],m['bytes']) for m in notes]==[(1,[144,*expected[i%4]]) for i in range(len(notes))]
    gaps=[(b[field]-a[field])/1e9 for a,b in zip(notes,notes[1:])]
    assert all(gap>=.05 for gap in gaps),('Source handoff emitted a note burst',gaps)
    c.results.append(dict(kind='external-start-handoff-no-burst',gaps_seconds=gaps,passed=True))
