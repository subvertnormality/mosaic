"""Ordered MIDI accounting, including explicitly expected overlapping voices."""
from collections import defaultdict,deque

def assert_schedule(events,onsets,durations,*,field,origin,stop_bounds,pulse_rate=144,tolerance=2e-9):
    assert len(onsets)==len(durations) and onsets
    voices=defaultdict(deque);position=0;releases=0;previous=-1;rows=[]
    lower,upper=stop_bounds
    for event in events:
        assert event['index']>previous,'Reordered MIDI capture'
        previous=event['index'];data=event['bytes'];kind=data[0]&240
        if kind not in (128,144):continue
        key=(event['port'],data[0]&15,data[1])
        if kind==144 and data[2]>0:
            assert position<len(onsets),'Extra onset'
            tick,pitch,velocity=onsets[position]
            assert (event['port'],data)==(1,[144,pitch,velocity]),('Wrong onset',position,event)
            phase=(event[field]-origin)/1e9-tick/pulse_rate
            assert abs(phase)<=tolerance,('Onset phase',position,phase)
            assert not voices[key] or voices[key][0]['due']>tick,('Due release followed retrigger',position)
            voices[key].append(dict(note=event,due=tick+durations[position],duration=durations[position]))
            position+=1
        else:
            assert voices[key],('Extra or misrouted release',event)
            voice=voices[key].popleft();expected=voice['due']/pulse_rate
            phase=(event[field]-origin)/1e9-expected
            regular=abs(phase)<=tolerance
            truncated=(origin+expected*1e9>=lower-tolerance*1e9 and lower-tolerance*1e9<=event[field]<=upper+tolerance*1e9)
            assert regular or truncated,('Release deadline',event,expected,phase)
            assert data[2]==voice['note']['bytes'][2] or (truncated and data[2]==0),('Release velocity',event)
            if regular:
                duration=(event[field]-voice['note'][field])/1e9
                assert abs(duration-voice['duration']/pulse_rate)<=tolerance,('Note duration',duration,voice['duration']/pulse_rate)
            releases+=1;rows.append(dict(pitch=data[1],expected_release_seconds=expected,phase_error_seconds=phase,truncated=not regular))
    assert position==len(onsets),'Missing onset'
    assert releases==position and not any(voices.values()),'Missing release'
    return rows
