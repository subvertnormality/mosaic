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
