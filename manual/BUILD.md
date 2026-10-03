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

Browser acceptance: `NODE_PATH=/home/andy/mosaic-manual-tools/node_modules node tests/behaviour/manual_browser.cjs` while the loopback preview is running on port 8765. This checks exact screen/grid rendering, navigation, responsive layouts and audio decoding/synchronisation.

Published binding audit: `python3 tools/manual_verify.py`. This validates source freshness, native observation hashes, exact semantic contracts, every captured screen/grid pair and the separate pilot audio case in `contracts.json`.
