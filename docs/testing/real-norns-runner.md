# Real norns behaviour runner

`tests/behaviour/real_norns.py` is an additive exclusive-device smoke runner. It does not alter or replace the emulator-backed behaviour suite. It moves existing `/home/we/dust/code/mosaic`, `/home/we/dust/data/mosaic`, and `/home/we/dust/data/system.state` into a run-owned recovery directory before deploying the selected checkout. An active marker prevents a second run from overwriting unfinished recovery. Always run `restore` with the same run ID.

SSH credentials remain external. Use an agent, SSH config, key, or control socket through repeated `--ssh-option`; there is no password argument. Forward official Maiden port 5555 and run:

```sh
ssh -MN -S /tmp/norns.sock -L 15555:127.0.0.1:5555 -L 15556:127.0.0.1:5556 we@norns.local
python3 tests/behaviour/real_norns.py workflow --host norns.local --ssh-option=-S --ssh-option=/tmp/norns.sock --maiden-url ws://127.0.0.1:15555/ --crone-url ws://127.0.0.1:15556/ --source "$PWD" --run-id review-001 --artifacts ../mosaic-behaviour-runs/real-norns-review-001
python3 tests/behaviour/real_norns.py restore --host norns.local --ssh-option=-S --ssh-option=/tmp/norns.sock --maiden-url ws://127.0.0.1:15555/ --crone-url ws://127.0.0.1:15556/ --run-id review-001 --artifacts ../mosaic-behaviour-runs/real-norns-restore-001
```

The workflow loads the exact revision through Maiden, sends encoder/key input through matron's stock `/remote/enc` and `/remote/key` OSC routes, exports a screen screenshot, and retains capability, action, runtime, journal, and source evidence. It is a representative screen-visible smoke and sets `campaign_complete` false.

Stock norns has no remote grid-input endpoint or readable LED-state API. Maiden `_norns.grid.key` would bypass device/matron ingress, so grid actions are refused and grid cases are explicitly skipped. Exact MIDI and clock evidence requires a stable duplex ALSA endpoint; `aconnect` inventory alone is not acceptance. Screenshot file I/O stays outside timing measurements. This runner interrupts the current script and requires an explicitly scheduled exclusive-device window.
