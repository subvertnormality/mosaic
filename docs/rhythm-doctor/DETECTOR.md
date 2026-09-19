# RD-02 candidate A diagnostic

The earlier `detector-diagnostic/` result is retained as an **invalid pilot
harness outcome**, not a model-quality failure: it scored whole-song references
against 20-second predictions, emitted dense frame predictions instead of
onsets, used a non-maximal matcher and averaged stereo channels. Do not cite its
scores or model hash as empirical architecture evidence.

The replacement harness crops MIDI-render references to the analyzed interval,
uses the independent `quality.onset_score` one-to-one 50 ms scorer, fixed
source-disjoint 9/11 tracks, dev-only threshold selection with peak/refractory
conversion, stereo magnitude features (phase-inversion invariant), and explicit
low-frequency harmonic bass support. Raw labels come from MIDI note maps plus
metadata `inst_class: Bass`, never predictions.

## Current scope — 2026-09-19

The active feature scope is BD, SD, CHH, OHH and BASS. CHH and OHH require
separate labels, predictions and all acceptance gates; historical combined `HH`
does not satisfy either. TOM is no longer an active lane. The measurements below
retain their original HH/TOM names and values because they are historical
diagnostics, not evidence for the amended scope. They must not be relabelled,
split, or aggregated into a current acceptance claim.

`rd02-preliminary-v1` is a 80-crop full-mixture pilot only. Its missing
isolated/sparse/source-kit strata mean no result is acceptance evidence and the
harness reports `acceptance_claimed: false`; it does not report a grid-F1 gate.
Frozen BabySlakh archive SHA-256 is
`6490dc83d8b59ccbe7e9e0304023af8e585d2065f9a5f5921952a273fac4a9b0`.

## Pretrained-first decision — 2026-09-19

Rhythm Doctor must use frozen pretrained inference weights.  It must not train,
fine-tune, transfer-learn, or learn an output head as part of the product
architecture.  A development split may select fixed peak thresholds and the
versioned event/velocity decoder; the held partition remains untouched until
that configuration and every artifact hash are frozen.  The earlier Candidate-A
and ADTOF transfer experiments below are diagnostics, not the selected product
path.

