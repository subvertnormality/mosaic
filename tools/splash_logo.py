"""Generate lib/ui_splash_logo.lua from images/logo.svg.

The start-up splash draws Mosaic's logo: its grid of round dots and pill bars
(15 columns x 9 rows, four shades) and the lowercase "mosaic" wordmark. This
tool reads the logo once and writes the blocks and letter outlines as plain
data, scaled to the norns screen, so the splash draws the real logo with
screen primitives and no SVG at run time.

    python3 tools/splash_logo.py           # write lib/ui_splash_logo.lua
    python3 tools/splash_logo.py --check   # fail if it is stale
"""
import re
import sys
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
SVG = ROOT / "images" / "logo.svg"
OUT = ROOT / "lib" / "ui_splash_logo.lua"

# Logo geometry (SVG units): dot centres step 42 across from x 63 and ~38.4
# down from y 66; a dot is ~30 across. The wordmark sits below y 405.
COLUMN_X0, COLUMN_STEP, COLUMNS = 63.0, 42.0, 15
ROW_Y0, ROW_STEP, ROWS = 66.0, 38.3, 9
WORD_TOP = 405.0

# Screen placement: the block grid fills the screen (8 px columns, 7 px rows),
# the wordmark is centred and 22 px tall.
CELL_W, CELL_H, GRID_X, GRID_Y = 8, 7, 4, 0
WORD_HEIGHT, WORD_CENTRE = 22.0, (64.0, 32.0)


def flatten(d, steps=10):
    """SVG path data -> list of closed polygons (lists of (x, y))."""
    tokens = re.findall(r"[MmLlHhVvCcQqZz]|-?(?:\d+\.?\d*|\.\d+)(?:e-?\d+)?", d)
    polys, poly = [], []
    x = y = sx = sy = 0.0
    cmd = None
    i = 0

    def take(n):
        nonlocal i
        vals = [float(v) for v in tokens[i:i + n]]
        i += n
        return vals

    while i < len(tokens):
        if re.match(r"[A-Za-z]", tokens[i]):
            cmd = tokens[i]
            i += 1
            if cmd in "Zz":
                if poly:
                    polys.append(poly)
                poly = []
                x, y = sx, sy
                continue
        rel = cmd.islower()
        c = cmd.upper()
        if c == "M":
            nx, ny = take(2)
            if rel:
                nx, ny = x + nx, y + ny
            if poly:
                polys.append(poly)
            poly = [(nx, ny)]
            x, y, sx, sy = nx, ny, nx, ny
            cmd = "l" if rel else "L"
        elif c == "L":
            nx, ny = take(2)
            if rel:
                nx, ny = x + nx, y + ny
            poly.append((nx, ny)); x, y = nx, ny
        elif c == "H":
            (nx,) = take(1)
            x = x + nx if rel else nx
            poly.append((x, y))
        elif c == "V":
            (ny,) = take(1)
            y = y + ny if rel else ny
            poly.append((x, y))
        elif c in "CQ":
            n = 6 if c == "C" else 4
            v = take(n)
            pts = [(v[k] + (x if rel else 0), v[k + 1] + (y if rel else 0)) for k in range(0, n, 2)]
            p0 = (x, y)
            for s in range(1, steps + 1):
                t = s / steps
                if c == "C":
                    p1, p2, p3 = pts
                    px = (1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * p1[0] + 3 * (1 - t) * t * t * p2[0] + t ** 3 * p3[0]
                    py = (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * p1[1] + 3 * (1 - t) * t * t * p2[1] + t ** 3 * p3[1]
                else:
                    p1, p2 = pts
                    px = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
                    py = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
                poly.append((px, py))
            x, y = pts[-1]
        else:
            raise ValueError("unsupported path command " + cmd)
    if poly:
        polys.append(poly)
    return polys


def luminance(hex_colour):
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[k:k + 2], 16) for k in (0, 2, 4))
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255


def fill_of(el, gradients):
    fill = el.get("fill")
    style = el.get("style") or ""
    m = re.search(r"fill:([^;]+)", style)
    if m:
        fill = m.group(1)
    if fill and fill.startswith("url("):
        stops = gradients[fill[5:-1]]
        return sum(luminance(s) for s in stops) / len(stops)
    return luminance(fill)


def level_of(lum):
    # The logo's four block shades, dark to white, as norns levels.
    for bound, level in ((0.40, 2), (0.52, 4), (0.62, 6), (0.80, 9)):
        if lum < bound:
            return level
    return 15


