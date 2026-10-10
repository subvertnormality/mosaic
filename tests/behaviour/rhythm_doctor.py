"""Rhythm Doctor proposed user contract; characterisation outside current README.

PLAN.md User contract: fifth button is native (16,2); existing IDs do not move.
This acceptance is intentionally red until RD-04 is integrated after RD-02.
PCM/inference timing is real-time only; this UI mapping also admits controlled time.
"""
import argparse
import hashlib
import json
from pathlib import Path
import traceback

from driver import Driver


def fifth_algorithm(c, route="R01"):
    """Enter algorithm five; `route` is the Doctor screen it opens (R01 with no
    bank, R05 WINDOW with a READY bank), whose exact title row is asserted."""
    ui = c.ui
    ui.tap_control("pattern_editor")
    # Exercise legacy enum positions through ordinary input before selecting 5.
    for algorithm, column, name in (("drum", 12, "Drum algorithm"),
                                    ("tresillo", 13, "Tresillo algorithm"),
                                    ("euclidean", 14, "Euclidean algorithm"),
                                    ("numeric_repetitor", 15, "Numeric repetitor")):
        ui.select_rhythm_doctor_algorithm(algorithm)
        ui.expect_rhythm_doctor_tooltip(name + " selected")
        c.results.append(dict(kind="legacy-algorithm-tooltip", column=column, name=name,
                              contract="PLAN.md: first four algorithms keep IDs and controls"))
    ui.select_rhythm_doctor_algorithm("rhythm_doctor")
    try:
        ui.expect_rhythm_doctor_header(route)
    except Exception as error:
        raise AssertionError("RD-04: fifth algorithm button must display RHYTHM DOCTOR") from error
    c.results.append(dict(kind="screen-header", expected="RHYTHM DOCTOR", matched=True,
                          contract="PLAN.md User contract and coordinate convention"))
    # Three lanes at x3..x5. x2 stays reserved, and x6 and x7 are inert: both
    # carried a lane before the set shrank, so they must go dark rather than
    # leave lanes the player can see but not select.
    ui.expect_rhythm_doctor_lanes({"reserved": "dark", "BD": "selected", "SD": "blink_low",
                                   "CYM": "blink_low", "withdrawn_BASS": "dark", "retired": "dark"})
    c.results.append(dict(kind="rhythm-doctor-lanes", selected="BD", selected_coordinate=[3, 2],
                          reserved_coordinate=[2, 2],
                          contract="README: x2 reserved; x3..5 select BD/SD/CYM"))
    ui.select_rhythm_doctor_lane("CYM")
    ui.expect_rhythm_doctor_lanes({"BD": "blink_low", "SD": "blink_low", "CYM": "selected",
                                   "withdrawn_BASS": "dark", "retired": "dark"})
    c.results.append(dict(kind="rhythm-doctor-lane-selection", selected="CYM",
                          coordinate=[5, 2], contract="README: CYM is native x5,y2"))
    # x6 carried BASS until that lane was withdrawn.
    ui.tap_control("withdrawn_lane_bass")
    ui.expect_rhythm_doctor_lanes({"BD": "blink_low", "SD": "blink_low", "CYM": "selected",
                                   "withdrawn_BASS": "dark", "retired": "dark"})
    c.results.append(dict(kind="rhythm-doctor-withdrawn-column", coordinate=[6, 2],
                          retained_lane="CYM",
                          contract="README: columns 6 and 7 are inert"))
    ui.tap_control("retired_lane")
    ui.expect_rhythm_doctor_lanes({"BD": "blink_low", "SD": "blink_low", "CYM": "selected",
                                   "withdrawn_BASS": "dark", "retired": "dark"})
    c.results.append(dict(kind="rhythm-doctor-retired-column", coordinate=[7, 2],
                          retained_lane="CYM",
                          contract="README: column 7 is inert"))


def phrase_navigation(c):
    """The move buttons browse the recording in Rhythm Doctor, and only there.

    Columns 10, 11 and 12 of row 8 shift a previewed pattern in every other
    algorithm. In algorithm 5 they page the four-bar window and return to the
    calculated phrase start, and they must do so while the player is BROWSING
    -- not only while a paint preview is up, which is precisely when they have
    stopped browsing and decided what to paint.
    """
    # Algorithm 5 with nothing captured: the buttons answer, and what they
    # answer is that there is no window yet -- not "Shift reset", which would
    # mean they were still shifting a paint pattern.
    c.ui.select_rhythm_doctor_algorithm("rhythm_doctor")
    for x, label in ((11, "centre"), (10, "left"), (12, "right")):
        try:
            c.ui.tap_rhythm_doctor_phrase_button(label)
            c.ui.expect_rhythm_doctor_tooltip("NOT_READY")
        except Exception as error:
            raise AssertionError(
                "RD phrase navigation: %s button (x%d,y8) must act in algorithm 5 "
                "without a paint preview" % (label, x)) from error
        c.results.append(dict(kind="rhythm-doctor-phrase-navigation", coordinate=[x, 8],
                              button=label, outcome="NOT_READY",
                              contract="README: centre returns to the phrase start, "
                                       "the sides page a four-bar phrase"))

    # Algorithm 1 keeps the paint shift these buttons have always had.
    c.ui.select_rhythm_doctor_algorithm("drum")
    c.ui.tap_control("shift_reset")
    c.results.append(dict(kind="paint-shift-unchanged-elsewhere", coordinate=[11, 8],
                          algorithm="Drum algorithm",
                          contract="README: in every other algorithm the move buttons "
                                   "still shift a previewed pattern"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-root", required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--artifacts", required=True)
    parser.add_argument("--experimental-install", required=True)
    parser.add_argument("--clock-mode", choices=["real-time", "controlled-experimental"], required=True)
    args = parser.parse_args()
    out = Path(args.artifacts)
    out.mkdir(parents=True, exist_ok=False)
    c = None
    failure = cleanup_failure = None
    try:
        c = Driver(out, app_root=args.app_root, clock_mode=args.clock_mode,
                   experimental_install=args.experimental_install)
        fifth_algorithm(c)
        phrase_navigation(c)
    except Exception:
        failure = traceback.format_exc()
    finally:
        if c is not None:
            try:
                c.finish()
            except Exception:
                cleanup_failure = traceback.format_exc()
    result = dict(case="RD-UI-001", passed=failure is None and cleanup_failure is None,
                  failure=failure, cleanup_failure=cleanup_failure,
                  declared_source_revision=args.source_revision,
                  source_identity=c.identity if c is not None else None,
                  recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  clock_mode=args.clock_mode, complete_regression_run=False,
                  scope="fifth algorithm UI and phrase navigation; "
                        "no audio or classification claim")
    (out / "manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passed": result["passed"], "manifest": str(out / "manifest.json")}))
    return int(not result["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
