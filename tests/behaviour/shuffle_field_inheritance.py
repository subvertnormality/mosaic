"""Local sentinel round trips with nondefault global musical settings."""


def shuffle_field_inheritance(c, field):
    from shuffle_matrix import pulse_plan
    from note_accounting import note_pairs

    assert field in ('feel', 'basis', 'amount')
    ui = c.ui
    ui.configure()
    ui.song_editor()
    ui.turn(1, 1)                                                # original Song Editor E1 +1

    def set_clock_field(name, offset, value):
        ui.select_field(name, offset=offset)
        ui.set_value(value)
        ui.press_key(3)

    set_clock_field('shuffle', 1, 1)                             # Shuffle.
    set_clock_field('feel', 1, 2)                                # Heavy.
    set_clock_field('basis', 1, 3)                               # Basis 6.
    ui.select_field('amount', offset=1)
    ui.set_value(-101)
    ui.press_key(3)
    ui.set_value(50)
    ui.press_key(3)

    ui.menu('channel_editor')
    # The source has no screen_header oracle here; preserve only the E1 -1.
    ui.channel_page('clock_mods', 'midi_config', channel=1, confirm=False)
    ui.select_field(field, offset={'feel': 2, 'basis': 3, 'amount': 4}[field])
    maximum = {'feel': 4, 'basis': 6, 'amount': 100}[field]
    previous = 0
    for label, value in [('untouched-X', 0), ('minimum-override', 1), ('maximum-override', maximum), ('restored-X', 0)]:
        if label != 'untouched-X':
            ui.set_value(value - previous)
            ui.press_key(3)
        previous = value
        feel, basis, amount = 'Heavy', 4, 50
        if value:
            if field == 'feel':
                feel = ('Drunk', 'Smooth', 'Heavy', 'Clave')[value - 1]
            elif field == 'basis':
                basis = value
            else:
                amount = value
        before = c.snapshot()['midi_count']
        notes = c.playback([(1, [144, n, v]) for n, v in ((60, 127), (62, 117), (64, 107), (65, 97))], cycles=4, timeout=8)
        events = [e for e in c.snapshot()['midi'] if e['index'] > before]
        pairs = note_pairs(events)
        assert len(pairs) == sum(e['bytes'][0] == 144 and e['bytes'][2] > 0 for e in events)
        clock_field = 'logical_ns' if c.clock_mode == 'controlled-experimental' else 'monotonic_ns'
        tolerance = 2e-9 if c.clock_mode == 'controlled-experimental' else .01
        pulses = pulse_plan(feel, basis, amount, len(notes))
        errors = [(n[clock_field] - notes[0][clock_field]) / 1e9 - pulse / 144 for n, pulse in zip(notes, pulses)]
        assert max(map(abs, errors)) <= tolerance, dict(field=field, stage=label, expected=pulses, errors=errors)
        for n, nxt in zip(notes, notes[1:]):
            off = next(e for e in events if e['index'] > n['index'] and e['bytes'] == [128, n['bytes'][1], n['bytes'][2]])
            assert abs(off[clock_field] - nxt[clock_field]) / 1e9 <= tolerance
        c.results.append(dict(kind='shuffle-field-inheritance', field=field, stage=label, local_value=value, effective_feel=feel, effective_basis=basis, effective_amount=amount, onsets=len(notes), release_pairs=len(pairs), max_phase_error_seconds=max(map(abs, errors)), passed=True))
