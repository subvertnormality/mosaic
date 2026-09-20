"""A correction refused after a reload must say so on the screen.

A project saved with a completed bank reloads straight to READY: the bank is
restored from the file and no analysis backend is involved. The retained audio
does not come back with it, so a correction cannot be dispatched and is
refused. The draft is deliberately kept so the player can edit or cancel it,
which is exactly why the refusal has to be visible - otherwise the screen reads
as it did before K3 and nothing appears to have happened.

This uses only the emulator's public key/encoder input and the observed
framebuffer. It makes no claim about audio capture or inference.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import traceback
from pathlib import Path

import base64

from driver import Driver, EMULATOR_ROOT
from frame_oracle import render
from rhythm_doctor import fifth_algorithm

REPO = Path(__file__).resolve().parents[2]


# The status line owns the left of the screen; the right-hand third is where
# the dancing doctor is drawn, and he is placed to start past it.
STATUS_COLUMNS = 97


def status_band(text):
    """Match only the part of the screen carrying the status line.

    The rest shows live bank detail - hit counts, tempo, window positions, and
    the doctor - which is not what this case is about, so comparing whole
    frames would make it fail for unrelated reasons. The bound is the same one
    the sprite is held to in test_app_surface, so text and drawing cannot
    silently start overlapping without that test failing.
    """
    literal = render([(0, 22, 10, text)])
    region = [((y * 128 + x) * 4 + channel)
              for y in range(15, 26) for x in range(STATUS_COLUMNS) for channel in range(3)]

    def expected(state):
        actual = base64.b64decode(state["frame"]["pixels_base64"])
        return all(actual[i] == literal[i] for i in region)
    return expected
# Norns applies Mosaic's default encoder sensitivity of 2, so two raw detents
# are one logical step at this public boundary.
DETENT = 2


def seed_project_with_bank(c):
    """Let the app autosave a real project, then add a completed bank to it."""
    ptn = c.data_directory / "autosave.ptn"
    idle = 0
    while idle < 61:
        step = min(30, 61 - idle)
        c.elapse(step)
        idle += step
    c.wait(lambda _: ptn.is_file(), timeout=5)
    c.results.append(dict(kind="correction-fixture-autosave", file=str(ptn.name), passed=True))
    return ptn


def inject_bank(ptn):
    norns_lua = json.loads((EMULATOR_ROOT / ".runtime/current.json").read_text())["source"] + "/lua/lib"
    # The CI container installs lua5.3 without a bare `lua` alias.
    interpreter = shutil.which("lua5.3") or shutil.which("lua")
    if not interpreter:
        raise AssertionError("no Lua interpreter available to seed the bank")
    done = subprocess.run([interpreter, str(REPO / "tests/behaviour/fixtures/inject_ready_bank.lua"),
                           str(ptn), norns_lua],
                          cwd=str(REPO), capture_output=True, text=True)
    if done.returncode != 0:
        raise AssertionError("could not seed a completed bank: " + done.stdout + done.stderr)
    return done.stdout.strip()


def refused_correction_is_visible(c):
    fifth_algorithm(c)

    # The reloaded bank is READY without any analysis backend.
    ready = status_band("BASS / READY")
    c.wait(ready)
    c.results.append(dict(kind="correction-reload-ready", state="READY",
                          contract="README: a saved bank reloads ready without a backend"))

    # Open the alignment draft through the ordinary READY controls.
    for _ in range(4):
        c.action(type="enc", n=2, delta=DETENT)
        c.elapse(.06)
    c.action(type="enc", n=3, delta=DETENT)
    c.elapse(.08)
    c.wait(status_band("ALIGNMENT / HALF TEMPO"))
    c.results.append(dict(kind="correction-draft-open", field="HALF TEMPO",
                          contract="README: E2 chooses the alignment field, E3 opens the draft"))

    # K3 applies it. The retained audio is gone, so it must be refused visibly.
    c.action(type="key", n=3, state=1); c.elapse(.04)
    c.action(type="key", n=3, state=0); c.elapse(.12)
    try:
        c.wait(status_band("CAPTURE AUDIO UNAVAILABLE"))
    except Exception as error:
        raise AssertionError(
            "a correction refused after reload left the screen unchanged") from error
    c.results.append(dict(kind="correction-refused-visible", shown="CAPTURE AUDIO UNAVAILABLE",
                          contract="the refusal replaces the alignment label on screen"))

    # The draft survives the refusal, so the player can edit or cancel it.
    c.action(type="enc", n=2, delta=DETENT); c.elapse(.08)
    c.wait(status_band("ALIGNMENT / DOUBLE TEMPO"))
    c.results.append(dict(kind="correction-draft-retained", field="DOUBLE TEMPO",
                          contract="a refused correction keeps its draft and clears the refusal"))

    # K2 discards it and the bank is still usable.
    c.action(type="key", n=2, state=1); c.action(type="key", n=2, state=0); c.elapse(.1)
    c.wait(ready)
    c.results.append(dict(kind="correction-cancelled", state="READY",
                          contract="cancelling a refused correction returns the ready bank"))


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
    first = second = None
    failure = cleanup_failure = injected = None
    try:
        (out / "seed").mkdir()
        first = Driver(out / "seed", app_root=args.app_root, clock_mode=args.clock_mode,
                       experimental_install=args.experimental_install)
        first.configure()
        ptn = seed_project_with_bank(first)
        seed_directory = first.data_directory
        first.finish(); first = None
        injected = inject_bank(ptn)

        (out / "reloaded").mkdir()
        second = Driver(out / "reloaded", app_root=args.app_root, clock_mode=args.clock_mode,
                        experimental_install=args.experimental_install,
                        project_seed=seed_directory)
        refused_correction_is_visible(second)
    except Exception:
        failure = traceback.format_exc()
    finally:
        for session in (first, second):
            if session is not None:
                try:
                    session.finish()
                except Exception:
                    cleanup_failure = traceback.format_exc()
    result = dict(case="RD-UI-003", passed=failure is None and cleanup_failure is None,
                  failure=failure, cleanup_failure=cleanup_failure,
                  declared_source_revision=args.source_revision,
                  source_identity=second.identity if second is not None else None,
                  injected_bank=injected,
                  recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  clock_mode=args.clock_mode, complete_regression_run=False,
                  scope="refused correction after reload; no audio or classification claim")
    (out / "manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passed": result["passed"], "manifest": str(out / "manifest.json")}))
    return int(not result["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
