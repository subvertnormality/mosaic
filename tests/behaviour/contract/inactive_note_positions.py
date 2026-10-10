from contract.duration_assertions import assert_durations

def inactive_note_positions(c):
    c.ui.configure();c.ui.set_range(1,64);c.ui.pattern_editor(view='trigger')
    for x in range(1,5):c.ui.tap_step(x)
    c.ui.tap_control('pattern_select',3);c.ui.pattern_editor(view='note',from_view='trigger')
    pitches=[60,62,64,65,67,69,71]
    cells=[((s-1)%16+1,(s-1)//16+4) for s in range(1,65)]
    for page in range(4):
        c.ui.tap_control('pattern_group',page+1)
        selections=[(x,7-((page*16+x-1)%7)) for x in range(1,17)]
        for x,y in selections:c.ui.tap_control('pattern_note_degree',(x,7-y))
        # Characterisation, not manual text: selected pattern 3 blinks on row 1.
        # A selected note at that cell is 11/13; all other selected notes stay 12.
        steady=[cell for cell in selections if cell != (3,1)]
        c.led_values(steady,[12]*len(steady))
        if (3,1) in selections:
            state=c.wait(lambda state: state['grid'][2] in (11,13))
            c.results.append(dict(kind='selected-note-pattern-blink',cell=[3,1],
                                  allowed=[11,13],actual=state['grid'][2],passed=True))
    c.ui.tap_control('channel_editor');c.ui.tap_control('pattern_slot',1);c.ui.tap_control('pattern_slot',3)
    def silence(label):
        c.led_values(cells,[2]*64)
        before=c.snapshot()['midi_count'];c.ui.play();c.elapse(64/3+.1);c.ui.stop()
        state=c.snapshot();notes=[m for m in state['midi'] if m['index']>before and 144<=m['bytes'][0]<=159 and m['bytes'][2]>0]
        assert not notes and not state['midi_capture']['outstanding'],notes
        c.results.append(dict(kind='inactive-position-silence',phase=label,steps=64,complete_cycles=2,passed=True))
    def phrase(label):
        expected=[(1,[144,pitches[(s-1)%7],100]) for s in range(1,65)]
        notes=c.playback(expected,cycles=2,timeout=4,settle_seconds=64/3-.1)
        assert_durations(c,notes,[1]*128)
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        errors=[(b[field]-a[field])/1e9-1/6 for a,b in zip(notes,notes[1:])]
        assert len(errors)>=128 and all(abs(x)<=(2e-9 if c.clock_mode=='controlled-experimental' else .01) for x in errors),errors
        c.results.append(dict(kind='inactive-position-playback',phase=label,steps=64,complete_cycles=2,max_spacing_error_seconds=max(abs(x) for x in errors),passed=True))
    silence('all64-authored-without-trigs')
    c.ui.pattern_editor(view='note');c.ui.tap_control('pattern_select',2)
    for x,y in cells:c.ui.tap_control('pattern_note_degree',(x,7-y))
    c.led_values(cells,[15]*64);c.ui.tap_control('channel_editor');c.ui.tap_control('pattern_slot',3);c.ui.tap_control('pattern_slot',2)
    c.ui.hold_control_tap('note_merge_mode','pattern_slot',None,3);c.ui.expect_leds({("pattern_slot",3):"off",("pattern_slot",2):"selected",("note_merge_mode",None):"selected"})
    phrase('unassigned-priority-source-all64')
    c.ui.tap_control('pattern_slot',3);phrase('assigned-inactive-priority-source-all64')
    c.ui.tap_control('pattern_slot',2);c.ui.pattern_editor(view='note');c.ui.tap_control('pattern_select',3)
    for x,y in cells:c.ui.tap_control('pattern_note_degree',(x,7-y))
    c.led_values(cells,[15]*64);c.ui.tap_control('channel_editor');phrase('all64-later-activated')
    c.ui.pattern_editor(view='note')
    for x,y in cells:c.ui.tap_control('pattern_note_degree',(x,7-y))
    c.ui.tap_control('channel_editor');silence('all64-trigs-removed-again')
