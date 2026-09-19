# Rhythm Doctor RD-02 corpus

## Active-scope amendment — 2026-09-19

The acceptance corpus now targets **BD, SD, CHH, OHH and BASS**. CHH (closed
hi-hat) and OHH (open hi-hat) must be separately annotated; combined `HH` is not
an active acceptance label, and `TOM` is outside the active feature scope. The
validator's active schema is `BD`/`SD`/`CHH`/`OHH`/`BASS`; the frozen manifests
described below retain the historical `BD`/`SD`/`HH`/`TOM`/`BASS` schema. Those
immutable diagnostic and provenance records cannot qualify the amended feature.
A newly frozen source-disjoint corpus must validate the active schema.

The amended corpus must apply every existing structural and quality requirement
to each active lane independently: 40 development and 40 held-out exact-four-bar
clips; at least 10 held positive clips and 50 held events; at least 5
full-mixture, 2 sparse and 2 isolated positives; electronic and acoustic timbre
evidence; at least 5 absent-lane negatives; held onset F1 >=0.80 in each lane
and stratum and quantised-cell F1 >=0.85; zero default-threshold events on
negatives; and the
stated velocity gates. A combined-HH score, a TOM score, or a macro average
cannot substitute for either hat articulation. Schema-v2 tooling emits and
validates only the amended lane set; it never rewrites frozen evidence JSON.

The RD-02 corpus is external to this Git repository. Audio, source archives,
annotations, and provenance records must never be replaced with generated toy
audio or detector output. Run the validator before tuning or accepting a detector:

```sh
python tests/rhythm_doctor/test_corpus.py
PYTHONPATH=tests/rhythm_doctor python -c "from corpus import validate_manifest; print(validate_manifest('/path/to/rd02/manifest.json'))"
```

The manifest is version 1 JSON and every file path is relative to the supplied
external corpus root. The validator resolves paths, rejects paths that escape
that root (including Windows drive paths), and hashes every referenced byte. It contains `sources` and `clips`. A source records an
immutable HTTPS record URL, an approved SPDX identifier (`CC-BY-4.0`,
`CC0-1.0`, or `GPL-2.0`) and license URL, plus
SHA-256-pinned local copies of its downloaded archive and source-license record.
Each source declares its `rendered` or `recorded` domain. Each clip records its
source/song/kit identity and offset in the source recording, an SHA-256-pinned
audio file, and a SHA-256-pinned render recipe. The recipe declares a
`source_mix`, `frozen_submix`, or `isolated_stem` result and makes a stratum
auditable instead of silently relabelling a stem. Each clip also has
an SHA-256-pinned annotation JSON. Annotation JSON has exactly the five lanes
`BD`, `SD`, `HH`, `TOM`, and `BASS`; each onset carries `time_seconds` in the
half-open crop interval `[0, duration_seconds)` and a
1–127 MIDI reference velocity. Its `reference_origin` is either
`independent_human` or `independent_render_metadata`, and it identifies the
annotator or frozen rendering metadata. `detector_output` is rejected.
Every acoustic/electronic lane label has a separately SHA-256-pinned timbre
evidence JSON. It must name the source patch metadata, source render
specification, or independent audition record supporting that exact label;
kit-name inference is not evidence.

An exploratory manifest may use `unverified` for a lane whose source cannot
support either timbre claim. It remains structurally auditable, but the held-out
timbre gate will fail and it must never be reported as an accepted corpus.

The validator enforces the plan’s structural gates: 40 development and 40
held-out exact-four-bar clips, song and kit separation across those partitions,
held-out positive/event/stratum/timbre counts for every lane, absent-lane
negatives, three genuine silence clips, the clipping/phase-inverted/kick+bass
controls, and separately annotated acquisition fixtures no longer than 45
seconds across the specified tempo/scenario envelope. Passing it establishes
only that the corpus is eligible for scoring; it does not establish a quality
result.

## Source record acquired for corpus construction

