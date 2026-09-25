"""Live UI acceptance matrix items (docs/ui-reimplementation/spec.json#/acceptance_matrix).

Each case drives the live norns screen through its real inputs and checks the
three observables the matrix names: the native framebuffer (live header and
selected-field oracles, rendered independently by frame_oracle), grid LEDs and
MIDI. The musical column is always checked against exact MIDI: navigation and
inspection must leave the canonical four-note phrase from configure() exactly
as it was, and edits must change exactly the notes/CCs the README describes.

Texts marked "characterisation" are implementation messages or labels the
README does not quote; they are pinned so a refactor cannot silently change
them. Where the live app has no route for a matrix input, the requirement's
domain text in manual-inventory.json says so; nothing here stands in for it.
"""
import base64

from midi_window import MidiWindow

# configure(): steps 1-4 play C4 D4 E4 F4 at velocities 127/117/107/97 on port 1, MIDI channel 1.
PHRASE = ((60, 127), (62, 117), (64, 107), (65, 97))
MELODY = [(1, [144, n, v]) for n, v in PHRASE]
NOTE_NAMES = {60: 'C3', 62: 'D3', 64: 'E3', 65: 'F3'}  # norns note names (C3 = MIDI 60)


def _melody(pairs):
    return [(1, [144, n, v]) for n, v in pairs]


