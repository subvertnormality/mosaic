# Rhythm Doctor component evidence

The feature is not integrated or qualified. Passing these commands proves only
its named components. See STATUS.md for unresolved RD-01/RD-02 gates.

## Repeatable component tests

From the repository root on Linux/WSL with Lua 5.3 and Python 3:

```sh
python3 tests/rhythm_doctor/run_components.py --output /tmp/rd-components-new-run
```

The output directory must be new. Each command has its own log; report.json
records source hashes, selected layers and failures. A source changed during the
run invalidates the report. Skipped selected tests are failures, not passes.
This includes bank/schema, lifecycle, paint/journal and independent score/corpus
validation. It does not start Mosaic or perform detector quality acceptance.

For native PCM tests, install GCC, JACK development/runtime tools and aubio.
The default tempo build uses the pinned Ubuntu 20.04 aubio packages extracted by
`tools/rhythm_doctor_tempo/bootstrap_local_aubio.sh`; it does not replace a system
installation. The explicit `RD_TEMPO_SYSTEM_AUBIO=1` mode uses installed aubio and
must remain a separately identified dependency environment.

Detector unit tests additionally require Python 3.10 and the pinned packages in
`tools/rhythm_doctor_analysis/requirements.txt`. Install them into a virtual
environment. The dedicated CI job uses Ubuntu 22.04 and records dependency versions.

```sh
python3 tests/rhythm_doctor/run_components.py --native --detector --output /tmp/rd-components-all-new-run
```

The existing full Mosaic Lua suite remains separately required (`./test.sh`).
Its current measured result and the focused source-revision result are in
STATUS.md. Native callback timing is measured in real time; controlled time is
not evidence of audio scheduling accuracy.

## Physical Norns

Follow the existing real-norns runbook for access and exclusive device ownership.
`tests/rhythm_doctor/run_hardware_core.py` runs pure Lua components from an isolated
temporary directory, verifies deployed hashes and removes its files. It does not
replace or load the user's script. Supply `--host`, `--control-path` and a new
`--output` report path. Pure component passes are not full-feature device evidence.

`tests/rhythm_doctor/run_hardware_capture.py` deploys and hash-verifies the capture
probe and native sources in an isolated device directory, runs three trials,
and removes exactly its own files even on failure. Supply the same connection
arguments and a new output path. The probe in
`tests/behaviour/rhythm_doctor_capture_hardware.py` verifies
owned JACK injection/capture continuity and route restoration. It is not an ADC,
physical grid or classifier test. Bank benchmarks report Lua CPU, not UI latency.

## Actual application and corpus gates

`tests/behaviour/rhythm_doctor.py` starts the actual app and asserts the first four
algorithm tooltips followed by the proposed fifth-mode framebuffer title. The
frozen base fails at the missing fifth title in both time lanes. This intentionally
red acceptance is not excluded from a claim of complete feature acceptance; no
such claim is currently made. Full input/PCM/paint/MIDI cases remain to implement.

Corpus assets stay outside Git. Their manifests pin audio, annotations, licenses
and render recipes. BabySlakh material used to select prototype architectures is
explicitly validation-pilot data, not a pristine final test partition. Synthesized
or sampled isolated fixtures cannot replace full-mixture evidence. A passing
metric validator cannot authenticate source provenance or a device measurement.

## Pretrained corpus evaluation

`tools/rhythm_doctor_analysis/pretrained_corpus_evaluate.py` scores a pinned
runtime against a validated schema-v2 corpus. It never trains, downloads or
changes a model. Supply `--manifest`, `--corpus-root`, `--cache-dir` and a
`--report` path; `--corpus-root` is separate because manifest descriptors are
relative to the external cache root, not to the manifest directory. Gates are
selected from development clips only and held-out data is aggregated once with
those gates frozen.

The resume cache is keyed by model identity, corpus identity and each clip's
audio and annotation digests, so changing the backend correctly invalidates it.
A full cold run over 106 clips took roughly 26–40 minutes on x86 with peak RSS
891,800 KiB. Model paths come from `RHYTHM_DOCTOR_OMNIZART_SOURCE`,
`RHYTHM_DOCTOR_OMNIZART_ONNX`, `RHYTHM_DOCTOR_UMXHQ_BASS` and
`RHYTHM_DOCTOR_BASIC_PITCH_ONNX`.

A green report is quality only. It does not establish corpus provenance,
redistribution rights, ARM inference or device acceptance, and it sets
`complete_rd02_acceptance` false.

## Component campaign

`tests/rhythm_doctor/run_components.py --output <new dir>` runs the component
groups and requires a directory that does not already exist. With `--native`
and `--detector` it selects 49 groups: 20 Lua, 12 Python, 4 native and 13
detector. `--analysis-python` must point at an interpreter carrying the pinned
detector dependencies; the default interpreter will not satisfy the detector
groups. `--native` additionally needs GCC, JACK and aubio.

## Physical Norns dependencies

The device has no internet. Its only route is an isolated 10.42.0.0/24 hotspot,
so `apt` cannot run there and every dependency must be staged from a host and
copied across. The device also ships no numpy and no pip.

Install nothing into device system directories for a test. Unpack dependencies
into a directory under `/tmp` and reach them through `PYTHONPATH` and
`LD_LIBRARY_PATH`, so cleanup is removing one directory. Debian's numpy needs
the BLAS and LAPACK alternatives subdirectories on `LD_LIBRARY_PATH` because the
alternatives symlinks are not unpacked.
