# CI recovery evidence — 12 October 2026

Failed source: `f9205324c0d3d570dae498b5fd98e866fc5f196f` on `codex/1.4.0`, PR #98.

## Observed failures and corrections

1. [Manual run 38205559039](https://github.com/subvertnormality/mosaic/actions/runs/38205559039) completed all 49 generation/browser stages. Packaging subsequently failed in the controlled publication audit: it called the reader validator without the fresh target-MIDI receipt already used by generation. The final audit now supplies the sealed producer receipt, exact manifest digest and build root. Missing, altered and mixed retained/fresh receipts remain rejected. The independently verified MIDI admission is reported separately from the canonical reader report, whose hashes still compare exactly with the generation stage.
2. [Behaviour run 38205559076](https://github.com/subvertnormality/mosaic/actions/runs/38205559076) had two first-attempt real-time failures in shard 10. Its aggregate correctly rejected the successful retries. `M-MERGE-FRAGMENTS-002` expected idle footer hints immediately after applying an edited draft; the captured framebuffer instead showed the documented `APPLIED` feedback. The case now requires that exact feedback and retains its grid/MIDI checks.
3. `M-PARAM-005` captured a note 63.307 ms late while a diagnostic observation request occupied the native input/ack interval for approximately 139 ms. Fixed-note acquisition now leaves capture running through a quiet two-phrase window before requesting diagnostics. All captured packets, pitches, velocities, releases and the existing 10 ms real-time/2 ns controlled timing oracles remain checked. Controlled advances remain bounded to 60 ms. A negative regression still rejects the late mandatory note.

The 26 saved reports have one shared source/runtime identity, one fast-layer report, no duplicate cases and exact coverage of all 1,765 applicable case/lane/profile runs. These are diagnostic findings, not a passing full campaign: the unchanged aggregate still rejects the two retry-dependent cases.

## Local validation

- New quiet-acquisition regression fails on the original `f920532` helper, which requests immediate observation instead of the quiet window.
- New final-packaging regression fails on the original audit with the same missing typed-MIDI receipt error seen in CI.
- Linux packaging/publisher checks: 58 passed.
- Focused controlled-generation, acquisition, UI recipe and aggregation checks: 12 passed.
- Related reader projection, publication, MIDI receipt, build and UI suites: 374 passed.
- Full Lua suite: 2,455 passed; no network fetching of norns source was attempted.
- Native controlled-time cases `M-MERGE-FRAGMENTS-002` and `M-PARAM-005`: both passed, with normal session cleanup. The local checks used the existing release-integration emulator/runtime; the exact CI pin and real-time lane still require GitHub Actions qualification.

No local real-time tests, audio recordings or full manual rebuilds were run for these corrections. Passing CI and a published manual artifact remain separate required evidence.

## Retained failure evidence

Original job logs and downloaded immutable artifacts are retained locally under `.ci-diagnostics/run-f920532/`, outside the reader and Git payload. Downloaded archives were checked against GitHub's SHA-256 digests.

| Evidence | SHA-256 |
| --- | --- |
| Behaviour aggregate job log | `2dc0399fd63cbf8108402d5131d951b362077e2b20ce1e9954ebc6af5bbe7aec` |
| Manual build job log | `ea818c28c78f93e494c59b6800aa8c29cd1c1258812adf4ddaeef5f3ec1af187` |
| Manual diagnostic artifact | `0822a6f0034721c7e87f3a7629b480658b5302a3b2b5ea6888b3824af34cde63` |
| Native controlled-case result log | `424deb1ab8c9e21a3acec2116d72d5a9750523410f71765f3400f58e607841e3` |

## Follow-up: post-disarm recording stimulus

[Behaviour run 38236046195](https://github.com/subvertnormality/mosaic/actions/runs/38236046195)
tested source `c2c15c0ac3b1171c423bcb9dd5a5c24d5b4abb58` through PR merge
`5eef5e8866d0895482fdb9b9b30cf45896bafdff`. All 26 reports cover the 1,765
applicable case/lane/profile runs with one source/runtime identity. Both earlier
failures, `M-PARAM-005` and `M-MERGE-FRAGMENTS-002`, passed on their first attempts
in both lanes. The aggregate correctly rejected one different retry-dependent
failure: `M-REC-029` in the real-time lane.

The failed native trace shows preview note 83 delivered at `2220334934583` ns,
before the recording grid release was acknowledged at `2220351948899` ns.
The case scheduled the supposed post-disarm preview only 100 ms after the chord,
then used client observation and an unscheduled tap to disarm. The delayed tap
therefore let Mosaic correctly record the preview as another chord voice.
This is an invalid test stimulus, not evidence that Mosaic records while disarmed.

The two post-disarm preview cases now schedule the recording grid press/release
through the existing public UI scheduler, between the chord and preview. The
real-time acquisition keeps native capture active without diagnostic polling
across this interval and verifies the actual delivered MIDI/control order.
An incomplete or late disarm fails explicitly. All original MIDI deadlines,
replay pitches/velocities, shared half-second chord durations, release-order
checks and timing tolerances remain unchanged. The other chord-release cases
retain their original acquisition path.

The deterministic fixture regression reproduces the extra recorded preview on
the unfixed `c2c15c0a` case. The corrected fixture passes; a negative regression
still rejects a late native disarm. These clock-simulated regressions run without
real-time emulation or sleeping and characterize stimulus construction only.

Validation after this correction:

- Fixture and UI checks: 185 passed on Linux.
- Full Lua suite: 2,455 passed, without fetching norns Lua source.
- Native controlled cases `M-REC-028` and `M-REC-029`: passed with normal cleanup.
- The native checks use emulator source `68ab70903d22500237ce68edc7e31c3b867cf179`,
  matching CI, and an isolated runtime built through the same qualified-runtime
  builder. Its dependency, binary and interpreted-source guards passed.
- The first local trial used the older release-integration runtime and failed on
  its grouped MIDI transport. Those trials are retained and are not relabelled
  as passes. No assertion or runtime guard was relaxed to accommodate them.
- No local real-time behaviour test, audio recording or full manual rebuild ran.
  Real-time qualification remains delegated to CI.

Raw follow-up evidence is retained under `.ci-diagnostics/run-c2c15c0a/` and in
the Linux scratch checkout. The current manual CI build continues independently;
this follow-up does not establish a green complete campaign or publication.

| Follow-up evidence | SHA-256 |
| --- | --- |
| GitHub shard 14 archive | `ccc6db83cead62db969fb541a3ea0b8d964dcdab60c3b5f0d4eccfd8703735b6` |
| Unfixed deterministic regression log | `04543dcf7849332d891d96dc5c28814541dfb3e59ce00b1bcd2be533faa1eafe` |
| Linux fixture/UI validation log | `b94dec82fd64857f5591e47e79a811077907a47ce23a2717123cc1cb4938f688` |
| Controlled `M-REC-028` manifest | `5fb975564cfd437110990a5e048c1dcbd655298ef142faae117f38787dab83e5` |
| Controlled `M-REC-029` manifest | `3af498e14f242f7fc901c4ab63488ef25aefebc4438b75074ec23425ca9ec401` |

## Follow-up: compiled title receipts

[Manual run 38236046286](https://github.com/subvertnormality/mosaic/actions/runs/38236046286)
recorded its audio successfully and passed all 49 generation/browser stages
(124.2 minutes across timed stages). Its final audit passed the corrected fresh
MIDI admission and reader projection checks, then rejected an editorial title
overlay with `Compiled caption changed native contract`. No static preview was
uploaded from that failed package command.

The caption compiler already supports reviewed scene and step titles, with an
exact receipt for each changed field. The final checker still assumed the older
caption-only format: it treated `step_title_overlay`, changed step titles and
`scene_title_overlay` as native-contract edits. The three affected scenes are
`parameter-slot-endpoints`, `workflow-compose-two-channels` and
`workflow-second-channel`.

The final checker now validates the original title hash, revised title hash and
the producer's unchanged original contract hash for each title edit. Missing,
altered, extra or unneeded receipts remain rejected. Native inputs, expectations,
output bindings, citations, evidence, scene identity and step order remain bound
by the original complete native-body comparison. No capture or authored contract
pin was changed. The checker compares a copy and does not modify the raw or
compiled lesson.

Validation after this correction:

- A compiler-to-final-auditor regression fails on the unfixed checker with the
  same native-contract error, then passes on the correction.
- Affected caption, publication and generation-audit suites: 97 passed.
- Packaging and publisher suites: 58 passed.
- Related reader, publication, starting-state, MIDI receipt and build suites:
  119 passed.
- Replay against all 146 actual CI-compiled scenes: passed. For 61 scenes with
  editorial receipts, the baseline was reconstructed from the CI-compiled
  scene and recorded authored baseline wording; each reconstructed complete
  native contract exactly matches its recorded producer hash. This is a
  hash-verified reconstruction, not a new capture or relabelled native run.
- The old checker rejects exactly the three title-overlay scenes above.
- The replay rejects 438 mutations of native inputs, expectations and outputs.
  Additional regression boundaries reject citation, evidence, scene-owner and
  step-order changes, as well as malformed title receipts.

No generation or audio recording was repeated for this diagnosis. The recording
stimulus correction above remains independently validated; a new complete CI
campaign and a published artifact are still required.

| Title-audit evidence | SHA-256 |
| --- | --- |
| Failed manual command log (downloaded during evidence upload) | `12e4b662405d7819f0593e8efc5db0ef66de90dd9745ad444f85e9340b5862a8` |
| Complete CI generation evidence archive | `ae49849844d23d0ad84f7f4673288a6e21e15f6939a773547e63d47f6ae14b97` |
| Unfixed title-receipt regression log | `90665857cd39fb968357d3dcc3a3679a9b5ba118b6bc3ece5529125db3227f5e` |
| Actual CI-scene contract replay report | `9c8b54b141c082e289a42256dc4211156bd8848d75f75b22a79652d09e735943` |
