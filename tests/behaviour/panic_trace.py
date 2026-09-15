"""Complete exported output accounting for panic and intervening melody windows."""
from note_accounting import note_pairs

def verify_panic_trace(events, windows, kind, reports):
    midi=[e for e in events if e.get('kind') in (3,11)]
    assert all(e['kind']==kind for e in midi),'Mixed MIDI clock domains'
    assert [e['sequence'] for e in midi]==list(range(1,len(midi)+1)),'Incomplete native MIDI sequence'
    assert windows
    owned=set();previous=0
    selected={'channel':3,'scale':4,'trig':5,'note':5,'velocity':5,'song':6}
    melody=((60,127),(62,117),(64,107),(65,97))
    field='logical_ns' if kind==11 else 'monotonic_ns'
    for window in windows:
        after,cursor=window['after'],window['cursor']
        assert type(after) is int and type(cursor) is int
        assert previous<=after<=cursor<=len(midi),'Invalid/overlapping capture boundaries'
        previous=cursor;captured=midi[after:cursor]
        notes=[e for e in captured if e['bytes'][0]&240 in (128,144)]
        owned.update(e['sequence'] for e in notes)
        if window['type']=='panic':
            assert window['button'] in (3,4,5,6)
            expected=[[128+channel,note,0] for note in range(128) for channel in range(16)] if window['button']!=selected[window['source']] else []
            actual={port:[e['bytes'] for e in captured if e['port']==port] for port in (1,2,3)}
            reports.append(dict(kind='panic-port-counts',button=window['button'],source=window['source'],repeat=window['repeat'],counts={p:len(v) for p,v in actual.items()},expected_per_port=len(expected)))
            assert all(e['port'] in (1,2,3) for e in captured),'Unexpected panic port'
            for port in (1,2,3):
                assert actual[port]==expected,('Incomplete panic output',window['source'],window['button'],port,len(actual[port]),len(expected))
            assert len(captured)==3*len(expected),'Missing/extra panic event'
            assert all(e[field]>=window['minimum_ns'] for e in captured),'Premature panic output'
            reports.append(dict(kind='panic-navigation',held_button=window['button'],selected_page=window['source'],repeat=window['repeat'],expected_panic=bool(expected),passed=True))
        elif window['type']=='melody':
            pairs=note_pairs(captured)
            ons=[e for e in notes if e['bytes'][0]&240==144 and e['bytes'][2]>0]
            assert len(ons)>=9 and len(pairs)==len(ons),'Incomplete melody population'
            for i,on in enumerate(ons):
                pitch,velocity=melody[i%4]
                assert (on['port'],on['bytes'])==(1,[144,pitch,velocity]),'Navigation changed melody'
            for on,off in pairs:
                assert off['port']==1 and off['bytes'][:2]==[128,on['bytes'][1]] and off['bytes'][2] in (0,on['bytes'][2]),'Unexpected melody release'
            reports.append(dict(kind='panic-melody-accounting',pairs=len(pairs),passed=True))
        else:raise AssertionError('Unknown output window')
    all_notes={e['sequence'] for e in midi if e['bytes'][0]&240 in (128,144)}
    assert owned==all_notes,('Notes outside declared windows',sorted(all_notes-owned)[:10])
    reports.append(dict(kind='panic-full-stream-accounting',note_events=len(all_notes),windows=len(windows),unaccounted=0,passed=True))
