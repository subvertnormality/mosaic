"""A18 native screen sweep (docs/ui-reimplementation spec.json#/acceptance_matrix A18,
README "Norns Menu Navigation" and "Tooltips").

Every live screen the app can reach through public input (grid, keys and
encoders only) is opened and checked on the native framebuffer:

* the exact title row and scope (frame_oracle.live_header_matches);
* no LAYOUT OVERFLOW on the layout's overflow line (lib/ui_render.lua paints it
  at (1, status_y) level 15 when a value cannot be drawn whole);
* the footer (rows 56..63) is exactly one owner: the screen's control hints, a
  focused screen's neighbour labels ('< previous' level 7 / 'next >' level 10,
  or '| START' / 'END |'), or a named tooltip, and nothing else overlaps it;
* where the state is known, the selected field's label and whole value on its
  layout's full-value route (frame_oracle.selected_field_matches).

Titles, layouts and art come from the spec (docs/ui-reimplementation/spec.json
screens[*].title and live_render), never from app output. Control hints and
tooltip texts are characterised implementation messages. The values are the
known state of a fresh configured project (ui.configure) and of the edits the
sweep itself makes. Each checked frame is written to screens/NNN-<id>.png in the
run directory as evidence.

Screens no public input shows on this build (C08, C10, C11, S04, S05, M04,
M08..M11, H06, H12..H16, H18, F*, R02..R16) are listed, with the reasons, in
docs/ui-reimplementation/reviews/ACCEPTANCE.md, with the defects the sweep
found and their fixes. Since the owner feedback of 25 September 2026, C12/C13
(Mask detail, Trig detail) are no longer Channel tasks; M14 (Merge reason)
is reached from Merge result's Reason row. Dashboards are
checked whole (every row, no cursor) with frame_oracle.dashboard_matches.
"""
import base64
import json
import struct
import zlib
from pathlib import Path

from ui_map import trig_param_cell_label

from frame_oracle import (dashboard_matches, fit, live_header_matches, render, selected_field_matches, variants,
                          overview_cell_matches)

SPEC = json.loads((Path(__file__).resolve().parents[3] / "docs/ui-reimplementation/spec.json").read_text())["screens"]

# Characterised control hints per screen profile (lib/ui_live.lua FOOTER).
HINTS = {
    "masks": "E2 MASK  E3 SET", "parameters": "E2 SLOT  E3 SET  K2 ASSIGN",
    "history": "E3 MOVE  K2 UNDO  K3 REDO", "clock": "E3 SET  K3 APPLY  K2 CANCEL",
    "device": "E3 SET  K3 APPLY  K2 CANCEL", "assignment": "E3 PICK  K3 SET  K2 BACK",
    "scale": "E3 SET  K3 APPLY  K2 CANCEL", "scale_clock": "E3 SET  K3 APPLY  K2 CANCEL",
    "song": "E3 SET  K3 APPLY  K2 CANCEL", "song_clock": "E3 SET  K3 APPLY  K2 CANCEL",
    "trig_options": "E3 SET  K3 APPLY", "merge_modes": "E2 MODE  E3 SET  K2 BACK", "feature": "E3 SET  K3 APPLY  K2 BACK",
    "tasks": "E2 CHOOSE  K3 OPEN", "read_only": "E1 TASKS", "doctor": "E2 FIELD  E3 SET",
    "confirmation": "K3 CONFIRM  K2 CANCEL", "native": "K1 PARAMS",
}
# lib/ui_render.lua: the line LAYOUT OVERFLOW would be painted on, per layout.
OVERFLOW_Y = {"overview_masks": 53, "overview_params": 53, "pattern64": 17, "detail": 17, "focused": 55,
              "dashboard": 7}
FOOTER_ROWS = range(56, 64)
START, END = object(), object()
# The pattern editor's scope names the edited pattern before the viewed channel.
PAT = "PAT01 CH01"


def _pixels(state):
    return base64.b64decode(state["frame"]["pixels_base64"])


def _same(actual, expected, rows, left=0, right=128):
    return all(actual[(y * 128 + x) * 4 + k] == expected[(y * 128 + x) * 4 + k]
               for y in rows for x in range(left, right) for k in range(3))


