"""Render the dancing doctor to a PNG, so the sprite can be looked at.

Pixel art cannot be judged from source. This reads the poses out of
lib/rhythm_doctor/dancing_doctor.lua and writes both a pose sheet and the
sprite in place on a 128x64 norns screen, with the page's text drawn as bars,
so placement and silhouette can be checked before anything reaches a device.

    python3 tools/rhythm_doctor/preview_dancing_doctor.py --output /tmp/doctor

Standard library only: a Norns has nothing else, and neither should this.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[2]
SPRITE = ROOT / "lib" / "rhythm_doctor" / "dancing_doctor.lua"
# Where trigger_edit_page_ui puts him, and the rows the page writes text on.
DOCTOR_X, DOCTOR_Y = 97, 15
SCREEN_W, SCREEN_H = 128, 64
PAGE_TEXT = [(9, "RHYTHM DOCTOR"), (22, "BD / READY"), (34, "HITS 24 / READY"),
             (46, "124.0 BPM / AUTO"), (58, "START 1-4")]


def write_png(path: Path, pixels, scale: int = 1) -> None:
    height, width = len(pixels), len(pixels[0])
    lines = []
    for row in pixels:
        packed = bytearray()
        for value in row:
            packed.extend(bytes([value]) * scale)
        lines.extend([b"\x00" + bytes(packed)] * scale)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    header = struct.pack(">IIBBBBB", width * scale, height * scale, 8, 0, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
                     + chunk(b"IDAT", zlib.compress(b"".join(lines), 9)) + chunk(b"IEND", b""))


def poses():
    """The pose strings and their level marks, read from the module itself."""
    text = SPRITE.read_text(encoding="utf-8")
    levels = {name: int(value) for name, value in
              re.findall(r"(\w+)\s*=\s*(\d+)", text[text.index("local LEVELS"):text.index("\n", text.index("local LEVELS"))])}
    block = text[text.index("local POSES = {"):text.index("local function compile")]
    found, current = [], []
    for line in block.splitlines():
        row = re.match(r"\s*'([^']*)',\s*$", line)
        if row:
            current.append(row.group(1))
        elif line.strip() == "},":
            if current:
                found.append(current)
                current = []
    return found, levels


def grey(mark: str, levels) -> int:
    return 0 if mark == "." else levels[mark] * 17


def sheet(found, levels, gap: int = 2):
    height, width = len(found[0]), len(found[0][0])
    out = [[0] * ((width + gap) * len(found)) for _ in range(height)]
    for index, pose in enumerate(found):
        for y in range(height):
            for x in range(width):
                out[y][index * (width + gap) + x] = grey(pose[y][x], levels)
    return out


def screen(pose, levels):
    out = [[0] * SCREEN_W for _ in range(SCREEN_H)]
    for baseline, value in PAGE_TEXT:          # text as bars: placement, not typography
        for i in range(len(value) * 5):
            if i % 5 != 4:
                for dy in range(-5, 0):
                    out[baseline + dy][2 + i] = 9 * 17
    for y, row in enumerate(pose):
        for x, mark in enumerate(row):
            value = grey(mark, levels)
            if value and 0 <= DOCTOR_Y + y < SCREEN_H and 0 <= DOCTOR_X + x < SCREEN_W:
                out[DOCTOR_Y + y][DOCTOR_X + x] = value
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="directory for the PNGs")
    parser.add_argument("--scale", type=int, default=6)
    arguments = parser.parse_args()
    arguments.output.mkdir(parents=True, exist_ok=True)
    found, levels = poses()
    if not found:
        print("no poses found in " + str(SPRITE), file=sys.stderr)
        return 1
    write_png(arguments.output / "poses.png", sheet(found, levels), arguments.scale)
    write_png(arguments.output / "screen.png", screen(found[0], levels), arguments.scale)
    print("%d poses, %dx%d, written to %s" % (len(found), len(found[0][0]), len(found[0]), arguments.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
