"""Capture documentation images of the live norns screen from the emulator.

Run from the worktree with MONOME_EMULATOR set:
    python3 tools/docs_capture.py
Each image is the native framebuffer at 3x, written under images/norns/. The
matching screens are asserted semantically by the live-UI behaviour cases
(tests/behaviour/contract/live_ui.py); an image never replaces those assertions.
"""
import base64
import struct
import sys
import tempfile
import time
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests" / "behaviour"))
from driver import Driver, REPO  # noqa: E402

SCALE = 3


def write_png(path, rgba):
    rows = []
    for y in range(64 * SCALE):
        line = bytes(rgba[((y // SCALE) * 128 + x // SCALE) * 4] for x in range(128 * SCALE))
        rows.append(b"\x00" + line)

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    header = struct.pack(">IIBBBBB", 128 * SCALE, 64 * SCALE, 8, 0, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(b"".join(rows))) + chunk(b"IEND", b""))


def frame(driver):
    return base64.b64decode(driver.snapshot()["frame"]["pixels_base64"])


def main():
    final = REPO / "images" / "norns"
    final.mkdir(parents=True, exist_ok=True)
    # Sessions pin the source tree, images included: write after they finish.
    with tempfile.TemporaryDirectory() as scratch, tempfile.TemporaryDirectory() as staged:
        out = Path(staged)
        # The splash is captured from a start with no input: any input skips it.
        (Path(scratch) / "splash").mkdir()
        (Path(scratch) / "screens").mkdir()
        driver = Driver(Path(scratch) / "splash", midi_lead_time_ms=None)
        try:
            time.sleep(0.9)
            write_png(out / "splash.png", frame(driver))
            driver.key(2)  # an input trace for the session check; skips the rest
        finally:
            driver.finish()
        driver = Driver(Path(scratch) / "screens")
        try:
            driver.ui.tap_control("channel_editor")
            driver.ui.channel_page("masks")
            driver.ui.turn(3, 1)
            driver.elapse(0.5)
            write_png(out / "note-masks.png", frame(driver))
            driver.enc(1, 2)
            driver.enc(2, 1)
            driver.elapse(0.5)
            write_png(out / "channel-tasks.png", frame(driver))
        finally:
            driver.finish()
        for image in sorted(out.glob("*.png")):
            (final / image.name).write_bytes(image.read_bytes())
            print("wrote", final / image.name)


if __name__ == "__main__":
    main()
