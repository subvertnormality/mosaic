def strum_reset_continuity(c):
    import time
    from midi_window import MidiWindow
    from note_schedule import assert_schedule
    c.configure();c.ui.hold_control_tap('step','step',1,3);c.ui.turn(1,-4);c.ui.turn(2,3);c.ui.set_value(2)  # unset chord masks start from X
    # Note Masks shows the selected Chord 1 mask's full label and value.
    c.ui.expect_selected_field('overview_masks',label='Chord 1',value='3rd');c.results.append(dict(kind='chord-mask-screen',label='3rd',passed=True))
    c.ui.turn(1,3);c.ui.set_value(-11);c.ui.press_key(3);c.ui.turn(1,-2)
    c.ui.assign_trig_parameter_key('chord_note_strum');c.ui.set_value(8)
    for reset in (False,True):
        c.ui.set_mosaic_options([('Reset on song seq change',False),('Reset on pattern repeat',reset)])
        capture=MidiWindow(c.snapshot()['midi_count']);c.ui.play();c.elapse(24);capture.extend(c.snapshot())
        controlled=c.clock_mode=='controlled-experimental'
        lower=c.logical_ns if controlled else time.monotonic_ns()
        c.ui.control_edge('play_stop',True);c.ui.control_edge('play_stop',False)
        upper=c.logical_ns if controlled else time.monotonic_ns()
        # A deferred strum beyond Stop must never sound.
        c.elapse(2);capture.extend(c.snapshot());c.wait(lambda state:not state['midi_capture']['outstanding'])
        expected=[]
        for tick in range(3457):
            origin=(tick//1536)*1536 if reset else 0
            if (tick-origin)%216==0:
                step=((tick-origin)//216)%3;velocity=[127,117,107][step]
                expected.append((tick,[60,62,64][step],velocity,216))
                if tick+108<=3456:expected.append((tick+108,[64,65,67][step],velocity,108))
        # Sort only the independently constructed musical table, never emissions.
        expected.sort(key=lambda row:row[0])
        field='logical_ns' if controlled else 'monotonic_ns';notes=capture.note_ons();assert notes
        rows=assert_schedule(capture.events,[row[:3] for row in expected],[row[3] for row in expected],field=field,origin=notes[0][field],stop_bounds=(lower,upper),tolerance=2e-9 if controlled else .01)
        c.results.append(dict(kind='native-strum-reset',reset=reset,onsets=len(expected),release_checks=len(rows),scope='Half-step third-degree strum retains the established one-step root gate through resets; no deferred onset after Stop',passed=True))
