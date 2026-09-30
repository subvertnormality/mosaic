# RD-02 streaming tempo feasibility

This is a native aubio experiment, not a Rhythm Doctor feature or a claim that
automatic tempo acquisition is ready. It does not connect to JACK, invoke the
capture spike, alter Mosaic state, select a bar-one downbeat, analyse instruments,
or paint anything.

## Local reproducibility and dependency boundary

`tools/rhythm_doctor_tempo/bootstrap_local_aubio.sh` downloads and extracts,
without installation, the two Ubuntu focal packages pinned in
`AUBIO_LOCAL_LOCK.txt` into `/tmp/rd-tempo-aubio-0.4.9/extracted`. The local
build script links only that extracted `libaubio.so.5.4.8`; its locked SHA-256
values are verified before extraction. This is an x86_64 local feasibility
environment, not a deployed dependency or an ARM performance result.

The implementation uses the stable aubio C tempo calls
`new_aubio_tempo`, `aubio_tempo_do`, `aubio_tempo_get_last`,
`aubio_tempo_get_bpm`, and `aubio_tempo_get_confidence`. Those calls are the
API boundary to check against the known norns aubio 0.5.0-alpha package. No
norns operation was performed here, and this 0.4.9 result must not be used to
claim norns latency, memory, scheduling, or detector equivalence.

For CI, setting `RD_TEMPO_SYSTEM_AUBIO=1` selects a separate, explicit system
lane. It requires `pkg-config --exists aubio`, links with that package's cflags
and libraries, and writes `<output>.aubio-build.json` with the aubio version,
resolved shared-library path, library SHA-256, and compiled-binary SHA-256. It never falls back to the pinned
extraction. The local Ubuntu 20.04 host does not provide system aubio, so its
explicit system-mode invocation visibly fails at `pkg-config`; the pinned lane
remains the tested local build. The test setup uses `sh build_local_aubio.sh`
so checkout executable bits are not an implicit CI requirement.

## Candidate contract

`rd_tempo.c --raw-f32 FILE SAMPLE_RATE [METHOD|onset-ac]` streams a real mono
float32 PCM file in 512-sample chunks and emits measured detector positions,
BPM/confidence values, and an independently calculated candidate.
`--candidate-beats` accepts a known beat table solely for candidate unit tests;
it is not a detector oracle. The candidate requires at least eight detected
positions and three independently spaced, confidence-qualified BPM estimates
spanning four seconds within 2%. They are deliberately not required to be
consecutive: at 40 BPM even three consecutive observations span only three
seconds.

A four-bar candidate requires a full buffered duration of 16 beat intervals,
with `end = origin + 16 * period` inside the retained PCM. It does not require
17 detector callbacks: eight observed positions can support a region when the
remaining duration is actually retained. It searches later stable spans after an
early transient or phase failure. For every proposed span it validates every
retained detector estimate for BPM drift above 2%. Beat-phase fit is evaluated
on onsets that support the proposed beat grid; other detected onsets are retained
as subdivision/offbeat residuals rather than being incorrectly required to lie on
a beat. The maximum phase error of every supporting beat remains 50 ms, not a
mean that could hide a bad beat. A candidate still needs at least eight supported
grid positions and a full retained 16-interval region. It compares half/double
grid scores and returns `UNCERTAIN` rather than inventing a region whenever any
gate fails.

The source records a 32-bit frame origin/end because the supplied PCM length is
bounded; a later capture-bank integration must retain the RD-01 source timing
and use its full sample-index contract.

## Corrected logic and measured local result

The first implementation was invalid: it required three **consecutive** beat
callbacks to span four seconds, which cannot happen from valid regular beats at
the supported 40–240 BPM envelope. It also used 15 intervals for four bars,
returned after its first failed phase fit, and averaged phase error. Its prior
all-uncertain observation is retained only as `INVALID_CANDIDATE_LOGIC`, not as
evidence about aubio.