The official [BabySlakh v2 Zenodo record](https://zenodo.org/records/4603870)
is an initial licensed source cache: twenty 16 kHz WAV multi-track songs derived
from Slakh, distributed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Its upstream archive is `babyslakh_16k.tar.gz`, published MD5
`311096dc2bde7d61c97e930edbfc7f78`; the acquired archive SHA-256 is
`6490dc83d8b59ccbe7e9e0304023af8e585d2065f9a5f5921952a273fac4a9b0`.
The saved Zenodo record response has SHA-256
`7a0b1943f0f9b8dfe7ad99d3316c7635474b354d1902b34a9dcb7f4ba611301e`.
Store both under an external corpus cache and extract only selected source files.
Slakh aligned MIDI/render metadata can supply
independent render references after a separately reviewed five-lane mapping.

BabySlakh is a construction source, not an accepted RD-02 corpus: it has only
twenty songs and consists of synthesized mixtures. It can contribute explicitly
labelled rendered-domain mixtures, acoustic/electronic timbres where independently
reviewed from the frozen render data, and frozen submix/isolated strata. The
currently inspected BabySlakh metadata does not classify its named kits as
electronic, so an electronic-lane gate remains unmet until a pinned source record
does. It cannot
alone establish a result for a different recorded-music domain. Build the final
80-plus clip manifest with disjoint songs and kits, preserve the actual
source/license bytes and hashes, and add the required independent review before
any gate is reported as passing.

The official [AVP-LVT Zenodo record](https://zenodo.org/records/5578744) is a
second, small CC BY 4.0 construction source. Its acquired `AVP-LVT_Dataset.zip`
has published-and-verified MD5 `3cc38636623e2861cbda145d889e959a`. It contains
recorded vocal-percussion WAVs and published per-gesture CSV labels for kick,
snare, and hi-hat. Corpus v4 uses original short recorded gestures only in
explicitly labelled frozen isolated render schedules. These fixtures contribute
independently referenced BD/SD/HH controls, but vocal percussion does **not**
establish acoustic or electronic *instrument* timbre, TOM coverage, or
mixed-music quality. Those lane timbres remain `unverified`.

The external preliminary v4 manifest lives at
`/home/andy/.cache/rhythm-doctor-corpus/rd02-preliminary-v4/manifest.json`.
It has 40 development and 51 held-out clips. It intentionally remains rejected:
the first current gate failure is missing held BD sparse stratum coverage, with
TOM, source-backed timbres, complete negatives, and long acquisition fixtures
also unresolved in its gate report. v1, v2, and v3 remain immutable exploratory
manifests. An exact shared source span is permitted only for a separately pinned
frozen submix/stem render; it is one provenance span and cannot inflate the 40
unique base spans in either split.

The official [Hydrogen source repository](https://github.com/hydrogen-music/hydrogen)
is a bounded GPL-2.0 source candidate. Its checked `GMRockKit` manifest calls
it a sampled five-piece Pearl DX drum kit, and its `TR808EmulationKit` manifest
says that its sounds are synthesized from basic waves. Selected kick, snare,
closed-hat and tom assets and both manifests are cached with the repository
`COPYING` file. This provides source-backed acoustic and electronic identities
for scheduled isolated renders; renders remain supplemental controlled fixtures,
not evidence for mixed-music quality.

Corpus v6 is superseded and invalid for acceptance because it incorrectly
recorded FreePats CC0 source material as CC BY. It remains as audit evidence;
v7 corrects those source entries to `CC0-1.0` without rewriting v6.

`rd02-clean-v8` and its copied `rd02-clean-v9` draft are invalid diagnostic
corpora, not clean held-out candidates. The v8 audit found forty held entries
but only six distinct non-silence PCM SHA-256 values: the seeded renderer
reused audio while changing annotation metadata. It also used constant PCM gain
despite reported velocity variation, cited drum-kit metadata for BASS timbres,
and omitted FreePats license records from mixed-source provenance. Keep this
finding with the exact audited manifest at
`/home/andy/.cache/rhythm-doctor-corpus/rd02-clean-v8/manifest.json`; do not
reuse either draft for tuning or acceptance. The validator rejects duplicate
non-silence held PCM descriptors under distinct source-song identities. Shared
zero-byte silence controls are allowed but cannot establish the forty-example
inventory.

The official [Groove MIDI Dataset](https://magenta.withgoogle.com/datasets/groove)
is a separately downloaded auxiliary source for documented electronic-drum-kit
performances. Google licenses its aligned Roland TD-11 WAV/MIDI recordings under
CC BY 4.0 and publishes the `groove-v1.0.0.zip` SHA-256 as
`21559feb2f1c96ca53988fd4d7060b1f2afe1d854fb2a8dcea5ff95cf3cce7e9`.
The local SHA-256 verification has not completed, so do not select GMD assets
for a corpus manifest yet.
Its documented note map supplies BD, SD, HH and TOM reference events. It has no
pitched-bass lane and therefore cannot satisfy the five-lane corpus alone. A TD-11
is electronic triggering hardware, but its recordings may use acoustic samples;
do not label a selected clip `electronic` until the specific patch/sound identity
is pinned in its timbre evidence. Retain the source-specific map and render-domain
record beside every selected clip.

## Current frozen inventory (v12)

`rd02-scheduled-v12/manifest.json` in the external cache has SHA-256
`b7a804939e53f64858296c1073a8060bd14c9a36967f758438936474bb04dbdf`.
It is the active schema-v2 corpus: 40 BabySlakh development clips, 66 scheduled
held clips and seven 45-second acquisition fixtures. Original BabySlakh MIDI
supplies independent BD, SD, CHH, OHH and BASS development references. Pedal
hi-hat, tom and other cymbal notes remain audible interference and are not
relabeled. The held partition uses separately frozen closed- and open-hat
samples from two Hydrogen kits. Its 42 full-mixture/control renders have
distinct audio hashes.

The independent validator passes every source, licence, partition, active-lane,
stratum, timbre and control requirement. Held positives are 49 BD, 48 SD, 48
CHH, 48 OHH and 49 BASS clips, containing 550, 531, 1,588, 557 and 732 events
respectively. Each deterministic source archive contains every sample, README
and licence byte used by its recipes. The durable inventory and PCM results are
`evidence/v12-corpus-inventory.json` and `evidence/v12-rendered-audit.json`.
This establishes eligibility for frozen scoring; it is not transcription
quality evidence.

## Superseded frozen inventory (v11)

`rd02-scheduled-v11/manifest.json` in the external cache has SHA-256
`1cd3dc6e86461e78330ea0c885880d3f01131b572183da5a84b3da101a8e5e6b`.
It contains 40 BabySlakh development clips, 66 newly scheduled held clips and
seven 45-second acquisition fixtures. The 42 held full-mixture/control renders
have distinct audio hashes. Each lane has both sampled physical-instrument and
synthesized timbres, isolated gain ladders, sparse and full-mixture positives,
and absent-lane negatives. Sampled electric bass is recorded physical strings;
this does not claim upright acoustic bass. The held mixtures are a rendered
music domain, not field recordings of bands. Its limited two-kit diversity must
remain visible in any quality report.

The v11 annotations aggregate hats as `HH`, and every scheduled HH source asset
is a closed hat. Most mixtures also contain audible TOM events. It therefore
cannot be relabeled into the active CHH/OHH schema and remains historical
evidence only.

`tools/rhythm_doctor_corpus/build_scheduled.py` creates a new directory only,
using pinned Hydrogen and FreePats source samples and an independent seeded
schedule. Audio gain and annotation velocity come from the same schedule;
no detector supplies the labels. Both bass sample archives include the actual
sample, README and CC0 license. The renderer currently requires the previously
materialized v7 development/source descriptors in the external cache; it is not
a one-command download installer.

The independent inventory and PCM audits are recorded in
`evidence/v11-corpus-inventory.json` and `evidence/v11-rendered-audit.json`.
The audit recomputes audio hashes, duration, stereo cancellation and gain scaling.
v10 is preserved with its one-LSB phase-inversion failure; v11 quantizes once
before making the opposite integer channel. This is fixture qualification only.
Neither the final transcription nor acquisition quality gate has been measured
on this frozen partition. Keep it separate from reused BabySlakh diagnostics.

## First scored use of the frozen v12 partition (2026-09-19)

v12 has now been used once for a held-out RD-02 score. Development clips
selected the per-lane gates and the 66 held-out clips were aggregated once with
those gates frozen. The pinned pretrained candidate failed; the corpus itself
behaved as designed. See DETECTOR.md and
`evidence/pretrained-v12-quality-2026-09-19.json`.

Two partition properties proved load-bearing and should be kept.

The absent-lane controls did their job. Measuring false positives on clips where
a lane is absent is what exposed cross-lane leakage as the dominant failure
(CHH 62.1%, SD 49.4%, BD 45.1% of all false positives). Aggregate scoring alone
would have hidden this.

The isolated stratum is the harshest on a leaky detector, because every
cross-fire there is an unambiguous false positive while in a full mix it may
coincide with a real event of that lane. That is why isolated scored worse than
full_mix. This ordering is a property of the detector, not a corpus defect: beat
tracking was verified correct on 10/10 isolated and 41/41 full-mix held-out
clips, so the strata are not mistracked.

`v12-phase`, the phase-inverted stereo control, is only meaningful against a
detector that preserves stereo. Its mono downmix is exactly zero while its
interleaved buffer peaks at 7964, so any mono-downmix chain can only score
false negatives on it. Keep the clip: that is a real property to test for, but
read its contribution as a statement about the candidate rather than about the
corpus.

The rendered-domain limitation still stands. Held material comes from two kits
and synthesized or sampled timbres, so a failure here is strong evidence against
a candidate while a pass would still not establish field-recording performance.

## Domain mismatch: v12 is not a valid acceptance gate for real music

The user confirmed on 2026-09-19 that Rhythm Doctor is intended to capture
**real music**, not isolated drum parts, drum-machine patterns or sample
one-shots. That makes the corpus domain the largest open risk in RD-02, larger
than any individual detector candidate.

v12 is a rendered corpus built from two drum kits (Hydrogen GMRockKit and
TR808) plus sampled and synthesized bass, with BabySlakh development material.
It contains no vocals, guitars or keys, no real room or mastering chain, and no
kit diversity beyond those two. A pass or a failure on v12 therefore transfers
weakly to the intended domain, and the transfer is unreliable in **both**
directions:

- It may be unfairly harsh on a model trained on real recordings, because the
  rendered material is out of that model's training distribution. This is an
  unexcluded confound in the v12 failure of the pinned candidate, which was
  trained on real music.
- It would be unfairly generous to a model trained on rendered material, which
  would match the corpus domain without demonstrating anything about real music.

The published literature supports treating this as severe rather than
theoretical. Vogl et al.'s 18-class drum transcriber scores open hi-hat around
F 0.69 on in-set cross-validation but collapses to F 0.12 when trained on RBMA
and evaluated on MDB. Cross-dataset generalisation is the known failure mode of
automatic drum transcription, not an edge case.

Two consequences follow.

**Training on rendered material is contraindicated.** StemGMD is attractive on
licence (CC-BY 4.0) and is the only permissively licensed source found with
genuinely separate closed and open hi-hat stems, but it is Groove MIDI rendered
through sampled kits. Training on it and validating on v12 would measure
rendered-drum performance twice and establish nothing about real music.

**A real-music evaluation set is required before the next candidate decision.**
Licence constraints are substantially weaker for evaluation than for training:
measuring privately against a non-commercially licensed corpus distributes
nothing, whereas shipping weights derived from it does. Sets such as MDB-Drums,
ENST-Drums and RBMA are therefore usable as measuring sticks even where they are
closed as training data. Keep v12 for what it is good at — exact provenance,
deterministic renders, absent-lane controls and gain ladders — and stop treating
it as the sole acceptance gate.
