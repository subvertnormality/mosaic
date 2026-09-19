"""First bar with Shuffle on, recorded live (probe for suspected defect S40).

S40 (m_lattice.lua:550-553 via :345/:574): a delayed sprocket whose first step is
re-rounded to a different length loses its delay. Mosaic's only delayed channel sprocket
is each channel's end-of-step processor (m_clock.lua, delay = 1, the channel's shuffle
settings), which commits live-recorded notes when their step ends. Smooth basis 1 at 100%
on a 1/16 channel is such a case: its first step (96 x 5/18 = 26.67 pulses) rounds to 27
at creation and to 26 at the first pulse.

What a user can hear or see there, through real input:
- the first bar's timing with Shuffle on (README 683: Shuffle "uses more complex patterns
  and can be set to a feel and a basis"), with the independently specified Smooth table
  and nearest-pulse plan of M-SHUFFLE-002 (shuffle_matrix.pulse_plan), and complete gates;
- live recording in that first bar (README 239: notes played while record is armed "will
  be captured as note masks on the currently selected channel ... the step active when
  Mosaic processes the note-on"; their lengths are "committed when you release them"):
  a short note in step 2 and a note held from step 3 across the step 3 -> 4 boundary,
  where the end-of-step processor commits it, then released. Replayed after disarming,
  steps 2 and 3 carry the recorded notes and steps 1 and 4 keep the pattern.
"""
import time

PHRASE = [(60, 127), (62, 117), (64, 107), (65, 97)]
PULSE_RATE = 144


def shuffle_first_bar_record(c):
    from midi_window import MidiWindow
    from note_accounting import note_pairs
    from shuffle_matrix import pulse_plan
    c.configure(); c.enc(1, -1); c.screen_header('Ch. 1 Clocks', selected=4)
    c.enc(2, 1); c.enc(3, 2); c.key(3)                            # X -> local Shuffle
    c.enc(2, 1); c.enc(3, 2); c.key(3)                            # feel Smooth
    c.enc(2, 1); c.enc(3, 1); c.key(3)                            # basis 1 (9)
    c.enc(2, 1); c.enc(3, -101); c.key(3); c.enc(3, 100); c.key(3)   # amount 100
    plan = pulse_plan('Smooth', 1, 100, 9)                        # 0, 26, 48, 69, 96, ...
    c.tap(2, 8)                                                   # arm recording
    controlled = c.clock_mode == 'controlled-experimental'
    field = 'logical_ns' if controlled else 'monotonic_ns'
    tolerance = 2e-9 if controlled else .01
    capture = MidiWindow(c.snapshot()['midi_count'])
    c.action(type='grid', x=1, y=8, state=1); c.action(type='grid', x=1, y=8, state=0)
    origin = c.logical_ns if controlled else time.monotonic_ns()
    def at(pulse): return origin + round(pulse * 1e9 / PULSE_RATE)
    middle = [(a + b) / 2 for a, b in zip(plan, plan[1:])]         # middle of steps 1..8
    # A: step 2, released inside it. B: pressed in step 3, released in step 4.
    packets = [(at(middle[1]), [144, 72, 90]), (at(middle[1]) + 20000000, [128, 72, 0]),
               (at(middle[2]), [144, 79, 80]), (at(middle[3]), [128, 79, 0])]
    domain = 'logical' if controlled else 'monotonic'
    events = [dict(port=1, bytes=data, **{'at_' + domain + '_ns': when}) for when, data in packets]
    request = dict(type='midi_schedule', schedule_id=1, events=events)
    if controlled: request['time_domain'] = 'logical'
    c.action(**request)
    c.wait(lambda s: capture.extend(s) and len(s['midi_input_schedule']['delivered']) == len(events)
           and len([m for m in capture.note_ons() if m['bytes'][1] in (60, 62, 64, 65)]) >= 5, timeout=3)
    c.action(type='grid', x=1, y=8, state=1); c.action(type='grid', x=1, y=8, state=0)
    c.elapse(.06); c.wait(lambda s: capture.extend(s) and not s['midi_capture']['outstanding'])
    c.tap(2, 8)                                                   # disarm
    notes = [m for m in capture.note_ons() if m['bytes'][1] in (60, 62, 64, 65)]
    first_bar = notes[:4]
    assert [(m['port'], m['bytes']) for m in first_bar] == [(1, [144, n, v]) for n, v in PHRASE], \
        [m['bytes'] for m in first_bar]
    start = first_bar[0][field]
    errors = [(m[field] - start) / 1e9 - p / PULSE_RATE for m, p in zip(first_bar, plan)]
    assert max(map(abs, errors)) <= tolerance, dict(expected_pulses=plan[:4], errors=errors)
    # Every complete one-step gate of the first bar ends at the following shuffled onset.
    for note, nxt in zip(first_bar, notes[1:5]):
        off = [e for e in capture.events if e['index'] > note['index'] and e['bytes'] == [128, note['bytes'][1], note['bytes'][2]]][0]
        assert abs(off[field] - nxt[field]) / 1e9 <= tolerance, dict(note=note['bytes'], off=off, next=nxt['bytes'])
    assert len(note_pairs(capture.events)) == len(capture.note_ons()), 'Unbalanced first-bar gates'
    c.results.append(dict(kind='shuffle-first-bar', expected_pulses=plan[:4], max_phase_error_seconds=max(map(abs, errors)), passed=True))
    # README 239: the step active at each note-on holds the recorded note.
    replay = c.playback([(1, [144, 60, 127]), (1, [144, 72, 90]), (1, [144, 79, 80]), (1, [144, 65, 97])], cycles=2)
    start = replay[0][field]
    errors = [(m[field] - start) / 1e9 - p / PULSE_RATE for m, p in zip(replay, plan)]
    assert max(map(abs, errors)) <= tolerance, dict(expected_pulses=plan, errors=errors)
    c.results.append(dict(kind='shuffle-first-bar-recorded-replay', onsets=len(replay), max_phase_error_seconds=max(map(abs, errors)), passed=True))
