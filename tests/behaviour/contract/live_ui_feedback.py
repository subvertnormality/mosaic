"""Live UI owner feedback of 25 September 2026 (README "Norns Menu Navigation",
"Adding Trigs", "Rhythm Doctor", "Navigating the Norns Display").

The owner asked for: a selectable Trig Algorithm picker that selects exactly as
the grid algorithm keys do; a Paint Preview that shows the preview's real state;
one-screen dashboards for information-only screens (no cursor); Scale tasks
without Channel view and Trig options with only the tresillo amount; E3 on the
64-cell pattern screens always turning the viewed channel; and grid actions that
show the screen and value they changed. Every check here is exact: live headers,
selected rows and whole dashboards are rendered independently by frame_oracle,
grid LEDs are compared level by level, and the paint preview's trig count on the
screen is compared with the preview cells the grid lights in the same frame.
"""
from frame_oracle import dashboard_row_matches

ALGORITHMS = ('Drum', 'Tresillo', 'Euclidean', 'Numeric', 'Rhythm Doctor')
ALGORITHM_FADER = [(x, 2) for x in range(12, 17)]
STEP_CELLS = [((s - 1) % 16 + 1, (s - 1) // 16 + 4) for s in range(1, 65)]


def _algorithm_leds(c, algorithm):
    """The grid algorithm fader (row 2, columns 12..16) lights exactly the algorithm in use."""
    index = ALGORITHMS.index(algorithm)
    c.led_values(ALGORITHM_FADER, [15 if k == index else 2 for k in range(5)])


def _picker(c, label, selected):
    """P06 TRIG ALGORITHM (detail): the chosen row is ``label``; it reads SELECTED when it
    is the algorithm in use, else blank."""
    c.ui.expect_header('trig_algorithm')
    c.ui.expect_selected_field('detail', label, 'SELECTED' if selected else '')


def _lit_steps(state):
    """Pattern steps the grid lights above the empty-pattern level 2: the paint preview's
    cells (15, or 12 on the blink's dim phase) on an empty pattern."""
    grid = state['grid']
    return frozenset(step for step, (x, y) in enumerate(STEP_CELLS, start=1) if grid[(y - 1) * 16 + x - 1] > 2)


def _paint_preview(c, painting, algorithm, shift, stage):
    """P07 PAINT PREVIEW shows exactly Preview / Algorithm / Shift / Trigs, and Trigs is the
    number of preview cells the grid lights in the same frame (NONE and no cell when not
    painting). Returns the lit preview steps."""
    rows = [('Preview', 'PAINTING' if painting else 'OFF'), ('Algorithm', algorithm), ('Shift', shift)]
    found = []

    def matches(state):
        lit = _lit_steps(state)
        trigs = str(len(lit)) if painting else 'NONE'
        if not painting and lit:
            return False
        if all(dashboard_row_matches(state, i, label, value) for i, (label, value) in enumerate(rows, start=1)) \
                and dashboard_row_matches(state, 4, 'Trigs', trigs):
            found.append(lit)
            return True
        return False
    c.ui.expect_header('paint_preview')
    row = dict(kind='paint-preview', stage=stage, painting=painting, algorithm=algorithm, shift=shift, passed=False)
    c.results.append(row)
    # The preview is built by a debounced job: a frame taken before it lands agrees with
    # itself (no cell, Trigs 0). Accept only a state that still holds, with the same cells,
    # 0.6 s later (longer than the job's debounce).
    for _ in range(10):
        c.wait(matches)
        first = found[-1]
        c.elapse(.6)
        c.wait(matches)
        if found[-1] == first:
            break
    else:
        raise AssertionError(('paint preview never settled', stage))
    row.update(passed=True, trigs=len(found[-1]), steps=sorted(found[-1]))
    return found[-1]


# ---------------------------------------------------------------------------------------------

def live_ui_algorithm(c):
    """README Adding Trigs / Rhythm Doctor: a grid algorithm press shows Trig Algorithm focused
    on the pressed algorithm, which reads SELECTED; E2 moves through the five algorithms and K3
    selects one exactly as its grid key does (the grid fader follows and the next prime paints
    with it); Algorithm in Pattern tasks opens the same screen; K3 on Rhythm Doctor opens the
    Doctor."""
    ui = c.ui
    ui.tap_control('pattern_editor')
    ui.expect_header('trigger_editor')
    # Grid press on Euclidean (14,2): the picker lands on it, SELECTED.
    c.tap(14, 2)
    _picker(c, 'Euclidean', True)
    _algorithm_leds(c, 'Euclidean')
    # E2 moves one row per detent; the other rows are blank and nothing is selected by moving.
    for delta, label in ((-1, 'Tresillo'), (-1, 'Drum'), (-1, 'Drum')):
        c.enc(2, delta)
        _picker(c, label, False)
    _algorithm_leds(c, 'Euclidean')
    # K3 selects Drum exactly as its grid key: SELECTED, tooltip, fader LEDs.
    c.key(3)
    _picker(c, 'Drum', True)
    _expect_footer(c, 'Drum algorithm selected')
    _algorithm_leds(c, 'Drum')
    # The next prime paints with Drum.
    c.tap(16, 8)
    drum = _paint_preview(c, True, 'Drum', '0', 'drum-prime')
    c.tap(14, 8)
    _paint_preview(c, False, 'Drum', '0', 'drum-cancel')
    # Pattern tasks > Algorithm opens the picker on the algorithm in use.
    ui.open_task('Trig', 'algorithm')
    _picker(c, 'Drum', True)
    c.enc(2, 2)
    _picker(c, 'Euclidean', False)
    c.key(3)
    _picker(c, 'Euclidean', True)
    _algorithm_leds(c, 'Euclidean')
    c.tap(16, 8)
    euclidean = _paint_preview(c, True, 'Euclidean', '0', 'euclidean-prime')
    assert euclidean and euclidean != drum, ('The prime after K3 did not use Euclidean', sorted(drum), sorted(euclidean))
    c.results.append(dict(kind='prime-uses-selected-algorithm', drum=sorted(drum), euclidean=sorted(euclidean),
                          passed=True))
    c.tap(14, 8)
    _paint_preview(c, False, 'Euclidean', '0', 'euclidean-cancel')
    # K3 on Rhythm Doctor selects it and opens the Doctor (R01), as its grid key does.
    ui.open_task('Trig', 'algorithm')
    _picker(c, 'Euclidean', True)
    c.enc(2, 2)
    _picker(c, 'Rhythm Doctor', False)
    c.key(3)
    ui.expect_rhythm_doctor_header('R01')
    c.results.append(dict(kind='k3-rhythm-doctor-opens-r01', passed=True))
    c.results.append(dict(kind='live-ui-algorithm-summary', passed=True))


def live_ui_paint(c):
    """README Adding Trigs (prime and paint, move controls): prime shows Paint Preview with the
    preview showing, its algorithm, shift 0 and exactly as many trigs as the grid previews;
    shift right / left / reset update Shift (+1, 0, -1, 0) and move the previewed cells by one
    step; cancel shows the preview off with no trigs."""
    ui = c.ui
    ui.tap_control('pattern_editor')
    ui.expect_header('trigger_editor')
    # Numeric: a sparse preview on the empty pattern (Euclidean's default fills every step,
    # so a shift would not move anything visible).
    c.tap(15, 2)
    _picker(c, 'Numeric', True)
    ui.tap_control('paint')
    base = _paint_preview(c, True, 'Numeric', '0', 'prime')
    assert base and len(base) < 64, ('Numeric preview', sorted(base))

    def moved(steps, by):
        return frozenset((s - 1 + by) % 64 + 1 for s in steps)
    for control, shift, by in (('shift_right', '+1', 1), ('shift_left', '0', 0), ('shift_left', '-1', -1),
                               ('shift_reset', '0', 0)):
        ui.tap_control(control)
        shown = _paint_preview(c, True, 'Numeric', shift, control + shift)
        assert shown == moved(base, by), (control, shift, sorted(shown), sorted(moved(base, by)))
        c.results.append(dict(kind='paint-shift-cells', control=control, shift=shift, passed=True))
    ui.tap_control('cancel')
    _paint_preview(c, False, 'Numeric', '0', 'cancel')
    c.results.append(dict(kind='live-ui-paint-summary', passed=True))


def live_ui_dashboards(c):
    """README Norns Menu Navigation / Note Dashboard / Navigating the Norns Display:
    information-only screens (Scale overview, Output, Song playback) list every value at once
    with no cursor, and E2/E3 change nothing on them; Scale tasks are exactly Scale, Scale clock
    and Overview; Trig options has only the tresillo amount."""
    ui = c.ui
    c.configure()
    # Output (C06): six rows, before any event.
    ui.tap_control('channel_editor')
    ui.channel_page('note_dashboard', confirm=False)
    output = [(label, 'NO EVENT') for label in ('Note', 'Vel / Len', 'Step', 'Degree', 'Pitch', 'Sent')]
    ui.expect_dashboard('note_dashboard', output, channel=1)
    # Scale overview (S03): five rows, no View channel, no cursor; E2/E3 change nothing.
    ui.tap_control('scale_editor')
    ui.expect_header('scale', slot=1)
    ui.open_task('Scale', 'overview')
    overview = [('Playing scale', '01'), ('Edit scale', '01'), ('Step / range', '01 / 01..64'),
                ('Transpose', '0'), ('Step lock', 'NONE')]
    ui.expect_dashboard('scale_overview', overview, slot=1)
    for encoder, delta in ((2, 2), (3, 3), (2, -4), (3, -1)):
        c.enc(encoder, delta)
        ui.expect_dashboard('scale_overview', overview, slot=1)
    # Scale tasks: exactly Scale, Scale clock, Overview (E1 opens it on Overview, the row of
    # the screen it came from; the list clamps on Overview and on Scale).
    c.enc(1, 1)
    ui.expect_header('scale_tasks', slot=1)
    ui.expect_task_row('Overview')
    c.enc(2, 1)
    ui.expect_task_row('Overview')
    for label in ('Scale clock', 'Scale', 'Scale'):
        c.enc(2, -1)
        ui.expect_task_row(label)
    c.results.append(dict(kind='scale-tasks-rows', rows=['Scale', 'Scale clock', 'Overview'], passed=True))
    # Song playback (A03): five rows at once.
    ui.tap_control('song_editor')
    song = [('Playing', 'SONG 01'), ('Next', 'SONG 01'), ('Pass', '1 / 1'), ('Global length', '64'),
            ('Song mode', 'AUTO')]
    ui.expect_dashboard('song', song)
    # Trig options (P02): only the tresillo amount; a single field shows the control hints,
    # not neighbours, and E2 stays on it.
    ui.tap_control('pattern_editor')
    ui.trig_options()
    ui.expect_selected_field('focused', 'Tresillo amount', 'x24')
    _expect_footer(c, 'E3 SET  K3 APPLY')
    c.enc(2, 3)
    ui.expect_selected_field('focused', 'Tresillo amount', 'x24')
    _expect_footer(c, 'E3 SET  K3 APPLY')
    c.results.append(dict(kind='live-ui-dashboards-summary', passed=True))


def _expect_footer(c, text):
    from frame_oracle import footer_matches
    row = dict(kind='footer', text=text, passed=False)
    c.results.append(row)
    c.wait(lambda state: footer_matches(state, text))
    row['passed'] = True


def live_ui_view_channel(c):
    """README Adding Trigs: on Channel view (P05) and Pattern Trig (P01) E3 turns the viewed
    channel straight after the screen opens, and still after E2 (which moves no focus on a
    64-cell screen); the selected channel does not change."""
    ui = c.ui
    ui.tap_control('pattern_editor')
    ui.expect_header('trigger_editor')
    ui.open_task('Trig', 'channel_view')
    ui.expect_header('channel_view', channel=1)
    c.enc(3, 1)  # first input on the new screen
    ui.expect_header('channel_view', channel=2)
    c.enc(2, 1); c.enc(3, 1)
    ui.expect_header('channel_view', channel=3)
    c.enc(2, -3); c.enc(3, -1)
    ui.expect_header('channel_view', channel=2)
    # P01 (Pattern tasks > Pattern) shares the Trig viewer: it opens on channel 2; E3 first,
    # then E2 + E3.
    ui.open_task('Trig', 'pattern')
    ui.expect_header('trigger_editor', channel=2)
    c.enc(3, 2)
    ui.expect_header('trigger_editor', channel=4)
    c.enc(2, 1); c.enc(3, -1)
    ui.expect_header('trigger_editor', channel=3)
    # The selected channel is still 1 (channel row LEDs; Masks scope).
    c.led_values([(x, 1) for x in range(1, 17)], [15] + [2] * 15)
    ui.tap_control('channel_editor')
    ui.expect_header('masks', channel=1)
    c.results.append(dict(kind='live-ui-view-channel-summary', passed=True))


def live_ui_grid_focus(c):
    """README Norns Menu Navigation (a grid action brings up the screen that shows what it
    changed, with that value chosen): a trig merge press on Masks shows Merge detail on Trig
    mode, K2 returns to Masks; a Pattern Trig step tap lights that cell on the screen; the song
    length fader shows Song playback with the exact global length."""
    ui = c.ui
    c.configure()
    ui.tap_control('channel_editor')
    ui.channel_page('masks')
    ui.tap_control('trig_merge_mode')
    ui.expect_header('merge_detail', channel=1)
    ui.expect_selected_field('detail', 'Trig mode', 'ONLY')
    _expect_footer(c, 'Only trig merge mode')
    c.key(2)
    ui.expect_header('masks', channel=1)
    ui.tap_control('trig_merge_mode')
    ui.expect_header('merge_detail', channel=1)
    ui.expect_selected_field('detail', 'Trig mode', 'ALL')
    c.key(2)
    ui.expect_header('masks', channel=1)
    # Pattern Trig: pattern 2 is empty over channel 1's steps 1-4 (context, capped at 3);
    # tapping step 9 lights cell 9 at 15.
    ui.tap_control('pattern_editor')
    ui.tap_control('pattern_select', 2)
    ui.expect_header('trigger_editor', pattern=2)
    context = [3] * 4 + [0] * 60
    _pattern_cells(c, context, 'pattern2-empty')
    ui.tap_step(9)
    _pattern_cells(c, [15 if k == 8 else level for k, level in enumerate(context)], 'step9-lit')
    ui.expect_header('trigger_editor', pattern=2)
    # Song length fader: decrement shows Song playback with Global length 63.
    ui.tap_control('song_editor')
    ui.expect_header('song')
    ui.tap_control('global_pattern_length', 1)
    song = [('Playing', 'SONG 01'), ('Next', 'SONG 01'), ('Pass', '1 / 1'), ('Global length', '63'),
            ('Song mode', 'AUTO')]
    ui.expect_dashboard('song', song)
    ui.tap_control('global_pattern_length', 8)
    song[3] = ('Global length', '64')
    ui.expect_dashboard('song', song)
    c.results.append(dict(kind='live-ui-grid-focus-summary', passed=True))


def _pattern_cells(c, levels, stage):
    import base64

    def matches(state):
        pixels = base64.b64decode(state['frame']['pixels_base64'])
        for k, level in enumerate(levels):
            x, y = 2 + (k % 16) * 8, 24 + (k // 16) * 8
            if any(pixels[((y + dy) * 128 + x + dx) * 4] != level * 17 for dy in range(4) for dx in range(4)):
                return False
        return True
    row = dict(kind='pattern-cells', stage=stage, passed=False)
    c.results.append(row)
    c.wait(matches)
    row['passed'] = True
