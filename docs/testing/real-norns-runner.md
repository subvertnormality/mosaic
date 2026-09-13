# Real norns behaviour runner

`tests/behaviour/real_norns.py` is an additive exclusive-device smoke runner; the emulator suite is unchanged. It exports tracked `HEAD` with `git archive`, separately materializes the recorded `lib/nb` gitlink, builds a SHA256 manifest, deploys only that clean tree, and verifies every file remotely before loading it.

The runner creates an ownership marker and copies `/home/we/dust/code/mosaic`, `/home/we/dust/data/mosaic`, and `/home/we/dust/data/system.state` before asking Maiden to clear the running script. A failed run retains those recovery copies. `restore` validates the run ID, restores all three and reloads the prior script. `finalize` is a separate explicit action: it keeps the tested Mosaic installation, restores the user's original Mosaic data and system state, and removes the temporary recovery copies; the local source manifest, screenshots and evidence remain.

Credentials stay in an SSH agent/config/key/control socket supplied through repeated `--ssh-option`. The runner talks directly to Maiden's official nanomsg BUS WebSocket with `ctypes`; provide its host `libnanomsg` path if `libnanomsg.so.5` is unavailable. Key and encoder inputs are correctly padded OSC packets sent from Python, so the device does not need `oscsend`. Example:

```sh
ssh -MN -S /tmp/norns.sock -L 15555:127.0.0.1:5555 we@norns.local
python3 tests/behaviour/real_norns.py workflow --host norns.local --ssh-option=-S --ssh-option=/tmp/norns.sock --maiden-url ws://127.0.0.1:15555 --osc-host norns.local --osc-port 10111 --source "$PWD" --run-id review-001 --artifacts ../mosaic-behaviour-runs/real-norns-review-001
python3 tests/behaviour/real_norns.py restore --host norns.local --ssh-option=-S --ssh-option=/tmp/norns.sock --maiden-url ws://127.0.0.1:15555 --osc-host norns.local --run-id review-001 --artifacts ../mosaic-behaviour-runs/real-norns-restore-001
```

The workflow captures validated 640x384 PNGs before and after normal `/remote/enc` and `/remote/key` controls and requires the screen hash to change. It retains source hashes, capability inventory, packets and runtime logs. ALSA discovery is capability evidence only; exact MIDI/clock acceptance needs a stable duplex ALSA endpoint.

Stock norns exposes no remote physical-grid input or LED readback. `--synthetic-grid --grid-device-id N` optionally invokes `_norns.grid.key` for a clearly labelled Lua-only visible smoke; it bypasses device/matron ingress. Physical grid input and LED readback remain skipped and `campaign_complete` remains false. Screenshot file I/O stays outside timing claims. Running this mode interrupts the active script and requires an exclusive-device window.
