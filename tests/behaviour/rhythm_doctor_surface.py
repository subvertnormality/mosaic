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
from rhythm_doctor import fifth_algorithm


def setup_frame(c, field, mode, bpm, input_source):
    c.ui.expect_rhythm_doctor_setup(field, mode, bpm, input_source)


def stopped_setup_controls(c):
    # The emulator public input is the native raw-detent path. Norns applies
    # Mosaic's default encoder sensitivity of 2 before calling the script, so
    # two raw detents are one logical encoder step at this boundary.
    detent = 2
    ui = c.ui
    # E2/E3 edit a draft. K2 must discard every field together.
    ui.rhythm_doctor_setup_field(-detent); c.elapse(.06)
    setup_frame(c, "INPUT", "auto", 120, "STEREO")
    ui.adjust_rhythm_doctor_setup_value(detent); c.elapse(.06)
    setup_frame(c, "INPUT", "auto", 120, "L")
    ui.rhythm_doctor_setup_field(-detent); ui.adjust_rhythm_doctor_setup_value(7 * detent); c.elapse(.06)
    setup_frame(c, "MANUAL BPM", "auto", 127, "L")
    ui.rhythm_doctor_setup_field(-detent); ui.adjust_rhythm_doctor_setup_value(detent); c.elapse(.06)
    setup_frame(c, "TEMPO", "manual", 127, "L")
    ui.rhythm_doctor_key_edge("discard_draft", True)
    ui.rhythm_doctor_key_edge("discard_draft", False); c.elapse(.06)

    # Reopen the draft from the unchanged Auto/120/Stereo values, then commit a
    # manual configuration and prove the committed values seed the next draft.
    ui.adjust_rhythm_doctor_setup_value(detent); c.elapse(.06)
    setup_frame(c, "TEMPO", "manual", 120, "STEREO")
    ui.rhythm_doctor_setup_field(detent); ui.adjust_rhythm_doctor_setup_value(7 * detent); c.elapse(.06)
    setup_frame(c, "MANUAL BPM", "manual", 127, "STEREO")
    ui.rhythm_doctor_setup_field(detent); ui.adjust_rhythm_doctor_setup_value(detent); c.elapse(.06)
    setup_frame(c, "INPUT", "manual", 127, "L")
    ui.rhythm_doctor_key_edge("apply_correction", True)
    ui.rhythm_doctor_key_edge("apply_correction", False); c.elapse(.06)
    ui.rhythm_doctor_setup_field(-detent); c.elapse(.06)
    setup_frame(c, "MANUAL BPM", "manual", 127, "L")
    ui.rhythm_doctor_key_edge("discard_draft", True)
    ui.rhythm_doctor_key_edge("discard_draft", False); c.elapse(.06)
    c.results.append(dict(kind="rhythm-doctor-setup", tempo="manual", manual_bpm=127,
                          input="L", contract="PLAN.md stopped-only setup draft, K2 discard and K3 commit"))


def owned_input_and_transport_gate(c):
    ui = c.ui
    fifth_algorithm(c)  # enters algorithm five and leaves CYM selected at x5,y2
    # Four lanes occupy columns 3-6 and the retired fifth column is inert, so
    # the selected lane is CYM at column 5; columns 6 and 7 must stay dark.
    active_lanes = {"BD": "blink_low", "SD": "blink_low", "CYM": "selected",
                    "withdrawn_BASS": "dark", "retired": "dark"}
    ui.expect_rhythm_doctor_lanes(active_lanes)
    stopped_setup_controls(c)

    # Record is an x1/y2 key-down claim.  Its owned key-up must not turn this
    # gesture into the legacy Pattern 1 fader action or lose lane selection.
    ui.rhythm_doctor_capture_edge(True); c.elapse(.08)
    ui.rhythm_doctor_capture_edge(False); c.elapse(.08)
    ui.expect_rhythm_doctor_lanes(active_lanes)
    c.results.append(dict(kind="rhythm-doctor-record-ownership", cell=[1, 2],
                          selected_lane="CYM", contract="PLAN.md Record key-down ownership"))

    # K2/K3 are routed through the Rhythm Doctor trigger screen while its fifth
    # algorithm is active.  On an unavailable worker they are inert, but still
    # must preserve the active page and lane rather than leaking a legacy edit.
    for key in (2, 3):
        ui.rhythm_doctor_key_edge("discard_draft" if key == 2 else "apply_correction", True)
        c.elapse(.04)
        ui.rhythm_doctor_key_edge("discard_draft" if key == 2 else "apply_correction", False)
        c.elapse(.06)
        ui.expect_rhythm_doctor_lanes(active_lanes)
    c.results.append(dict(kind="rhythm-doctor-norns-keys", keys=[2, 3],
                          selected_lane="CYM", contract="PLAN.md K2/K3 routing"))

    # Starting Mosaic transport gates capture controls.  A lane tap is still
    # received by the app, but must retain CYM until transport has stopped.
    ui.play(); c.elapse(.1)
    ui.select_rhythm_doctor_lane("CYM")
    ui.expect_rhythm_doctor_lanes(active_lanes)
    ui.stop(); c.elapse(.1)
    c.results.append(dict(kind="rhythm-doctor-transport-gate", attempted_lane="CYM",
                          retained_lane="CYM", contract="PLAN.md capture transport gate"))


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
    # Capture owns no private directory now, but a developer machine carries
    # leftovers from older runs. The property is that this run adds none, not
    # that the machine is clean.
    private_roots_before = {str(path) for path in Path("/tmp").glob("mosaic-rd-*")}
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
                strays = sorted({str(path) for path in Path("/tmp").glob("mosaic-rd-*")}
                                - private_roots_before)
                runtime_cleanup = dict(cancel=(runtime / "cancel").is_file(),
                                       analysis_pid=(runtime / "pid").exists(),
                                       analysis_process_alive=still_running(pid),
                                       capture_runtime=(c.data_directory / "rhythm-doctor-runtime").exists(),
                                       private_capture_roots=strays)
                assert not runtime_cleanup["analysis_process_alive"], runtime_cleanup
                # The capture worker and the private /tmp root it owned went with
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
