"""Adapters for the three pretrained models, loaded lazily.

Nothing here is imported at module scope. The contract, the pipeline and the
HTTP layer are all testable without a GPU or several gigabytes of weights, and
a server started without the models installed reports that clearly instead of
failing to start.

Licences, because they differ and it matters:
  htdemucs_6s (Demucs)  MIT
  LarsNet               check before redistributing; used here as a dependency
  Beat This!            MIT, for the code AND the published weights

Beat This! is used rather than madmom deliberately. madmom's code is BSD but
its model files are CC BY-NC-SA, which makes commercial use conditional on
permission from the authors; Beat This! is MIT throughout and is the stronger
tracker.
"""
from __future__ import annotations

import numpy as np

SR = 44100


class ModelUnavailable(RuntimeError):
    """A model was asked for and is not installed."""


def load_demucs(name: str = "htdemucs_6s"):
    """Six-stem separation: drums, bass, other, vocals, guitar, piano."""
    try:
        import torch
        from demucs.apply import apply_model
        from demucs.pretrained import get_model
    except ImportError as error:                      # pragma: no cover - env
        raise ModelUnavailable("demucs is not installed: %s" % error) from error
    model = get_model(name)
    model.eval()
    sources = list(model.sources)

    def separate(mono: np.ndarray, sample_rate: int) -> dict[str, np.ndarray]:
        if sample_rate != model.samplerate:
            raise ValueError("demucs expects %d Hz" % model.samplerate)
        # Demucs is a stereo model; a mono capture is presented as two
        # identical channels rather than resampled or padded with silence.
        wave = torch.tensor(np.stack([mono, mono]), dtype=torch.float32)[None]
        with torch.no_grad():
            out = apply_model(model, wave, split=True, overlap=0.25, progress=False)[0]
        return {name: out[index].mean(dim=0).cpu().numpy().astype(np.float32)
                for index, name in enumerate(sources)}

    return separate, {"separator": name, "separator_sources": ",".join(sources)}


def load_larsnet(checkpoint: str | None = None):
    """Drum-kit separation: kick, snare, toms, hihat, cymbals."""
    try:
        import torch
        from larsnet import LarsNet                   # pragma: no cover - env
    except ImportError as error:                      # pragma: no cover - env
        raise ModelUnavailable("larsnet is not installed: %s" % error) from error
    model = LarsNet.from_checkpoint(checkpoint) if checkpoint else LarsNet.pretrained()
    model.eval()

    def separate_drums(drums: np.ndarray, sample_rate: int) -> dict[str, np.ndarray]:
        wave = torch.tensor(np.stack([drums, drums]), dtype=torch.float32)[None]
        with torch.no_grad():
            pieces = model(wave)
        return {name: piece[0].mean(dim=0).cpu().numpy().astype(np.float32)
                for name, piece in pieces.items()}

    return separate_drums, {"drum_separator": "larsnet"}


def load_beat_this(checkpoint: str = "final0"):
    """Joint beat and downbeat tracking on the mix."""
    try:
        from beat_this.inference import File2Beats    # pragma: no cover - env
    except ImportError as error:                      # pragma: no cover - env
        raise ModelUnavailable("beat_this is not installed: %s" % error) from error
    tracker = File2Beats(checkpoint_path=checkpoint, dbn=False)

    def track_beats(mono: np.ndarray, sample_rate: int) -> tuple[list[int], list[int]]:
        beats, downbeats = tracker(mono, sample_rate)
        return ([int(round(t * sample_rate)) for t in beats],
                [int(round(t * sample_rate)) for t in downbeats])

    return track_beats, {"beat_tracker": "beat_this:" + checkpoint}
