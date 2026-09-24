"""Long external-master phase and drift regression."""
from external_clock_faults import TICK_NS,_actual_delivery,_assert_notes,_configure_midi_source,_schedule


def long_external_phase(c):
    import time
    _configure_midi_source(c)
    controlled=c.clock_mode=='controlled-experimental'
    domain='logical' if controlled else 'monotonic';key='at_'+domain+'_ns';field=domain+'_ns'
    now=c.logical_ns if controlled else time.monotonic_ns()
    origin=now+1_750_000_000;warm_origin=origin-1_250_000_000
    clocks=1536 # Sixteen4/4 bars at24PPQN:256 sixteenth-note onsets.
    events=[dict(port=1,bytes=[248],**{key:warm_origin+i*TICK_NS}) for i in range(1,50)]
    events.append(dict(port=1,bytes=[250],**{key:origin}))
    events.extend(dict(port=1,bytes=[248],**{key:origin+i*TICK_NS}) for i in range(clocks))
    stop=origin+(clocks-1)*TICK_NS+TICK_NS//2
    events.append(dict(port=1,bytes=[252],**{key:stop}))
    events.extend(dict(port=1,bytes=[248],**{key:stop+i*TICK_NS}) for i in range(1,13))
    events.sort(key=lambda event:(event[key],0 if event['bytes']==[250] else 1))
    capture,state=_schedule(c,events,421,48,controlled_batch=True)
    delivered=state['midi_input_schedule']['delivered']
    assert [(e['port'],e['bytes'],e['intended_'+domain+'_ns']) for e in delivered]==[
        (e['port'],e['bytes'],e[key]) for e in events]
    tolerance=2 if controlled else 10_000_000
    targets=[origin+i*6*TICK_NS for i in range(clocks//6)]
    pitches=(60,62,64,65);velocities=(127,117,107,97)
    onsets=[(target,pitches[i%4],velocities[i%4]) for i,target in enumerate(targets)]
    releases=targets[1:]+[stop]
    actual_stop=_actual_delivery(delivered,[252],stop,domain)
    accounting=_assert_notes(capture.events,field,onsets,releases,tolerance,
                             causal_releases={len(onsets)-1:actual_stop},
                             transport_tolerance_ns=tolerance)
    first=next(e for e in capture.events if e['port']==1 and e['bytes']==[144,60,127])
    sounding=[e for e in capture.events if e['port']==1 and len(e['bytes'])==3 and
              e['bytes'][0]&240==144 and e['bytes'][2]>0]
    accumulated=(sounding[-1][field]-first[field])-(len(sounding)-1)*6*TICK_NS
    assert abs(accumulated)<=tolerance,('Long-run accumulated phase drift',accumulated)
    assert state['midi_capture']['outstanding']==[]
    c.results.append(dict(kind='external-clock-long-phase',bars=16,input_clocks=clocks,
                          expected_onsets=len(onsets),duration_seconds=(stop-origin)/1e9,
                          accumulated_phase_error_ns=accumulated,tolerance_ns=tolerance,
                          actual_stop_ns=actual_stop,passed=True,**accounting))