def build():
    tree = ElementTree.parse(SVG)
    gradients = {}
    for g in tree.iter("{http://www.w3.org/2000/svg}linearGradient"):
        gradients[g.get("id")] = [s.get("stop-color") for s in g.iter("{http://www.w3.org/2000/svg}stop")]
    blocks, letters, holes = [], [], []
    for el in tree.getroot().iter("{http://www.w3.org/2000/svg}path"):
        polys = flatten(el.get("d"))
        xs = [p[0] for poly in polys for p in poly]
        ys = [p[1] for poly in polys for p in poly]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        if x1 - x0 > 600:
            continue  # the background
        lum = fill_of(el, gradients)
        if y0 >= WORD_TOP:
            (holes if lum < 0.2 else letters).append((x0, polys))
            continue
        if x1 - x0 < 18 or y1 - y0 < 18:
            continue  # shading slivers inside a pill
        row = round(((y0 + y1) / 2 - ROW_Y0) / ROW_STEP)
        first = round((x0 + 15 - COLUMN_X0) / COLUMN_STEP)
        last = round((x1 - 15 - COLUMN_X0) / COLUMN_STEP)
        blocks.append({"row": row, "first": first, "last": max(first, last), "level": level_of(lum),
                       "area": (x1 - x0) * (y1 - y0)})
    # Overlapping shading pieces: the larger block owns its cells.
    blocks.sort(key=lambda b: -b["area"])
    owned, kept = set(), []
    for b in blocks:
        cells = {(b["row"], c) for c in range(b["first"], b["last"] + 1)}
        if cells & owned:
            continue
        owned |= cells
        kept.append(b)
    kept.sort(key=lambda b: (b["row"], b["first"]))
    assert all(0 <= b["row"] < ROWS and 0 <= b["first"] <= b["last"] < COLUMNS for b in kept), kept

    # Wordmark: scale the letter outlines to WORD_HEIGHT, centred.
    all_pts = [p for _, polys in letters for poly in polys for p in poly]
    wx0, wx1 = min(p[0] for p in all_pts), max(p[0] for p in all_pts)
    wy0, wy1 = min(p[1] for p in all_pts), max(p[1] for p in all_pts)
    scale = WORD_HEIGHT / (wy1 - wy0)
    ox = WORD_CENTRE[0] - (wx1 - wx0) * scale / 2
    oy = WORD_CENTRE[1] - WORD_HEIGHT / 2

    def screen_poly(poly):
        out, last = [], None
        for px, py in poly:
            q = (round(ox + (px - wx0) * scale, 1), round(oy + (py - wy0) * scale, 1))
            if q != last:
                out.append(q)
            last = q
        return out

    def area(poly):
        return sum(poly[k][0] * poly[(k + 1) % len(poly)][1] - poly[(k + 1) % len(poly)][0] * poly[k][1]
                   for k in range(len(poly))) / 2

    letters.sort(key=lambda item: item[0])
    words = []
    for x0, polys in letters:
        glyph = {"fill": [screen_poly(p) for p in polys], "holes": []}
        for hx0, hpolys in holes:
            hx = [p[0] for poly in hpolys for p in poly]
            gx = [p[0] for poly in polys for p in poly]
            if min(gx) <= min(hx) and max(hx) <= max(gx):
                glyph["holes"] += [screen_poly(p) for p in hpolys]
        # A hole is wound against its letter's outline, so a non-zero fill of
        # the one path leaves it open.
        outer = max(glyph["fill"], key=lambda p: abs(area(p)))
        glyph["holes"] = [h if area(h) * area(outer) < 0 else h[::-1] for h in glyph["holes"]]
        words.append(glyph)

    def lua_poly(poly):
        return "{" + ", ".join("%g, %g" % p for p in poly) + "}"

    lines = [
        "-- Generated by tools/splash_logo.py from images/logo.svg. Do not edit by hand.",
        "-- blocks: the logo's dots (first == last) and pills, row 0..8, columns 0..14,",
        "-- with the norns level of their shade. letters: the \"mosaic\" wordmark,",
        "-- left to right, as screen-space polygons (x, y pairs) with any holes.",
        "return {",
        "  cell_w = %d, cell_h = %d, grid_x = %d, grid_y = %d, columns = %d, rows = %d," % (
            CELL_W, CELL_H, GRID_X, GRID_Y, COLUMNS, ROWS),
        "  blocks = {",
    ]
    for b in kept:
        lines.append("    {row = %d, first = %d, last = %d, level = %d}," % (b["row"], b["first"], b["last"], b["level"]))
    lines.append("  },")
    lines.append("  letters = {")
    for g in words:
        lines.append("    {fill = {" + ", ".join(lua_poly(p) for p in g["fill"]) + "},")
        lines.append("     holes = {" + ", ".join(lua_poly(p) for p in g["holes"]) + "}},")
    lines.append("  },")
    lines.append("}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    text = build()
    if "--check" in sys.argv:
        if not OUT.exists() or OUT.read_text() != text:
            sys.exit("lib/ui_splash_logo.lua is stale; run tools/splash_logo.py")
        print("splash logo current")
    else:
        OUT.write_text(text)
        print("wrote", OUT.relative_to(ROOT), len(text), "bytes")
