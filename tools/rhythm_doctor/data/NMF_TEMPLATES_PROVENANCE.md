# NMF drum template provenance

`nmf_drum_templates.npz` contains the three fixed drum spectral templates
(BD, SD, CHH) used by `dsp_drum_backend.py`.

**Source:** the `WD` dictionary shipped as `src/DefaultSetting.mat` in
[cwu307/NmfDrumToolbox](https://github.com/cwu307/NmfDrumToolbox), the reference
implementation accompanying:

> C.-W. Wu and A. Lerch, "Drum Transcription using Partially Fixed Non-Negative
> Matrix Factorization", ISMIR 2015.

**Licence:** NmfDrumToolbox is **GPL-3.0**. Mosaic is also GPL-3.0, so the
templates are redistributed here under GPL-3.0 with attribution. This is a
licence-compatible reuse, not an independent derivation.

**What was changed:** the three columns were reordered to BD, SD, CHH by
ascending spectral centroid (the toolbox stores them HH, BD, SD) and each
column was L2-normalised. No values were otherwise altered.

**Geometry:** the templates are magnitude-STFT columns for a 2048-sample window
at 512 hop, 44.1 kHz. Using any other STFT geometry invalidates them.
