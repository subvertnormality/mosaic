"""Mosaic user gestures during native MIDI removal and reconnection."""
import json
from panic_hotplug_trace import verify_hotplug_sweep
from panic_trace import verify_panic_trace
def panic_hotplug(c,removed_before,reconnect_during):
    c.configure();c.tap(6,8)
    before=c.snapshot()['midi_count']
    def change(connected):c.action(type='midi_connection',port=1,connected=connected)
    def reached(note):c.wait(lambda s:any(e['index']>before and e['port']==3 and e['bytes']==[143,note,0] for e in s['midi']),timeout=2)
    if removed_before:change(False)
    c.action(type='grid',x=5,y=8,state=1);held=True
    try:
        reached(24)
        if not removed_before:change(False)
        c.action(type='grid',x=5,y=8,state=0);held=False
        if reconnect_during:reached(64);change(True)
        reached(127)
        if not reconnect_during:change(True)
    finally:
        if held:c.action(type='grid',x=5,y=8,state=0)
    c.elapse(.1);after=c.snapshot()['midi_count']
    c.led_values([(x,8) for x in (3,4,5,6)],[2,2,2,15])
    # Fresh physical-style keyboard input must still use the restored mapping.
    keyboard_before=c.snapshot()['midi_count']
    c.action(type='midi',port=1,bytes=[144,60,100]);c.action(type='midi',port=1,bytes=[128,60,0]);c.elapse(.05)
    keyboard_after=c.snapshot()['midi_count']
    c.wait(lambda s:not s['midi_capture']['outstanding'])
    # A new panic must now reach all ports fully, without stale debounce jobs.
    full_before=c.snapshot()['midi_count'];c.action(type='grid',x=5,y=8,state=1)
    try:c.elapse(1.9)
    finally:c.action(type='grid',x=5,y=8,state=0)
    c.elapse(.1);full_after=c.snapshot()['midi_count']
    c.led_values([(x,8) for x in (3,4,5,6)],[2,2,2,15])
    melody_before=c.snapshot()['midi_count']
    c.playback([(1,[144,n,v]) for n,v in ((60,127),(62,117),(64,107),(65,97))],cycles=2)
    melody_after=c.snapshot()['midi_count'];c.finish()
    try:
        events=[json.loads(line) for line in (c.out/'native/native-events.jsonl').read_text().splitlines()]
        midi=[e for e in events if e.get('kind') in (3,11)];kind=11 if c.clock_mode=='controlled-experimental' else 3
        assert all(e['kind']==kind for e in midi)
        assert [e['sequence'] for e in midi]==list(range(1,len(midi)+1))
        transitions=[e for e in events if e.get('kind')==18 and e.get('input_sequence')]
        assert len(transitions)==2
        combined=sorted(midi[before:after]+transitions,key=lambda e:e['monotonic_ns'])
        c.results.append(verify_hotplug_sweep(combined,removed_before,reconnect_during))
        assert [(e['port'],e['bytes']) for e in midi[keyboard_before:keyboard_after]]==[(1,[144,60,100]),(1,[128,60,0])],'Restored keyboard mapping differs'
        full=midi[full_before:full_after];expected=[[128+channel,note,0] for note in range(128) for channel in range(16)]
        assert len(full)==6144 and all(e['port'] in (1,2,3) for e in full)
        for port in (1,2,3):assert [e['bytes'] for e in full if e['port']==port]==expected,'Fresh panic after reconnect differs'
        melody=[dict(e,sequence=i+1,index=i+1) for i,e in enumerate(midi[melody_before:melody_after])]
        verify_panic_trace(melody,[dict(type='melody',after=0,cursor=len(melody))],kind,c.results)
        outside=midi[:before]+midi[after:keyboard_before]+midi[keyboard_after:full_before]+midi[full_after:melody_before]+midi[melody_after:]
        assert not [e for e in outside if e['bytes'][0]&240 in (128,144)],'Notes outside declared windows'
        c.results.append(dict(kind='panic-hotplug-complete-stream',fresh_panic_events=6144,keyboard_messages=2,melody_recovered=True,passed=True))
    finally:(c.out/'results.json').write_text(json.dumps(c.results,indent=2)+'\n')
