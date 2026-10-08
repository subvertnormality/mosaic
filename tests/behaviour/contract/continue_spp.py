"""README.md#external-midi-transport: Continue/SPP leave Mosaic stopped and in place."""
def continue_spp_unsupported(c):
    import base64
    import time
    from cases import menu_label,menu_value
    from midi_window import MidiWindow
    from note_schedule import assert_schedule
    from contract.continue_spp_frame_oracle import assert_same_outside_mini
    from contract.mini_header_animation_ui import atlas as mini_atlas, native_events
    from mini_phase_oracle import check_stopped_phase

    c.configure();c.key(1);c.ui.turn(1,4);c.key(3);menu_label(c,'LEVELS >')
    roots=c.snapshot()['diagnostics']['parameter_roots']
    position=next(i for i,v in enumerate(roots) if v['name']=='CLOCK')
    c.enc(2,position);c.key(3);menu_label(c,'source')
    menu_value(c,'internal');c.enc(3,1);menu_value(c,'midi');c.key(1);c.screen_header('Ch. 1 Device Config')
    controlled=c.clock_mode=='controlled-experimental';domain='logical' if controlled else 'monotonic'
    field='logical_ns' if controlled else 'monotonic_ns';tolerance=2e-9 if controlled else .01
    # README.md#ui-motion describes the stopped-screen animation; the authored C05 footprint and exact beat-phase contract are checked independently.
    spec=mini_atlas()['C05']
    assert spec['origin']==[106,0] and spec['width']==22 and spec['height']==8

    def phase_check(state,before_index,expected_tempo=None):
        image_index=len(c.observations)-1
        observation=c.observations[image_index]
        diagnostics=state['diagnostics']
        events=native_events(c)
        matching=[event for event in events if event.get('kind')==1
                  and event.get('revision')==observation['frame_revision']
                  and event.get('sha256')==state['frame']['sha256']]
        assert len(matching)==1,'Exact native C05 frame revision is missing or ambiguous'
        draw_ns=matching[0]['monotonic_ns']
        after=state;after_index=image_index
        if diagnostics.get('monotonic_ns',-1)<draw_ns:
            after=c.wait(lambda current:current.get('diagnostics',{}).get('monotonic_ns',-1)>=draw_ns,timeout=1)
            after_index=len(c.observations)-1
        def receipt(index):
            diag=c.observations[index]['state'].get('diagnostics',{})
            return {key:diag.get(key) for key in ('beats','tempo','monotonic_ns','clock_epoch')}
        sample=dict(observation_index=image_index,
                    frame_sha256=state['frame']['sha256'],
                    frame_revision=observation['frame_revision'],
                    monotonic_ns=observation['monotonic_ns'],
                    clock_before_observation_index=before_index,
                    clock_after_observation_index=after_index,
                    clock_before=receipt(before_index),clock_after=receipt(after_index),
                    native_clock={key:diagnostics.get(key) for key in ('beats','tempo','monotonic_ns','clock_epoch')})
        return check_stopped_phase(sample,c.observations,events,spec,True,expected_tempo,c.clock_mode)

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
    stopped_grid=state['grid'];stopped_midi=state['midi_count']
    stopped_frame=base64.b64decode(state['frame']['pixels_base64'])
    controls=[];control_phase=[]
    timeline=([242,8,0],[251],*([[248]]*24))
    control_packets=[]
    for data in timeline:
        if data in ([242,8,0],[251]):
            before_index=len(c.observations)-1
            c.elapse(.125);state=c.snapshot()
        else:
            at=(c.logical_ns if controlled else time.monotonic_ns())+(25_000_000 if controlled else 75_000_000)
            state,events=schedule([(at,data)]);control_packets.extend(events)
            before_index=len(c.observations)-1
            c.elapse(.1);state=c.snapshot()
        assert state['grid']==stopped_grid and state['midi_count']==stopped_midi and state['clock']['admitted'] is False
        assert_same_outside_mini(state,stopped_frame,spec)
        control_phase.append(phase_check(state,before_index))
        controls.append(base64.b64decode(state['frame']['pixels_base64']))

    unsupported=MidiWindow(stopped_midi);messages=[];stable_samples=0;screen_phase=[]
    for index,data in enumerate(timeline):
        at=(c.logical_ns if controlled else time.monotonic_ns())+(25_000_000 if controlled else 75_000_000)
        state,events=schedule([(at,data)]);messages.extend(events)
        before_index=len(c.observations)-1
        c.elapse(.1);state=c.snapshot();unsupported.extend(state)
        assert state['grid']==stopped_grid
        assert state['midi_count']==stopped_midi and state['clock']['admitted'] is False
        assert_same_outside_mini(state,controls[index],spec)
        screen_phase.append(phase_check(state,before_index))
        stable_samples+=1
    assert not unsupported.events
    restarted=MidiWindow(state['midi_count'])
    restart_start=(c.logical_ns if controlled else time.monotonic_ns())+250_000_000
    first_restart_clock=restart_start+25_000_000
    stop3=first_restart_clock+162_500_000
    packets=[(restart_start,[250])]+[(first_restart_clock+i*25_000_000,[248]) for i in range(7)]+[(stop3,[252])]
    packets.sort(key=lambda item:(item[0],0 if item[1]==[250] else 1))
    # manual:external-midi-transport: Start marks the next Clock as beat zero; keep the first Clock strictly after Start.
    assert packets[:2]==[(restart_start,[250]),(first_restart_clock,[248])]
    assert first_restart_clock-restart_start==25_000_000
    state,restart=schedule(packets);restarted.extend(state)
    assert_schedule(restarted.events,[(0,60,127),(6,62,117)],[6,1],field=field,origin=first_restart_clock,stop_bounds=(stop3,stop3),pulse_rate=40,tolerance=tolerance)
    c.results.append(dict(kind='continue-spp-explicitly-unsupported',initial=initial,unsupported=messages,restart=restart,
        stopped_grid_level=stopped_grid[112],stable_ui_samples=stable_samples,raw_delivery_count=len(messages),
        paired_screen_scope=dict(page='C05',atlas_origin=spec['origin'],atlas_width=spec['width'],atlas_height=spec['height'],
            paired_intervals=stable_samples,control_excluded_transport_packets=[[242,8,0],[251]],control_clock_packets=control_packets,outside_footprint_exact=True,control_mini_phases=control_phase,input_mini_phases=screen_phase,citations=['README.md#external-midi-transport','README.md#ui-motion']),passed=True))
