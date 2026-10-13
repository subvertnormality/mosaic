"""Navigation-contract adapters for the recording-lifetime MIDI workflows."""

from recording_lifetimes import recording_lifetime


def stop(c):
    return recording_lifetime(c, "stop")


def nonselected_wrap(c):
    return recording_lifetime(c, "nonselected-wrap", scale_page=True)
