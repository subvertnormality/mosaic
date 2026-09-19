# Performance improvement passes

Mosaic performance work uses the emulator's opt-in norns performance profile
(`monome-emulator` branch `codex/norns-performance-calibration`,
`docs/testing/norns-calibration/PROFILE.md`). Profile `cm3plus-norns-260102`
v1.0.0 reproduces physical-norns pass/fail for Lua-thread-bound sequencing,
slides, rendering and Lua-overload recovery. Timing magnitudes are within about
0.7–1.4×, validated against a CM3+ norns on two host types. It is screening
evidence; accepted wins are confirmed on hardware.

## Setup (once per host)

```sh
cd /path/to/monome-emulator
./dev/emu fetch --locked && ./dev/emu build
python3 scripts/build_performance_profile_runtime.py --output .runtime/performance-profile
python3 scripts/calibration/native_probe_run.py --output /tmp/probe --repeats 3 \
  --experimental-install .runtime/performance-profile/installation.json \
  --performance-profile profiles/norns/cm3plus-norns-260102.json
python3 scripts/calibration/profile_check.py --profile profiles/norns/cm3plus-norns-260102.json --probe-run /tmp/probe
```

Do not use a host whose check fails.

## 1. Find hot paths

```sh
MONOME_EMULATOR=/path/to/monome-emulator python3 tests/behaviour/perf_calibration_emulator.py \
  --case PERF-002-HW-16 --output ../mosaic-behaviour-runs/<name> --windows 4 \
  --experimental-install <installation.json> --lua-profile 1000
```

`lua-profile-windows.json` lists instruction samples for the measured windows
only. Functions are inclusive, lines are self. Counts are deterministic Lua work
and do not depend on host speed, so they are the most sensitive regression
signal. Profiled runs are never timing evidence. In PERF-002-HW-4 about
two-thirds of window samples were in `lib/clock/m_lattice.lua` `pulse`, and
about a quarter in screen redraw (`mosaic.lua redraw` → `lib/ui.lua` → page
draw).

## 2. Measure a change (A/B)

```sh
MONOME_EMULATOR=/path/to/monome-emulator python3 tests/behaviour/perf_campaign.py \
  --baseline <revision-or-tree> --candidate <revision-or-tree> \
  --install <installation.json> --profile <profile.json> \
  --cases PERF-002-HW-4,PERF-002-HW-16,PERF-003-HW-16,PERF-005-HW-4 \
  --repeats 3 --lua-profile 1000 --output ../mosaic-behaviour-runs/<name>
```

The runner:

- calibrates the host once and pins that Lua factor for every run;
- alternates A/B order between repeats;
- claims `improved` or `regressed` only when the per-repeat medians do not
  overlap, and needs at least 3 repeats to claim anything.

`report.md` lists timing medians, pass counts, instruction-sample change and the
hottest functions for both trees.

Cases:

| Case | Use |
|---|---|
| PERF-002-HW-1/4/8/16 | dense sequencing; the device knee is between 1 and 4 channels |
| PERF-003-HW-1/8/16 | parameter slides |
| PERF-005-HW-1/4 | dense sequencing with UI rendering pressure |
| PERF-008L-HW-4 | recovery after a fixed Lua overload |
| MIX-HW-8 | slides, rendering and overload together |
| PERF-009-HW-4/8/16 | dense sequencing with four CC trig parameters per channel: defaults sent on every step, locks on steps 1 and 9, no slides (not part of profile validation; needs its own device baseline) |
| PERF-EXT-HW-16 | stress probe at any tempo: a four-note chord, three locked CCs and a sliding CC on every channel, every other step |
| PERF-010-HW-16 | the PERF-EXT-HW-16 project at 200 bpm, gated: about 1,080 messages a second, the capacity of one MIDI 1.0 port. The capture times writes on the norns, not DIN delivery |

The gated 16-channel cases fix their tempo: PERF-002-HW-16, PERF-003-HW-16 and
PERF-009-HW-16 at 130 bpm, PERF-010-HW-16 at 200 bpm. The runner sets it and refuses a
`--tempo` that differs. The smaller cases take `--tempo`, and calibrate against the
emulator lane at the norns default of 90 bpm.

## 3. Confirm on hardware

Run the same cases on the norns with `tests/behaviour/real_norns.py performance`
(see `real-norns-runner.md`). Use `--device-map-id cc_device --stock-clock-errors
record --measured-windows 4` (and `--tempo 90` for the calibration cases), and follow
each case with `restore`.

## Limits that affect interpretation

- **Pure arithmetic Lua loops** are under-modelled 1.7–2.4×. Cache-heavy table
  access runs about 2× slow. A change that only removes numeric loops, or only
  table lookups, needs hardware confirmation of its size.
- **Intermittent device spikes** (about one window in four, 12–16 ms) are not
  reproduced, so single-window hardware failures at low load are noise.
- **Not modelled:** background CPU contention, screen render thread, audio load,
  storage, mods.
- **Thresholds:** keep all musical timing thresholds unchanged. Retain failed
  runs.
