# Reproduce the pilot

Run from this fresh checkout. Python requires PyYAML and jsonschema; the capture environment is Linux with the emulator's independently built native norns runtime, JACK and SuperCollider.

```sh
export MONOME_EMULATOR=/home/andy/projects/monome-emulator-ci-combined
python3 tools/manual_capture.py --mod-code-root /home/andy/mosaic-manual-voices
python3 -m http.server 8000
# open http://localhost:8000/manual/
```

The first command validates the YAML, checks the cited existing behaviour cases, replays authored scenes, records full live frame and grid data, verifies musical output, captures multi-voice audio and publishes generated output only after every required stage succeeds. Raw immutable evidence is stored outside the checkout; the concise report records its path and hashes.

Optional `--visuals-only` is a development command and reports incomplete audio. `--clock-mode controlled-experimental --experimental-install PATH` checks visual/MIDI scenes in logical time; audio always requires real time. Controlled time is diagnostic evidence, not hardware scheduling acceptance.

Schema and contracts: `python3 -m unittest discover -s tests/behaviour -p test_manual_model.py`.
Full existing Lua suite: `cd lib/tests && lua run_tests.lua`.
Changing a caption changes the generated data hash; changing an input must replay to a new captured consequence or fail its semantic expectation. No synthetic fallback frames or substitute oscillator audio are provided.
