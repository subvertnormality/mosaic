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

LANES = DRUM_LANES + MELODIC_LANES

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
    [(lane, 0.30) for lane in DRUM_LANES] + [(lane, 0.45) for lane in MELODIC_LANES])

assert set(DEFAULT_GATE) == set(LANES), "every lane needs exactly one gate"
assert set(STEM_FOR_LANE) == set(MELODIC_LANES), "every melodic lane needs a stem"
assert set(STEM_FOR_LANE.values()) <= set(DEMUCS_STEMS), "stems must exist in htdemucs_6s"
