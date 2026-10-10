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
def window_onsets(events):
    """Note-ons in a captured window, selected exactly as Driver.playback selects them."""
    return [event for event in events if 144<=event['bytes'][0]<=159 and event['bytes'][2]>0]
def continuation_onsets(c,notes,onsets,expected,offset_seconds,context=None):
    """Return a post-Stop window's onsets beyond Driver.playback()'s notes.

    playback() fixes its notes at the closing onset, but a window read after
    Stop also spans the observe/tap round trips before Stop takes effect. In
    real time further correctly scheduled onsets may land there. The returned
    notes must be the window's exact onset prefix; every later onset must
    continue the exact cyclic expected pattern at offset_seconds(ordinal)
    after the first onset within the real-time 10 ms tolerance. Controlled
    time admits none.
    """
    assert [m['index'] for m in onsets[:len(notes)]]==[m['index'] for m in notes],('Window does not begin with the played notes',context)
    late=onsets[len(notes):]
    assert not late or c.clock_mode=='real-time',('Onset after the closing onset in controlled time',late,context)
    for ordinal,m in enumerate(late,len(notes)):
        assert (m['port'],m['bytes'])==expected[ordinal%len(expected)],('Late onset breaks the cyclic pattern',ordinal,m,context)
        assert abs((m['monotonic_ns']-notes[0]['monotonic_ns'])/1e9-offset_seconds(ordinal))<=.01,('Late onset off its scheduled time',ordinal,m,context)
    return late
