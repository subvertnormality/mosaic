"""Per-sequence tempo as clock divisions of the global tempo (README "Clocks, Swing and
Shuffle"; SEM-014 user decision).

Global length 4 at 90 BPM (1/6 s global steps). Slot 1 keeps channel 1 at /1;
slot 2 is a copy at /2 with octave +1; slot 3 a copy at x2 with octave +2. With
song mode on and the default reset on sequence change (README 1074), each slot restarts
channel 1 at step 1 and applies its own division for its four global steps:
slot 2 sounds steps 1-2 at 1/3 s, slot 3 plays steps 1-4 twice at 1/12 s (a
channel cannot exceed the global length and repeats, README 917), and slot 1 returns at 1/6 s.
"""
import base64

PHRASE = [(60, 127), (62, 117), (64, 107), (65, 97)]
# Selector order on the Clocks page: /1 is index 13; negative E3 moves toward slower divisions.
DIVISIONS = {2: ('/2', -2, 2), 3: ('x2', 3, .5)}               # slot: (label, E3 detents, step factor)
OCTAVE = {1: 0, 2: 1, 3: 2}; OCTAVE_KEY = {2: 11, 3: 12}


def song_tempo_divisions(c):
    from frame_oracle import render
    c.configure()
    c.tap(6, 8); c.tap(2, 7)
    for _ in range(3): c.tap(8, 7)                               # global length 4
    for slot, (label, detents, _) in DIVISIONS.items():
        c.tap(6, 8); c.tap(1, 1); c.hold_tap((1, 1), (slot, 1)); c.tap(slot, 1); c.tap(3, 8)
        c.tap(1, 1); c.tap(OCTAVE_KEY[slot], 8)                  # this slot's channel 1 octave
        c.enc(1, -5); c.enc(1, 3); c.screen_header('Ch. 1 Clocks', selected=4)
        c.enc(3, detents); c.key(3)
        expected = render([(0, 26, 15, label)])
        c.wait(lambda s: all(base64.b64decode(s['frame']['pixels_base64'])[(y*128+x)*4+k] == expected[(y*128+x)*4+k]
                             for y in range(20, 30) for x in range(48) for k in range(3)))
        c.results.append(dict(kind='slot-clock-division', slot=slot, label=label, passed=True))
    c.tap(6, 8); c.tap(1, 1); c.tap(3, 8)                        # play from slot 1
    plan = []                                                     # (global-step time, pitch, velocity)
    for cycle in range(2):
        for slot in (1, 2, 3):
            factor = DIVISIONS[slot][2] if slot in DIVISIONS else 1
            origin = 12 * cycle + 4 * (slot - 1)
            for step in range(int(4 / factor)):                   # channel steps starting inside the slot
                pitch, velocity = PHRASE[step % 4]                    # the channel wraps at the global length
                plan.append((origin + step * factor, pitch + 12 * OCTAVE[slot], velocity))
    plan.append((24, 60, 127))                                    # slot 1 again before Stop
    before = c.snapshot()['midi_count']; c.tap(1, 8)
    def onsets(s): return [m for m in s['midi'] if m['index'] > before and m['bytes'][0] == 144 and m['bytes'][2] > 0]
    state = c.wait(lambda s: len(onsets(s)) >= len(plan), timeout=8)
    c.tap(1, 8); c.wait(lambda s: not s['midi_capture']['outstanding'])
    notes = onsets(state)[:len(plan)]
    assert [(m['port'], m['bytes']) for m in notes] == [(1, [144, n, v]) for _, n, v in plan], \
        dict(expected=[p[1:] for p in plan], actual=[m['bytes'] for m in notes])
    field = 'logical_ns' if c.clock_mode == 'controlled-experimental' else 'monotonic_ns'
    tolerance = 2e-9 if c.clock_mode == 'controlled-experimental' else .01
    offsets = [(m[field] - notes[0][field]) / 1e9 for m in notes]
    wanted = [t / 6 for t, _, _ in plan]
    assert all(abs(a - w) <= tolerance for a, w in zip(offsets, wanted)), dict(expected=wanted, actual=offsets)
    c.results.append(dict(kind='per-sequence-tempo', plan=plan, offsets_seconds=offsets, passed=True))
