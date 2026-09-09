"""Two independent receivers share phase; disabled outputs receive no clock."""
def master_multi_output(c):
    import base64
    from master_clock import configure_master_output,assert_master_receiver
    from cases import menu_label
    from midi_window import MidiWindow
    configure_master_output(c)
    c.enc(2,1);menu_label(c,'2. Second MIDI')
    def enabled(state):
        pixels=base64.b64decode(state['frame']['pixels_base64'])
        return all(pixels[(y*128+x)*4+k]==255 for y in range(26,29) for x in range(124,127) for k in range(3))
    assert not enabled(c.snapshot());c.enc(3,1);c.wait(enabled)
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    for phase in (.001,.025):
        c.elapse(phase);capture=MidiWindow(c.snapshot()['midi_count'])
        c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
        c.elapse(1.2);capture.extend(c.snapshot())
        c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
        c.wait(lambda state:capture.extend(state) and not state['midi_capture']['outstanding'])
        first=assert_master_receiver(capture.events,field,tolerance)
        # Receiver2 uses its own transport/clock, compared with the actual note
        # stream on port1. No application scheduler/state determines its beat.
        second_stream=[dict(e,port=1) for e in capture.events
                       if (e['port']==2 and e['bytes'] in ([248],[250],[252]))
                       or (e['port']==1 and len(e['bytes'])==3 and e['bytes'][0] in (128,144))]
        second=assert_master_receiver(second_stream,field,tolerance)
        assert first['clock_ticks']==second['clock_ticks']
        assert abs(first['first_clock_ns']-second['first_clock_ns'])/1e9<=tolerance
        assert not any(e['port']==3 and e['bytes']==[248] for e in capture.events),'Clock leaked to disabled port3'
        assert not any(e['port']==2 and len(e['bytes'])==3 and e['bytes'][0]==144 and e['bytes'][2]>0 for e in capture.events),'Notes leaked to port2'
        c.results.append(dict(kind='master-two-receiver-phase',phase_delay_seconds=phase,receivers=[first,second],events=capture.events,passed=True))
