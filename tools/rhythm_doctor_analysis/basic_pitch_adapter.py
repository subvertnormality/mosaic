"""Basic Pitch 0.4.0 output coordinates; diagnostic adapter, not a model.

Frame-time formula derives from Spotify AB's Apache-2.0 licensed
basic_pitch/note_creation.py:model_frames_to_time (copyright 2022 Spotify AB).
https://github.com/spotify/basic-pitch/blob/v0.4.0/basic_pitch/note_creation.py
See licenses/basic-pitch-LICENSE.txt and basic-pitch-NOTICE.txt.
The upstream window correction is retained exactly; bounds checks are local.
"""


def midi_pitch_slice(low, high):
    """Inclusive MIDI range into the 88 note/onset columns beginning at A0."""
    if type(low) is not int or type(high) is not int or not 21 <= low <= high <= 108:
        raise ValueError('pitch range must be integer MIDI notes 21..108')
    return slice(low - 21, high - 21 + 1)


def frame_time(frame):
    """Seconds using the pinned upstream model's cumulative window correction."""
    if type(frame) is not int or frame < 0:
        raise ValueError('frame must be a nonnegative integer')
    rate, hop, annotation_frames = 22050, 256, 172
    audio_samples = rate * 2 - hop
    offset = (hop / rate) * (annotation_frames - audio_samples / hop) + .0018
    return frame * hop / rate - (frame // annotation_frames) * offset