`test_tempo_candidate.py` now independently proves the corrected candidate on
known regular 40/60/120/180/240 BPM tables, distinguishes 15 from 16 complete
intervals, skips an initial transient to a later stable span, rejects continuing
tempo drift, and exposes half/double values. These are algorithm tests; they do
not stand in for detector evidence.

On 2026-09-19, the pinned local build ran deterministic actual-PCM fixtures in
`test_tempo_native.py` at 44.1 kHz. The direct aubio callback methods and the
separate onset-strength/autocorrelation experiment are reported separately:

| Fixture | Detector observation | Candidate result |
| --- | --- | --- |
| 40 s 120 BPM percussive pulse, `default` | reported about 121.62 BPM; 17 callbacks | `UNCERTAIN / phase-fit` |
| Same PCM, `energy` | reported about 121.95 BPM; 27 callbacks | `UNCERTAIN / phase-fit` |
| Same PCM, `specdiff` | reported about 122.03 BPM; 19 callbacks | `UNCERTAIN / phase-fit` |
| Same PCM, `onset-ac` | 512-frame PCM-energy peaks, phase-fold autocorrelation | `READY / stable`, about 120 BPM |
| Silence | no beat callbacks; reported about 40.69 BPM at zero confidence | `UNCERTAIN / insufficient-beats` |
| 40 s half/double stress pattern, `energy` | reported about 121.73 BPM; 30 callbacks | `UNCERTAIN / phase-fit` |
| 40 s syncopated pulse pattern, `energy` | reported about 121.95 BPM; 26 callbacks | `UNCERTAIN / phase-fit` |
| 24 s 100→145 BPM drift | 4 callbacks; final reported about 140.72 BPM | `UNCERTAIN / insufficient-beats` |

The direct aubio `default`, `energy`, and `specdiff` callbacks did not produce
an in-bounds, full-four-bar candidate for this PCM; `energy` had enough
callbacks but failed maximum phase fit. This remains a grounded negative result
for those three methods and parameters.

`onset-ac` is a separate, cheap native PCM path, not a claim that aubio's onset
callback solved the fixture. It measures energy per 512-frame input hop, keeps
local maxima above three times the fixture mean, evaluates 40..240 BPM in 0.25
BPM increments using a 50 ms pair tolerance, then phase-folds the observed
positions through a linear period fit. The path uses the same candidate 2%,
four-bar, and maximum-50-ms gates. Its frozen development envelope contains
exact 40-second percussive fixtures at 40, 60, 120, 180, and 240 BPM. All five
were `READY`, in bounds, and within 2% (5/5, 100%). This is development-fixture
evidence only, not held-out accuracy, robustness, musical downbeat selection,
or a product acceptance claim.

The half/double stress input is intentionally excluded from that denominator.
Its sparse 60 BPM accents plus intervening pulses can establish a 120-pulse
period, but PCM periodicity alone cannot establish whether 60 is the intended
half-time meter. The JSON keeps half/double candidate values and the candidate
returns `UNCERTAIN / half-double-ambiguous` when its grid scores actually cannot
separate them. No half/double result is counted as correct.

The test suite pins both the direct-aubio uncertainty observations and the
controlled `onset-ac` result. A future change must explicitly re-measure and
revise this record; it may not weaken the 2%, phase, half/double, or in-bounds
gates.

## Held corpus result

The read-only `scan_babyslakh.py` tool streams the first 45 seconds (the RD-01
retained-window size) of each supplied 16 kHz BabySlakh `Track00001` through
`Track00020` full mix to the same native binary. The archive identity recorded
by the frozen manifest is BabySlakh v2 SHA-256
`6490dc83d8b59ccbe7e9e0304023af8e585d2065f9a5f5921952a273fac4a9b0`.
Tempo references come from MIDI `set_tempo` events, using `mido` when it is
available and a standard-MIDI fallback reader only on this local host, where
`mido` is absent. Audio never supplies the expected BPM.

