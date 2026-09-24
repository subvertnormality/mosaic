"""Adapters for the three pretrained models, loaded lazily.

Nothing here is imported at module scope. The contract, the pipeline and the
HTTP layer are all testable without a GPU or several gigabytes of weights, and
a server started without the models installed reports that clearly instead of
failing to start.

Licences, because they differ and one of them constrains what you may do:

  htdemucs_6s (Demucs)   MIT
  Beat This!             MIT, for the code AND the published weights
  LarsNet checkpoints    CC BY-NC 4.0 -- NON-COMMERCIAL

The LarsNet weights are the drum-splitting half of this server, and they are
licensed for non-commercial use only. Everything still runs without them: the
server falls back to the drums stem as a single lane and the melodic lanes are
unaffected, which is what `--no-drum-split` produces. Read that licence before
building anything commercial on this.

Beat This! is used rather than madmom deliberately, for the same reason:
madmom's code is BSD but its model files are CC BY-NC-SA, so commercial use is
conditional on the authors' permission. Beat This! is MIT throughout and is
the stronger tracker.
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


def load_larsnet(repository: str | None = None, config: str = "config.yaml",
                 device: str = "cpu"):
    """Drum-kit separation: kick, snare, toms, hihat, cymbals.

    LarsNet is not on PyPI and is not importable as a package: it is a
    repository with a config file naming its checkpoints. The directory has to
    be on sys.path and the pretrained weights downloaded into it separately.
    The checkpoints are CC BY-NC 4.0; see the module docstring.
    """
    import os
    import sys
    root = repository or os.environ.get("LARSNET_ROOT", "")
    if not root or not os.path.isdir(root):
        raise ModelUnavailable(
            "larsnet repository not found; clone it and set LARSNET_ROOT")
    if root not in sys.path:
        sys.path.insert(0, root)
    try:
        import torch
        from larsnet import LarsNet                   # pragma: no cover - env
    except ImportError as error:                      # pragma: no cover - env
        raise ModelUnavailable("larsnet is not importable: %s" % error) from error
    config_path = config if os.path.isabs(config) else os.path.join(root, config)
    if not os.path.isfile(config_path):
        raise ModelUnavailable("larsnet config not found: %s" % config_path)
    # The checkpoint paths in config.yaml are relative, and LarsNet resolves
    # them against the CURRENT WORKING DIRECTORY rather than against the config
    # file. Changing directory would fix it for one call and corrupt every
    # other thread in this server, so the paths are made absolute in a copy of
    # the config instead.
    import tempfile
    import yaml
    with open(config_path, "r", encoding="utf-8") as handle:
        settings = yaml.safe_load(handle)
    checkpoints = settings.get("inference_models") or {}
    for stem, relative in list(checkpoints.items()):
        absolute = relative if os.path.isabs(relative) else os.path.join(root, relative)
        if not os.path.isfile(absolute):
            raise ModelUnavailable(
                "larsnet checkpoint missing for %s: %s -- run fetch_models.py" % (stem, absolute))
        checkpoints[stem] = absolute
    settings["inference_models"] = checkpoints
    handle = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8")
    yaml.safe_dump(settings, handle)
    handle.close()
    try:
        model = LarsNet(config=handle.name, device=device)
    finally:
        os.unlink(handle.name)
    model.eval()

    def separate_drums(drums: np.ndarray, sample_rate: int) -> dict[str, np.ndarray]:
        # LarsNet takes (channels, samples) and returns {stem: (channels, samples)}.
        # It is a stereo model, so a mono drums stem is presented as two
        # identical channels and the result is collapsed back to mono.
        wave = torch.tensor(np.stack([drums, drums]), dtype=torch.float32)
        with torch.no_grad():
            pieces = model(wave)
        out = {}
        for name, piece in pieces.items():
            value = piece.detach().cpu().numpy()
            out[name.lower()] = (value.mean(axis=0) if value.ndim == 2 else value).astype(np.float32)
        return out

    return separate_drums, {"drum_separator": "larsnet", "drum_separator_config": config}


def load_beat_this(checkpoint: str = "final0", device: str = "cpu"):
    """Joint beat and downbeat tracking on the mix.

    Audio2Beats, not File2Beats: the capture is already in memory and
    File2Beats only accepts a path. dbn=False keeps madmom out of the
    dependency list, which matters because madmom's model files are
    CC BY-NC-SA and Beat This! without the DBN is the published configuration
    anyway.
    """
    try:
        from beat_this.inference import Audio2Beats   # pragma: no cover - env
    except ImportError as error:                      # pragma: no cover - env
        raise ModelUnavailable("beat_this is not installed: %s" % error) from error
    tracker = Audio2Beats(checkpoint_path=checkpoint, device=device, dbn=False)

    def track_beats(mono: np.ndarray, sample_rate: int) -> tuple[list[int], list[int]]:
        # Returns positions in SECONDS; the rest of the pipeline works in
        # samples of the original capture.
        beats, downbeats = tracker(mono, sample_rate)
        return ([int(round(float(t) * sample_rate)) for t in beats],
                [int(round(float(t) * sample_rate)) for t in downbeats])

    return track_beats, {"beat_tracker": "beat_this:" + checkpoint}
