# Rebuild the complete manual

Run this from the fresh manual checkout. Each native installation must match
its own emulator checkout. The modulation sources are separate from the audio
voice sources. Python requires PyYAML and jsonschema; browser checks require
the isolated Playwright install.

```sh
python3 tools/manual_build.py \
  --emulator /home/andy/projects/monome-emulator-ci-combined \
  --real-install /home/andy/projects/monome-runtime-candidates/final-qualification-controlled-01/installation.json \
  --controlled-install /home/andy/projects/monome-runtime-candidates/final-qualification-controlled-01/installation.json \
  --readability-real-install /home/andy/projects/monome-runtime-candidates/final-qualification-controlled-01/installation.json \
  --audio-emulator /home/andy/projects/monome-emulator-behaviour-audio-crow \
  --audio-install /home/andy/projects/monome-emulator-behaviour-audio-crow/.runtime/combined-audio-crow-tools-01/installation.json \
  --mod-code-root /home/andy/mosaic-manual-voices \
  --modulation-code-root /home/andy/projects/mosaic-output-mods \
  --ffmpeg /home/andy/mosaic-manual-tools/imageio_ffmpeg/binaries/ffmpeg-linux64-v4.2.2 \
  --node-path /home/andy/mosaic-manual-tools/node_modules
```

Add `--plan-only` to inspect every command without starting native sessions or
changing files. `--plans scene-plans.yaml` selects an explicit plan file; repeat
it for several files. Leaving it unset selects every `manual/scene-plans*.yaml`.
Separate `--modulation-emulator` and `--modulation-controlled-install` options
are available when modulation needs a different matching checkout/runtime.

The command replays Masks and the independently authored First sound walkthrough
in separate real and controlled lanes. First sound starts from its empty-project
fixture, runs the full M-PAT-001 baseline and verifies its own equal-note phrase
and screen/grid expectations; its real lane publishes while its controlled lane
keeps evidence only. Both use the external native lock. Its authored source
manual/features/first-sound-capture.yaml remains indexed during scene refresh.
The command then replays
each case-derived plan/profile in both lanes, publishes only real-time scenes,
and regenerates every musical example with the matching audio checkout. DSP
audio uses real time. Device-picker scenes are then projected from the successful audio runs, using matched native fields and semantic assertions rather than fixed observation indices. The projection retains each pre-confirmation frame and the subsequent K3 action.

The readability plan replays the canonical public-input workflow in both lanes.
Its 17 checkpoints capture actual Assignment detail overflow with UI motion Off and On, fitting
Clock and Scale text stability, unchanged overviews and the same musical output.
Ten checkpoints additionally match the exact frozen eight-pose mini-header atlas
for Trig Params, Clock, Scale and Masks with motion Off/On, plus Clock at 40 and
240 BPM. Slow and normal loops must expose every distinct authored pose; the
fast case retains bounded redraw behavior without requiring every pose.
It does not claim a native overflowing vertical field where none is reachable;
that boundary remains separate component evidence.

Reason and Swing plans load the separately pinned local case helper with `--extra-cases`; the original native-case registry remains unchanged.

Doctor's Manual and stock Auto workflows run through the public stereo ADC in
real time, with their exact report paths and hashes captured from each command.
The independent collection publisher checks both immutable reports, native
frames, preview/paint LEDs, emitted MIDI, actual recorded PCM, local analysis
and cleanup before writing either scene. Controlled-time audio is explicitly
inapplicable. No latest-directory inference or synthetic fallback is used.

Doctor option qualification is a separate mandatory seven-run gate. It runs
Manual Stereo, Auto Left and Manual Right through actual ADC audio in real time,
then Setup and Ready controls in both real and controlled lanes. Manual Right
also exports a genuine application-autosaved Ready project. Each Ready run uses
only that same build stage's finalized fixture, with its exact hash checked
before the native driver imports the seed. The three audio runs have no
controlled-time substitute.

The builder resolves all seven report paths from successful, hashed stage logs
and receipts. A separate `doctor-options-audit` stage independently checks those
reports and the exact Ready fixture. Qualification reports retain their
`doctor-options-qualification` identity; they do not replace Doctor's two
published teaching scenes. A complete build requires all seven gates and this
independent audit, in addition to feature/course readiness and browser checks.

Case and audio capture tools own their native lock;
generic Masks captures use the same lock externally.

After capture, the command refreshes the complete scene-source index, rebuilds
inventory, compiled manual and quick reference, then audits native bindings
and runs the renderer, complete-book and audio-race browser checks against a
temporary loopback preview. It archives obsolete generated scene publications
before replacing their index entries; immutable native run evidence remains
unchanged. Failed runs retain their stage logs and never claim a completed
build. Individual successful capture publications may already have updated
when a later stage fails.

Every build gets a fresh evidence directory under
`/home/andy/mosaic-manual-build-runs`, with a manifest written once, source
snapshots and stage hashes. `complete_regression_run` remains false: rebuilding
the manual is distinct from the exhaustive behaviour campaign, and controlled
time is diagnostic evidence.

