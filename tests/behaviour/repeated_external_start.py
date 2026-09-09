"""Absolute MIDI follower phase, anchored to the external source, not output."""
def repeated_external_start(c):
    import time,base64
    from cases import menu_label,menu_value
    from midi_window import MidiWindow
    from note_schedule import assert_schedule
    c.configure();c.key(1);c.enc(1,4);c.key(3);menu_label(c,'LEVELS >')
    position=next(i for i,v in enumerate(c.snapshot()['diagnostics']['parameter_roots']) if v['name']=='CLOCK')
    c.enc(2,position);c.key(3);menu_label(c,'source');menu_value(c,'internal')
    c.enc(3,1);menu_value(c,'midi')
    c.enc(2,8);menu_label(c,'2. Second MIDI')
    def enabled(state):
        pixels=base64.b64decode(state['frame']['pixels_base64'])
        return all(pixels[(y*128+x)*4+k]==255
                   for y in range(26,29) for x in range(124,127) for k in range(3))
    assert not enabled(c.snapshot());c.enc(3,1);c.wait(enabled)
    controlled=c.clock_mode=='controlled-experimental';domain='logical' if controlled else 'monotonic'
    # Upstream clock_midi_handle_start sets counter=-1; the next established
    # tick increments to0 and emits transport Start. Warm49 ticks establish
    # the24-sample estimator. Cold estimator behaviour is a separate case.
    for index,gap in enumerate((0,)):
        origin=(c.logical_ns if controlled else time.monotonic_ns())+500_000_000
        first=origin+1_250_000_000;stop=origin+2_737_500_000
        packets=[(origin+i*25_000_000,248) for i in range(1,50)]
        packets += [(first-gap,250)]
        packets += [(first+i*25_000_000,248) for i in range(60)]
        packets += [(first+500_000_000,250),(stop,252)]
        # Stable order puts Start before Clock when they share a deadline.
        packets.sort(key=lambda x:(x[0],0 if x[1]==250 else 1))
        events=[dict(port=1,bytes=[value],**{'at_'+domain+'_ns':at}) for at,value in packets]
        capture=MidiWindow(c.snapshot()['midi_count'])
        request=dict(type='midi_schedule',schedule_id=100+index,events=events)
        if controlled:request['time_domain']='logical'
        c.action(**request)
        state=c.wait(lambda state:capture.extend(state) and len(state['midi_input_schedule']['delivered'])==len(events),timeout=5)
        c.wait(lambda state:capture.extend(state) and not state['midi_capture']['outstanding'])
        notes=capture.note_ons();assert len(notes)==11,dict(gap=gap,count=len(notes))
        field='logical_ns' if controlled else 'monotonic_ns'
        stops=[e for e in capture.events if e['port']==1 and e['bytes']==[252]]
        assert len(stops)==1 and stops[0][field]>=stop,('Restart echoed a premature Stop',stops)
        release=next(e for e in capture.events if e['port']==1 and e['bytes'][:2]==[128,65])
        assert release['index']<notes[4]['index'],'Restart note preceded the held-note release'
        onsets=[(6*i,(60,62,64,65)[i],(127,117,107,97)[i]) for i in range(4)]
        onsets += [(20+6*i,(60,62,64,65)[i%4],(127,117,107,97)[i%4]) for i in range(7)]
        checks=assert_schedule(capture.events,onsets,[6,6,6,2]+[6]*7,field=field,origin=first,stop_bounds=(stop,stop),pulse_rate=40,tolerance=2e-9 if controlled else .01)
        active=False;tick=-1;receiver_notes=0;starts=0;forwarded=0;cleanup_stops=0
        for event in capture.events:
            data=event['bytes']
            if event['port']==2:
                if data==[250]:active=True;tick=-1;starts+=1
                elif data==[252]:active=False;cleanup_stops+=1
                elif data==[248] and active:tick+=1;forwarded+=1
            elif event['port']==1 and len(data)==3 and data[0]==144 and data[2]>0:
                expected=6*(receiver_notes if receiver_notes<4 else receiver_notes-4)
                assert active and tick==expected,('Repeated Start forwarded phase',receiver_notes,tick,expected)
                receiver_notes+=1
        # The second incoming Start replaces the active owner without echoing a
        # cleanup Stop. Its coincident F8 becomes receiver tick zero again.
        assert starts==2 and cleanup_stops==1 and forwarded==60
        stop_event=next(e for e in capture.events if e['port']==2 and e['bytes']==[252])
        second_start=[e for e in capture.events if e['port']==2 and e['bytes']==[250]][1]
        assert stop_event['index']>second_start['index'], 'Restart emitted a cleanup Stop'
        assert receiver_notes==11 and tick==39
        assert not any(e['port'] in (1,3) and e['bytes']==[248] for e in capture.events)
        c.results.append(dict(kind='repeated-external-start-reset',start_to_first_clock_ns=gap,first_clock_deadline_ns=first,stop_deadline_ns=stop,first_note_offset_ns=notes[0][field]-first,onsets=len(notes),restart_deadline_ns=first+500_000_000,release_checks=len(checks),stimulus=events,delivered=state['midi_input_schedule']['delivered'],passed=True))
