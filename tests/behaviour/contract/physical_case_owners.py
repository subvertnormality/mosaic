"""Contract-owned registry entrypoints for nine exact classifier cases.

These wrappers retain the established public scenarios and forward the same
arguments; they make the registry's physical contract ownership explicit.
"""
from trig_parameter_interactions import live_parameter_recording


def editor_hold_boundaries(c):
    # Keep the original measured public-input recipe and all of its assertions.
    from cases import editor_hold_boundaries as existing_recipe
    return existing_recipe(c)


def live_parameter_recording_with_visual_checkpoints(c):
    return live_parameter_recording(c, visual_checkpoints=True)


def live_parameter_recording_switch_return(c):
    return live_parameter_recording(c, switch_return=True)


def live_parameter_recording_empty_step(c):
    return live_parameter_recording(c, empty_step=True)


def live_parameter_recording_edit_zero(c):
    return live_parameter_recording(c, edit_value=0)


def live_parameter_recording_edit_off(c):
    return live_parameter_recording(c, edit_value=-1)


def live_parameter_recording_empty_step_trigless_off(c):
    return live_parameter_recording(c, empty_step=True, trigless=False)


def live_parameter_recording_probability_zero_trigless_off(c):
    return live_parameter_recording(c, probability_zero=True, trigless=False)