Thirteen tracks had one finite MIDI tempo in the measured window's source:
00001, 00002, 00003, 00004, 00009, 00012–00017, 00019, and 00020. `onset-ac`
returned `READY` for 0/13. The failures were eight
`UNCERTAIN / unstable-estimates` and five `UNCERTAIN / phase-fit`; no failure
was converted into an eligible result. For example, the fixed source hashes in
the regression identify Track00001 mix as
`e6590a50b9c4d6aa84d67e03368b42e0d79d56ba4b1244c26c5b9d6ecab89f34` and
drum MIDI as
`1fd7413b8f01be812d8b45ab9c7926fa849bdcfd6f6b1fe8763d59a53019bcfb`.
Its MIDI reference is 80.010028 BPM, while this method produced 41.959461 BPM
and `UNCERTAIN / phase-fit`; that discrepancy is pinned as a held failure.

Tracks 00005, 00006, 00007, 00008, 00010, 00011, and 00018 contain more than
one finite MIDI tempo and are excluded from the single-meter denominator. They
remain separately uncertain; Track00005 is hash-pinned in the suite and
returned `UNCERTAIN / unstable-estimates`. This corpus result prevents treating
the 5/5 synthetic development envelope as general audio acquisition accuracy.

The full raw result is stored as
`tools/rhythm_doctor_tempo/babyslakh_scan_2026-09-19.json`. It contains all 20
candidate payloads plus the compiled-binary, `rd_tempo.c`, scanner-script, WAV,
and MIDI SHA-256 values. The normal component suite has a fixed inventory and
does not load this external corpus. `test_tempo_corpus.py` is an opt-in module:
when selected it requires `RD_TEMPO_CORPUS_ROOT` and fails visibly if that root
or its frozen files are missing.

## Development-method comparison

This separate development-only experiment did not alter detector parameters and
did not inspect the held or v10 corpus. It streamed the first 45 seconds of
BabySlakh Tracks 00003, 00004, 00005, 00007, 00010, 00012, 00013, 00017, and
00018 through `default`, `energy`, `specdiff`, and `onset-ac`. MIDI tempo events
and tick-zero phase form the independent references; audio labels are not used.
The complete raw callbacks, confidence values, candidate payloads, diagnostics,
and binary/C/scanner/WAV/MIDI hashes are retained in
`tools/rhythm_doctor_tempo/babyslakh_dev_methods_2026-09-19.json`.

All 36 method/track candidates were `UNCERTAIN`. The first candidate failures
were quantitative rather than a retained-window shortage: `default` had seven
`phase-fit` and two `unstable-estimates`; `energy` five and four; `specdiff`
seven and two; and `onset-ac` two and seven. Every source window retained 45
seconds and each diagnostic reports that 16 intervals at its first MIDI tempo
fit within that duration. Direct aubio methods returned 28–49 callbacks over
37.2–42.1 seconds, so none failed for too few positions. `onset-ac` returned
27–78 peaks over 26.1–44.7 seconds; its `unstable-estimates` results are
preserved rather than coerced into a grid.

For the five tracks with one tick-zero MIDI tempo, direct aubio reports were
roughly 0.26–0.74 of that tempo, and their maximum MIDI-grid phase errors ranged
from 76.7 to 317.4 ms. That exposes octave/subdivision choices and jitter rather
than a claim of acquisition. `onset-ac` Track00017 had a 27.0 ms maximum error
to the MIDI grid but reported 50.93 BPM against 103.00 BPM; it still failed its
own all-peak phase candidate gate. This difference is intentional evidence that
attack peaks alone do not establish meter. No method was selected or retuned.

Run the bounded local evidence with:

```
RD_TEMPO_AUBIO_ROOT=/tmp/rd-tempo-aubio-0.4.9/extracted \
python3 -m unittest tests/rhythm_doctor/test_tempo_candidate.py tests/rhythm_doctor/test_tempo_native.py
```

To inspect the complete held scan, first build the binary and then run:

```
python3 tools/rhythm_doctor_tempo/scan_babyslakh.py /tmp/rd-tempo-warnings \
  /home/andy/.cache/rhythm-doctor-corpus/slakh/babyslakh-selected/babyslakh_16k
```

The development method comparison is reproducible without adding material to
the held set:

