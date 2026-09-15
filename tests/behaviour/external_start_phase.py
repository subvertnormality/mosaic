"""Absolute MIDI follower phase, anchored to the external source, not output."""
def external_start_phase(c):
    import time
    from cases import menu_label,menu_value
    from midi_window import MidiWindow
    from note_schedule import assert_schedule
    c.configure();c.key(1);c.enc(1,4);c.key(3);menu_label(c,'LEVELS >')
    position=next(i for i,v in enumerate(c.snapshot()['diagnostics']['parameter_roots']) if v['name']=='CLOCK')
    c.enc(2,position);c.key(3);menu_label(c,'source');menu_value(c,'internal')
    c.enc(3,1);menu_value(c,'midi')
    controlled=c.clock_mode=='controlled-experimental';domain='logical' if controlled else 'monotonic'
    # Upstream clock_midi_handle_start sets counter=-1; the next established
    # tick increments to0 and emits transport Start. Warm49 ticks establish
    # the24-sample estimator. Cold estimator behaviour is a separate case.
    for index,gap in enumerate((0,1,12_500_000,24_000_000)):
        origin=(c.logical_ns if controlled else time.monotonic_ns())+500_000_000
        first=origin+1_250_000_000;stop=origin+2_725_000_000
        packets=[(origin+i*25_000_000,248) for i in range(1,50)]
        packets += [(first-gap,250)]
        packets += [(first+i*25_000_000,248) for i in range(60)]
        packets += [(stop,252)]
        # Stable order puts Start before Clock when they share a deadline.
        packets.sort(key=lambda x:x[0])
        events=[dict(port=1,bytes=[value],**{'at_'+domain+'_ns':at}) for at,value in packets]
        capture=MidiWindow(c.snapshot()['midi_count'])
        request=dict(type='midi_schedule',schedule_id=100+index,events=events)
        if controlled:request['time_domain']='logical'
        c.action(**request)
        state=c.wait(lambda state:capture.extend(state) and len(state['midi_input_schedule']['delivered'])==len(events),timeout=5)
        c.wait(lambda state:capture.extend(state) and not state['midi_capture']['outstanding'])
        notes=capture.note_ons();assert len(notes)==10,dict(gap=gap,count=len(notes))
        field='logical_ns' if controlled else 'monotonic_ns'
        onsets=[(6*i,(60,62,64,65)[i%4],(127,117,107,97)[i%4]) for i in range(10)]
        checks=assert_schedule(capture.events,onsets,[6]*10,field=field,origin=first,stop_bounds=(stop,stop),pulse_rate=40,tolerance=2e-9 if controlled else .01)
        c.results.append(dict(kind='external-start-absolute-phase',start_to_first_clock_ns=gap,first_clock_deadline_ns=first,stop_deadline_ns=stop,first_note_offset_ns=notes[0][field]-first,onsets=len(notes),release_checks=len(checks),stimulus=events,delivered=state['midi_input_schedule']['delivered'],passed=True))
