"""Literal rendered selector bounds for the three chord division parameters."""


def parameter_division_bounds(c,parameter):
    import base64
    from frame_oracle import render
    parameter_label=c.ui.trig_parameter_label(parameter)
    def label(value):
        expected=render([(0,25,15,value)])
        indices=[(y*128+x)*4+k for y in range(19,27) for x in range(24) for k in range(3)]
        def matches(state):
            actual=base64.b64decode(state['frame']['pixels_base64'])
            return all(actual[i]==expected[i] for i in indices)
        c.wait(matches);c.results.append(dict(kind='parameter-division-label',parameter=parameter_label,value=value,passed=True))
    c.configure();c.ui.turn(1,-3);c.ui.assign_trig_parameter_key(parameter)
    label('X');c.ui.set_value(-3);label('X')
    c.ui.set_value(1);label('1/24');c.ui.set_value(88);label('128')
    c.ui.set_value(3);label('128')
    c.ui.set_value(-1);label('120');c.ui.set_value(-88);label('X')


def chord_note_strum_divisions(c):
    return parameter_division_bounds(c, 'chord_note_strum')


def chord_note_arpeggio_divisions(c):
    return parameter_division_bounds(c, 'chord_note_arpeggio')


def chord_spread_divisions(c):
    return parameter_division_bounds(c, 'chord_spread')
