"""A swung channel restarted in the middle of a step by a song transition (README 1074:
"Reset at Song Sequence Change", on by default, "resets all channels when transitioning
from one song editor pattern to the next") keeps its swing (README 683: swing "moves
notes closer or further apart").

Channel 1 runs at /2 (an eighth, 48 pulses of the 96 PPQN lattice, 1/3 s at 90 BPM) with
local Swing 25: the first step of each pair lasts 48 * 1.25 = 60 pulses, the second
48 * 0.75 = 36 (positive swing lengthens the first step, as M-PATCH-021 checks at /1).
Global length 6 (144 pulses); slot 2 is a copy an octave up. Each slot therefore plays
steps 1-3 at 0, 60 and 96 pulses, and the transition at 144 falls inside step 3
(96-156), so every transition restarts the channel mid-step. A restarted channel is
the channel from its step 1 again: slot 2 must sound exactly like slot 1 from Play.
The baseline ran the restarted first step straight (48 pulses), shifting the swing
pairs until the next reset (suspected defect S41, m_lattice.lua:703-704).
"""
PHRASE = [(60, 127), (62, 117), (64, 107)]
PULSE_RATE = 144                    # 96 PPQN at 90 BPM
SLOT = 144                          # global length 6 x 24 pulses
SWUNG = [(0, 60), (60, 36), (96, 60)]  # (onset, one-step duration) within each slot


def swing_reset_mid_step(c):
    import time
    from midi_window import MidiWindow
    from note_schedule import assert_schedule
    c.configure(); c.enc(1, -1); c.screen_header('Ch. 1 Clocks', selected=4)
    c.enc(3, -2); c.key(3)                                         # /1 -> /2 (index 13 -> 15)
    c.enc(2, 1); c.enc(3, 1); c.key(3)                             # local Swing, not inherited X
    c.enc(2, 1); c.enc(3, 25 + 51); c.key(3)                       # X (-51) -> 25
    c.tap(6, 8); c.tap(2, 7)
    for _ in range(5): c.tap(8, 7)                                 # global length 6
    c.hold_tap((1, 1), (2, 1)); c.tap(2, 1); c.tap(3, 8); c.tap(11, 8)   # slot 2 = copy, octave +1
    c.tap(6, 8); c.tap(1, 1); c.tap(3, 8)
    # Slots 1, 2, 1, 2, then slot 1's first step: at least 13 onsets over 576 pulses (4 s).
    def plan(count):
        onsets, durations = [], []
        for n in range(count):
            slot, index = divmod(n, len(SWUNG))
            (offset, length), (pitch, velocity) = SWUNG[index], PHRASE[index]
            onsets.append((slot * SLOT + offset, pitch + 12 * (slot % 2), velocity))
            # README 805: a reset preserves the remaining duration of sounding notes, so
            # step 3's note keeps its 60 pulses across the transition at 144.
            durations.append(length)
        return onsets, durations
    capture = MidiWindow(c.snapshot()['midi_count']); c.tap(1, 8)
    c.wait(lambda s: capture.extend(s) and len(capture.note_ons()) >= 13, timeout=6)
    controlled = c.clock_mode == 'controlled-experimental'
    lower = c.logical_ns if controlled else time.monotonic_ns()
    c.action(type='grid', x=1, y=8, state=1); c.action(type='grid', x=1, y=8, state=0)
    upper = c.logical_ns if controlled else time.monotonic_ns()
    c.elapse(.06); c.wait(lambda s: capture.extend(s) and not s['midi_capture']['outstanding'])
    notes = capture.note_ons(); assert len(notes) >= 13, [m['bytes'] for m in notes]
    onsets, durations = plan(len(notes))
    field = 'logical_ns' if controlled else 'monotonic_ns'
    # README 683/1074 with the pulse arithmetic above: every slot, restarted mid-step,
    # plays 0/60/96 with 60/36/60-pulse notes, the same as slot 1 from Play.
    checks = assert_schedule(capture.events, onsets, durations, field=field, origin=notes[0][field],
                             stop_bounds=(lower, upper), pulse_rate=PULSE_RATE,
                             tolerance=2e-9 if controlled else .01)
    c.results.append(dict(kind='swing-reset-mid-step', onsets=[t for t, _, _ in onsets],
                          release_checks=len(checks), passed=True))