The default quick reference is staged at
`manual/generated/quick-reference.html`. After the coordinated authority
migration, add `--quick-output cheat_sheet.html` to regenerate the existing
public URL. The builder does not independently change README/AGENTS authority.
`--skip-browser-tests` is a development option; its omission is required for
complete renderer validation.


# Reproduce the pilot

Run from this fresh checkout. Python requires PyYAML and jsonschema; the capture environment is Linux with the emulator's independently built native norns runtime, JACK and SuperCollider.

```sh
export MONOME_EMULATOR=/home/andy/projects/monome-emulator-ci-combined
python3 tools/manual_capture.py \
  --mod-code-root /home/andy/mosaic-manual-voices \
  --audio-emulator /home/andy/projects/monome-emulator-behaviour-audio-crow \
  --audio-install /home/andy/projects/monome-emulator-behaviour-audio-crow/.runtime/combined-audio-crow-tools-01/installation.json \
  --ffmpeg /home/andy/mosaic-manual-tools/imageio_ffmpeg/binaries/ffmpeg-linux64-v4.2.2
python3 -m http.server 8000 --bind 127.0.0.1
# open http://localhost:8000/manual/
```

The first command validates the YAML, checks the cited existing behaviour cases, replays authored scenes, records full live frame and grid data, verifies musical output, captures multi-voice audio and publishes generated output only after every required stage succeeds. Raw immutable evidence is stored outside the checkout; the concise report records its path and hashes.

Optional `--visuals-only` is a development command and reports incomplete audio. `--clock-mode controlled-experimental --experimental-install PATH` checks visual/MIDI scenes in logical time; audio always requires real time. Controlled time is diagnostic evidence, not hardware scheduling acceptance.

Schema and contracts: `python3 -m unittest discover -s tests/behaviour -p test_manual_model.py`.
Full existing Lua suite: `cd lib/tests && lua run_tests.lua`.
Changing a caption changes the generated data hash; changing an input must replay to a new captured consequence or fail its semantic expectation. No synthetic fallback frames or substitute oscillator audio are provided.

The independent audio checkout is pinned at `801fcdcb9711e1054d898971942982862a30daf6`; the visual/MIDI checkout at `05fe7a1743f8517eaabb9184f2541e8bd6586935`. Each native installation must match its own checkout lock. The tool isolates application/data directories and closes sessions, releases holds, stops transport and panics notes even on failure. It never modifies the emulator.

`--reuse-visuals RUN_DIRECTORY` is a recovery option: it verifies the original authoring hash, unchanged scene inputs/expectations and preserved result/frame hashes before reusing successful native observations. Audio changes still require a new recording. Original failed reports remain immutable. The ordinary command above replays everything.

Browser acceptance, with the loopback preview running (the default test URL is port 8765):

```sh
export NODE_PATH=/home/andy/mosaic-manual-tools/node_modules
# Set MOSAIC_MANUAL_URL=http://localhost:8000/manual/ if using the server above.
node tests/behaviour/manual_inline.cjs
node tests/behaviour/manual_browser.cjs
node tests/behaviour/manual_book_browser.cjs
node tests/behaviour/manual_audio_race.cjs
```

These checks cover the native Masks controls, all feature destinations and referenced scene pixels/LEDs, every encoded audio example, seeking through every captured timeline frame, responsive layouts, header placement and a delayed audio download while changing examples. The audio race test must pass on the normal source. `MOSAIC_AUDIO_UNFIXED=1` is an explicit regression-evidence mode that removes the load-version guard from the browser response; it must fail because the earlier sound replaces the selected sound. Its source identity and failure are preserved in `evidence/audio-race-red.log`.

Published binding audit: `python3 tools/manual_verify.py`. This validates source freshness, native observation hashes, exact semantic contracts, every captured screen/grid pair and the separate pilot audio case in `contracts.json`.

Fresh publication is audited before editorial or teaching bindings are updated.
The build records exact terminal capture report paths and hashes for both clock
lanes. Caption receipt refresh preserves native publication bytes and desired
wording. Course binding requires the complete continuous project: ten scenes,
48 checkpoints and all 38 teaching stages in both lanes. Feature binding uses
successful current build receipts and the independently audited native scenes.
Each binding stage stores immutable before/after sources and audit receipts in
its own new evidence directory. A completed build additionally requires the
compiled manual's feature and course readiness; incomplete content fails the
completion gate even when the capture plan and browser checks pass.

The final browser checks also run `manual_controls_browser.cjs` against the freshly compiled manual to verify that pictured grid and norns controls navigate to the relevant teaching pages. The complete default plan contains 72 stages for its 18 scene plans.

The real readability stage requires `--readability-real-install`: an explicitly qualified installation exposing the native MIDI output boundary. It remains a real-time lane; capture participants retain the selected installation path, hash and runtime identity. Other real reference stages retain their default installations. Missing configuration fails before capture; there is no timing fallback.

Generic real-time Masks, First sound and reference captures require `--real-install`, matching the qualified runtime selection used by the behaviour campaign. Musical comparison MIDI workers receive it explicitly as `--midi-real-install`; their clock mode remains real time. Controlled MIDI uses its separate explicit installation. The existing readability override and profile-specific Doctor/DSP audio installation remain explicit.
