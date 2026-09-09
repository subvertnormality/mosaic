"""First-ever MIDI clock after Start must establish the external beat origin."""
def fast_acquisition(c,bpm=20):
    import time
    from cases import menu_label,menu_value
    from midi_window import MidiWindow
    from note_schedule import assert_schedule
    c.configure();c.enc(1,-1);c.enc(3,10);c.key(3);c.key(1);c.enc(1,4);c.key(3);menu_label(c,'LEVELS >')
    position=next(i for i,v in enumerate(c.snapshot()['diagnostics']['parameter_roots']) if v['name']=='CLOCK')
    c.enc(2,position);c.key(3);menu_label(c,'source');menu_value(c,'internal')
    c.enc(3,1);menu_value(c,'midi')
    controlled=c.clock_mode=='controlled-experimental';domain='logical' if controlled else 'monotonic'
    tick_ns=60_000_000_000/bpm/24
    # Fresh native process: no MIDI clocks have been sent before this Start.
    for index,gap in enumerate((0,)):
        origin=(c.logical_ns if controlled else time.monotonic_ns())+500_000_000
        first=origin+round(tick_ns)
        # Keep Stop distinctly before the final gate deadline at high tempo.
        stop=first+round(10.25*tick_ns)
        packets=[]
        packets += [(first-gap,250)]
        packets += [(first+round(i*tick_ns),248) for i in range(12)]
        packets += [(stop,252)]
        # Stable order puts Start before Clock when they share a deadline.
        packets.sort(key=lambda x:x[0])
        events=[dict(port=1,bytes=[value],**{'at_'+domain+'_ns':at}) for at,value in packets]
        capture=MidiWindow(c.snapshot()['midi_count'])
        request=dict(type='midi_schedule',schedule_id=100+index,events=events)
        if controlled:request['time_domain']='logical'
        c.action(**request)
        state=c.wait(lambda state:capture.extend(state) and len(state['midi_input_schedule']['delivered'])==len(events),timeout=2+12*60/bpm/24)
        c.wait(lambda state:capture.extend(state) and not state['midi_capture']['outstanding'])
        notes=capture.note_ons()
        field='logical_ns' if controlled else 'monotonic_ns'
        c.results.append(dict(kind='fast-acquisition-diagnostic',bpm=bpm,first_clock_deadline_ns=first,first_note_offset_ns=notes[0][field]-first if notes else None,note_count=len(notes),stimulus=events,delivered=state['midi_input_schedule']['delivered']))
        assert len(notes)==14,dict(gap=gap,count=len(notes))
        field='logical_ns' if controlled else 'monotonic_ns'
        # x8: each step is3/96beats, or3/4 of one MIDI tick.
        # Clock2 first establishes tempo at tick1. The missed tick0.75 step
        # is reconciled then; later deadlines keep the original external origin.
        onsets=[(0 if i==0 else max(.75*i,1),(60,62,64,65)[i%4],(127,117,107,97)[i%4]) for i in range(14)]
        assert_acquisition_release_order(capture.events)
        checks=assert_schedule(capture.events,onsets,[1,.5]+[.75]*12,field=field,origin=first,stop_bounds=(stop,stop),pulse_rate=bpm*24/60,tolerance=2e-9 if controlled else .01)
        c.results.append(dict(kind='fast-acquisition-reconciliation',start_to_first_clock_ns=gap,first_clock_deadline_ns=first,stop_deadline_ns=stop,first_note_offset_ns=notes[0][field]-first,onsets=len(notes),missed_initial_deadlines=1,nominal_step_ticks=.75,release_checks=len(checks),stimulus=events,delivered=state['midi_input_schedule']['delivered'],passed=True))

def assert_acquisition_release_order(events):
    releases=[e for e in events if e['port']==1 and e['bytes'][:2]==[128,60]]
    onsets=[e for e in events if e['port']==1 and e['bytes']==[144,62,117]]
    assert releases and onsets,'Missing acquisition transition events'
    assert releases[0]['index']<onsets[0]['index'],'Acquisition onset preceded the held-note release'
