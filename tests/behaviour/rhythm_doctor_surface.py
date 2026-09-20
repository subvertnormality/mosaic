"""Player-visible Rhythm Doctor ownership and shutdown regression.

Characterisation outside the current README.  This intentionally uses only the
emulator's public grid/key input and observed LEDs/framebuffer.  It does not
claim that audio capture or inference works in controlled time.
"""
import argparse
import hashlib
import json
import shutil
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
    # The emulator public input is the native raw-detent path. Norns applies
    # Mosaic's default encoder sensitivity of 2 before calling the script, so
    # two raw detents are one logical encoder step at this boundary.
    detent = 2
    # E2/E3 edit a draft. K2 must discard every field together.
    c.action(type="enc", n=2, delta=-detent); c.elapse(.06)
    setup_frame(c, "INPUT", "auto", 120, "STEREO")
    c.action(type="enc", n=3, delta=detent); c.elapse(.06)
    setup_frame(c, "INPUT", "auto", 120, "L")
    c.action(type="enc", n=2, delta=-detent); c.action(type="enc", n=3, delta=7 * detent); c.elapse(.06)
    setup_frame(c, "MANUAL BPM", "auto", 127, "L")
    c.action(type="enc", n=2, delta=-detent); c.action(type="enc", n=3, delta=detent); c.elapse(.06)
    setup_frame(c, "TEMPO", "manual", 127, "L")
    c.action(type="key", n=2, state=1); c.action(type="key", n=2, state=0); c.elapse(.06)

    # Reopen the draft from the unchanged Auto/120/Stereo values, then commit a
    # manual configuration and prove the committed values seed the next draft.
    c.action(type="enc", n=3, delta=detent); c.elapse(.06)
    setup_frame(c, "TEMPO", "manual", 120, "STEREO")
    c.action(type="enc", n=2, delta=detent); c.action(type="enc", n=3, delta=7 * detent); c.elapse(.06)
    setup_frame(c, "MANUAL BPM", "manual", 127, "STEREO")
    c.action(type="enc", n=2, delta=detent); c.action(type="enc", n=3, delta=detent); c.elapse(.06)
    setup_frame(c, "INPUT", "manual", 127, "L")
    c.action(type="key", n=3, state=1); c.action(type="key", n=3, state=0); c.elapse(.06)
    c.action(type="enc", n=2, delta=-detent); c.elapse(.06)
    setup_frame(c, "MANUAL BPM", "manual", 127, "L")
    c.action(type="key", n=2, state=1); c.action(type="key", n=2, state=0); c.elapse(.06)
    c.results.append(dict(kind="rhythm-doctor-setup", tempo="manual", manual_bpm=127,
                          input="L", contract="PLAN.md stopped-only setup draft, K2 discard and K3 commit"))


def owned_input_and_transport_gate(c):
    fifth_algorithm(c)  # enters algorithm five and selects BASS at x6,y2
    # Four lanes occupy columns 3-6 and the retired fifth column is inert, so
    # the selected lane is BASS at column 6 and column 7 must stay dark.
    active_lanes = [(3, 2), (4, 2), (5, 2), (6, 2), (7, 2)]
    lanes_with_bass = [4, 4, 4, 15, 0]
    c.led_values(active_lanes, lanes_with_bass)
    stopped_setup_controls(c)

    # Record is an x1/y2 key-down claim.  Its owned key-up must not turn this
    # gesture into the legacy Pattern 1 fader action or lose lane selection.
    c.action(type="grid", x=1, y=2, state=1); c.elapse(.08)
    c.action(type="grid", x=1, y=2, state=0); c.elapse(.08)
    c.led_values(active_lanes, lanes_with_bass)
    c.results.append(dict(kind="rhythm-doctor-record-ownership", cell=[1, 2],
                          selected_lane="BASS", contract="PLAN.md Record key-down ownership"))

    # K2/K3 are routed through the Rhythm Doctor trigger screen while its fifth
    # algorithm is active.  On an unavailable worker they are inert, but still
    # must preserve the active page and lane rather than leaking a legacy edit.
    for key in (2, 3):
        c.action(type="key", n=key, state=1); c.elapse(.04)
        c.action(type="key", n=key, state=0); c.elapse(.06)
        c.led_values(active_lanes, lanes_with_bass)
    c.results.append(dict(kind="rhythm-doctor-norns-keys", keys=[2, 3],
                          selected_lane="BASS", contract="PLAN.md K2/K3 routing"))

    # Starting Mosaic transport gates capture controls.  A lane tap is still
    # received by the app, but must retain BASS until transport has stopped.
    c.tap(1, 8); c.elapse(.1)
    c.tap(5, 2)
    c.led_values(active_lanes, lanes_with_bass)
    c.tap(1, 8); c.elapse(.1)
    c.results.append(dict(kind="rhythm-doctor-transport-gate", attempted_lane="CYM",
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
                # Capture runs through softcut inside crone, so it starts no
                # process and owns no private directory. Analysis is still a
                # detached worker, and is the one thing left to tear down.
                runtime = c.data_directory / "rhythm-doctor-analysis-runtime"
                pid = int((runtime / "pid").read_text()) if (runtime / "pid").is_file() else None
                # Teardown is asynchronous, and a process that has exited but not
                # been reaped keeps its /proc entry as a zombie. Neither means the
                # helper is still running, so wait long enough for a loaded CI
                # container and read the process state rather than the directory.
                def still_running(number):
                    if number is None: return False
                    try:
                        stat = Path("/proc").joinpath(str(number), "stat").read_text()
                    except (FileNotFoundError, ProcessLookupError, PermissionError):
                        return False
                    # State is the field after the parenthesised command name.
                    return stat.rsplit(") ", 1)[-1].split(" ", 1)[0] not in ("Z", "X", "x")
                deadline = time.monotonic() + 30
                while still_running(pid) and time.monotonic() < deadline:
                    time.sleep(.1)
                strays = sorted(str(path) for path in Path("/tmp").glob("mosaic-rd-*"))
                runtime_cleanup = dict(cancel=(runtime / "cancel").is_file(),
                                       analysis_pid=(runtime / "pid").exists(),
                                       analysis_process_alive=still_running(pid),
                                       capture_runtime=(c.data_directory / "rhythm-doctor-runtime").exists(),
                                       private_capture_roots=strays)
                assert not runtime_cleanup["analysis_process_alive"], runtime_cleanup
                # The capture worker and its owned /tmp root were removed with
                # the JACK path; nothing may quietly bring them back.
                assert not runtime_cleanup["capture_runtime"], runtime_cleanup
                assert strays == [], runtime_cleanup
                if runtime_cleanup["analysis_pid"]:
                    shutil.rmtree(runtime / "ipc", ignore_errors=True)
                    runtime_cleanup["harness_removed_dead_mailbox"] = True
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