The closest complete *label* fit is the published Omnizart drum checkpoint plus
the already-published Open-Unmix and Basic Pitch bass chain.  It is a concrete
research-worker architecture, not yet a standalone-norns selection.  In
particular, Omnizart's normal MIDI writer merges its three hat heads before
emitting one hi-hat lane.  The Mosaic adapter must consume the raw 13-head
activation tensor instead: output 0 is BD, 1 is SD, 4 is CHH (GM 42), and 6 is
OHH (GM 46).  Pedal HH (head 5 / GM 44) is discarded, never merged into either
required lane.  This is a frozen output adapter, not retraining.  The mapping is
defined in the upstream [label code](https://github.com/Music-and-Culture-Technology-Lab/omnizart/blob/main/omnizart/drum/labels.py);
the stock [inference code](https://github.com/Music-and-Culture-Technology-Lab/omnizart/blob/main/omnizart/drum/inference.py)
shows why its default three-lane MIDI output is insufficient.

The source mapping establishes the Keras checkpoint's label order; it does not
yet establish the tensor order of the separately published ONNX serialization.
The release includes `drum_keras@model.onnx`, which is the preferred portable
runtime candidate, but it must first pass a fixed-audio activation-parity test
against the source-defined heads before it supplies gates.  This is a conversion
identity check, not model training.

| Component | Pretrained artifact and labels | Published size | License/provenance | Runtime and selection |
| --- | --- | ---: | --- | --- |
| Omnizart `drum_keras` | The source Keras model has 13 raw drum heads; source heads 0/1/4/6 map to BD/SD/CHH/OHH. The release also supplies an ONNX serialization, whose tensor order must be proven equivalent before applying that mapping. | `drum_keras@model.onnx`: 31,048,009 bytes; downloaded SHA-256 `b6a2fd48850b3ef94fec3e2c97277ded6e3d366e7807a8ed2f0119b3da6e2d3f`. The alternative TF variable-data shard is 31,090,686 bytes. They are alternative serializations, not additive model size. The release supplies no checksum digest. | Source is MIT. The separately hosted checkpoint artifacts have no explicit licence or checksum digest, so source terms do not establish redistribution rights for the weights. | **Best drum research candidate; blocked.** The exact v0.4.2 CQT/beat frontend and bounded batch-one ONNX graph executed on an eight-second desktop fixture in 3.906 s + 2.897 s. Arena removal plus batch one reduced combined peak RSS from 1,216,540 KiB to 383,268 KiB; isolated inference was 147,036 KiB. Corrected batch-one and batch-32 tensors were bit-identical. This proves the graph/frontend path, not Keras parity or quality, and the x86 measurements do not prove ARMv7 norns headroom. |
| ADTOF-PyTorch | BD, SD and one HH class only; no separate CHH/OHH and no BASS. | 3,617,805 bytes. | The upstream ADTOF material is CC BY-NC-SA 4.0; the port/weight has no recorded compatible licence. | Rejected for active lanes and delivery.  Its executed old-corpus diagnostic also missed the quality gate; it remains useful only as historical evidence. |
| Open-Unmix UMXHQ BASS | Stereo bass stem, followed by a separate onset model; it does not create drum gates. | 35,637,796 bytes. | Open-Unmix source is MIT and the official Zenodo weight record declares MIT (`evidence/umxhq-official-license.json`). | **Pinned bass-separation candidate only.** The published `.pth` uses Torch/torchaudio and a three-layer bidirectional LSTM, so it is offline analysis and has no ARMv7/RSS/latency proof. Its separate magnitude-flux diagnostic F1 was 0.6098, below the gate; that is not a Basic Pitch-chain score. |
| Spotify Basic Pitch `nmp.tflite` | Instrument-agnostic pitched-note/onset activations; constrain its decoder to the declared bass range after separation, then retain onsets only. | 204,448 bytes. | The Basic Pitch repository is Apache-2.0 and distributes TF, TFLite and ONNX serializations together. | **Pinned BASS-onset candidate only.** It works best on one instrument at a time, so a mixture must not be sent directly to it. Existing corrected diagnostics concern the separately recorded 0.4.0 wheel/ONNX path and do not validate this TFLite serialization; no TFLite ARMv7 result exists. |
| DrumSep/MDX and Demucs families | Separation can yield BD/SD/HH-like stems, but no cited checkpoint supplies distinct CHH/OHH gates or BASS onset. | Not adopted. | The accessible DrumSep checkpoint has no original weight licence; Demucs does not supply the required five labels. | Rejected: adding separator(s) still leaves an instrument/onset classifier and exceeds the current norns evidence budget. |

The planned fixed pipeline is therefore: stereo capture -> immutable PCM ->
the release Omnizart ONNX candidate, after its Keras-head parity gate ->
independent BD/SD/CHH/OHH peak decoders, in parallel with Open-Unmix BASS
separation -> Basic Pitch TFLite bass-range onsets -> the common
timestamp/velocity/quantisation bank. No model result may be treated as a
velocity; a versioned attack-energy mapping supplies velocity after the gates.
All model calls occur after capture in an owned worker, never on the Lua UI or
audio callback.

This architecture has four release blockers. First, obtain a licence statement
and SHA-256 for the exact Omnizart ONNX asset; without them there is no
selectable legal drum weight. Second, prove Keras/ONNX raw-head parity and run
the adapter on the frozen v11 corpus, meeting every separate
BD/SD/CHH/OHH/BASS and stratum gate; an aggregate or combined-HH score cannot
substitute. Third, prove an ARMv7 norns worker with model/frontend parity,
cold/warm tail, incremental RSS and cancellation behavior. Neither
Python/TensorFlow/Torch nor a desktop measurement is such proof. Fourth, if
the UMXHQ/Basic-Pitch configuration misses the BASS gate, keep it as a failed
pretrained comparison; do not replace it with a newly trained native bass model
under this product decision.

Until those gates pass, expose this only as a separately named, opt-in local
computer research-worker profile with the same bank schema, never as local
norns transcription.  It must not upload audio or silently fall back to a
different model.  The primary-source observations and earlier identities are
preserved in `evidence/candidate_b_pretrained_research_2026-09-19.json`,
`evidence/umxhq-official-license.json`, and
`evidence/basic_pitch_adapter_corrected_v2.json`.

The implemented research-worker adapter is
`tools/rhythm_doctor/pretrained_composite_backend.py`. It accepts the standard
`--request` and `--result` worker arguments and requires a local runtime factory
through `RHYTHM_DOCTOR_PRETRAINED_RUNTIME_FACTORY`, formatted as
`/absolute/factory.py:callable`. The factory file is independently pinned by
`RHYTHM_DOCTOR_PRETRAINED_RUNTIME_FACTORY_SHA256`. Mosaic also requires the
backend executable, Omnizart drum artifact, and Open-Unmix/Basic Pitch bass
artifact identities through `RHYTHM_DOCTOR_ANALYSIS_BACKEND`,
`RHYTHM_DOCTOR_ANALYSIS_BACKEND_SHA256`,
`RHYTHM_DOCTOR_DRUM_ARTIFACT_SHA256`, and
`RHYTHM_DOCTOR_BASS_ARTIFACT_SHA256`. Partial configuration, a changed file, a
missing lane, or an identity mismatch fails closed. The adapter installs,
downloads, trains, and fine-tunes nothing; the operator must supply every frozen
local artifact and its runtime sessions explicitly.

The shipped model-free backend, `tools/rhythm_doctor/dsp_drum_backend.py`, uses
the second supported identity shape: it has no model artifacts, so it pins its
own source through `RHYTHM_DOCTOR_ANALYSIS_BACKEND_SHA256` and the published
NMF template table it reads through `RHYTHM_DOCTOR_TEMPLATE_SHA256`, alongside
`RHYTHM_DOCTOR_ANALYSIS_BACKEND`. A configuration must supply exactly one
complete shape: a template digest together with either model artifact digest is
rejected, as is half of either shape. Like the pretrained profile it is
unconfigured by default and downloads nothing.

`tools/rhythm_doctor/pretrained_bass_runtime.py` supplies the concrete pinned
desktop UMXHQ and Basic Pitch ONNX loaders used by that factory boundary. It
uses the UMXHQ centred-Hann STFT, magnitude mask and mixture-phase inverse STFT,
then Basic Pitch's mono polyphase-resampled frontend and published overlapping
ONNX windows. Basic Pitch's 88 output columns are mapped from MIDI offset 21,
so the BASS range MIDI 28..60 is columns 7..39. The executable model smoke and
resource result is recorded in
`evidence/omnizart-onnx-desktop-smoke-2026-09-19.json`; its synthetic fixture
and provisional gates are deliberately excluded from quality acceptance.
The concrete UMXHQ-to-Basic-Pitch execution smoke is separately recorded in
`evidence/pretrained-bass-desktop-smoke-2026-09-19.json`. Its sustained-sine
result proves the pinned sessions connect; it also confirms the decoder settings
still need the frozen five-lane corpus before they can become release gates.

The ready-to-inject factory is
`tools/rhythm_doctor/pretrained_runtime_factory.py:make`. In addition to the
worker's existing backend and factory pins, it requires local paths in
`RHYTHM_DOCTOR_OMNIZART_SOURCE`, `RHYTHM_DOCTOR_OMNIZART_ONNX`,
`RHYTHM_DOCTOR_UMXHQ_BASS`, and `RHYTHM_DOCTOR_BASIC_PITCH_ONNX`. It verifies
Omnizart source commit `0779fd5699be6605b9944ab3c5013af3c49f65df` and all
three artifact hashes before constructing sessions. Its named provisional
decoder gates exist for research execution only and cannot become release
defaults until the independent active-lane corpus passes.

The completed corrected 20-second pilot is immutable at
`tests/rhythm_doctor/artifacts/detector-pilot-corrected-v2/`, with raw
predictions and model SHA-256
`7312f19bb3cc502a0670535674cb88b6a06d0d40280280823b424897f09ac16e`.
Aggregate held event F1 was BD 0.7947, SD 0.2345, HH 0.5986, TOM 0.0000 and
BASS 0.7224. These are diagnostic pilot observations only; they do not satisfy
the required corpus inventory and do not establish a grid-F1 result.

A fresh longer-span pilot (`detector-pilot-longdev-v1/`) trained with 60 seconds
per development source and froze dev-only peak thresholds before the held pass.
It improved SD from 0.2345 to 0.5155, while BD/HH/BASS were 0.7485/0.6672/0.7412
and TOM remained 0.0000. The report's counts explain the TOM miss: only 24
development TOM references versus 588 BD, 412 SD, 1,692 HH and 826 BASS, and the
frozen model emitted one held TOM peak for 45 references. The model hash is
`a51a99de24c382f47222b7f4b2be4732c4ef52c22e35ec7186210058c6d3b750`.

The log-frequency/context experiment completed separately at
`detector-logfreq-v1/` with exit code 0 and model hash
`add40089583f74efe936d34c7529e6f453d1d4ef6989f81d584a6582b62c2424`.
Its held pilot F1 was BD 0.7451, SD 0.5639, HH 0.7160, TOM 0.0000 and BASS
0.6057. SD and HH improved over the coarse-band run, while BASS regressed and
TOM remained absent (3 predicted peaks for 45 references, after only 24 dev
references). This supports a data-coverage/class-imbalance diagnosis for TOM,
not a claim that temporal offset is the cause. The completed report predated
the new development-offset instrumentation, so it contains no valid offset mode;
the next bounded run must emit that diagnostic before changing feature alignment.

## Historical Candidate B comparison

This is the original metadata-only screen, retained to preserve its decision
context. Its statement that no Candidate-B weights were downloaded/executed was
true at that point only; later ADTOF, Open-Unmix and Basic Pitch diagnostics are
recorded below. It is superseded for architecture selection by the
pretrained-first decision above.

| Candidate | Evidence and fit | Decision |
| --- | --- | --- |
| ADTOF | The upstream repository distributes research material under CC BY-NC-SA 4.0, requires its dependency stack and makes its training data available on request. Its public description does not provide a frozen redistributable five-lane+BASS weight/runtime budget. | Not selected: no complete licence/weight/RSS provenance. |
| Demucs + drum/onset model | Demucs performs stem separation, not five-class drum transcription. Its upstream project requires PyTorch; no pinned small weight or <=256 MiB incremental-RSS evidence was found. Separation would also add a second drum and bass detector. | Rejected for this bounded local prototype before download. |
| Basic Pitch after bass separation | Spotify describes Basic Pitch as <20 MB peak memory and <17K parameters, but it transcribes arbitrary pitched instruments and its README says stereo input is downmixed to mono. It does not supply drums or source separation. | Potential BASS-only component after a separately validated stereo-safe separator; not a Candidate-B five-lane solution. |

Candidate B remains an explicit future benchmark: select frozen licence-compatible
weights, measure model plus feature/PCM peak RSS against 256 MiB on ARM, then
evaluate exactly the frozen held corpus without retuning. The Candidate-A pilot
does not establish either B's impossibility or its quality.

### Concrete pretrained follow-up, not a delivery selection

Metadata-only inspection found a complete **offline research-worker** chain:
[ADTOF-PyTorch](https://github.com/xavriley/ADTOF-pytorch) exposes bundled
3,617,805-byte weights and the MIDI classes 35 (BD), 38 (SD), 47 (TOM), 42
(HH), plus cymbal; its published dependencies are Torch, librosa and
pretty_midi. [Open-Unmix UMXHQ](https://github.com/sigsep/open-unmix-pytorch)
publishes a 35,637,796-byte bass-target weight; run that one target with a
residual, then send its bass waveform to [Basic Pitch's 204,448-byte TFLite
model](https://github.com/spotify/basic-pitch), constrained to bass frequencies.
Basic Pitch's source is Apache-2.0 and its documentation says it works best on
one instrument at a time, which is why it follows separation. The combined
published weights total 39,460,049 bytes. This historical note predates later
diagnostic downloads and must not be read as current asset state.

This is usable as a sharply defined next benchmark, not a standalone-norns
architecture yet. ADTOF-PyTorch has no LICENSE file in the inspected repository;
the upstream ADTOF repository is CC BY-NC-SA 4.0, so the port and its weight need
explicit compatible licensing before delivery. The earlier Open-Unmix weight
licence uncertainty is superseded: the official Zenodo record declares MIT
(`evidence/umxhq-official-license.json`). Both ADTOF-PyTorch and Open-Unmix require Python/Torch, while
the Basic Pitch Linux path requires TensorFlow Lite; no ARMv7 native worker,
incremental-RSS measurement or device latency measurement has been made. The
ADTOF and Open-Unmix networks are bidirectional, so this profile is final
offline analysis after capture rather than streaming inference.

RD-02's stop criterion therefore applies: do not call a five-lane standalone
feature feasible until the selected Omnizart raw-head drum checkpoint has
compatible frozen terms, the Omnizart/Open-Unmix/Basic-Pitch chain has a bounded
local norns worker, and the clean frozen corpus meets every per-lane and stratum
F1/grid/negative gate. The detailed URLs, HEAD byte counts, output mapping and
historical conditions are retained in
`docs/rhythm-doctor/evidence/candidate_b_pretrained_research_2026-09-19.json`.

### ADTOF-PyTorch executable diagnostic

The small ADTOF-PyTorch weight was evaluated without changing the held data or
thresholds. The frozen upstream frontend/model, 3,617,805-byte weight, isolated
CPU-only environment, activations and peak predictions are retained under
`tests/rhythm_doctor/artifacts/adtof-pilot-v2/`. Development-only thresholds
were frozen before the eleven held tracks were scored against independent source
MIDI at one-to-one 50 ms. Held F1 was BD 0.7319, SD 0.5767, HH 0.6343 and
TOM 0.0000 (0 TP, 29 FP, 45 FN). BASS and cymbal were deliberately not scored.
The full-source frontend pass took 248.97 seconds on desktop CPU; this is not
an ARM, incremental-RSS or latency claim.

This configuration therefore misses the old diagnostic's four-drum-lane gate,
but that pilot is not the clean acceptance corpus and does not decide the model
family's feasibility. Port/weight redistribution licensing is still unresolved.
Compact hashes and limitations are in
`docs/rhythm-doctor/evidence/candidate_b_adtof_pilot_v2.json`; the following
TOM audit preserves the original result and tests the mapping/reference boundary
before interpreting the zero score as a domain failure.

That read-only audit found the frozen upstream label order `[35, 38, 47, 42,
49]`; output class 47 is TOM and 42 is HH, so the adapter did not swap TOM and
HH. Held TOM references totalled 45 (29 note 43, 8 note 45, 2 note 47, 4 note
48 and 2 note 50). The positive-reference tracks emitted zero TOM predictions;
all 29 TOM false positives came from TOM-negative Track00019. Consequently no
reference had a nearby predicted TOM to indicate a global time offset. At the
frozen development threshold TOM was already weak (2 TP, 24 FP, 22 FN;
precision 0.0769, recall 0.0833). On the original aggregate DRUM stems, the
45 literal TOM times had median 30 ms post/pre RMS ratio 2.56; six coincided
with another drum onset within 50 ms, so that energy check cannot isolate every
tom. The audit supports a frozen model/domain failure rather than a discovered
mapping or universal timing error, while retaining its limitations. See
`docs/rhythm-doctor/evidence/candidate_b_adtof_tom_audit_v2.json`.

### ADTOF output-head transfer diagnostic

One bounded CPU-only transfer pass trained only the ADTOF output head (605
parameters) on all nine development songs. The backbone and original
3,617,805-byte checkpoint remained frozen. It used deterministic 10-second
development intervals, class-balanced binary cross entropy including TOM
positives, and development-only peak thresholds. The full run took 386.36
seconds, under its 600-second cap. The raw runner, input manifest, base weight,
tuned head, predictions, environment, and report are frozen under
`tests/rhythm_doctor/artifacts/adtof-transfer-v2/`.

This did not resolve TOM. Development F1 was BD 0.9141, SD 0.7141, HH 0.7227,
and TOM 0.0984. On the prior 11-track, 60-second diagnostic, whose data had
already been observed in earlier feasibility work, F1 was BD 0.8255, SD 0.5709,
HH 0.6390, and TOM 0.0290 (9 TP, 567 FP, 36 FN). The run did not use held
labels, thresholds, or intervals for training, but that old diagnostic is not
an untouched acceptance set. No BASS, grid-F1, ARM, incremental-RSS, latency,
or shipping-license claim follows. The hashes and exact limits are in
`docs/rhythm-doctor/evidence/candidate_b_adtof_transfer_v2.json`.

### ADTOF full-backbone priority-lane transfer diagnostic

A separate frozen run made all 449,741 ADTOF parameters trainable, but assigned
loss only to BD, SD, and HH. TOM and cymbal loss weights were zero, and TOM was
also absent from labels, thresholds, and metrics. The fixed epoch completed all
222 development intervals: 70.56 seconds of development frontend work and
363.87 seconds of training compute, below the 600-second cap. The full wall
time of 722.07 seconds includes the development and then fixed held evaluation.

On the old 11-track, 60-second diagnostic, BD reached F1 0.8170 (so it clears
the 0.80 onset threshold), SD reached 0.6083, and HH reached 0.7405. SD and HH
therefore miss the threshold, and this runner has no BASS or grid result, so it
does not establish the priority profile. The held set was already observed by
earlier feasibility work and is not an untouched acceptance set. Compact frozen
hashes, count tables, and limits are in
`docs/rhythm-doctor/evidence/candidate_b_adtof_fullbackbone_priority_v5.json`.

The development-to-held gap is largest for SD (0.7570 to 0.6083), while HH is
closer (0.7822 to 0.7405). A next development-only step should use a
predeclared song-level validation partition and fixed checkpoint schedule to
choose early stopping or regularization for SD generalization before another
longer full-backbone pass. It must not use the old held diagnostic to choose the
training configuration.

The bounded weak-template experiment has now completed as a separate Candidate-B
diagnostic. It selected development-only template windows from the original
aggregate `DRUM` stem only when source MIDI had no other drum lane within
150 ms and no preceding drum onset within 100 ms. It used original `BASS` stems
where source MIDI existed, then held those non-negative spectral templates fixed
during mixture activation inference. Peak thresholds were selected on the nine
development tracks only, before scoring the eleven held tracks with the
independent one-to-one 50 ms onset scorer.

The immutable v4 report is at
`tests/rhythm_doctor/artifacts/nmf-template-pilot-v4/report.json`; its frozen
source SHA-256 is
`b0a6f9def0d356f8ac159130f6f502cd9f5de2251bafdce20ae9387ec3aadf8c`.
Held pilot F1 was BD 0.5926, SD 0.2267, HH 0.3840, TOM 0.0080 and BASS 0.2784.
The Windows process peak working set was 283,553,792 bytes and wall time was
13.23 seconds for the 9/11 × 60-second diagnostic. That is total desktop-process
working set, not incremental RSS and not an ARM result; it cannot establish a
failure of the plan's <=256 MiB incremental-RSS gate. This is a failed
weak-template quality configuration, not evidence that all model-based
approaches are unworkable. It reports no grid-F1 or device inference result.
Development Track00017 had no exported
source BASS MIDI, so its bass template labels were excluded rather than
fabricated. Compact provenance and metrics are preserved in
`docs/rhythm-doctor/evidence/candidate_b_weak_template_v4.json`.

### UMXHQ BASS magnitude-flux diagnostic - rejected

The official UMXHQ BASS weight was also tested as a desktop-only BASS onset
component. The original OpenUnmix core and STFT/normalisation frontend were
executed from pinned upstream source; the local torchaudio compatibility shim is
recorded because the historical `complex_norm` export is absent in torchaudio
0.11. Flux-peak thresholds were selected only on eight valid old BabySlakh DEV
tracks. On eleven old diagnostic-held tracks, one-to-one 50 ms BASS scoring was
143 TP, 136 FP and 47 FN (precision 0.512545, recall 0.752632, F1 0.609808).
It fails the BASS gate and is not selected.

Track00017 is deliberately unscored. Its authoritative metadata lists S04 as
BASS, while the selected source MIDI inventory omits S04.mid, so an empty
reference would fabricate a negative. This test establishes neither ARM nor
norns performance, memory, latency, waveform reconstruction, or clean-corpus
quality. The compact result and frozen identities are in
`docs/rhythm-doctor/evidence/umxhq_bass_pilot_v2.json`.

### Basic Pitch decoder audit - adapter-invalid historical results

A subsequent independent upstream-wheel audit found three adapter errors:
raw pitch selection used MIDI 49..81 columns while claiming 28..60; both
paths omitted the upstream accumulating timestamp correction (over 100 ms
by frame 1720); and the official decoder's exclusive upper bound omitted
MIDI 60. Consequently these historical scores cannot reject Basic Pitch as
a bass architecture. The true-stem diagnostics reused these adapters and
share the limitation. Their raw artifacts remain unchanged.

The explicit pitch/time adapter now has three passing regressions; its
missing-module baseline, authoritative wheel hash and defect details are in
`evidence/basic-pitch-adapter-red.json`. The corrected cached-posterior diagnostic uses independent one-to-one scoring
and development-only configuration selection. Old diagnostic-held F1 is 0.482
for raw onset (112 TP, 163 FP, 78 FN) and 0.402 for the official decoder
(70 TP, 88 FP, 120 FN), still below the bass requirement. See
`evidence/basic_pitch_adapter_corrected_v2.json`. The corrected direct true-Bass
DEV-only oracle at those fixed settings reaches F1 0.558/raw and 0.523/decoder;
`evidence/basic_pitch_direct_oracle_corrected_v3.json` preserves all eight tracks,
including empty predictions. These measurements supersede the adapter-invalid
conclusions below; no clean-corpus or device result is claimed.

Historical configuration, retained for traceability:

Basic Pitch was evaluated only after UMXHQ produced an estimated-BASS waveform
from mixture magnitude and mixture phase. The raw-onset peak configuration and
the upstream `output_to_notes_polyphonic` decoder configuration were both
tuned on valid DEV tracks only and both failed the old diagnostic-held BASS
score. The official decoder was worse: 39 TP, 572 FP and 151 FN (F1 0.097378).
Track00017 remains unscored because its declared BASS MIDI is missing. These
results do not cover phase-inverted stereo input, ARM, norns timing, memory, or
the clean corpus. See
`docs/rhythm-doctor/evidence/basic_pitch_bass_decoder_pilot.json`.


A subsequent independent audit found that the NMF template selector discarded
unmapped percussion notes (crash, ride, etc.) before testing isolation. Its v4
results remain a real measurement of that configuration, but the claim that all
selected windows excluded other drum attacks was too strong. A literal MIDI
regression (kick at 0.50 s, crash at 0.55 s) failed before the fix. The selector
now retains non-output percussion for collision rejection while excluding it
from five-lane score references. No corrected NMF quality rerun is claimed yet.

## Frozen v12 held-out result for the pinned pretrained candidate (2026-09-19)

The pinned Omnizart raw-head plus Open-Unmix/Basic Pitch candidate was scored
once against the frozen v12 corpus. **It fails RD-02.** Fourteen of the fifteen
lane/stratum domains miss both the 0.80 onset gate and the 0.85 quantized-cell
gate. Only CHH/full_mix passes, at onset F1 0.8874. The full report is
`evidence/pretrained-v12-quality-2026-09-19.json` and the diagnosis is
`evidence/pretrained-v12-failure-diagnosis-2026-09-19.json`.

Held-out onset F1, gates selected from development clips only and then frozen:

| lane | isolated | sparse | full_mix |
| ---- | -------- | ------ | -------- |
| BD   | 0.4058 | 0.4968 | 0.7017 |
| SD   | 0.3043 | 0.4604 | 0.6871 |
| CHH  | 0.1407 | 0.5612 | 0.8874 |
| OHH  | 0.1739 | 0.1156 | 0.2574 |
| BASS | 0.3590 | 0.5943 | 0.3504 |

Per-lane held-out recall/precision: BD 0.667/0.643, SD 0.657/0.600,
CHH 0.899/0.727, OHH 0.339/0.176, BASS 0.314/0.502. Velocity MAE fails for
every lane and the gain ladders are not monotonic.

Three findings explain the failure.

1. **OHH collapses.** 189 true positives against 884 false positives. Raw head
   6 / GM 46 does not separate open hats from the rest of the hat family here.
2. **The drum heads leak across lanes.** Of all false positives, the share
   occurring on clips where that lane is absent is CHH 62.1%, SD 49.4%,
   BD 45.1%, OHH 21.2%, BASS 0.9%. This is why the isolated stratum scores
   *worse* than full_mix: in a single-lane clip every cross-fire is an
   unambiguous false positive, while in a full mix it can coincide with a real
   event. The inversion is a lane-discrimination failure, not a timing defect.
3. **BASS misses most onsets.** Recall 0.314, with almost no invention on
   BASS-absent clips (2 of 228 false positives).

Two hypotheses were examined and excluded. There is no systematic timing
offset: on `v12-isolated-0-BD` references sit at 0.0,1.0,...,7.0 s and
predictions at 0.99,1.99,...,6.99 s, a -10 ms difference well inside the 50 ms
tolerance that matches successfully. Gate selection is also not the cause: an
oracle threshold fitted directly on held-out data — a deliberately
non-deployable diagnostic, never used for any reported score — raises BD only
to 0.6684, SD to 0.6367, OHH to 0.2886 and BASS to 0.4863. Only CHH clears
0.80. No threshold choice makes this candidate pass.

No gate was weakened, no class relabelled, no threshold tuned on held-out data
for a reported score, and no model trained or replaced. A replacement
pretrained-only candidate would have to improve open-hat discrimination, drum
lane separation and bass recall at the same time.

### Mono downmix blindness to phase-inverted stereo

The pinned frontend loads audio with `mono=True`, so an exactly phase-inverted
stereo capture cancels to digital silence before the model sees it. Held-out
clip `v12-phase` has an interleaved peak of 7964 and a mono downmix of exactly
zero. Previously this crashed madmom's tempo estimator and aborted the whole
evaluation; the backend now stops before the frontend and paints nothing.
Across all 113 clips exactly four take that path — the three silence controls
and `v12-phase`, all held out — so no development clip and no audible mono
signal is affected. This is a real weakness of a mono-downmix drum chain and
`v12-phase` can only ever contribute false negatives.

## Licence test every candidate must pass

Mosaic is licensed GPL-3.0 (`LICENSE`, and README "released under the GNU
license"). That sets a harder constraint on pretrained models than a permissive
licence would, and it is the test to apply before spending evaluation effort on
any new candidate.

Assess the **code licence and the published weights licence separately**. They
frequently differ, and the weights are usually the restricted half. Omnizart is
the standing example: MIT source, with separately hosted checkpoints carrying no
explicit licence at all.

GPL-3 compatible: MIT, BSD, Apache-2.0 (compatible with GPLv3 specifically, not
GPLv2), LGPL, GPL-3, CC0.

Not compatible: any non-commercial or research-only restriction — CC BY-NC,
CC BY-NC-SA, "research use only", bespoke academic terms. GPL-3 forbids adding
use restrictions downstream, so a non-commercially licensed model cannot be a
dependency of this project. ADTOF was already excluded on exactly this ground:
its research material is CC BY-NC-SA 4.0, which is both non-commercial and a
conflicting copyleft.

That Mosaic is not operated commercially does not relax this. GPL-3 grants every
downstream recipient the right to use the program commercially, so depending on
a non-commercial model would contradict the licence the project itself grants.

Note which risk actually binds. Mosaic never redistributes weights — they are
gitignored and staged locally — so the weaker risk is redistribution. The
sharper risk is a **use restriction**, which binds even though nothing is
redistributed. Academic music-information-retrieval releases are the usual
source of such restrictions, so any separation-first candidate drawn from that
literature must have its weights licence established before evaluation, not
after. Treat an unverified or absent weights licence as a blocker to record, not
an unknown to set aside.

## Real-music transfer of the frozen candidate (2026-09-19)

The frozen pinned candidate was scored against MDB-Drums full mixes with the v12
**development** thresholds applied verbatim, so nothing was tuned on the new
corpus. Drum lanes only: MDB-Drums carries no bass and no velocity annotations.
Full report in `evidence/real-music-transfer-2026-09-19.json`.

| lane | real-music F1 | recall | precision | v12 full_mix F1 |
| ---- | ------------- | ------ | --------- | --------------- |
| BD   | 0.7973 | 0.8434 | 0.7560 | 0.7017 |
| SD   | 0.5688 | 0.4246 | 0.8610 | 0.6871 |
| CHH  | 0.4590 | 0.9762 | 0.3000 | 0.8874 |
| OHH  | 0.1693 | 0.8550 | 0.0940 | 0.2574 |

**The rendered corpus was misleading in both directions**, which is what the
domain-mismatch section of CORPUS.md warned about.

BD *improves* on real music, from 0.7017 to 0.7973, essentially at the 0.80
gate. Real records have consistent, well-produced kicks, and v12 was
understating the lane.

CHH *collapses*, from 0.8874 to 0.4590. Recall is near-perfect at 0.9762 but
precision is 0.3000 across 4,206 false positives. MDB-Drums contains 835 ride
and 126 crash onsets that are not CHH references, and the hat head answers
cymbals generally. v12's sparse two-kit material never exposed this. Painting a
ride hit into the closed-hat lane is a genuine product failure, not a scoring
artefact.

SD is precision-strong at 0.8610 and recall-poor at 0.4246, and the deficit is
almost entirely jazz brushwork.

### Performance is strongly genre-dependent

Recall only; per-track false positives were not retained, and CHH's precision
problem is present in both groups.

| group | tracks | BD | SD | CHH |
| ----- | ------ | -- | -- | --- |
| rock/pop/other | 15 | 0.8901 | 0.7639 | 0.9828 |
| jazz | 8 | 0.7790 | 0.2900 | 0.9386 |

Jazz supplies 1,900 of the 2,654 SD references and scores 0.2900 recall against
0.7639 for everything else, so it dominates the aggregate. Brushed and ghosted
jazz snare behaves as a different instrument. If the realistic capture is a
groove or break from rock, pop, funk or disco, the drum lanes are materially
better than the headline suggests.

One caveat must stay attached to these numbers. The thresholds are v12-selected,
which is what makes this an honest transfer test, but it means CHH's precision
failure is partly a gate calibrated for the wrong domain. Whether CHH is
recoverable with domain-appropriate gating or fundamentally confuses cymbals is
a separate question, and answering it must not become tuning on the evaluation
set.

## The closed-hat lane cannot be fixed with more templates (2026-09-19)

CHH is the weakest lane for **both** architectures, and they fail in the same
direction: the pinned pretrained chain scores 0.459 F1 on real music with 0.976
recall and 0.300 precision, and the classical-DSP backend scores 0.4374 with
0.8337 recall and 0.2965 precision. Recall is high; precision is the problem.
Ride and crash cymbals activate the hat lane.

The literature's recommended mitigation is a decoy template, so those events
compete for a column of their own. It was tried, using ride and crash samples
extracted from the corpus's own pinned Hydrogen commit, and it is **marginal**:
CHH precision moves from 0.4748 to 0.4935 and F1 from 0.6049 to 0.6144 on the
development half, while slightly costing BD. Full numbers in
`evidence/chh-cymbal-decoy-2026-09-19.json`.

The reason is physical, and it also explains why BD is the strongest lane.

A bass string vibrates in integer ratios and a kick membrane in Bessel ratios,
so one is harmonic and the other is not. Partially fixed NMF exploits exactly
that asymmetry: the freely adapting harmonic dictionary absorbs the bass stack
while the fixed inharmonic template keeps the kick. Kick and bass are different
kinds of vibration, so they separate.

A hi-hat and a ride are the same kind of object — inharmonic metal plates with
dense, overlapping energy from roughly 5 to 15 kHz. There is no harmonic
asymmetry to exploit, so a template can only separate them by spectral shape,
and their shapes are genuinely alike. The one property that does separate them
is decay time, and decay stops discriminating in a full mix: sweeping the hat
decay gate from 0.06 s to 0.60 s moved F1 by 0.02, because guitars, vocals and
other cymbals keep that band energised so nothing decays cleanly.

Two unrelated architectures failing identically, in the same direction, is
evidence about the problem rather than about either implementation. The
literature records no published rule separating closed hat from ride on full
mixes, and the researcher looked for one specifically.

**Consequence.** CHH cannot be made shippable by adding templates. The options
are to descope it as OHH and TOM were descoped, or to ship it at roughly 0.30
precision and make that visible to the player rather than silent.
