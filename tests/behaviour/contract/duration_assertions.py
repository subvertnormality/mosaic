def assert_durations(c,notes,lengths,events=None):
    assert lengths and len(notes)>=len(lengths),'Missing duration observations'
    state=c.snapshot();rows=[]
    events=state['midi'] if events is None else events
    for note,length in zip(notes,lengths):
        off=next(m for m in events if m['index']>note['index'] and m['port']==note['port'] and m['bytes']==[128+(note['bytes'][0]&15),note['bytes'][1],note['bytes'][2]])
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        actual=(off[field]-note[field])/1e9
        rows.append(dict(pitch=note['bytes'][1],expected_seconds=length/6,actual_seconds=actual,error_ms=1000*(actual-length/6)))
    c.results.append(dict(kind='duration',rows=rows))
    # Two nanoseconds cover native integer deadline rounding; no wall jitter in D.
    tolerance_ms=.000002 if c.clock_mode=='controlled-experimental' else 10
    assert all(abs(row['error_ms'])<=tolerance_ms for row in rows),rows