```
python3 tools/rhythm_doctor_tempo/scan_babyslakh_dev_methods.py /tmp/rd-tempo-warnings \
  /home/andy/.cache/rhythm-doctor-corpus/slakh/babyslakh-selected/babyslakh_16k \
  tools/rhythm_doctor_tempo/babyslakh_dev_methods_2026-09-19.json
```

## Grid-support phase experiment — not a viable candidate

The prior all-onset fit was structurally wrong for syncopated music: the plan's
50 ms requirement is a beat-grid phase requirement, not a demand that hats,
flams, or other subdivisions land on the beat. The source and earlier
`babyslakh_dev_methods_2026-09-19.json` are retained unchanged. This bounded
replacement experiment added literal unit regressions for 16th-note
syncopation and half-time ambiguity before changing the candidate. It records
`grid_support`, `offbeat_residual`, and main/half/double grid scores; unavailable
alternatives use score `-1` when outside 40–240 BPM.

The candidate uses only supported grid positions for phase, preserves residual
offbeats, still requires eight supports, the original 50 ms maximum, three
stable estimates, and the complete 16-interval buffer. Literal syncopation now
has supported beats plus residual offbeats rather than `phase-fit`; a literal
regular 120 BPM pulse is correctly `UNCERTAIN / half-double-ambiguous`, because
its audio pulses cannot resolve 60 versus 120 meter. No tolerance was relaxed.

The frozen candidate was then measured once against the same nine development
tracks only. Raw output is in
`tools/rhythm_doctor_tempo/babyslakh_dev_grid_candidate_2026-09-19.json`; it
contains MIDI references and binary/C/scanner/WAV/MIDI hashes. It produced five
`READY` candidates out of 36, all wrong against the independent MIDI tempo:
Track00004 `default`/`specdiff` reported about 59 against 115 BPM,
Track00013 `default`/`specdiff` about 66 against 128 BPM, and Track00018
`energy` about 70 against 137 BPM. Their main grid scores (0.56–0.73) beat the
reported double-grid scores (0.77–0.86), so this raw beat stream provides no
internal evidence to reject the false half-tempo lock. That is a detector
failure, not a reason to weaken ambiguity or phase rules.

This candidate is not selected for delivery. No held, v10, or v11 audio was
evaluated in this experiment; those remain reserved for a separately frozen
candidate. The normal tests pass, but they establish bounded algorithm behavior,
not corpus acquisition accuracy.

Run its two pinned corpus regressions only with an explicit mount:

```
RD_TEMPO_AUBIO_ROOT=/tmp/rd-tempo-aubio-0.4.9/extracted \
RD_TEMPO_CORPUS_ROOT=/home/andy/.cache/rhythm-doctor-corpus/slakh/babyslakh-selected/babyslakh_16k \
python3 -m unittest tests/rhythm_doctor/test_tempo_corpus.py
```

`RD_TEMPO_PRINT=1` prints the complete actual detector JSON while running the
same tests. Controlled musical time is inapplicable to this wall-clock-free PCM
streaming detector; the fixtures have exact sample origins, while the unresolved
native callback/input timing belongs to the separate RD-01 hardware evidence.

## UMXHQ BASS onset diagnostic - rejected

This is not a tempo candidate. A desktop-only comparison separated the mixture
with the official UMXHQ BASS weight and scored magnitude spectral-flux peaks
against source BASS MIDI at one-to-one 50 ms. The threshold was selected only on
eight valid old BabySlakh development tracks. The eleven diagnostic-held tracks
then produced precision 0.512545, recall 0.752632, and F1 0.609808. This fails
the BASS gate and is not selected for delivery.

Track00017 was excluded rather than counted as a zero-BASS negative: its source
metadata declares BASS stem S04, but S04.mid is absent from the selected source
MIDI inventory. The result has no ARM, norns latency, memory, waveform, or clean
held-corpus claim. Exact runner, model, source, input and raw-flux identities,
including the separately retained invalid v1 reproduction, are in
`docs/rhythm-doctor/evidence/umxhq_bass_pilot_v2.json`.
