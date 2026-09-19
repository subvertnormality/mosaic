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

`rd02-preliminary-v1` is a 80-crop full-mixture pilot only. Its missing
isolated/sparse/source-kit strata mean no result is acceptance evidence and the
harness reports `acceptance_claimed: false`; it does not report a grid-F1 gate.
Frozen BabySlakh archive SHA-256 is
`6490dc83d8b59ccbe7e9e0304023af8e585d2065f9a5f5921952a273fac4a9b0`.

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

## Candidate B comparison

Candidate B is unproven for the bounded local norns profile; no Candidate-B
weights were downloaded or executed. This is a gap in evidence, not a conclusion
that model-based transcription cannot work.

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
published weights total 39,460,049 bytes; none was downloaded.

This is usable as a sharply defined next benchmark, not a standalone-norns
architecture yet. ADTOF-PyTorch has no LICENSE file in the inspected repository;
the upstream ADTOF repository is CC BY-NC-SA 4.0, so the port and its weight need
explicit compatible licensing before delivery. Open-Unmix source is MIT, but the
inspected documentation did not state a separate redistribution licence for the
UMXHQ bass weight. Both ADTOF-PyTorch and Open-Unmix require Python/Torch, while
the Basic Pitch Linux path requires TensorFlow Lite; no ARMv7 native worker,
incremental-RSS measurement or device latency measurement has been made. The
ADTOF and Open-Unmix networks are bidirectional, so this profile is final
offline analysis after capture rather than streaming inference.

RD-02's stop criterion therefore applies: do not call a five-lane standalone
feature feasible until a compatible licensed replacement or permission is
frozen, all three components are cross-built into a bounded local norns worker,
and the clean frozen corpus meets every per-lane and stratum F1/grid/negative
gate. The detailed URLs, HEAD byte counts, output mapping and unresolved
conditions are retained in
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
