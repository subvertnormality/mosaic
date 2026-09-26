"""Per-slot repetition counts checked by independent octave fingerprints."""
def song_repetition_domain(c):
    import time
    from midi_window import MidiWindow
    from note_schedule import assert_schedule
    c.configure();c.tap(6,8);c.tap(2,7);c.tap(8,7)
    c.hold_tap((1,1),(2,1));c.tap(2,1);c.tap(3,8);c.tap(11,8);c.tap(6,8);c.tap(1,1)
    c.ui.set_mosaic_options([('Song mode',True),('Reset on song seq change',True),('Reset on pattern repeat',True)])
    # The Song button lands on Song Playback (A03); Repeats is on Slot Setup (A01),
    # which stays showing while the grid selects slot 1.
    c.ui.open_task('Song','slot_setup');c.ui.expect_selected_field('focused',label='Repeats')
    previous=1
    for repeats in range(1,17):
        c.tap(1,1);c.enc(3,repeats-previous);c.key(3);previous=repeats
        c.ui.expect_selected_field('focused',label='Repeats',value=str(repeats))
        capture=MidiWindow(c.snapshot()['midi_count']);c.tap(1,8)
        target=2*repeats+3
        c.wait(lambda state:capture.extend(state) and len(capture.note_ons())>=target,timeout=10)
        assert len(capture.note_ons())==target,'Missed repeat stop window'
        controlled=c.clock_mode=='controlled-experimental';lower=c.logical_ns if controlled else time.monotonic_ns()
        c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
        upper=c.logical_ns if controlled else time.monotonic_ns()
        # A real-time Stop may cross the next tick before its grid event is handled.
        # Validate that concurrent continuation too, then require the stopped LED and quiescence.
        c.elapse(.06)
        stopped=c.wait(lambda state:capture.extend(state) and state['grid'][112]==2 and not state['midi_capture']['outstanding'])
        stopped_count=len(capture.note_ons());c.elapse(.25);capture.extend(c.snapshot())
        notes=capture.note_ons()
        assert len(notes)==stopped_count,dict(repeats=repeats,late_onsets=len(notes)-stopped_count)
        assert len(notes)>=target,dict(repeats=repeats,expected_prefix=target,actual=len(notes))
        cycle=[(60,127),(62,117)]*repeats+[(72,127),(74,117)]
        phrase=[cycle[i%len(cycle)] for i in range(len(notes))]
        assert phrase[:target]==[(60,127),(62,117)]*repeats+[(72,127),(74,117),(60,127)]
        onsets=[(24*i,p,v) for i,(p,v) in enumerate(phrase)]
        checks=assert_schedule(capture.events,onsets,[24]*len(notes),field='logical_ns' if controlled else 'monotonic_ns',origin=notes[0]['logical_ns' if controlled else 'monotonic_ns'],stop_bounds=(lower,upper),tolerance=2e-9 if controlled else .01)
        c.results.append(dict(kind='song-repetition-domain',repeats=repeats,second_slot_repeats=1,transition_indices=[2*repeats,2*repeats+2],onsets=target,observed_onsets=len(notes),release_checks=len(checks),stopped_led=stopped['grid'][112],passed=True))
