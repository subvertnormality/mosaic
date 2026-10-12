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
