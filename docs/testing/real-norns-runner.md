# Real norns behaviour runner

`tests/behaviour/real_norns.py` adds an exclusive-device hardware lane. It does not change the emulator lane or Mosaic's normal local behaviour. The runner exports tracked `HEAD` with `git archive`, materializes the recorded `lib/nb` gitlink, builds a SHA-256 manifest, deploys only that clean tree, and verifies every deployed file before loading it.

## Recovery model

`workflow` creates an ownership marker and recovery copies of `/home/we/dust/code/mosaic`, `/home/we/dust/data/mosaic`, and `/home/we/dust/data/system.state` before clearing the active script. A failed run leaves those copies intact. `resume` requires the matching marker and rechecks the complete deployed-source manifest. `restore` returns code, data, and system state to their pre-run versions. `finalize` keeps the tested Mosaic source, restores the user's original data and system state, and removes temporary recovery state. Evidence remains on the test host.

Credentials stay in an SSH agent, config, key, or caller-supplied control socket. The preferred control transport is the official Maiden text WebSocket with subprotocol `bus.sp.nanomsg.org`; `--websocket-wheel` selects a pinned `websockets` wheel. The raw nanomsg client remains a fallback. Use a persistent SSH forward:

```sh
ssh -MN -S /tmp/norns.sock -L 15555:127.0.0.1:5555 we@norns.local
```

## Inputs and observations

`--maiden-input` invokes Mosaic's `enc(n,d)` and `key(n,z)` callbacks after the stock norns encoder-processing boundary. This gives deterministic single-tick actions without bypassing Mosaic's hardware callback. `--osc-via-ssh` is a transport-conformance option for stock `/remote/enc` and `/remote/key`; it is not used for timing cases because opening and retiring control peers adds settling latency.

`--synthetic-grid` auto-discovers the live `grid.devices` ID and calls stock `_norns.grid.key(id,x,y,state)` with 1-based coordinates. It reaches the same script callback as a physical grid event, but bypasses serialosc and electrical ingress. The evidence labels it accordingly.

Monome grids have no query-current-LED-state command. During a hardware case the runner temporarily wraps `_norns.grid_set_led`, `_norns.grid_all_led`, and `_norns.monome_refresh`, records their arguments, and forwards every call to the original driver. It reconstructs the effective 16×8 physical state using the stock low-nibble conversion (`value & 15`) while retaining raw signed driver values. This covers assertions for every behavior case that reads grid LEDs without requiring a camera. It proves the commands sent to the attached grid, not that individual LEDs emitted light. A camera or human observer would be required for photon-level confirmation and is not an automated acceptance dependency.

The runner similarly wraps and forwards `_norns.midi_send`. The `M-PAT-001` case records musical messages and omits one-byte MIDI real-time traffic so observation does not add material matron load. MIDI timestamps come from `util.time()` on the norns. Screen evidence uses the real 640×384 framebuffer through `screen.export_screenshot`.

## M-PAT-001

The first hardware behavior case runs the registered `cases.py` four-note recipe through `HardwareDriver`; the hardware runner does not carry a second copy of its gestures or musical expectations. The adapter uses the existing behavior-suite MIDI descriptor as opt-in isolated test data, finds that map by ID rather than assuming selector order, performs user-level grid/key/encoder gestures, and asserts:

- the configured pattern LED and edited note LED at the norns grid-driver boundary;
- C-D-E-F and edited C-D-E-G MIDI phrases over at least three complete cycles;
- note-off cleanup after Stop;
- sixteenth-note spacing derived from the norns' live tempo, within 20 ms;
- both selected-pattern blink phases; and
- two valid, changing norns framebuffer captures.

```sh
python3 tests/behaviour/real_norns.py case \
  --case M-PAT-001 \
  --config-source tests/behaviour/config \
  --device-map-id emu-test \
  --host norns.local \
  --ssh-option=-S --ssh-option=/tmp/norns.sock \
  --maiden-url ws://127.0.0.1:15555/ \
  --websocket-wheel /path/to/pinned/websockets-wheel.whl \
  --osc-host norns.local \
  --maiden-input --synthetic-grid \
  --source "$PWD" --run-id review-001 \
  --artifacts ../mosaic-behaviour-runs/real-norns-review-001
```

As of 2026-09-13, this case passed on a physical norns at source revision `6f4ac36942c5e24c817a71882bc68644d97a24a6`: all 1,061 deployed files matched, both MIDI phrases passed at 122 BPM, and the worst measured sixteenth-note error was 4.53 ms. The successful run used the emulator project's narrow `0011-clock-cancel-queued-resume.patch` against the device's norns runtime. Stock norns reproducibly queued a resume after Mosaic cancelled the corresponding thread and failed at `core/clock.lua:58` with `thread expected` on Stop. The candidate ignores only missing integer IDs that were previously allocated; arbitrary unknown IDs still fail. This is a norns runtime limitation, not a green stock-hardware claim.

The hardware mode currently implements `M-PAT-001`, the generic smoke, and a dedicated stock-norns `clock.cancel` queued-resume comparison. Performance/load, musical timing and drift, and MIDI master/slave sync remain focused targets until their hardware adapters and oracles are implemented. The broad functional suite remains emulator coverage; a recipe is never treated as hardware-compatible merely because it happens to call methods present on the adapter.

`clock-cancel` runs the same queued-resume probe against the installed stock `clock.lua`, atomically installs a caller-supplied complete candidate file, reruns the probe, and restores the fetched stock bytes in `finally`. It verifies and records the stock, candidate, and restored SHA-256 values, then reloads the previously active script. The procedure does not reboot norns or restart JACK:

```sh
python3 tests/behaviour/real_norns.py clock-cancel \
  --clock-cancel-candidate /path/to/candidate/clock.lua \
  --host norns.local --maiden-url ws://127.0.0.1:15555/ \
  --run-id clock-cancel-001 \
  --artifacts ../mosaic-behaviour-runs/clock-cancel-001
```

The applicability command is local and contacts no hardware. It emits capabilities plus one fail-closed row for every registered case, distinguishing implemented, targeted-but-deferred, controlled-only, emulator-only fault injection, and broad emulator coverage:

```sh
python3 tests/behaviour/real_norns.py applicability
```

Physical grid ingress, external cable transmission, audio output, Crow, n.b., controlled time, and framebuffer text recognition are outside this increment's evidence.

The same report describes the performance adaptation boundary. `perf_dense.py` can reuse the adapter's ordered MIDI/grid observations, but still needs an on-device resource sampler and device threshold calibration. `perf_input.py` additionally needs scheduled external-MIDI ingress with an accepted/delivered ledger and comparable acknowledgement times. `perf_overload.py` needs a bounded on-device load generator, resource samples that bracket it, and a revision-based visual recovery oracle. These execution paths remain deferred so emulator-native scheduler logs and container throttling counters are not relabelled as hardware measurements. `perf_storage.py` remains outside the hardware timing suite because its current recipe defines no storage-speed threshold or musical timing correlation.

Running hardware mode interrupts the active script and requires exclusive access to the device. Screenshot file I/O and config seeding occur outside musical timing claims.
