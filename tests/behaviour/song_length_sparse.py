"""Silent steps must retain their musical duration at global length boundaries."""
def sparse_song_lengths(c):
    import time
    from midi_window import MidiWindow
    from note_schedule import assert_schedule
    c.configure();c.hold_tap((1,4),(16,7));c.tap(6,8)
    for length in (1,2,63,64,2):
        c.tap(7 if length>=63 else 2,7)
        if length==63:c.tap(1,7)
        elif length==2:c.tap(8,7)
        capture=MidiWindow(c.snapshot()['midi_count']);c.tap(1,8)
        c.wait(lambda state:capture.extend(state) and len(capture.note_ons())>=9,timeout=25)
        assert len(capture.note_ons())==9,'Observation missed intended stop window'
        controlled=c.clock_mode=='controlled-experimental'
        lower=c.logical_ns if controlled else time.monotonic_ns()
        c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
        upper=c.logical_ns if controlled else time.monotonic_ns()
        c.elapse(.06);c.wait(lambda state:capture.extend(state) and not state['midi_capture']['outstanding'])
        notes=capture.note_ons();assert len(notes)==9,'Extra onset before Stop'
        field='logical_ns' if controlled else 'monotonic_ns';audible=min(4,length)
        steps=[length*(i//audible)+(i%audible) for i in range(9)]
        onsets=[(24*step,(60,62,64,65)[i%audible],(127,117,107,97)[i%audible]) for i,step in enumerate(steps)]
        checks=assert_schedule(capture.events,onsets,[24]*9,field=field,origin=notes[0][field],stop_bounds=(lower,upper),tolerance=2e-9 if controlled else .01)
        assert sum(not row['truncated'] for row in checks)>=8
        c.results.append(dict(kind='sparse-song-length',length=length,expected_steps=steps,onsets=9,release_checks=checks,passed=True))