def _step_cells():
    return [((s - 1) % 16 + 1, (s - 1) // 16 + 4) for s in range(1, 65)]


def _grid(c):
    return list(c.snapshot()['grid'])


def _expect_grid(c, expected, stage):
    """Every one of the 128 LEDs equals ``expected`` (a full grid snapshot)."""
    cells = [(x, y) for y in range(1, 9) for x in range(1, 17)]
    c.led_values(cells, list(expected))
    c.results.append(dict(kind='full-grid-unchanged', stage=stage, passed=True))


def _wait_frame(c, predicate, kind, **detail):
    row = dict(kind=kind, passed=False, **detail)
    c.results.append(row)
    c.wait(predicate)
    row['passed'] = True


def _live_header(c, title, scope, layout, stage):
    from frame_oracle import live_header_matches
    _wait_frame(c, lambda s: live_header_matches(s, title, scope, layout), 'live-header',
                title=title, scope=scope, stage=stage)


def _overview_selection(state, layout, cells, selected):
    """Every overview cell shows its short label and compact value; only
    ``selected`` (1-based) draws its label at the selection level 15, every
    other label at 9 (lib/ui_render.lua overview layouts).

    A cell is (label, value) or (label, value, marker): ``marker`` is the
    one-letter state marker the renderer draws in the cell's top-right corner
    ('L' a lock on a held step, 'S' a slide; None or absent: no marker). With a
    marker the label is fitted to w-11 and the letter drawn at (x+w-6, y+7)
    level 15; each cell's whole region is compared, so a marker that is not
    expected (or a missing one) fails the cell."""
    from frame_oracle import render, fit, _region_matches
    columns, width = (4, 32) if layout == 'overview_masks' else (5, 25)
    commands = []
    for index, cell in enumerate(cells, start=1):
        label, value = cell[:2]
        marker = cell[2] if len(cell) > 2 else None
        x = ((index - 1) % columns) * width
        y = 9 + ((index - 1) // columns) * 18
        commands.append((x + 2, y + 7, 15 if index == selected else 9, fit(label, width - 11 if marker else width - 5)))
        if marker:
            commands.append((x + width - 6, y + 7, 15, marker))
        commands.append((x + 2, y + 15, 13, str(value)))
    expected = render(commands)
    actual = base64.b64decode(state['frame']['pixels_base64'])
    for index in range(1, len(cells) + 1):
        x = ((index - 1) % columns) * width
        y = 9 + ((index - 1) // columns) * 18
        if not _region_matches(actual, expected, y + 1, y + 16, x + 1, x + width - 3):
            return False
    return True


MASK_LABELS = ('Trig', 'Note', 'Vel', 'Len', 'Chd1', 'Chd2', 'Chd3', 'Chd4')


def _expect_masks(c, values, selected, label, value, stage):
    """C01: all eight cells, the selected cell and its full value line."""
    from frame_oracle import selected_field_matches
    cells = list(zip(MASK_LABELS, values))
    _wait_frame(c, lambda s: _overview_selection(s, 'overview_masks', cells, selected)
                and selected_field_matches(s, 'overview_masks', label, value),
                'masks-overview', stage=stage, selected=selected, label=label, value=value)


def _expect_params(c, cells, selected, label, value, stage):
    """C02: all ten slots, the selected slot and its full value line."""
    from frame_oracle import selected_field_matches
    _wait_frame(c, lambda s: _overview_selection(s, 'overview_params', cells, selected)
                and selected_field_matches(s, 'overview_params', label, value),
                'params-overview', stage=stage, selected=selected, label=label, value=value)


def _expect_focused(c, label, value, stage):
    from frame_oracle import selected_field_matches
    _wait_frame(c, lambda s: selected_field_matches(s, 'focused', label, value),
                'focused-field', stage=stage, label=label, value=value)


def _expect_detail(c, label, value, stage):
    from frame_oracle import selected_field_matches
    _wait_frame(c, lambda s: selected_field_matches(s, 'detail', label, value),
                'detail-row', stage=stage, label=label, value=value)


def _expect_footer(c, text, stage):
    """The footer line (1,63) level 9 shows exactly ``text`` (a tooltip)."""
    from frame_oracle import render
    region = [(y * 128 + x) * 4 + k for y in range(56, 64) for x in range(128) for k in range(3)]
    expected = render([(1, 63, 9, text)])
    wanted = [expected[i] for i in region]

    def matches(state):
        pixels = base64.b64decode(state['frame']['pixels_base64'])
        return [pixels[i] for i in region] == wanted
    _wait_frame(c, matches, 'footer-tooltip', stage=stage, text=text)


def _silent_midi(c, marker, stage):
    count = c.snapshot()['midi_count']
    assert count == marker, ('MIDI emitted without transport', stage, marker, count)
    c.results.append(dict(kind='no-midi', stage=stage, midi_count=count, passed=True))


_HELD = set()


def _hold(c, *steps):
    for step in steps:
        x, y = c.ui.step(step)
        c.action(type='grid', x=x, y=y, state=1)
        _HELD.add(step)


def _release(c, *steps):
    """Release steps still held (a finally clause may name already released ones)."""
    for step in steps:
        if step in _HELD:
            x, y = c.ui.step(step)
            c.action(type='grid', x=x, y=y, state=0)
            _HELD.discard(step)


def _shift_key(c, key):
    """K1 held as a modifier (long enough not to be a menu press), then ``key``."""
    c.action(type='key', n=1, state=1)
    try:
        c.elapse(.3)
        c.key(key)
    finally:
        c.action(type='key', n=1, state=0)
    c.elapse(.1)


def _set_lock(c, value):
    """Set the selected trig parameter to ``value`` from Off: E3 edits are relative to the
    parameter's last value (not the held step's), so saturate to Off (X) first, then one
    detent reaches 0 (README Trig Param Locks; the same recipe as the memory lock cases)."""
    c.action(type='enc', n=3, delta=-126)
    c.elapse(.15)
    c.enc(3, value + 1)


def _play_window(c, onsets, timeout=6):
    """Play until ``onsets`` note-ons arrive, stop, and return every event in order."""
    window = MidiWindow(c.snapshot()['midi_count'])
    c.tap(1, 8)
    state = c.wait(lambda s: len(MidiWindow(window.cursor).extend(s).note_ons()) >= onsets, timeout)
    window.extend(state)
    c.tap(1, 8)
    window.extend(c.wait(lambda s: s['midi_capture']['outstanding'] == []))
    return window


def _no_notes_while_playing(c, seconds, stage):
    window = MidiWindow(c.snapshot()['midi_count'])
    c.tap(1, 8)
    c.elapse(seconds)
    window.extend(c.snapshot())
    c.tap(1, 8)
    window.extend(c.wait(lambda s: s['midi_capture']['outstanding'] == []))
    ons = window.note_ons()
    assert not ons, ('Muted channel sounded', stage, [e['bytes'] for e in ons])
    c.results.append(dict(kind='muted-silence', stage=stage, seconds=seconds, passed=True))


# ---------------------------------------------------------------------------------------------
# A01: E1 opens Channel tasks on the row it came from; rows move one per event, clamped; each
# family keeps its remembered field; held steps still switch families; no music changes.

CHANNEL_TASK_LABELS = ('Masks', 'Trig params', 'Output', 'Harmony', 'Clock', 'Merge modes', 'Device', 'History',
                       'Merge Shape')


def _e1_event(c, delta):
    """One native E1 event of ``delta`` (a large single turn when |delta| > 2)."""
    c.action(type='enc', n=1, delta=delta)
    c.elapse(.2)


def _task_row(c, label, stage):
    c.ui.expect_header('channel_tasks', channel=1)
    c.ui.expect_task_row(label)
    c.results.append(dict(kind='task-row', stage=stage, label=label, passed=True))


def ui_accept_a01(c):
    """README Norns Menu Navigation / Grid Menu Navigation (owner decision 25 September 2026):
    E1 opens Channel tasks from Masks and from Trig params, on the row of the screen it came
    from; in the list E1 moves one row per encoder event (a large single event too), clamped at
    both ends, and K3 opens the row; each family keeps its own selected field when reopened;
    with a step held E1 still switches Masks <-> Trig params (clamped); navigation never
    changes MIDI output, masks or grid LEDs."""
    ui = c.ui
    c.configure()
    c.playback(MELODY, cycles=2)
    ui.tap_control('channel_editor')
    ui.channel_page('masks')
    marker = c.snapshot()['midi_count']
    x8 = ['X'] * 8
    c.enc(2, -10); c.enc(2, 2)
    _expect_masks(c, x8, 3, 'Velocity', 'X', 'c01-select-velocity')
    grid_before = _grid(c)
    # E1 negative (one detent) at C01 opens Channel tasks on the Masks row.
    c.enc(1, -1)
    _task_row(c, 'Masks', 'c01-e1-negative-opens-tasks-on-masks')
    # At the first row, E1 negative clamps: one detent, then one large single event.
    c.enc(1, -1)
    _task_row(c, 'Masks', 'first-row-e1-negative-clamped')
    _e1_event(c, -20)
    _task_row(c, 'Masks', 'first-row-large-negative-clamped')
    # Large positive single events move exactly one row each, never skipping.
    _e1_event(c, 20)
    _task_row(c, 'Trig params', 'large-positive-one-row')
    _e1_event(c, 20)
    _task_row(c, 'Output', 'second-large-positive-one-row')
    _e1_event(c, -20)
    _task_row(c, 'Trig params', 'large-negative-one-row')
    # K3 opens Trig params; give it its own remembered field (slot 3).
    c.key(3)
    ui.expect_header('trig_locks', channel=1)
    c.enc(2, -12); c.enc(2, 2)
    slots = [('None', 'X')] * 10
    _expect_params(c, slots, 3, 'None', 'X', 'c02-select-slot3')
    # E1 positive (one detent) at C02 opens the list on Trig params; K3 goes straight back.
    c.enc(1, 1)
    _task_row(c, 'Trig params', 'c02-e1-positive-opens-tasks-on-trig-params')
    c.key(3)
    ui.expect_header('trig_locks', channel=1)
    _expect_params(c, slots, 3, 'None', 'X', 'c02-field-kept-through-tasks')
    # A large single E1 event at C02 opens the list only (on Trig params, not a row further).
    _e1_event(c, 20)
    _task_row(c, 'Trig params', 'c02-large-e1-opens-tasks-only')
    c.enc(1, -1)
    _task_row(c, 'Masks', 'e1-back-to-masks-row')
    c.key(3)
    ui.expect_header('masks', channel=1)
    _expect_masks(c, x8, 3, 'Velocity', 'X', 'c01-field-kept')
    # Last row: eight large events reach Merge Shape one row at a time; the next clamps.
    _e1_event(c, 20)
    _task_row(c, 'Masks', 'c01-large-e1-opens-tasks-only')
    for label in CHANNEL_TASK_LABELS[1:]:
        _e1_event(c, 20)
        _task_row(c, label, 'large-positive-to-' + label)
    _e1_event(c, 20)
    _task_row(c, 'Merge Shape', 'last-row-large-positive-clamped')
    c.enc(1, 1)
    _task_row(c, 'Merge Shape', 'last-row-e1-positive-clamped')
    # Back up with E1 one detent at a time to Trig params; it opens with slot 3 kept.
    for label in reversed(CHANNEL_TASK_LABELS[1:-1]):
        c.enc(1, -1)
        _task_row(c, label, 'e1-negative-to-' + label)
    c.key(3)
    ui.expect_header('trig_locks', channel=1)
    _expect_params(c, slots, 3, 'None', 'X', 'n01-restores-c02-field')
    # Held steps: E1 switches between the edit families (clamped), never opening tasks.
    with ui.hold_step(5):
        ui.expect_header('trig_locks', channel=1, held=(5,))
        c.enc(1, 1)
        ui.expect_header('trig_locks', channel=1, held=(5,))
        c.enc(1, -1)
        ui.expect_header('masks', channel=1, held=(5,))
        c.enc(1, -1)
        ui.expect_header('masks', channel=1, held=(5,))
        c.enc(1, 1)
        ui.expect_header('trig_locks', channel=1, held=(5,))
        c.results.append(dict(kind='held-e1-switches-family', passed=True))
    ui.expect_header('trig_locks', channel=1)
    ui.channel_page('masks')
    _expect_masks(c, x8, 3, 'Velocity', 'X', 'c01-restored')
    # No output, mask or LED change from any of it.
    _silent_midi(c, marker, 'e1-navigation')
    _expect_grid(c, grid_before, 'e1-navigation')
    c.playback(MELODY, cycles=2)
    c.results.append(dict(kind='a01-summary', passed=True))


# ---------------------------------------------------------------------------------------------
# A02: held-set clears on Masks and Trig params with K1 down; release order; defaults kept.

def _cc_cycles(window, steps=4):
    """Per played cycle, per step: the CC and note-on messages from just after the previous
    note-on up to and including this step's note-on (a lock's CC is sent just before its
    note; slide values fall between notes). The window starts at step 1."""
    events = [tuple(e['bytes']) for e in window.events
              if e['bytes'][0] == 176 or (e['bytes'][0] == 144 and e['bytes'][2] > 0)]
    rows, current = [], []
    for event in events:
        current.append(event)
        if event[0] == 144:
            rows.append(current)
            current = []
    return [rows[i:i + steps] for i in range(0, len(rows) - steps + 1, steps)]


def ui_accept_a02(c):
    """README Removing Masks / Mask Locks / Trig Param Locks: with steps 1 and 64 held,
    K1+K2 clears only the held steps' overrides (held steps take precedence while K1 is
    down); channel defaults and unheld locks stay; either release order restores the
    family screen at channel scope."""
    ui = c.ui
    c.configure()
    ui.tap_control('channel_editor')
    ui.channel_page('masks')
    range_leds = [15] * 4 + [0] * 60
    c.led_values(_step_cells(), range_leds)
    # Channel default velocity mask 3 (X -> 0 on the first detent).
    c.enc(2, -10); c.enc(2, 2); c.enc(3, 4)
    _expect_masks(c, ['X', 'X', '3', 'X', 'X', 'X', 'X', 'X'], 3, 'Velocity', '3', 'channel-default-velocity')
    c.enc(2, -1)
    # Note locks on steps 1, 2 and 64 (X -> C-2 on the first detent).
    for step, detents, name in ((1, 2, 'C#-2'), (2, 4, 'D#-2'), (64, 5, 'E-2')):
        with ui.hold_step(step):
            ui.expect_header('masks', channel=1, held=(step,))
            c.enc(3, detents)
            _expect_masks(c, ['X', name, '3', 'X', 'X', 'X', 'X', 'X'], 2, 'Note', name,
                          'note-lock-step%d' % step)
    # README Snap Note Masks to Scale (default on): C#-2 plays C-2 (0), D#-2 plays D-2 (2).
    locked = _melody([(0, 3), (2, 3), (64, 3), (65, 3)])
    c.playback(locked, cycles=2)
    # Held set {1, 64}: K1+K2 clears only these steps' mask overrides. Both steps are held
    # past the 1 s grid long press first: a quicker end-first release of the same keys is
    # also the Channel Length dual-press gesture and commits range 1-64 (owner grid
    # semantics, reported separately); this case observes the clear alone.
    _hold(c, 1, 64)
    c.elapse(1.2)
    try:
        ui.expect_header('masks', channel=1, held=(1, 64))
        _shift_key(c, 2)
        ui.expect_header('masks', channel=1, held=(1, 64))
        _expect_masks(c, ['X', 'X', '3', 'X', 'X', 'X', 'X', 'X'], 2, 'Note', 'X', 'held-set-cleared')
        # Release order one: 64 first, 1 still held.
        _release(c, 64)
        ui.expect_header('masks', channel=1, held=(1,))
        _expect_masks(c, ['X', 'X', '3', 'X', 'X', 'X', 'X', 'X'], 2, 'Note', 'X', 'step1-cleared')
    finally:
        _release(c, 1, 64)
    ui.expect_header('masks', channel=1)
    _expect_masks(c, ['X', 'X', '3', 'X', 'X', 'X', 'X', 'X'], 2, 'Note', 'X', 'channel-scope-restored')
    c.led_values(_step_cells(), range_leds)  # channel range 1-4 unchanged
    with ui.hold_step(2):
        ui.expect_header('masks', channel=1, held=(2,))
        _expect_masks(c, ['X', 'D#-2', '3', 'X', 'X', 'X', 'X', 'X'], 2, 'Note', 'D#-2', 'unheld-lock-kept')
    ui.expect_header('masks', channel=1)
    with ui.hold_step(64):
        _expect_masks(c, ['X', 'X', '3', 'X', 'X', 'X', 'X', 'X'], 2, 'Note', 'X', 'step64-cleared')
    ui.expect_header('masks', channel=1)
    after_masks = _melody([(60, 3), (2, 3), (64, 3), (65, 3)])
    c.playback(after_masks, cycles=2)

    # Trig params: CC 1 in slot 1, step locks on 1, 3 and 64, default Off (X).
    ui.channel_page('trig_locks')
    c.enc(2, -12)
    ui.assign_trig_parameter('CC 1')
    ui.expect_header('trig_locks', channel=1)
    none = [('None', 'X')] * 9
    _expect_params(c, [('CC1', 'X')] + none, 1, 'CC 1', 'X', 'cc1-assigned')
    for step, value in ((1, '10'), (3, '20'), (64, '30')):
        with ui.hold_step(step):
            ui.expect_header('trig_locks', channel=1, held=(step,))
            _set_lock(c, int(value))
            # 'L' at once: a lock made while the step is held is that step's lock even
            # before release commits its history portion (recorder.add_trig_lock_event_portion).
            _expect_params(c, [('CC1', value, 'L')] + none, 1, 'CC 1', value, 'cc-lock-step%d' % step)
    ui.expect_header('trig_locks', channel=1)

    def heard(stage, step_ccs):
        window = _play_window(c, 9)
        cycles = _cc_cycles(window)
        assert len(cycles) >= 2, (stage, cycles)
        want = []
        for (note, vel), cc in zip(after_masks_pairs, step_ccs):
            want.append(([(176, 1, cc)] if cc is not None else []) + [(144, note, vel)])
        for cycle in cycles:
            assert cycle == want, dict(stage=stage, expected=want, actual=cycle)
        c.results.append(dict(kind='cc-and-notes', stage=stage, cycles=cycles, passed=True))
    after_masks_pairs = [(60, 3), (2, 3), (64, 3), (65, 3)]
    heard('cc-locks', [10, None, 20, None])
    _hold(c, 1, 64)
    c.elapse(1.2)  # past the grid long press, as above
    try:
        ui.expect_header('trig_locks', channel=1, held=(1, 64))
        _shift_key(c, 2)
        _expect_params(c, [('CC1', 'X')] + none, 1, 'CC 1', 'X', 'held-cc-cleared')
        # Release order two: 1 first, 64 still held.
        _release(c, 1)
        ui.expect_header('trig_locks', channel=1, held=(64,))
        _expect_params(c, [('CC1', 'X')] + none, 1, 'CC 1', 'X', 'step64-cc-cleared')
    finally:
        _release(c, 1, 64)
    ui.expect_header('trig_locks', channel=1)
    _expect_params(c, [('CC1', 'X')] + none, 1, 'CC 1', 'X', 'cc-default-still-off')
    c.led_values(_step_cells(), range_leds)
    with ui.hold_step(3):
        # 'L': the held step has a (committed) lock in this slot.
        _expect_params(c, [('CC1', '20', 'L')] + none, 1, 'CC 1', '20', 'unheld-cc-lock-kept')
    heard('after-held-cc-clear', [None, None, 20, None])
    # The Masks channel default and the unheld step-2 mask survived the Trig params clear.
    ui.channel_page('masks')
    _expect_masks(c, ['X', 'X', '3', 'X', 'X', 'X', 'X', 'X'], 2, 'Note', 'X', 'masks-after-trig-clear')
    c.results.append(dict(kind='a02-summary', passed=True))


# ---------------------------------------------------------------------------------------------
# A03: assignment picker keeps its target slot; K2 discards an unapplied browse; K3 applies.

def ui_accept_a03(c):
    """README Trig Param Locks / Param Slides: K2 on a slot opens its parameter picker, E3
    browses, K2 leaves without applying, K3 applies (repeatable) to the same slot; a held
    step + K3 slides the lock toward the next lock; Off (X) sends no CC."""
    ui = c.ui
    c.configure()
    ui.tap_control('channel_editor')
    ui.channel_page('trig_locks')
    c.enc(2, -12); c.enc(2, 1)
    none10 = [('None', 'X')] * 10
    _expect_params(c, none10, 2, 'None', 'X', 'target-slot2')
    c.key(2)
    ui.expect_header('assignment', channel=1)
    ui.expect_list_label('None')
    c.enc(3, 1)
    ui.expect_list_label('Fixed Note')
    c.key(2)  # cancel the unapplied browse
    ui.expect_header('trig_locks', channel=1)
    _expect_params(c, none10, 2, 'None', 'X', 'cancel-keeps-slot2-unassigned')
    _expect_footer(c, 'Action cancelled', 'k2-cancel')  # characterisation
    c.key(2)
    ui.expect_header('assignment', channel=1)
    ui.expect_list_label('None')  # the discarded candidate is not remembered
    c.enc(3, 15)
    ui.expect_list_label('CC 1')
    c.key(3)
    ui.expect_header('assignment', channel=1)
    _expect_detail(c, 'CC 1', 'CURRENT', 'k3-applied')
    c.key(3)
    ui.expect_header('assignment', channel=1)
    _expect_detail(c, 'CC 1', 'CURRENT', 'k3-repeat-idempotent')
    c.enc(3, 1)
    _expect_detail(c, 'CC 2', '', 'browse-after-apply')
    c.key(2)
    ui.expect_header('trig_locks', channel=1)
    slots = [('None', 'X'), ('CC1', 'X')] + [('None', 'X')] * 8
    _expect_params(c, slots, 2, 'CC 1', 'X', 'applied-to-slot2-browse-discarded')
    # Off policy: an assigned CC with default X sends no CC at all.
    window = _play_window(c, 9)
    cycles = _cc_cycles(window)
    assert cycles and all(cycle == [[(144, n, v)] for n, v in PHRASE] for cycle in cycles), cycles
    c.results.append(dict(kind='cc-off-sends-nothing', cycles=cycles, passed=True))
    # Lock step 1 = 10 and slide it (held K3) toward step 3 = 40.
    with ui.hold_step(1):
        ui.expect_header('trig_locks', channel=1, held=(1,))
        _set_lock(c, 10)
        slots[1] = ('CC1', '10', 'L')  # the held step's lock, shown at once (see A02)
        _expect_params(c, slots, 2, 'CC 1', '10', 'step1-lock')
        c.key(3)
        ui.expect_header('trig_locks', channel=1, held=(1,))
        slots[1] = ('CC1', '10', 'S')  # the held step now slides (S takes the corner from L)
        _expect_params(c, slots, 2, 'CC 1', '10', 'step1-slide-keeps-value')
    with ui.hold_step(3):
        _set_lock(c, 40)
        slots[1] = ('CC1', '40', 'L')  # the held step's new lock, no slide of its own: L
        _expect_params(c, slots, 2, 'CC 1', '40', 'step3-lock')
    ui.expect_header('trig_locks', channel=1)
    window = _play_window(c, 9)
    cycles = _cc_cycles(window)
    assert len(cycles) >= 2, cycles
    for cycle in cycles:
        one, two, three, four = cycle
        # Step 1: its lock value, sent before its note (order).
        assert one == [(176, 1, 10), (144, 60, 127)], cycle
        # The slide moves linearly from 10 and arrives at step 3's lock 40 before step 3's
        # note (six equal pulses of 5 across the two step gaps); wrap is off, so nothing
        # slides after step 3.
        assert two == [(176, 1, 15), (176, 1, 20), (144, 62, 117)], cycle
        assert three == [(176, 1, 25), (176, 1, 30), (176, 1, 35), (176, 1, 40), (144, 64, 107)], cycle
        # Step 4 has no lock and the default is Off: no CC.
        assert four == [(144, 65, 97)], cycle
    c.results.append(dict(kind='cc-slide', cycles=cycles, passed=True))
    # The slide never moved the assignment: slot 1 is still unassigned, slot 2 still CC 1.
    slots[1] = ('CC1', 'X')
    _expect_params(c, slots, 2, 'CC 1', 'X', 'slot-assignment-kept')
    c.results.append(dict(kind='a03-summary', passed=True))


# ---------------------------------------------------------------------------------------------
# A10: the screen follows resolved channel-page grid actions; merge arithmetic unchanged.

PATTERN_ROW = [(x, 2) for x in range(1, 17)]
PATTERN_NOTES = [(60, 114), (60, 109), (60, 107), (60, 97)]
CHANNEL_ROW = [(x, 1) for x in range(1, 17)]


def ui_accept_a10(c):
    """README Norns Menu Navigation / Adding Patterns to Channels / Merge Modes / Channel Length /
    Muting Channels: a pattern assignment or merge button on the Channel page shows Merge detail
    with the changed row chosen, and K2 returns to Masks with its field (usability audit 25
    September 2026); channel selection, mutes and ranges keep Masks with footer feedback (a mute
    shows in the scope); a held note-merge + pattern slot shows Merge detail without assigning
    the pattern; merged MIDI follows the README arithmetic."""
    ui = c.ui
    c.configure()
    c.playback(MELODY, cycles=2)
    # Pattern 2: trigs on steps 1 and 2, default note 0 (C4) and velocity 100.
    ui.tap_control('pattern_editor')
    ui.expect_header('trigger_editor')
    ui.tap_control('pattern_select', 2)
    ui.tap_step(1); ui.tap_step(2)
    ui.tap_control('channel_editor')
    ui.channel_page('masks')
    c.enc(2, -10); c.enc(2, 1)
    x8 = ['X'] * 8
    _expect_masks(c, x8, 2, 'Note', 'X', 'start')
    c.led_values(PATTERN_ROW, [15] + [2] * 15)
    # Channel selection: scope follows, Masks and its field stay.
    ui.select_channel(3)
    ui.expect_header('masks', channel=3)
    _expect_footer(c, 'Channel 3 selected', 'select-3')
    c.led_values(CHANNEL_ROW, [2, 2, 15] + [2] * 13)
    ui.select_channel(1)
    ui.expect_header('masks', channel=1)
    c.led_values(CHANNEL_ROW, [15] + [2] * 15)
    # Remove pattern 1 then add pattern 2: each shows Merge detail on Patterns (the new
    # assignment) with the tooltip; K2 returns to Masks.
    ui.tap_control('pattern_slot', 1)
    _merge_follow(c, 'Patterns', 'NONE', 'Pattern 1 removed from ch. 1', 'remove-1')
    c.led_values(PATTERN_ROW, [2] * 16)
    ui.tap_control('pattern_slot', 2)
    _merge_follow(c, 'Patterns', '02', 'Pattern 2 added to ch. 1', 'add-2')
    c.led_values(PATTERN_ROW, [2, 15] + [2] * 14)
    c.playback(_melody([(60, 100), (60, 100)]), cycles=2)  # pattern 2 alone
    ui.tap_control('pattern_slot', 1)
    _merge_follow(c, 'Patterns', '01 02', 'Pattern 1 added to ch. 1', 'add-1')
    _expect_masks(c, x8, 2, 'Note', 'X', 'field-kept-after-patterns')
    c.led_values(PATTERN_ROW, [15, 15] + [2] * 14)
    # Merge detail shows the full assignment and the current modes.
    ui.open_channel_task('merge')
    _live_header(c, 'MERGE MODES', 'CH01', 'detail', 'merge-detail')
    c.enc(2, -6)
    _expect_detail(c, 'Patterns', '01 02', 'merge-patterns')
    c.enc(2, 1)
    _expect_detail(c, 'Trig mode', 'SKIP', 'merge-trig-mode-default')
    # Skip: trigs only where exactly one pattern has one (steps 3 and 4).
    c.playback(_melody([(64, 107), (65, 97)]), cycles=2)
    c.key(2)  # K2 returns to the remembered Channel family (Masks)
    ui.expect_header('masks', channel=1)
    # Trig merge (14,8) cycles Skip -> Only -> All; each shows Merge detail on Trig mode.
    ui.tap_control('trig_merge_mode')
    _merge_follow(c, 'Trig mode', 'ONLY', 'Only trig merge mode', 'trig-only')
    # Only: steps where both patterns trig; velocity average rounds half up:
    # (127+100)/2 = 113.5 -> 114, (117+100)/2 = 108.5 -> 109; note average (0+0)/2 = 0 -> C4,
    # (1+0)/2 = 0.5 -> 1 -> D4 (README Note/Velocity Merge Modes: Average).
    c.playback(_melody([(60, 114), (62, 109)]), cycles=2)
    ui.tap_control('trig_merge_mode')
    _merge_follow(c, 'Trig mode', 'ALL', 'All trig merge mode', 'trig-all')
    all_average = [(60, 114), (62, 109), (64, 107), (65, 97)]
    c.playback(_melody(all_average), cycles=2)
    # Held note merge + an unassigned pattern (3): Merge detail follows, the pattern is a
    # note source only, never an assignment.
    with ui.hold_control('note_merge_mode'):
        c.elapse(.2)
        ui.tap_control('pattern_slot', 3)
        _live_header(c, 'MERGE MODES', 'CH01', 'detail', 'note-merge-source')
        _expect_footer(c, 'Note merge mode pattern 3', 'note-merge-3')  # characterisation
    # Merge detail keeps its own row (Trig mode); the assignment is still patterns 1 and 2,
    # and the note merge source reads as the manual names it.
    _expect_detail(c, 'Trig mode', 'ALL', 'follow-keeps-merge-row')
    c.enc(2, 1)
    _expect_detail(c, 'Note mode', 'PAT 3', 'note-merge-source-row')
    c.enc(2, -3)
    _expect_detail(c, 'Patterns', '01 02', 'source-not-assigned')
    c.led_values(PATTERN_ROW, [15, 15] + [2] * 14)
    c.key(2)
    ui.expect_header('masks', channel=1)
    _expect_masks(c, x8, 2, 'Note', 'X', 'k2-returns-from-merge-follow')
    # Note merge Pattern with pattern 2: every trigged step takes pattern 2's note value
    # (README: the chosen pattern need not even be assigned, so it supplies the notes, not
    # the trigs): all four notes are degree 0 (C4); velocity stays Average.
    with ui.hold_control('note_merge_mode'):
        c.elapse(.2)
        ui.tap_control('pattern_slot', 2)
        _expect_footer(c, 'Note merge mode pattern 2', 'note-merge-2')
    c.key(2)
    ui.expect_header('masks', channel=1)
    c.playback(_melody(PATTERN_NOTES), cycles=2)
    # Mute: K1 + channel select mutes immediately; the screen stays on Masks, and its scope
    # shows the mute (CH01 MUTE).
    _shift_channel(c, 1)
    _expect_footer(c, 'Channel 1 muted', 'mute-shift')
    ui.expect_header('masks', channel=1, mute=True)
    # README: the button dims; selected and muted shows level 7 (characterisation).
    c.led_values(CHANNEL_ROW, [7] + [2] * 15)
    _no_notes_while_playing(c, 1.5, 'shift-mute')
    _shift_channel(c, 1)
    _expect_footer(c, 'Channel 1 unmuted', 'unmute-shift')
    ui.expect_header('masks', channel=1)
    c.led_values(CHANNEL_ROW, [15] + [2] * 15)
    # Long press (1 s) on another channel mutes it without moving the scope.
    with ui.hold_control('channel', 4):
        c.elapse(1.3)
    _expect_footer(c, 'Channel 4 muted', 'mute-long')
    ui.expect_header('masks', channel=1)
    c.led_values(CHANNEL_ROW, [15, 2, 2, 0] + [2] * 12)
    c.playback(_melody(PATTERN_NOTES), cycles=2)
    # Dual range, documented order (end released first, then start): steps 1-2 only.
    ui.set_range(1, 2)
    _expect_footer(c, 'Channel 1 length changed', 'range-1-2')
    ui.expect_header('masks', channel=1)
    c.playback(_melody([(60, 114), (60, 109)]), cycles=2)
    ranged = [15, 15] + [0] * 62  # README: the active range is the brighter buttons
    c.led_values(_step_cells(), ranged)
    # Start released first: resolved as a reversed selection and rejected (characterisation),
    # the range and the screen unchanged.
    ui.gesture([('step', 1), ('step', 4)], [('step', 1), ('step', 4)])
    _expect_footer(c, 'End must follow start', 'range-start-released-first')
    ui.expect_header('masks', channel=1)
    c.led_values(_step_cells(), ranged)
    c.playback(_melody([(60, 114), (60, 109)]), cycles=2)
    _expect_masks(c, x8, 2, 'Note', 'X', 'field-kept-at-end')
    c.results.append(dict(kind='a10-summary', passed=True))


def _merge_follow(c, label, value, tooltip, stage):
    """A Channel-page merge/assignment tap shows Merge detail (C09) with the row it changed
    chosen and the action's tooltip; K2 returns to Masks (usability audit 25 September 2026)."""
    _live_header(c, 'MERGE MODES', 'CH01', 'detail', stage)
    _expect_detail(c, label, value, stage)
    _expect_footer(c, tooltip, stage)
    c.key(2)
    c.ui.expect_header('masks', channel=1)


def _shift_channel(c, channel):
    c.action(type='key', n=1, state=1)
    try:
        c.elapse(.3)
        c.ui.tap_control('channel', channel)
    finally:
        c.action(type='key', n=1, state=0)
    c.elapse(.1)


# ---------------------------------------------------------------------------------------------
# A11: view_channel E3 is inspection only.

def _viewer_cells(state, levels):
    pixels = base64.b64decode(state['frame']['pixels_base64'])
    for k, level in enumerate(levels):
        x = 2 + (k % 16) * 8
        y = 24 + (k // 16) * 8
        if any(pixels[((y + dy) * 128 + x + dx) * 4] != level * 17 for dy in range(4) for dx in range(4)):
            return False
    return True


CH01_CELLS = [15] * 4 + [0] * 60
EMPTY_CELLS = [2] * 64


def ui_accept_a11(c):
    """README Adding Trigs / Adding Notes / Adding Velocity / Rhythm Doctor (pattern viewer):
    on the 64-cell screens E3 moves only the viewed channel (clamped 1..16, kept per context),
    also right after E2, which moves no focus there; Scale overview has no viewer and E2/E3
    change nothing on it; the selected channel, MIDI and grid edits stay on the selected
    channel."""
    from frame_oracle import live_header_matches
    ui = c.ui
    c.configure()
    c.playback(MELODY, cycles=2)
    marker = c.snapshot()['midi_count']

    def viewer(title, scope, cells, stage):
        if title != 'CHANNEL VIEW':
            # The pattern editor names the edited pattern (1) before the viewed channel and
            # draws that pattern's trigs (steps 1-4) at 15 over the viewed channel, which is
            # capped at level 3 as context (usability audit 25 September 2026).
            scope = 'PAT01 ' + scope
            cells = [15 if k < 4 else min(level, 3) for k, level in enumerate(cells)]
        _wait_frame(c, lambda s: live_header_matches(s, title, scope, 'pattern64') and _viewer_cells(s, cells),
                    'pattern-viewer', title=title, scope=scope, stage=stage)
    ui.tap_control('pattern_editor')
    viewer('PATTERN TRIG', 'CH01', CH01_CELLS, 'p01-ch1')
    c.enc(3, -1)
    viewer('PATTERN TRIG', 'CH01', CH01_CELLS, 'p01-lower-clamp')
    c.enc(3, 15)
    viewer('PATTERN TRIG', 'CH16', EMPTY_CELLS, 'p01-ch16')
    c.enc(3, 1)
    viewer('PATTERN TRIG', 'CH16', EMPTY_CELLS, 'p01-upper-clamp')
    # A 64-cell screen shows only its viewed channel: E2 moves no focus, so E3 after E2
    # still turns the viewed channel (owner decision 25 September 2026).
    c.enc(2, 1); c.enc(3, -3)
    viewer('PATTERN TRIG', 'CH13', EMPTY_CELLS, 'p01-e2-then-e3-turns-view')
    c.enc(2, -1); c.enc(3, 3)
    viewer('PATTERN TRIG', 'CH16', EMPTY_CELLS, 'p01-e2-back-e3-turns-view')
    ui.tap_control('pattern_editor')
    viewer('PATTERN NOTE', 'CH01', CH01_CELLS, 'p03-own-state')
    c.enc(3, 5)
    viewer('PATTERN NOTE', 'CH06', EMPTY_CELLS, 'p03-ch6')
    c.enc(3, 10)
    viewer('PATTERN NOTE', 'CH16', EMPTY_CELLS, 'p03-ch16')
    c.enc(3, 1)
    viewer('PATTERN NOTE', 'CH16', EMPTY_CELLS, 'p03-upper-clamp')
    ui.tap_control('pattern_editor')
    viewer('PATTERN VELOCITY', 'CH01', CH01_CELLS, 'p04-own-state')
    c.enc(3, 15)
    viewer('PATTERN VELOCITY', 'CH16', EMPTY_CELLS, 'p04-ch16')
    c.enc(3, -15)
    viewer('PATTERN VELOCITY', 'CH01', CH01_CELLS, 'p04-back-to-ch1')
    c.enc(3, -1)
    viewer('PATTERN VELOCITY', 'CH01', CH01_CELLS, 'p04-lower-clamp')
    ui.tap_control('pattern_editor')
    viewer('PATTERN TRIG', 'CH16', EMPTY_CELLS, 'p01-kept-ch16')
    # P05 in the Trig context shares the Trig viewer.
    ui.open_task('Trig', 'channel_view')
    viewer('CHANNEL VIEW', 'CH16', EMPTY_CELLS, 'p05-trig-ch16')
    c.enc(3, 1)
    viewer('CHANNEL VIEW', 'CH16', EMPTY_CELLS, 'p05-upper-clamp')
    c.enc(3, -15)
    viewer('CHANNEL VIEW', 'CH01', CH01_CELLS, 'p05-ch1')
    c.enc(3, -1)
    viewer('CHANNEL VIEW', 'CH01', CH01_CELLS, 'p05-lower-clamp')
    # S03 (Scale overview) is a dashboard without a channel viewer (owner decision
    # 25 September 2026): its five rows show at once, and E2/E3 change nothing on it.
    ui.tap_control('scale_editor')
    ui.expect_header('scale', slot=1)
    ui.open_task('Scale', 'overview')
    s03 = [('Playing scale', '01'), ('Edit scale', '01'), ('Step / range', '01 / 01..64'), ('Transpose', '0'),
           ('Step lock', 'NONE')]
    ui.expect_dashboard('scale_overview', s03, slot=1)
    c.enc(3, 15); c.enc(2, 1); c.enc(3, -3)
    ui.expect_dashboard('scale_overview', s03, slot=1)
    c.results.append(dict(kind='s03-no-viewer', passed=True))
    # P05 in the Song context has its own viewer: moving it to 16 leaves the Trig viewer
    # (left on channel 1 by P05 in the Trig context above) where it was.
    ui.tap_control('song_editor')
    ui.expect_header('song')
    ui.open_task('Song', 'channel_view')
    song_viewer = lambda scope, cells, stage: _wait_frame(
        c, lambda s: live_header_matches(s, 'CHANNEL VIEW', scope, 'pattern64') and _viewer_cells(s, cells),
        'pattern-viewer', title='CHANNEL VIEW', scope=scope, stage=stage)
    song_viewer('SONG 01', CH01_CELLS, 'p05-song-own-ch1')
    c.enc(3, -1)
    song_viewer('SONG 01', CH01_CELLS, 'p05-song-lower-clamp')
    c.enc(3, 15)
    song_viewer('SONG 01', EMPTY_CELLS, 'p05-song-ch16')
    c.enc(3, 1)
    song_viewer('SONG 01', EMPTY_CELLS, 'p05-song-upper-clamp')
    ui.tap_control('pattern_editor')
    viewer('PATTERN TRIG', 'CH01', CH01_CELLS, 'p01-kept-after-song-viewer')
    # Nothing was written: no MIDI, the selected channel is still 1.
    _silent_midi(c, marker, 'viewer-inspection')
    ui.tap_control('channel_editor')
    ui.channel_page('masks')
    c.led_values(CHANNEL_ROW, [15] + [2] * 15)
    c.playback(MELODY, cycles=2)
    # A grid step edit still edits channel 1: a velocity lock on step 1 plays on MIDI channel 1.
    c.enc(2, -10); c.enc(2, 2)
    with ui.hold_step(1):
        ui.expect_header('masks', channel=1, held=(1,))
        c.enc(3, 6)
        _expect_masks(c, ['X', 'X', '5', 'X', 'X', 'X', 'X', 'X'], 3, 'Velocity', '5', 'step1-velocity-lock')
    ui.expect_header('masks', channel=1)
    c.playback(_melody([(60, 5), (62, 117), (64, 107), (65, 97)]), cycles=2)
    c.results.append(dict(kind='a11-summary', passed=True))


# ---------------------------------------------------------------------------------------------
# A19: Output (C06) inspects the latest event, or a held step in place, without side effects.

def _event_rows(step, held=False):
    """C06 dashboard rows for a played step of the configure() phrase (no chord voice plays):
    the note, velocity / length, the step (HELD while inspected), the pattern degree (0..3,
    signed; no merge changed it), the scale pitch (no harmony moved it) and the note sent, as
    musicutil.note_num_to_name(n, true) names them."""
    note, velocity = PHRASE[step - 1]
    degree = step - 1
    return [('Note', NOTE_NAMES[note]), ('Vel / Len', '%d / 1.0' % velocity),
            ('Step', 'STEP%02d' % step + (' HELD' if held else '')),
            ('Degree', '+%d' % degree if degree > 0 else str(degree)),
            ('Pitch', NOTE_NAMES[note]), ('Sent', NOTE_NAMES[note])]


def _no_event_rows(step=None):
    """No event at all (or a held step without one): every row reads NO EVENT, the step
    row names the held step when one is inspected."""
    rows = [(label, 'NO EVENT') for label in ('Note', 'Vel / Len', 'Step', 'Degree', 'Pitch', 'Sent')]
    if step:
        rows[2] = ('Step', 'STEP%02d HELD' % step)
    return rows


def ui_accept_a19(c):
    """README Note Dashboard / Harmony: Output shows the last played notes of the selected
    channel on one dashboard (note and chord voices, velocity / length, step, pattern degree,
    scale pitch, note sent); nothing played reads NO EVENT; holding a step shows what that step plays in place; a
    step without an event borrows nothing; release returns to the latest event. E2/E3/K3 and
    inspection send no MIDI and change no selection, LED or music."""
    ui = c.ui
    c.configure()
    ui.tap_control('channel_editor')
    ui.channel_page('note_dashboard', confirm=False)
    ui.expect_header('note_dashboard', channel=1)
    ui.expect_dashboard('note_dashboard', _no_event_rows(), channel=1)
    start = c.snapshot()['midi_count']
    c.playback(MELODY, cycles=2)
    state = c.snapshot()
    ons = [m for m in state['midi'] if m['index'] > start and 144 <= m['bytes'][0] <= 159 and m['bytes'][2] > 0]
    latest = [n for n, _ in PHRASE].index(ons[-1]['bytes'][1]) + 1
    c.results.append(dict(kind='latest-event', step=latest, note=ons[-1]['bytes'][1]))
    marker = c.snapshot()['midi_count']
    grid_before = _grid(c)
    ui.expect_header('note_dashboard', channel=1)
    latest_rows = _event_rows(latest)
    ui.expect_dashboard('note_dashboard', latest_rows, channel=1)
    # E2, E3 and K3 on the dashboard change nothing (no cursor, no edit).
    for encoder, delta in ((2, 3), (3, 1), (3, -2), (2, -5)):
        c.enc(encoder, delta)
        ui.expect_dashboard('note_dashboard', latest_rows, channel=1)
    c.key(3)
    ui.expect_header('note_dashboard', channel=1)
    ui.expect_dashboard('note_dashboard', latest_rows, channel=1)
    # Held step with an event: inspected in place on C06.
    held_step = 2 if latest != 2 else 3
    with ui.hold_step(held_step):
        ui.expect_header('note_dashboard', channel=1, held=(held_step,))
        # The event rows (step, degree, pitch, sent) are the held step's; the Note and
        # Vel / Len rows keep the last played note (characterisation: they are the channel's
        # note displays, not the inspected event).
        held_rows = latest_rows[:2] + _event_rows(held_step, held=True)[2:]
        ui.expect_dashboard('note_dashboard', held_rows, channel=1, held=(held_step,))
    ui.expect_header('note_dashboard', channel=1)
    ui.expect_dashboard('note_dashboard', latest_rows, channel=1)
    for step in (40, 64):
        with ui.hold_step(step):
            ui.expect_header('note_dashboard', channel=1, held=(step,))
            ui.expect_dashboard('note_dashboard', _no_event_rows(step), channel=1, held=(step,))
        ui.expect_header('note_dashboard', channel=1)
        ui.expect_dashboard('note_dashboard', latest_rows, channel=1)
    # Inspection sent nothing, moved no selection, changed no LED.
    _silent_midi(c, marker, 'c06-inspection')
    _expect_grid(c, grid_before, 'c06-inspection')
    # The held step was not latched for editing: K2 returns to the remembered Channel
    # family screen (Masks: Channel tasks opens straight from it) at channel scope.
    c.key(2)
    ui.expect_header('masks', channel=1)
    c.playback(MELODY, cycles=2)
    c.results.append(dict(kind='a19-summary', passed=True))