def footer_render(footer):
    """Expected footer pixels: a hint/tooltip string, or a (previous, next) neighbour pair."""
    if isinstance(footer, tuple):
        previous, following = footer
        left = "| START" if previous is START else "< " + previous
        right = "END |" if following is END else following + " >"
        return render([(1, 63, 7, fit(left, 61)), ((None, 127), 63, 10, fit(right, 61))])
    return render([(1, 63, 9, fit(footer, 126))])


def _png(pixels, path, scale=4):
    rows = [b"\x00" + bytes(pixels[((y // scale) * 128 + x // scale) * 4] for x in range(128 * scale))
            for y in range(64 * scale)]

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 128 * scale, 64 * scale, 8, 0, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(b"".join(rows))) + chunk(b"IEND", b""))


class Sweep:
    def __init__(self, c):
        self.c = c
        self.count = 0
        self.seen = []
        self.failures = []
        self.frames = Path(c.out) / "screens"
        self.frames.mkdir(exist_ok=True)

    def checks(self, sid, scope, field, footers, rows=None):
        entry = SPEC[sid]
        live = entry["live_render"]
        layout = live["layout"]
        overflow = render([(1, OVERFLOW_Y[layout], 15, "LAYOUT OVERFLOW")])
        # Every marquee phase of each footer (cut text scrolls).
        wanted = [frame for f in footers for frame in variants(lambda f=f: footer_render(f))]
        y = OVERFLOW_Y[layout]
        # A dashboard's sixth row (baseline 56) reaches row 57; the footer text is 58..63.
        footer_rows = range(58, 64) if layout == "dashboard" else FOOTER_ROWS

        def evaluate(state):
            actual = _pixels(state)
            result = {
                "header": live_header_matches(state, entry["title"], scope, layout),
                "no_overflow": not _same(actual, overflow, range(y - 7, y + 2)),
                "footer": any(_same(actual, w, footer_rows) for w in wanted),
            }
            if rows is not None:
                # A dashboard: every row at once, exactly, and no cursor.
                result["dashboard"] = dashboard_matches(state, entry["title"], scope, rows)
            if field is not None and field != (None, None):
                label, value = field
                result["field"] = selected_field_matches(state, layout, label, value, art=bool(live.get("art")))
            return result
        return evaluate

    def screen(self, sid, scope="CH01", field=None, footer=None, tips=(), timeout=5, note=None, rows=None):
        """Wait for screen `sid` to show exactly; record it and its frame."""
        entry = SPEC[sid]
        layout = entry["live_render"]["layout"]
        if footer is None:
            # Channel tasks names K1 for the norns parameters (Norns settings is gone).
            footer = "K3 OPEN  K1 PARAMS" if sid == "N01" else HINTS[entry["profile"]]
        # Idle autosave may announce itself on any screen (M-TOOLTIP-002).
        footers = [footer] + list(tips) + ["Autosaved"]
        if layout == "dashboard":
            assert field is None and rows is not None, (sid, "a dashboard is checked by its rows")
        evaluate = self.checks(sid, scope, field, footers, rows)
        state = None
        try:
            state = self.c.wait(lambda s: all(evaluate(s).values()), timeout=timeout)
            outcome = evaluate(state)
        except AssertionError:
            state = self.c.snapshot()
            outcome = evaluate(state)
        self.count += 1
        _png(_pixels(state), self.frames / ("%03d-%s.png" % (self.count, sid)))
        passed = all(outcome.values())
        record = dict(kind="a18-screen", screen=sid, title=entry["title"], scope=scope, layout=layout,
                      field=list(field) if field else None, rows=[list(r) for r in rows] if rows else None,
                      checks=outcome, frame="%03d-%s.png" % (self.count, sid),
                      passed=passed)
        if note:
            record["note"] = note
        self.c.results.append(record)
        self.seen.append(sid)
        if not passed:
            self.failures.append(record)
        return passed

    def row(self, y, label, value):
        """A detail row that is not selected: label level 6 at x7, value right at x126 level 8."""
        from frame_oracle import text_width
        room = min(72, 119 - text_width(value) - 4)
        frames = variants(lambda: render([(7, y, 6, fit(label, room)), ((None, 126), y, 8, value)]))
        ok = True
        try:
            self.c.wait(lambda s: any(_same(_pixels(s), expected, range(y - 7, y + 2)) for expected in frames))
        except AssertionError:
            ok = False
            self.failures.append(dict(kind="a18-row", y=y, label=label, value=value))
        self.c.results.append(dict(kind="a18-row", y=y, label=label, value=value, passed=ok))

    def cell(self, layout, index, short_label, value):
        ok = True
        try:
            self.c.wait(lambda s: overview_cell_matches(s, layout, index, short_label, value))
        except AssertionError:
            ok = False
            self.failures.append(dict(kind="a18-cell", index=index, label=short_label, value=value))
        self.c.results.append(dict(kind="a18-cell", layout=layout, index=index, short_label=short_label,
                                   value=value, passed=ok))

    def finish(self):
        self.c.results.append(dict(kind="a18-sweep", screens=sorted(set(self.seen)), checked=self.count,
                                   failures=len(self.failures), passed=not self.failures))
        assert not self.failures, json.dumps(self.failures, indent=1)


# Navigation (public input only) ------------------------------------------------------------

def channel_task(c, row):
    c.ui.open_channel_task(row)


def task(c, context, row):
    c.ui.open_task(context, row)


def e2(c, n):
    c.enc(2, n)


def live_ui_sweep(c):
    sw = Sweep(c)
    ui = c.ui
    c.configure()
    # Configure ends on Device with the length tooltip of its last grid gesture.
    sw.screen("C05", field=("Device", None), tips=("Channel 1 length changed",))

    # Channel: family and Channel tasks ---------------------------------------------------------
    # The Channel button returns to the remembered family, Masks: configure never
    # passed Trig params (E1 opens Channel tasks from any screen).
    ui.tap_control("channel_editor")
    sw.screen("C01", field=("Note", "X"), tips=("Channel Editor",))
    c.enc(1, 1)
    sw.screen("N01", field=("Masks", ""), tips=("Channel Editor",))
    # Norns settings (N04) left the list (owner, 25 September 2026): its footer names K1.
    rows = ["Masks", "Trig params", "Output", "Harmony", "Clock", "Merge modes", "Device", "History",
            "Merge Shape"]
    e2(c, -12)
    for index, label in enumerate(rows):
        sw.screen("N01", field=(label, ""), tips=("Channel Editor",))
        e2(c, 1)
    e2(c, 1)  # clamps on the last row
    sw.screen("N01", field=("Merge Shape", ""), tips=("Channel Editor",))

    channel_task(c, "output")
    sw.screen("C06", rows=C06_NO_EVENT)
    channel_task(c, "harmony")
    sw.screen("H01", field=("Mode", "OFF"), footer=(START, "Group"))
    channel_task(c, "clock")
    sw.screen("C04", field=("Rate", "/1"), footer=(START, "Swing type"))
    channel_task(c, "merge")
    sw.screen("C09", field=("Patterns", "01"))
    c.key(2)
    sw.screen("C01", field=("Note", "X"))
    channel_task(c, "device")
    sw.screen("C05", field=("Device", None))
    channel_task(c, "history")
    sw.screen("C03", field=("Position", "0 of 0"))
    channel_task(c, "merge_shape")
    sw.screen("M02", field=("Mode", "OFF"), footer=(START, "Rhythm"))
    channel_screens(c, sw)
    merge_screens(c, sw)
    harmony_screens(c, sw)
    scale_screens(c, sw)
    song_screens(c, sw)
    pattern_screens(c, sw)
    native_menu(c, sw)
    sw.finish()


def neighbours(sid, labels, label):
    """A focused screen with several fields names its neighbours in the footer.

    On owner-selection screens `labels` lists only the fields E2 can reach.
    """
    if SPEC[sid]["live_render"]["layout"] != "focused" or len(labels) < 2:
        return None if len(labels) >= 2 or SPEC[sid]["live_render"]["layout"] != "focused" else (START, END)
    i = labels.index(label)
    return (labels[i - 1] if i else START, labels[i + 1] if i + 1 < len(labels) else END)


def walk(c, sw, sid, fields, labels=None, visits=None, top=False, **kw):
    """E2 through a screen's fields, checking each selected (label, value).

    `fields` lists (label, value) in screen order (value None: label only);
    `labels` is every visible field when the walk reaches fewer (an owner's E2
    skips fields it does not select); `visits` the labels E2 reaches, in order.
    """
    if top:
        e2(c, -len(fields) - 2)
    values = dict(fields)
    labels = labels or [label for label, _ in fields]
    for n, label in enumerate(visits or [label for label, _ in fields]):
        if n:
            e2(c, 1)
        sw.screen(sid, field=(label, values.get(label)), footer=kw.get("footer") or neighbours(sid, labels, label),
                  **{k: v for k, v in kw.items() if k != "footer"})


def channel_screens(c, sw):
    # Output (C06) with no event yet: a dashboard of six rows, every one NO EVENT
    # (not the owner's default C-2). E2 and E3 change nothing on it.
    channel_task(c, "output")
    sw.screen("C06", rows=C06_NO_EVENT)
    e2(c, 3); c.enc(3, 2)
    sw.screen("C06", rows=C06_NO_EVENT)
    # Clock (C04): the owner's E2 selects Rate, Swing type and Swing; the
    # read-only Feel source is not reachable, so the footer skips it.
    channel_task(c, "clock")
    walk(c, sw, "C04", [("Rate", "/1"), ("Feel source", None), ("Swing type", "X"), ("Swing", "X")],
         labels=["Rate", "Swing type", "Swing"], visits=["Rate", "Swing type", "Swing"])
    channel_task(c, "history")
    walk(c, sw, "C03", [("Position", "0 of 0"), ("Selected event", "NO HISTORY"),
                        ("Undo available", "0"), ("Redo available", "0")])
    channel_task(c, "merge")
    walk(c, sw, "C09", [("Patterns", "01"), ("Trig mode", "SKIP"), ("Note mode", "AVERAGE"),
                        ("Velocity mode", "AVERAGE"), ("Length mode", "AVERAGE")])
    c.key(2)  # K2 returns, as its footer says, to the remembered family (Masks)
    sw.screen("C01", field=("Note", "X"))
    channel_task(c, "device")
    walk(c, sw, "C05", [("Device", "CC Device"), ("MIDI channel", "CC1"), ("MIDI port", "OUT 1")])
    # Maximum MIDI channel: a staged draft shows 16 whole, plus the staged
    # consequences; K2 cancels it.
    e2(c, -1)
    c.enc(3, 20)
    sw.screen("C05", field=("MIDI channel", "CC16"))
    # The staged consequences appear below the fields (not selectable).
    e2(c, 1)
    sw.screen("C05", field=("MIDI port", "OUT 1"))
    sw.row(45, "Device locks", "RESET")
    sw.row(54, "Slot defaults", "REBUILD")
    c.key(2)
    sw.screen("C05", field=("MIDI port", "OUT 1"))
    sw.row(36, "MIDI channel", "CC1")
    # Assignment picker (C07) and a long parameter name on the Trig params
    # overview: the cell shows the short name; the full value line names it whole.
    channel_task(c, "trig_params")
    c.key(2)
    sw.screen("C07", field=("None", ""))
    for label in ("Fixed Note", "Quantised Fixed Note", "Random Note"):
        c.enc(3, 1)
        sw.screen("C07", field=(label, ""), tips=("Press K3 to confirm",))
    c.enc(3, -1)
    sw.screen("C07", field=("Quantised Fixed Note", ""), tips=("Press K3 to confirm",))
    c.key(3)
    c.key(2)
    sw.screen("C02", field=("Quantised Fixed Note", "X"))
    # The cell names both parts of the short name, QUAN + NOTE, title-cased (it scrolls).
    sw.cell("overview_params", 1, trig_param_cell_label("QUAN", "NOTE"), "X")


# A false feature boolean reads OFF (distinct from NONE).
BOOLEAN_FALSE = "OFF"
# Channel 1's tone map, named by its assigned patterns and note merge mode.
H19_MAP = "PAT 1 / AVERAGE"
# Trig options keeps only the tresillo amount (owner decision 25 September 2026).
P02_FIELDS = [("Tresillo amount", "x24")]
# C06 before any event (usability audit 25 September 2026: six dashboard rows).
C06_NO_EVENT = [("Note", "NO EVENT"), ("Vel / Len", "NO EVENT"), ("Step", "NO EVENT"),
                ("Degree", "NO EVENT"), ("Pitch", "NO EVENT"), ("Sent", "NO EVENT")]


def merge_screens(c, sw):
    channel_task(c, "merge_shape")
    shape = [("Mode", "OFF"), ("Rhythm", ">"), ("Phrase", ">"), ("Pitch", ">"), ("Result", ">")]
    labels = [label for label, _ in shape]
    walk(c, sw, "M02", shape)
    e2(c, -3); c.key(3)
    rhythm = [("Anchor", "NONE"), ("Add amount", "100"), ("Amount detail", ">"), ("Add accent", "70"),
              ("Anchor gap", "0"), ("Seed", "0")]
    walk(c, sw, "M03", rhythm)
    rlabels = [label for label, _ in rhythm]
    # Minimum seed clamps; the anchor gap reaches its maximum 8; the amount
    # stays at its maximum 100. Each stays whole in the value region.
    c.enc(3, -1)
    sw.screen("M03", field=("Seed", "0"), footer=neighbours("M03", rlabels, "Seed"))
    e2(c, -1); c.enc(3, 10)
    sw.screen("M03", field=("Anchor gap", "8"), footer=neighbours("M03", rlabels, "Anchor gap"))
    e2(c, -3); c.enc(3, 1)
    sw.screen("M03", field=("Add amount", "100"), footer=neighbours("M03", rlabels, "Add amount"))
    e2(c, 1); c.key(3)
    walk(c, sw, "M12", [("Add amount", "100"), ("Eligible", "0"), ("Admitted", "0")])
    c.key(2)
    sw.screen("M03", field=("Amount detail", ">"), footer=neighbours("M03", rlabels, "Amount detail"))
    # K2 with a dirty draft discards it and returns to the root's launching row.
    c.key(2)
    sw.screen("M02", field=("Rhythm", ">"), footer=neighbours("M02", labels, "Rhythm"))
    e2(c, 1); c.key(3)
    walk(c, sw, "M06", [("Cycles", "1"), ("Shape", "FLAT"), ("Cycle 1", "100"), ("Variation", "FIXED")])
    c.key(2)
    sw.screen("M02", field=("Phrase", ">"), footer=neighbours("M02", labels, "Phrase"))
    e2(c, 1); c.key(3)
    pitch = [("Keep anchor", BOOLEAN_FALSE), ("Add target", "LEGACY"), ("Target setup", ">"), ("Voice leading", ">")]
    walk(c, sw, "M07", pitch)
    e2(c, -1); c.key(3)
    walk(c, sw, "M13", [("Target", "LEGACY"), ("Scope", "ADDITIONS")])
    c.key(2)
    sw.screen("M07", field=("Target setup", ">"), footer=neighbours("M07", [l for l, _ in pitch], "Target setup"))
    c.key(2)
    sw.screen("M02", field=("Pitch", ">"), footer=neighbours("M02", labels, "Pitch"))
    # M09 is not observable: the merge-mode short press shows it and its
    # release hides it within the same grid event (see ACCEPTANCE.md).
    # Result and its Reason are read-only; K2 backs out through the editor.
    e2(c, 1); c.key(3)
    walk(c, sw, "M05", [("Step", "1"), ("Role", "EMPTY"), ("Decision", "LEGACY"), ("Reason", ">")])
    c.key(3)
    walk(c, sw, "M14", [("Step", "1"), ("Role", "EMPTY"), ("Sources", "NONE"), ("Decision", "ADMITTED"),
                        ("Velocity", "NONE"), ("Pitch target", "LEGACY")])
    c.key(2)
    sw.screen("M05", field=("Reason", ">"))
    c.key(2)
    sw.screen("M02", field=("Result", ">"), footer=("Pitch", END))
    c.enc(1, 1)
    sw.screen("N01", field=("Merge Shape", ""))


def harmony_screens(c, sw):
    channel_task(c, "harmony")
    root = [("Mode", "OFF"), ("Group", "NOT USED"), ("Preset", "NOT USED"), ("Register", ">"), ("Bass", ">"),
            ("Groups", ">"), ("Rules", ">"), ("Entry", ">"), ("Result", ">")]
    labels = [label for label, _ in root]
    walk(c, sw, "H01", root)
    e2(c, -5); c.key(3)
    walk(c, sw, "H02", [("Role", "V1"), ("Low", "24"), ("High", "60"), ("Centre", "48"), ("Preferred leap", "12"),
                        ("Strict leap", BOOLEAN_FALSE)])
    c.key(2)
    sw.screen("H01", field=("Register", ">"), footer=neighbours("H01", labels, "Register"))
    e2(c, 1); c.key(3)
    # NEAREST sits at the 70 px art boundary: whole in the value region.
    walk(c, sw, "H03", [("Mode", "ROOT"), ("Direction", "NEAREST"), ("Strict direction", BOOLEAN_FALSE),
                        ("Pedal pitch", "48"), ("Non-chord pedal", BOOLEAN_FALSE), ("Bass register", ">")])
    c.key(2)
    e2(c, 2); c.key(3)
    rules = [("Crossing", BOOLEAN_FALSE), ("Pitch-class doubling", "FIXED INPUT"), ("Exact unison", BOOLEAN_FALSE),
             ("Common tones", "ON"), ("Upper spacing", "12"), ("Bass separation", "5"), ("Coverage", "FIXED INPUT")]
    walk(c, sw, "H08", rules)
    c.key(2)
    sw.screen("H01", field=("Rules", ">"), footer=neighbours("H01", labels, "Rules"))
    e2(c, 1); c.key(3)
    walk(c, sw, "H09", [("Start", "ANCHOR"), ("Song transition", "ANCHOR"), ("Same-slot repeat", "CONTINUE"),
                        ("Failure fallback", "SILENCE"), ("Absolute pitch", "PIN")])
    c.key(2)
    # Groups: create one and apply it (K3 on a value field), so K2 from its
    # child screens returns without discarding it; then the delete question.
    e2(c, -2); c.key(3)
    walk(c, sw, "H04", [("Group", "1"), ("Create group", ">")])
    c.key(3)
    group = [("Group", "1"), ("Create group", ">"), ("Four-part smooth", ">"), ("Members", ">"), ("Source", ">"),
             ("Policies", ">"), ("Entry", ">"), ("Result", ">"), ("Delete group", ">")]
    sw.screen("H04", field=("Create group", ">"))
    e2(c, -1); c.key(3)
    sw.screen("H04", field=("Group", "1"), tips=("APPLIED",))
    e2(c, 3); c.key(3)
    walk(c, sw, "H07", [("Voice count", "1"), ("bass", "1"), ("Group enabled", BOOLEAN_FALSE)], tips=("APPLIED",))
    c.key(2)
    sw.screen("H04", field=("Members", ">"), tips=("APPLIED",))
    e2(c, 1); c.key(3)
    # A long raw value keeps its whole width; the label shrinks.
    walk(c, sw, "H10", [("Source kind", "GLOBAL_EFFECTIVE"), ("Template count", "1"), ("Root offset", "0"),
                        ("Required 1", "ON")])
    c.key(2)
    sw.screen("H04", field=("Source", ">"))
    e2(c, 1); c.key(3)
    walk(c, sw, "H08", top=True, fields=[("Crossing", BOOLEAN_FALSE), ("Pitch-class doubling", "ON"), ("Exact unison", BOOLEAN_FALSE),
                        ("Common tones", "ON"), ("Upper spacing", "12"), ("Bass separation", "5"), ("Coverage", ">")])
    c.key(2)
    sw.screen("H04", field=("Policies", ">"))
    e2(c, 1); c.key(3)
    walk(c, sw, "H09", [("Start", "ANCHOR"), ("Song transition", "ANCHOR"), ("Same-slot repeat", "CONTINUE"),
                        ("Failure fallback", "SILENCE")])
    c.key(2)
    sw.screen("H04", field=("Entry", ">"))
    e2(c, 2); c.key(3)
    # A question owns E2/E3 (K3 CONFIRM  K2 CANCEL); the first row stays selected.
    sw.screen("H17", field=("Delete group", "1"))
    e2(c, 1)
    sw.screen("H17", field=("Delete group", "1"), tips=("K3 CONFIRM  K2 CANCEL",))
    c.key(2)
    sw.screen("H04", field=("Delete group", ">"))
    c.key(2)
    sw.screen("H01", field=("Groups", ">"), footer=neighbours("H01", labels, "Groups"))
    # Result (detail): Step, Status and one planned > sent row per voice; K2 backs out
    # to Voice leading.
    e2(c, 3); c.key(3)
    walk(c, sw, "H05", top=True, fields=[("Step", "1"), ("Status", "NO EVENT"), ("CH1", "NO EVENT")])
    c.key(2)
    sw.screen("H01", field=("Result", ">"), footer=("Entry", END))
    # Pattern mode adds Tone Map, whose reset asks a question.
    e2(c, -12)
    c.enc(3, 2)
    pattern = [("Mode", "PATTERN"), ("Group", "NOT USED"), ("Preset", "SMOOTH"), ("Tone Map", ">"), ("Register", ">"),
               ("Bass", ">"), ("Groups", ">"), ("Rules", ">"), ("Entry", ">"), ("Result", ">")]
    walk(c, sw, "H01", pattern)
    e2(c, -6); c.key(3)
    walk(c, sw, "H11", [("Tone 0", "RAW"), ("Tone 1", "RAW"), ("Tone 2", "RAW"), ("Tone 3", "RAW"), ("Reset map", ">")])
    c.key(3)
    # The question names the map by its patterns and note merge, whole.
    sw.screen("H19", field=("Reset map", H19_MAP))
    c.key(2)
    sw.screen("H11", field=("Reset map", ">"), footer=("Tone 3", END))
    c.key(2)
    # K2 with the unapplied mode change discards it: Mode is OFF again.
    sw.screen("H01", field=("Mode", "OFF"), footer=(START, "Group"))
    # From the clean root one E1 detent leaves for Channel tasks, also after a
    # cancelled Reset map question (its return frame is spent).
    c.enc(1, 1)
    sw.screen("N01", field=("Harmony", ""))


def scale_screens(c, sw):
    c.ui.tap_control("scale_editor")
    scale = [("Root", None), ("Scale", "Major"), ("Degree", "I"), ("Transpose", "0"), ("Rotation", "r0"),
             ("Pentatonic", None)]
    # The owner's E2 starts on Scale and stops at Rotation; the read-only
    # Pentatonic is not reachable, so the footer never names it.
    labels = ["Root", "Scale", "Degree", "Transpose", "Rotation"]
    sw.screen("S01", scope="SLOT 01", field=("Scale", "Major"), footer=neighbours("S01", labels, "Scale"),
              tips=("Scale Editor",))
    walk(c, sw, "S01", scale, labels=labels, visits=["Scale", "Degree", "Transpose", "Rotation", "Rotation"],
         scope="SLOT 01")
    c.enc(1, 1)
    # E1 opens Scale tasks on the Scale row; Channel view is no longer a Scale task.
    sw.screen("N02", scope="SLOT 01", field=("Scale", ""))
    tasks = ["Scale", "Scale clock", "Overview"]
    walk(c, sw, "N02", [(t, "") for t in tasks], top=True, scope="SLOT 01")
    task(c, "Scale", "scale_clock")
    # Scale clock is a detail screen: every row shows; the owner's E2 stays on Rate.
    sw.screen("S02", field=("Rate", "/1"), scope="SLOT 01")
    for y, label, value in ((36, "Selected range", "01..64"), (45, "Global cap", "64"),
                            (54, "Playable range", "01..64")):
        sw.row(y, label, value)
    e2(c, 2)
    sw.screen("S02", field=("Rate", "/1"), scope="SLOT 01")
    task(c, "Scale", "overview")
    sw.screen("S03", scope="SLOT 01", rows=[("Playing scale", "01"), ("Edit scale", "01"),
                                            ("Step / range", "01 / 01..64"), ("Transpose", "0"),
                                            ("Step lock", "NONE")])


def song_screens(c, sw):
    c.ui.tap_control("song_editor")
    playback = [("Playing", "SONG 01"), ("Next", "SONG 01"), ("Pass", "1 / 1"), ("Global length", "64"),
                ("Song mode", "AUTO")]
    sw.screen("A03", scope="SONG 01", rows=playback, tips=("Song Editor",))
    task(c, "Song", "slot_setup")
    walk(c, sw, "A01", [("Repeats", "1"), ("Song mode", "On")], scope="SONG 01")
    task(c, "Song", "tempo_feel")
    walk(c, sw, "A02", [("Tempo", "90"), ("Swing type", "Swing"), ("Swing", "0")], scope="SONG 01")
    task(c, "Song", "channel_view")
    sw.screen("P05", scope="SONG 01")
    c.enc(1, 1)
    walk(c, sw, "N05", [(t, "") for t in ("Playback", "Slot setup", "Tempo / feel", "Channel view")],
         top=True, scope="SONG 01")


def pattern_screens(c, sw):
    c.ui.tap_control("pattern_editor")
    sw.screen("P01", scope=PAT, tips=("Trig Editor",))
    c.enc(1, 1)
    walk(c, sw, "N03", [(t, "") for t in ("Pattern", "Options", "Algorithm", "Channel view")], top=True)
    task(c, "Trig", "options")
    # Trig options has one field (so its footer is the control hints); E2 moves
    # nothing, never the Trig viewer's channel.
    sw.screen("P02", field=P02_FIELDS[0])
    e2(c, 2)
    sw.screen("P02", field=P02_FIELDS[0])
    task(c, "Trig", "channel_view")
    sw.screen("P05")
    c.enc(3, -16)  # E3 on View channel clamps at channel 1
    sw.screen("P05")
    # Algorithm picker: the algorithm in use reads SELECTED, the others are
    # blank (not a sentinel); a grid press lands on the pressed algorithm. The
    # footer shows the grid inputs of the algorithm in use (characterisation).
    c.tap(12, 2)
    algorithms = ["Drum", "Tresillo", "Euclidean", "Numeric", "Rhythm Doctor"]
    sw.screen("P06", field=("Drum", "SELECTED"), tips=("Drum algorithm selected",), footer="BANK RND  PAT 1")
    # Once the tooltip has gone, the footer is the grid inputs alone.
    sw.screen("P06", field=("Drum", "SELECTED"), footer="BANK RND  PAT 1", timeout=10)
    for label in algorithms[1:]:
        e2(c, 1)
        sw.screen("P06", field=(label, ""), tips=("Drum algorithm selected",), footer="BANK RND  PAT 1")
    c.tap(13, 2)
    sw.screen("P06", field=("Tresillo", "SELECTED"), tips=("Tresillo algorithm selected",),
              footer="BANK RND  P1 1  P2 1")
    sw.screen("P06", field=("Tresillo", "SELECTED"), footer="BANK RND  P1 1  P2 1", timeout=10)
    c.tap(12, 2)
    # Paint preview: the preview's real state on one dashboard.
    c.tap(16, 8)
    sw.screen("P07", rows=[("Preview", "PAINTING"), ("Algorithm", "Drum"), ("Shift", "0"), ("Trigs", "0")],
              tips=("Painting pattern",))
    c.tap(14, 8)
    sw.screen("P07", rows=[("Preview", "OFF"), ("Algorithm", "Drum"), ("Shift", "0"), ("Trigs", "NONE")],
              tips=("Painting cancelled",))
    # Trig step edit while a trig step is held and another is pressed: its scope is
    # the pattern and the held step.
    c.action(type="grid", x=1, y=4, state=1)
    c.tap(3, 4)
    sw.screen("P08", scope="PAT01 ST01", tips=("Note length set",),
              rows=[("Toggle", "STEP01 ON"), ("Length", "01..03"), ("Reset length", "STEP01"),
                    ("Pattern select", "PAT01")])
    c.action(type="grid", x=1, y=4, state=0)
    # Rhythm Doctor (algorithm 5): R01 at rest, READY.
    c.tap(16, 2)
    sw.screen("R01", field=("Record", "READY"), footer=(START, "Tempo"), tips=("Rhythm Doctor selected",))
    c.enc(1, 1)
    walk(c, sw, "N03", [(t, "") for t in ("Pattern", "Options", "Algorithm", "Channel view", "Rhythm Doctor")],
         top=True, tips=("Rhythm Doctor selected",))
    # K3 on the Rhythm Doctor row opens R01.
    c.key(3)
    sw.screen("R01", field=("Record", "READY"), footer=(START, "Tempo"))
    task(c, "Trig", "pattern")
    sw.screen("P01", scope=PAT)
    c.tap(12, 2)
    c.ui.tap_control("pattern_editor")
    sw.screen("P03", scope=PAT, tips=("Note Editor",))
    c.enc(1, 1)
    walk(c, sw, "N03", [(t, "") for t in ("Pattern", "Channel view")], top=True)
    e2(c, -3); c.key(3)
    sw.screen("P03", scope=PAT)
    c.ui.tap_control("pattern_editor")
    sw.screen("P04", scope=PAT, tips=("Velocity Editor",))


def native_menu(c, sw):
    """A short K1 opens the norns menu and a second closes it; the live screen returns unchanged."""
    c.ui.enter_native_menu()
    c.ui.leave_native_menu()
    sw.screen("P04", scope=PAT)
