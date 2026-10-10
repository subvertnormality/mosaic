"""Native global/local clock inheritance round trips with independent pulse expectations."""


def _set_clock_field(ui, name, value):
    """Select a named field while retaining the source's physical offsets."""
    ui.select_field(name, offset=1)
    ui.set_value(value)
    ui.press_key(3)


def _open_clock_page(c):
    ui = c.ui
    ui.menu("channel_editor")
    # Preserve the original MIDI-config -> clocks E1 -1 navigation exactly.
    ui.channel_page("clock_mods", "midi_config", channel=1, confirm=False)
    # Preserve the original selected=4 / "Ch. 1 Clocks" header oracle without
    # adding the screen-header result that expect_header records.
    ui.wait_for_header("clock_mods", channel=1)


def shuffle_type_inheritance(c):
    from note_accounting import note_pairs

    ui = c.ui
    ui.configure()
    ui.menu("song_editor")
    ui.turn(1, 1)                                                # original Song Global settings E1 +1
    _set_clock_field(ui, "global-shuffle-type", 1)              # global Swing -> Shuffle
    _set_clock_field(ui, "global-shuffle-feel", 2)              # Drunk -> Heavy
    _set_clock_field(ui, "global-shuffle-basis", 3)             # Basis9 -> Basis6
    ui.select_field("global-shuffle-amount", offset=1)
    ui.set_value(-101)
    ui.press_key(3)
    ui.set_value(100)
    ui.press_key(3)
    _open_clock_page(c)
    ui.select_field("local-shuffle-type", offset=1)             # initially X
    stages=[('untouched-X',None,True),('local-Swing',1,False),
            ('explicit-X-from-Swing',-1,True),('local-Shuffle',2,True),
            ('explicit-X-from-Shuffle',-2,True)]
    for label,delta,shuffled in stages:
        if delta is not None:
            ui.set_value(delta)
            ui.press_key(3)
        before=c.snapshot()['midi_count']
        notes=c.playback([(1,[144,n,v]) for n,v in ((60,127),(62,117),(64,107),(65,97))],cycles=4,timeout=8)
        events=[e for e in c.snapshot()['midi'] if e['index']>before]
        pairs=note_pairs(events)
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        planned=[96*(i//4)+(0,16,32,48)[i%4] if shuffled else 24*i for i in range(len(notes))]
        errors=[(note[field]-notes[0][field])/1e9-pulse/144 for note,pulse in zip(notes,planned)]
        assert max(map(abs,errors))<=tolerance,dict(stage=label,expected_pulses=planned,errors=errors)
        for note,nxt in zip(notes,notes[1:]):
            off=next(e for e in events if e['index']>note['index'] and e['bytes']==[128,note['bytes'][1],note['bytes'][2]])
            assert abs(off[field]-nxt[field])/1e9<=tolerance
        c.results.append(dict(kind='shuffle-type-inheritance',stage=label,expected_pulses=planned,onsets=len(notes),release_pairs=len(pairs),passed=True))


def live_shuffle_type_inheritance(c,override=False):
    from midi_window import MidiWindow
    from note_accounting import note_pairs

    ui = c.ui
    ui.configure()
    ui.menu("song_editor")
    ui.turn(1, 1)
    _set_clock_field(ui, "global-shuffle-type", 1)
    _set_clock_field(ui, "global-shuffle-feel", 2)
    _set_clock_field(ui, "global-shuffle-basis", 3)
    ui.select_field("global-shuffle-amount", offset=1)
    ui.set_value(-101)
    ui.press_key(3)
    ui.set_value(100)
    ui.press_key(3)
    _open_clock_page(c)
    ui.select_field("local-shuffle-type", offset=1)
    ui.set_value(0 if override else 1)
    ui.press_key(3)                                           # Start inherited Shuffle or explicit Swing.
    capture=MidiWindow(c.snapshot()['midi_count'])
    ui.play()
    c.elapse(2)
    capture.extend(c.snapshot())
    ui.set_value(1 if override else -1)
    ui.press_key(3)                                           # Set Swing or restore X; commit at global step64.
    c.wait(lambda state:capture.extend(state) and len(capture.note_ons())>=85,timeout=20)
    ui.stop()
    c.wait(lambda state:capture.extend(state) and not state['midi_capture']['outstanding'])
    notes=capture.note_ons();pairs=note_pairs(capture.events)
    assert len(notes)>=85 and len(pairs)==len(notes)
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    # Global64 steps *24 pulses =1536. A four-step local loop must not commit
    # the edit early. From the boundary Heavy6 repeats16,16,16,48 pulses.
    pulses=[24*i if i<64 else 1536+96*((i-64)//4)+(0,16,32,48)[(i-64)%4] for i in range(len(notes))]
    if override:
        pulses=[96*(i//4)+(0,16,32,48)[i%4] if i<64 else 1536+24*(i-64) for i in range(len(notes))]
    checks=[]
    for i,(note,pulse) in enumerate(zip(notes,pulses)):
        assert (note['port'],note['bytes'])==(1,[144,(60,62,64,65)[i%4],(127,117,107,97)[i%4]])
        error=(note[field]-notes[0][field])/1e9-pulse/144
        checks.append(dict(index=i,expected_pulse=pulse,error_seconds=error))
        assert abs(error)<=tolerance,checks[-1]
    for note,nxt in zip(notes,notes[1:]):
        off=next(e for e in capture.events if e['index']>note['index'] and e['bytes']==[128,note['bytes'][1],note['bytes'][2]])
        assert abs(off[field]-nxt[field])/1e9<=tolerance
    c.results.append(dict(kind='live-shuffle-inheritance',override=override,boundary_pulse=1536,onsets=len(notes),release_pairs=len(pairs),checks=checks,passed=True))
