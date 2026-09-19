"""Player-visible Rhythm Doctor ownership and shutdown regression.

Characterisation outside the current README.  This intentionally uses only the
emulator's public grid/key input and observed LEDs/framebuffer.  It does not
claim that audio capture or inference works in controlled time.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import time
import traceback

from driver import Driver
from frame_oracle import render, matches
from rhythm_doctor import fifth_algorithm


def setup_frame(c, field, mode, bpm, input_source):
    expected = render([
        (0, 9, 10, "RHYTHM DOCTOR"), (120, 9, 10, "m"),
        (0, 22, 10, "SETUP / " + field),
        (0, 34, 10, (">" if field == "TEMPO" else " ") + "TEMPO " + mode.upper()),
        (0, 46, 10, (">" if field == "MANUAL BPM" else " ") + "MANUAL BPM " + str(bpm)),
        (0, 58, 10, (">" if field == "INPUT" else " ") + "INPUT " + input_source),
    ])
    c.wait(lambda state: matches(state, expected))


def stopped_setup_controls(c):
    # E2/E3 edit a draft. K2 must discard every field together.
    c.action(type="enc", n=2, delta=-1); c.elapse(.06)
    setup_frame(c, "INPUT", "auto", 120, "STEREO")
    c.action(type="enc", n=3, delta=1); c.elapse(.06)
    setup_frame(c, "INPUT", "auto", 120, "L")
    c.action(type="enc", n=2, delta=-1); c.action(type="enc", n=3, delta=7); c.elapse(.06)
    setup_frame(c, "MANUAL BPM", "auto", 127, "L")
    c.action(type="enc", n=2, delta=-1); c.action(type="enc", n=3, delta=1); c.elapse(.06)
    setup_frame(c, "TEMPO", "manual", 127, "L")
    c.action(type="key", n=2, state=1); c.action(type="key", n=2, state=0); c.elapse(.06)

    # Reopen the draft from the unchanged Auto/120/Stereo values, then commit a
    # manual configuration and prove the committed values seed the next draft.
    c.action(type="enc", n=3, delta=1); c.elapse(.06)
    setup_frame(c, "TEMPO", "manual", 120, "STEREO")
    c.action(type="enc", n=2, delta=1); c.action(type="enc", n=3, delta=7); c.elapse(.06)
    setup_frame(c, "MANUAL BPM", "manual", 127, "STEREO")
    c.action(type="enc", n=2, delta=1); c.action(type="enc", n=3, delta=1); c.elapse(.06)
    setup_frame(c, "INPUT", "manual", 127, "L")
    c.action(type="key", n=3, state=1); c.action(type="key", n=3, state=0); c.elapse(.06)
    c.action(type="enc", n=2, delta=-1); c.elapse(.06)
    setup_frame(c, "MANUAL BPM", "manual", 127, "L")
    c.action(type="key", n=2, state=1); c.action(type="key", n=2, state=0); c.elapse(.06)
    c.results.append(dict(kind="rhythm-doctor-setup", tempo="manual", manual_bpm=127,
                          input="L", contract="PLAN.md stopped-only setup draft, K2 discard and K3 commit"))


def owned_input_and_transport_gate(c):
    fifth_algorithm(c)  # enters algorithm five and selects BASS at x7,y2
    bass = [(3, 2), (4, 2), (5, 2), (6, 2), (7, 2)]
    c.led_values(bass, [4, 4, 4, 4, 15])
    stopped_setup_controls(c)

    # Record is an x1/y2 key-down claim.  Its owned key-up must not turn this
    # gesture into the legacy Pattern 1 fader action or lose lane selection.
    c.action(type="grid", x=1, y=2, state=1); c.elapse(.08)
    c.action(type="grid", x=1, y=2, state=0); c.elapse(.08)
    c.led_values(bass, [4, 4, 4, 4, 15])
    c.results.append(dict(kind="rhythm-doctor-record-ownership", cell=[1, 2],
                          selected_lane="BASS", contract="PLAN.md Record key-down ownership"))

    # K2/K3 are routed through the Rhythm Doctor trigger screen while its fifth
    # algorithm is active.  On an unavailable worker they are inert, but still
    # must preserve the active page and lane rather than leaking a legacy edit.
    for key in (2, 3):
        c.action(type="key", n=key, state=1); c.elapse(.04)
        c.action(type="key", n=key, state=0); c.elapse(.06)
        c.led_values(bass, [4, 4, 4, 4, 15])
    c.results.append(dict(kind="rhythm-doctor-norns-keys", keys=[2, 3],
                          selected_lane="BASS", contract="PLAN.md K2/K3 routing"))

    # Starting Mosaic transport gates capture controls.  A lane tap is still
    # received by the app, but must retain BASS until transport has stopped.
    c.tap(1, 8); c.elapse(.1)
    c.tap(3, 2)
    c.led_values(bass, [4, 4, 4, 4, 15])
    c.tap(1, 8); c.elapse(.1)
    c.results.append(dict(kind="rhythm-doctor-transport-gate", attempted_lane="BD",
                          retained_lane="BASS", contract="PLAN.md capture transport gate"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-root", required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--artifacts", required=True)
    parser.add_argument("--experimental-install", required=True)
    parser.add_argument("--clock-mode", choices=["real-time", "controlled-experimental"], required=True)
    args = parser.parse_args()
    out = Path(args.artifacts); out.mkdir(parents=True, exist_ok=False)
    c = None; failure = cleanup_failure = None; runtime_cleanup = None
    try:
        c = Driver(out, app_root=args.app_root, clock_mode=args.clock_mode,
                   experimental_install=args.experimental_install)
        owned_input_and_transport_gate(c)
    except Exception:
        failure = traceback.format_exc()
    finally:
        if c is not None:
            try:
                c.finish()
                runtime = c.data_directory / "rhythm-doctor-runtime"
                pid = int((runtime / "pid").read_text()) if (runtime / "pid").is_file() else None
                socket_path = (runtime / "socket").read_text().strip() if (runtime / "socket").is_file() else None
                for _ in range(20):
                    if pid is None or not Path("/proc").joinpath(str(pid)).exists(): break
                    time.sleep(.05)
                runtime_cleanup = dict(cancel=(runtime / "cancel").is_file(),
                                       status_socket=(runtime / "socket").exists(), status_pid=(runtime / "pid").exists(),
                                       process_alive=bool(pid and Path("/proc").joinpath(str(pid)).exists()),
                                       owned_socket_alive=bool(socket_path and Path(socket_path).exists()))
                assert not runtime_cleanup["process_alive"], runtime_cleanup
                # The emulator tears down its native process group without the
                # norns script-switch cleanup callback. Remove only that dead
                # session's verified private socket directory; physical-norns
                # cleanup is exercised by the hardware runner.
                if runtime_cleanup["owned_socket_alive"]:
                    owned_socket = Path(socket_path); owned_root = owned_socket.parent
                    assert re.fullmatch(r"mosaic-rd-[0-9]+-[A-Za-z0-9]+", owned_root.name), owned_root
                    owned_socket.unlink(); owned_root.rmdir()
                    runtime_cleanup["harness_removed_dead_socket"] = True
            except Exception:
                cleanup_failure = traceback.format_exc()
    result = dict(case="RD-UI-002", passed=failure is None and cleanup_failure is None,
                  failure=failure, cleanup_failure=cleanup_failure, runtime_cleanup=runtime_cleanup,
                  declared_source_revision=args.source_revision,
                  source_identity=c.identity if c is not None else None,
                  recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  clock_mode=args.clock_mode, complete_regression_run=False,
                  scope="grid/key ownership, transport gate and runtime cleanup; no audio/inference claim")
    (out / "manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passed": result["passed"], "manifest": str(out / "manifest.json")}))
    return int(not result["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
