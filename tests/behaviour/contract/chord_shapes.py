"""Contract-owned chord-shape cases and their exact physical MIDI oracle."""

import time

from midi_window import MidiWindow
from note_schedule import assert_schedule


def _assign_trig_parameter(c, label, offset=None):
    """Select a trig parameter through the real rendered parameter list."""
    c.key(2)
    c.enc(3, -50)
    if offset is None:
        for offset in range(50):
            if c.ui.expect_list_label(label, wait=False):
                break
            c.enc(3, 1)
        else:
            raise AssertionError("Parameter unavailable through native UI: " + label)
    elif offset:
        c.enc(3, offset)
    c.ui.expect_list_label(label)
    c.key(3)
    c.key(2)
    return offset


NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def _norns_name(n):
    """musicutil.note_num_to_name(n, true): C3 is MIDI 60."""
    return NOTE_NAMES[n % 12] + str(n // 12 - 2)


def chord_dashboard_display(c, root_velocity, voices):
    # C06 OUTPUT (the Note Dashboard) is a dashboard: its Note row shows the root
    # and the four chord voices sent (X for a slot that sent none), its Vel / Len
    # row the root velocity and length. Each row is asserted whole and exactly;
    # the root, velocity and length facts the old cells showed are within them.
    note = " ".join(["C3"] + [_norns_name(v) if v is not None else "X" for v in voices])
    c.ui.expect_output_field("note", note)
    c.ui.expect_output_field("vel_len", "%d / 4.0" % root_velocity)
    c.results.append(dict(kind="chord-root-dashboard", note="C3", chord=note,
                          velocity=root_velocity, length="4.0",
                          source="rendered framebuffer", passed=True))


def chord_shape_schedule(c, arp, shape, muted, mask_bits=15, velocity=50,
                         modifier=10, extra=None, dashboard=False):
    c.configure()
    c.hold_tap((1, 4), (16, 7))
    c.tap(5, 8)
    for x in (2, 3, 4):
        c.tap(x, 4)
    c.tap(3, 8)
    c.ui.turn(1, -4)
    c.enc(2, 1)
    c.enc(3, velocity + 1)
    c.enc(2, 1)
    c.enc(3, 26)
    c.ui.expect_field_value("length", "4")
    for i, turns in enumerate((2, 4, 5, 7)):
        c.enc(2, 1)
        if mask_bits & (1 << i):
            c.enc(3, turns)
    c.ui.turn(1, 3)
    c.enc(3, -11)
    c.key(3)
    c.ui.turn(1, -2)
    _assign_trig_parameter(c, "Chord Note Arpeggio" if arp else "Chord Note Strum")
    c.enc(3, 0 if extra == "disabled" else 8)
    c.enc(2, 1)
    _assign_trig_parameter(c, "Chord Pattern")
    c.enc(3, shape)
    c.enc(2, 1)
    _assign_trig_parameter(c, "Mute Chord Root")
    c.enc(3, int(muted))
    c.enc(2, 1)
    _assign_trig_parameter(c, "Chord Velocity Mod")
    c.enc(3, modifier)
    if extra == "accelerating":
        c.enc(2, 1)
        _assign_trig_parameter(c, "Chord Spread")
        c.enc(3, 5)
        c.enc(2, 1)
        _assign_trig_parameter(c, "Chord Accel Mod")
        c.enc(3, -1)
    if dashboard:
        c.ui.turn(1, 4)
    capture = MidiWindow(c.snapshot()["midi_count"])
    trigger = c.logical_ns
    c.action(type="grid", x=1, y=8, state=1)
    c.action(type="grid", x=1, y=8, state=0)
    c.elapse(2.625 if extra == "early-stop" else 3.25)
    capture.extend(c.snapshot())
    controlled = c.clock_mode == "controlled-experimental"
    lower = c.logical_ns if controlled else time.monotonic_ns()
    c.action(type="grid", x=1, y=8, state=1)
    c.action(type="grid", x=1, y=8, state=0)
    upper = c.logical_ns if controlled else time.monotonic_ns()
    c.elapse(1)
    capture.extend(c.snapshot())
    c.wait(lambda state: not state["midi_capture"]["outstanding"])
    order = {1: (0, 1, 2, 3, 4), 2: (4, 3, 2, 1, 0),
             3: (0, 1, 4, 2, 3), 4: (4, 1, 3, 2, 0)}[shape]
    pitches = (60, 64, 67, 69, 72)
    expected = [
        (ordinal * 108, pitches[slot], max(0, min(127, velocity + ordinal * modifier)))
        for ordinal, slot in enumerate(order)
        if (slot == 0 and not muted) or (slot > 0 and mask_bits & (1 << (slot - 1)))
    ]
    if extra == "disabled":
        expected = [(0, pitch, vel) for _, pitch, vel in expected]
    elif extra == "accelerating":
        ticks = {0: 0, 108: 162, 216: 270, 324: 324}
        expected = [(ticks[tick], pitch, vel) for tick, pitch, vel in expected
                    if tick in ticks]
    elif extra == "early-stop":
        expected = [row for row in expected if row[0] < 378]
    if arp and mask_bits == 0:
        expected = ([] if muted else
                    [(i * 108, 60, max(0, min(127, velocity + i * modifier)))
                     for i in range(5)])
    notes = capture.note_ons()
    assert notes or not expected
    field = "logical_ns" if controlled else "monotonic_ns"
    audible = [tick for tick, _, vel in expected if vel > 0]
    origin = (trigger if controlled else
              (notes[0][field] - audible[0] / 144 * 1e9 if notes and audible else 0))
    if not expected:
        assert not [m for m in capture.events if m["bytes"][0] & 240 in (128, 144)], \
            "Silent chord emitted MIDI notes/releases"
        rows = []
    elif modifier < 0 or any(vel == 0 for _, _, vel in expected):
        ons = [m for m in capture.events if m["bytes"][0] & 240 == 144]
        offs = [m for m in capture.events if m["bytes"][0] & 240 == 128]
        assert len(ons) == len(offs) == len(expected), "Velocity-bound MIDI count"
        tolerance = 2e-9 if controlled else .01
        pending = {}
        for event, (tick, pitch, vel) in zip(ons, expected):
            assert (event["port"], event["bytes"]) == (1, [144, pitch, vel]), \
                ("Clamped velocity", event, pitch, vel)
            assert abs((event[field] - origin) / 1e9 - tick / 144) <= tolerance
            pending[pitch] = vel
        for event in offs:
            pitch = event["bytes"][1]
            assert pitch in pending, "Duplicate or unrelated velocity release"
            assert event["port"] == 1 and event["bytes"][0] == 128
            assert event["bytes"][2] in (0, pending.pop(pitch))
            assert lower - tolerance * 1e9 <= event[field] <= upper + tolerance * 1e9, \
                "Release outside Stop drain"
        assert not pending
        rows = offs
    else:
        rows = assert_schedule(
            capture.events, expected, [108 if arp else 864] * len(expected),
            field=field, origin=origin, stop_bounds=(lower, upper),
            tolerance=2e-9 if controlled else .01)
    c.results.append(dict(kind="chord-shape-slots", arp=arp, shape=shape,
                          muted=muted, mask_bits=mask_bits,
                          onsets=len(expected), release_checks=len(rows), passed=True))
    if dashboard:
        # Chord slots 1..4 send pitches[1..4] when their mask bit is set.
        voices = [pitches[slot] if mask_bits & (1 << (slot - 1)) else None for slot in range(1, 5)]
        chord_dashboard_display(c, max(0, min(127,
                              velocity + (4 * modifier if shape in (2, 4) else 0))), voices)


def chord_shape_case(*args, **kwargs):
    """Return a registry callable whose code is owned by this contract module."""
    def run(c):
        return chord_shape_schedule(c, *args, **kwargs)
    return run
