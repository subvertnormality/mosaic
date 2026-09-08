"""Complete ordered accounting for monophonic-per-pitch MIDI captures."""
def note_pairs(events):
    active={};pairs=[];previous=-1
    for event in events:
        assert event['index']>previous,'MIDI order changed'
        previous=event['index'];data=event['bytes'];kind=data[0]&240
        if kind not in (128,144):continue
        assert len(data)==3,'Malformed note event'
        key=(event['port'],data[0]&15,data[1])
        if kind==144 and data[2]>0:
            assert key not in active,('Retrigger before release',key,event)
            active[key]=event
        else:
            assert key in active,('Unmatched or duplicate release',key,event)
            pairs.append((active.pop(key),event))
    assert not active,('Missing release',active)
    return pairs
