"""Literal rendered selector bounds for the three chord division parameters
(the selected slot's value on the live Trig params full value line)."""


def parameter_division_bounds(c,parameter):
    parameter_label=c.ui.trig_parameter_label(parameter)
    def label(value):
        # The selected slot's whole value on the Trig params overview's full
        # value line (C02), beside the assigned parameter's name.
        c.ui.expect_selected_field('overview_params',label=parameter_label,value=value)
        c.results.append(dict(kind='parameter-division-label',parameter=parameter_label,value=value,passed=True))
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
