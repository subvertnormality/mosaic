"""Pinned norns exposes Continue/SPP as MIDI data, not clock transport."""
def continue_spp_unsupported(c):
    import time
    from cases import menu_label,menu_value
    from midi_window import MidiWindow
    from note_schedule import assert_schedule
    c.configure();c.key(1);c.enc(1,4);c.key(3);menu_label(c,'LEVELS >')
    roots=c.snapshot()['diagnostics']['parameter_roots']
    position=next(i for i,v in enumerate(roots) if v['name']=='CLOCK')
    c.enc(2,position);c.key(3);menu_label(c,'source')
    menu_value(c,'internal');c.enc(3,1);menu_value(c,'midi');c.key(1);c.screen_header('Ch. 1 Device Config')
    controlled=c.clock_mode=='controlled-experimental';domain='logical' if controlled else 'monotonic'
    field='logical_ns' if controlled else 'monotonic_ns';tolerance=2e-9 if controlled else .01
    sequence=0
    def schedule(packets):
        nonlocal sequence
        sequence+=1;events=[dict(port=1,bytes=data,**{'at_'+domain+'_ns':at}) for at,data in packets]
        request=dict(type='midi_schedule',schedule_id=500+sequence,events=events)
        if controlled:request['time_domain']='logical'
        c.action(**request)
        state=c.wait(lambda state:len(state['midi_input_schedule']['delivered'])==len(events),timeout=5)
        state=c.wait(lambda state:not state['midi_capture']['outstanding'])
        return state,events
    origin=(c.logical_ns if controlled else time.monotonic_ns())+500_000_000
    first=origin+1_250_000_000;stop=first+312_500_000
    packets=[(origin+i*25_000_000,[248]) for i in range(1,50)]
    packets += [(first,[250])]+[(first+i*25_000_000,[248]) for i in range(13)]+[(stop,[252])]
    packets.sort(key=lambda item:(item[0],0 if item[1]==[250] else 1))
    capture=MidiWindow(c.snapshot()['midi_count']);state,initial=schedule(packets);capture.extend(state)
    c.elapse(.1);state=c.snapshot();capture.extend(state)
    assert_schedule(capture.events,[(0,60,127),(6,62,117),(12,64,107)],[6,6,1],field=field,origin=first,stop_bounds=(stop,stop),pulse_rate=40,tolerance=tolerance)
    stopped_grid=state['grid'];stopped_frame=state['frame']['sha256']
    unsupported=MidiWindow(state['midi_count']);messages=[];stable_samples=0
    for data in ([242,8,0],[251],*([[248]]*24)):
        at=(c.logical_ns if controlled else time.monotonic_ns())+(25_000_000 if controlled else 75_000_000)
        state,events=schedule([(at,data)]);messages.extend(events)
        c.elapse(.1);state=c.snapshot();unsupported.extend(state)
        assert state['grid'][112]==stopped_grid[112]
        assert state['frame']['sha256']==stopped_frame
        stable_samples+=1
    assert not unsupported.events
    restarted=MidiWindow(state['midi_count'])
    origin3=(c.logical_ns if controlled else time.monotonic_ns())+250_000_000
    stop3=origin3+162_500_000
    packets=[(origin3,[250])]+[(origin3+i*25_000_000,[248]) for i in range(7)]+[(stop3,[252])]
    packets.sort(key=lambda item:(item[0],0 if item[1]==[250] else 1))
    state,restart=schedule(packets);restarted.extend(state)
    assert_schedule(restarted.events,[(0,60,127),(6,62,117)],[6,1],field=field,origin=origin3,stop_bounds=(stop3,stop3),pulse_rate=40,tolerance=tolerance)
    c.results.append(dict(kind='continue-spp-explicitly-unsupported',initial=initial,unsupported=messages,restart=restart,stopped_grid_level=stopped_grid[112],stable_ui_samples=stable_samples,raw_delivery_count=len(messages),passed=True))
