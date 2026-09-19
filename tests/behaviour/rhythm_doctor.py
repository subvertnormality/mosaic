"""Rhythm Doctor proposed user contract; characterisation outside current README.

PLAN.md User contract: fifth button is native (16,2); existing IDs do not move.
This acceptance is intentionally red until RD-04 is integrated after RD-02.
PCM/inference timing is real-time only; this UI mapping also admits controlled time.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import traceback

from driver import Driver
from frame_oracle import render, matches


def fifth_algorithm(c):
    c.tap(5, 8)
    # Exercise legacy enum positions through ordinary input before selecting 5.
    for x, name in ((12, "Drum algorithm"), (13, "Tresillo algorithm"),
                    (14, "Euclidean algorithm"), (15, "Numeric repetitor")):
        c.tap(x, 2)
        literal = render([(0, 62, 10, name + " selected")])
        region = [((y * 128 + x) * 4 + channel)
                  for y in range(55, 64) for x in range(128) for channel in range(3)]
        def expected_legacy(state):
            actual = base64.b64decode(state["frame"]["pixels_base64"])
            return all(actual[i] == literal[i] for i in region)
        c.wait(expected_legacy)
        c.results.append(dict(kind="legacy-algorithm-tooltip", column=x, name=name,
                              contract="PLAN.md: first four algorithms keep IDs and controls"))
    c.tap(16, 2)
    expected = render([(0, 9, 10, "RHYTHM DOCTOR"), (120, 9, 10, "m")])[:128*10*4]
    try:
        c.wait(lambda state: matches(state, expected))
    except Exception as error:
        raise AssertionError("RD-04: fifth algorithm button must display RHYTHM DOCTOR") from error
    c.results.append(dict(kind="screen-header", expected="RHYTHM DOCTOR", matched=True,
                          contract="PLAN.md User contract and coordinate convention"))
    c.led_values([(2, 2), (3, 2), (4, 2), (5, 2), (6, 2), (7, 2)],
                 [0, 15, 4, 4, 4, 4])
    c.results.append(dict(kind="rhythm-doctor-lanes", selected="BD", reserved_column=0,
                          contract="PLAN.md: x2 reserved; x3..7 select BD/SD/HH/TOM/BASS"))
    c.tap(7, 2)
    c.led_values([(3, 2), (4, 2), (5, 2), (6, 2), (7, 2)], [4, 4, 4, 4, 15])
    c.results.append(dict(kind="rhythm-doctor-lane-selection", selected="BASS",
                          contract="PLAN.md: BASS is native x7,y2"))


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
                  scope="fifth algorithm UI; no audio or classification claim")
    (out / "manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passed": result["passed"], "manifest": str(out / "manifest.json")}))
    return int(not result["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
