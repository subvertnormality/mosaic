"""The lane set the remote analysis server produces.

Ten lanes against the local backend's three. Five come from LarsNet applied to
the drums stem, which separates a kit into its pieces rather than guessing at
them from a full mix; five are the remaining htdemucs_6s stems, each reduced to
onsets and velocity.

No pitch. The melodic stems contribute rhythm, not notes: Mosaic's bank stores
a gate and a velocity per cell and has nowhere to put a note number, so
transcribing one would be work whose result is discarded. That also keeps the
server free of a transcription model and its licence.
"""
from __future__ import annotations

# LarsNet separates the drums stem into these five.
DRUM_LANES = ("KICK", "SNARE", "TOMS", "HIHAT", "CYMBALS")

# The remaining htdemucs_6s stems. "OTHER" is demucs' own residual: whatever
# the five named stems did not claim, which in practice is synths and pads.
MELODIC_LANES = ("BASS", "GUITAR", "PIANO", "VOCALS", "OTHER")

# Without LarsNet the drums stem stays whole. That is a worse result -- one
# lane where there could be five -- but it is still six lanes against the
# device's three, and it keeps the server usable for anyone who cannot accept
# the CC BY-NC 4.0 licence on LarsNet's checkpoints.
UNSPLIT_DRUM_LANES = ("DRUMS",)

LANES = DRUM_LANES + MELODIC_LANES


def lane_set(drum_split: bool = True):
    """The lanes this server produces, given whether the kit can be split."""
    return (DRUM_LANES if drum_split else UNSPLIT_DRUM_LANES) + MELODIC_LANES


def gates_for(names) -> dict:
    """Default onset gates for a lane set."""
    return {lane: DEFAULT_GATE.get(lane, 0.30) for lane in names}

# htdemucs_6s stem names, in the order the model emits them.
DEMUCS_STEMS = ("drums", "bass", "other", "vocals", "guitar", "piano")

# Which stem feeds each melodic lane.
STEM_FOR_LANE = {"BASS": "bass", "GUITAR": "guitar", "PIANO": "piano",
                 "VOCALS": "vocals", "OTHER": "other"}

# Onset gates per lane. Drum lanes come from a separator that has already
# decided what is a kick, so they can sit low; melodic lanes are onset-detected
# from a stem that sustains between attacks, so they need more evidence before
# a gate is claimed.
DEFAULT_GATE = dict(
    [(lane, 0.30) for lane in DRUM_LANES] + [(lane, 0.45) for lane in MELODIC_LANES]
    + [(lane, 0.30) for lane in UNSPLIT_DRUM_LANES])

# Every lane the server can ever emit, split or unsplit, needs exactly one gate.
ALL_LANES = DRUM_LANES + UNSPLIT_DRUM_LANES + MELODIC_LANES
assert set(DEFAULT_GATE) == set(ALL_LANES), "every lane needs exactly one gate"
assert len(set(ALL_LANES)) == len(ALL_LANES), "lane names must be unique"
assert set(STEM_FOR_LANE) == set(MELODIC_LANES), "every melodic lane needs a stem"
assert set(STEM_FOR_LANE.values()) <= set(DEMUCS_STEMS), "stems must exist in htdemucs_6s"
