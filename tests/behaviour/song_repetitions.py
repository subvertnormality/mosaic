"""Per-slot repetition counts checked by independent octave fingerprints."""
def song_repetition_domain(c):
    import base64,time
    from cases import set_mosaic_options
    from frame_oracle import render
    from midi_window import MidiWindow
    from note_schedule import assert_schedule
    c.configure();c.tap(6,8);c.tap(2,7);c.tap(8,7)
    c.hold_tap((1,1),(2,1));c.tap(2,1);c.tap(3,8);c.tap(11,8);c.tap(6,8);c.tap(1,1)
    set_mosaic_options(c,[('Song mode',True),('Reset on song seq change',True),('Reset on pattern repeat',True)])
    previous=1
    for repeats in range(1,17):
        c.tap(1,1);c.enc(3,repeats-previous);c.key(3);previous=repeats
        expected=render([(0,37,15,str(repeats))])
        def feedback(state):
            actual=base64.b64decode(state['frame']['pixels_base64'])
            return all(actual[(y*128+x)*4+k]==expected[(y*128+x)*4+k] for y in range(31,39) for x in range(0,32) for k in range(3))
        c.wait(feedback)
        capture=MidiWindow(c.snapshot()['midi_count']);c.tap(1,8)
        target=2*repeats+3
        c.wait(lambda state:capture.extend(state) and len(capture.note_ons())>=target,timeout=10)
        assert len(capture.note_ons())==target,'Missed repeat stop window'
        controlled=c.clock_mode=='controlled-experimental';lower=c.logical_ns if controlled else time.monotonic_ns()
        c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
        upper=c.logical_ns if controlled else time.monotonic_ns()
        c.elapse(.06);c.wait(lambda state:capture.extend(state) and not state['midi_capture']['outstanding'])
        notes=capture.note_ons();assert len(notes)==target
        phrase=[(60,127),(62,117)]*repeats+[(72,127),(74,117),(60,127)]
        onsets=[(24*i,p,v) for i,(p,v) in enumerate(phrase)]
        checks=assert_schedule(capture.events,onsets,[24]*target,field='logical_ns' if controlled else 'monotonic_ns',origin=notes[0]['logical_ns' if controlled else 'monotonic_ns'],stop_bounds=(lower,upper),tolerance=2e-9 if controlled else .01)
        c.results.append(dict(kind='song-repetition-domain',repeats=repeats,second_slot_repeats=1,transition_indices=[2*repeats,2*repeats+2],onsets=target,release_checks=len(checks),passed=True))
