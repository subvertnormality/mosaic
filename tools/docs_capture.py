"""Capture documentation images of the live norns screen from the emulator.

Run from the worktree with MONOME_EMULATOR set:
    python3 tools/docs_capture.py                          (images/norns/*)
    python3 tools/docs_capture.py merge-shape-foundation   (images/merge-shape-foundation.png)
Each image is the native framebuffer at 3x, written under images/norns/ (or images/).
The merge-shape-foundation capture drives the same state as M-MERGE-FOUNDATION-001
(contract/foundation_workflow.py) and prints the sha256 of the first 55 framebuffer rows,
which that case records. The
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


def capture_foundation():
    """images/merge-shape-foundation.png: the applied Foundation Rhythm screen with Add
    accent selected, exactly as M-MERGE-FOUNDATION-001 reaches it. The most frequent frame
    over two seconds is kept, so a decorative blink is never the one captured."""
    import collections
    import hashlib
    from contract.foundation_workflow import setup_foundation
    rows = 55
    with tempfile.TemporaryDirectory() as scratch, tempfile.TemporaryDirectory() as staged:
        driver = Driver(Path(scratch))
        try:
            setup_foundation(driver)
            driver.ui.select_field("add_amount", offset=1)
            driver.ui.select_field("add_accent", offset=2)
            driver.ui.expect_selected_field("focused", "Add accent", "70", art=True)
            frames = collections.Counter()
            seen = {}
            for _ in range(40):
                pixels = frame(driver)
                key = hashlib.sha256(pixels[:128 * rows * 4]).hexdigest()
                frames[key] += 1
                seen[key] = pixels
                time.sleep(0.05)
            key, count = frames.most_common(1)[0]
            staged_png = Path(staged) / "merge-shape-foundation.png"
            write_png(staged_png, seen[key])
        finally:
            driver.finish()
        target = REPO / "images" / "merge-shape-foundation.png"
        target.write_bytes(staged_png.read_bytes())
        print("wrote", target)
        print("first %d rows sha256 %s (%d of %d samples)" % (rows, key, count, sum(frames.values())))


if __name__ == "__main__":
    if sys.argv[1:] == ["merge-shape-foundation"]:
        capture_foundation()
    else:
        main()
