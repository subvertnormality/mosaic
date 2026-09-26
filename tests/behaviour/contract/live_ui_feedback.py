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


# ---------------------------------------------------------------------------------------------
# Merge modes (C09) are selectable on the norns (owner request 25 September 2026).

_PHRASE_MERGE = {
    # configure() pattern 1 (C4 D4 E4 F4 at 127/117/107/97 on steps 1-4) merged with pattern 2
    # (trigs on steps 1 and 2, note 0 = C4, velocity 100); the same arithmetic as acceptance A10.
    'skip': [(64, 107), (65, 97)],                       # trigs where exactly one pattern has one
    'all': [(60, 114), (62, 109), (64, 107), (65, 97)],  # every trig; note/velocity average
    'all_note_pat2': [(60, 114), (60, 109), (60, 107), (60, 97)],  # notes from pattern 2
}
_TRIG_LED = {'SKIP': 2, 'ONLY': 5, 'ALL': 8}  # trig merge button (14,8): off / in range / medium


def live_ui_merge_modes(c):
    """README Merge Modes: Merge modes opens from Channel tasks; E2 chooses Trig, Note,
    Velocity or Length mode (Patterns stays grid-assigned); E3 steps a mode through what its
    grid button can set, clamped, exactly as the button does: the trig merge button LED
    follows SKIP -> ONLY -> ALL and the channel's MIDI follows the chosen modes."""
    ui = c.ui
    c.configure()
    ui.tap_control('pattern_editor')
    ui.tap_control('pattern_select', 2)
    ui.tap_step(1); ui.tap_step(2)
    ui.tap_control('channel_editor')
    ui.tap_control('pattern_slot', 2)
    ui.expect_header('merge_detail', channel=1)
    ui.expect_selected_field('detail', 'Patterns', '01 02')
    c.key(2)
    ui.expect_header('masks', channel=1)
    melody = lambda pairs: [(1, [144, n, v]) for n, v in pairs]

    def trig_mode(value):
        ui.expect_header('merge_detail', channel=1)
        ui.expect_selected_field('detail', 'Trig mode', value)
        c.led_values([(14, 8)], [_TRIG_LED[value]])
        c.results.append(dict(kind='merge-mode', row='Trig mode', value=value, passed=True))

    ui.open_channel_task('merge')
    _expect_footer(c, 'E2 MODE  E3 SET  K2 BACK')
    c.enc(2, -6)
    ui.expect_selected_field('detail', 'Patterns', '01 02')
    c.enc(3, 1)  # Patterns is read-only: nothing changes
    ui.expect_selected_field('detail', 'Patterns', '01 02')
    c.enc(2, 1)
    trig_mode('SKIP')
    c.playback(melody(_PHRASE_MERGE['skip']), cycles=2)
    c.enc(3, -1)
    trig_mode('SKIP')  # clamped at the first mode
    for value in ('ONLY', 'ALL', 'ALL'):  # the last detent clamps at All
        c.enc(3, 1)
        trig_mode(value)
    c.playback(melody(_PHRASE_MERGE['all']), cycles=2)
    # Note mode: Average -> Up -> Down -> PAT 1 -> PAT 2 (pattern 2 supplies every note), then back.
    c.enc(2, 1)
    ui.expect_selected_field('detail', 'Note mode', 'AVERAGE')
    for value in ('UP', 'DOWN', 'PAT 1', 'PAT 2'):
        c.enc(3, 1)
        ui.expect_selected_field('detail', 'Note mode', value)
    c.playback(melody(_PHRASE_MERGE['all_note_pat2']), cycles=2)
    c.enc(3, -1)
    ui.expect_selected_field('detail', 'Note mode', 'PAT 1')
    for value in ('DOWN', 'UP', 'AVERAGE', 'AVERAGE'):  # the last detent clamps at Average
        c.enc(3, -1)
        ui.expect_selected_field('detail', 'Note mode', value)
    c.playback(melody(_PHRASE_MERGE['all']), cycles=2)
    # The trig mode set here is the grid's: the next button press continues from All to Skip.
    c.key(2)
    ui.expect_header('masks', channel=1)
    ui.tap_control('trig_merge_mode')
    trig_mode('SKIP')
    c.results.append(dict(kind='live-ui-merge-modes-summary', passed=True))


# ---------------------------------------------------------------------------------------------
# Owner feedback from the device, 26 September 2026.

CHANNEL_ROW = [(x, 1) for x in range(1, 17)]


def _selected_channel_leds(c, channel):
    """The channel row lights exactly the selected channel (15), every other at 2."""
    c.led_values(CHANNEL_ROW, [15 if x == channel else 2 for x in range(1, 17)])


def live_ui_channel_select(c):
    """README Norns Menu Navigation (a grid channel select keeps the norns screen, which
    follows the new channel): Device and Clock stay with the new channel's scope and its own
    values, never jumping to Masks or Trig params; Harmony and Merge Shape reopen their
    editor root (Voice leading, Merge Shape) for the new channel, even from a child screen."""
    ui = c.ui
    c.configure()  # ends on Device (C05) for channel 1, which drives the configured CC Device
    ui.expect_header('midi_config', channel=1)
    ui.expect_selected_field('detail', 'Device', 'CC Device')
    # Device: channel 2 has no device; the screen stays Device and shows channel 2's.
    ui.select_channel(2)
    ui.expect_header('midi_config', channel=2)
    ui.expect_selected_field('detail', 'Device', 'None')
    _selected_channel_leds(c, 2)
    ui.select_channel(1)
    ui.expect_header('midi_config', channel=1)
    ui.expect_selected_field('detail', 'Device', 'CC Device')
    c.results.append(dict(kind='channel-select-keeps-device', passed=True))
    # Clock: set channel 2's rate from the Clock screen it stayed on, then each select shows
    # the selected channel's own rate on the same screen.
    ui.channel_page('clock_mods', channel=1)
    ui.expect_selected_field('focused', 'Rate', '/1', art=True)
    ui.select_channel(2)
    ui.expect_header('clock_mods', channel=2)
    ui.expect_selected_field('focused', 'Rate', '/1', art=True)
    ui.set_value(-2); ui.press_key(3)
    ui.expect_selected_field('focused', 'Rate', '/2', art=True)
    ui.select_channel(1)
    ui.expect_header('clock_mods', channel=1)
    ui.expect_selected_field('focused', 'Rate', '/1', art=True)
    _selected_channel_leds(c, 1)
    ui.select_channel(2)
    ui.expect_header('clock_mods', channel=2)
    ui.expect_selected_field('focused', 'Rate', '/2', art=True)
    c.results.append(dict(kind='channel-select-keeps-clock', passed=True))
    # Harmony: from its Register child on channel 2, a select shows Voice leading (H01) for
    # channel 1; from the root the same.
    ui.channel_page('harmony', channel=2)
    ui.select_row('register', 3); ui.press_key(3)
    ui.expect_header('harmony_register', channel=2)
    ui.select_channel(1)
    ui.expect_header('harmony', channel=1)
    ui.select_channel(2)
    ui.expect_header('harmony', channel=2)
    c.results.append(dict(kind='channel-select-reopens-voice-leading', passed=True))
    # Merge Shape: from its Rhythm child on channel 2, a select shows Merge Shape (M02) for
    # channel 1.
    ui.channel_page('merge_shape', channel=2)
    ui.select_row('rhythm', 1); ui.press_key(3)
    ui.expect_header('merge_rhythm', channel=2)
    ui.select_channel(1)
    ui.expect_header('merge_shape', channel=1)
    _selected_channel_leds(c, 1)
    c.results.append(dict(kind='channel-select-reopens-merge-shape', passed=True))
    c.results.append(dict(kind='live-ui-channel-select-summary', passed=True))


def _note_page_buttons(c, page):
    """Pattern Note/Velocity page buttons (9..12, 8): the page shown at 15, the others at 3."""
    c.led_values([(8 + k, 8) for k in range(1, 5)], [15 if k == page else 3 for k in range(1, 5)])


def live_ui_note_page_step(c):
    """README Adding Notes / Adding Velocity: on the Pattern Note and Velocity pages a held
    fader key is the step it edits on the 16-step page shown: column 6 on page 49-64 is step 54
    (header ST54, cell 54 outlined), not the channel-page position 22; the edit lands on step
    54 and the grid stays on page 49-64."""
    ui = c.ui
    ui.pattern_editor('trigger')
    ui.expect_header('trigger_editor')
    ui.pattern_editor('note', from_view='trigger')
    ui.expect_header('note_editor')
    ui.select_pattern_note_page(4)
    _note_page_buttons(c, 4)
    with ui.hold_control('pattern_note_fader', (6, 5)):
        ui.expect_header('note_editor', held=(54,))
        ui.expect_outlined_step(54)
    ui.expect_header('note_editor')
    # The press set step 54 (row 5 at offset 7: value 12, note 14 - 12); the screen shows the
    # held step's scope while held and the edit's tooltip after the release.
    _expect_footer(c, 'Step 54 note set to 2')
    # A tap sets step 54's note (row 3: value 10, note 4); the fader and page stay on 49-64.
    ui.tap_control('pattern_note_fader', (6, 3))
    _expect_footer(c, 'Step 54 note set to 4')
    c.led_values([(6, y) for y in (3, 5)], [12, 1])
    _note_page_buttons(c, 4)
    c.results.append(dict(kind='note-page-held-step', step=54, passed=True))
    # Velocity keeps its own page (1-16) until page 4 is chosen; then column 6 is step 54 too.
    ui.pattern_editor('velocity', from_view='note')
    ui.expect_header('velocity_editor')
    ui.select_pattern_note_page(4)
    _note_page_buttons(c, 4)
    with ui.hold_control('pattern_note_fader', (6, 5)):
        ui.expect_header('velocity_editor', held=(54,))
        ui.expect_outlined_step(54)
    ui.expect_header('velocity_editor')
    _note_page_buttons(c, 4)
    c.results.append(dict(kind='velocity-page-held-step', step=54, passed=True))
    c.results.append(dict(kind='live-ui-note-page-step-summary', passed=True))


# Foundation (contract.foundation_workflow.setup_foundation): pattern 1 plays C4 D4 E4 F4 on
# steps 1-4 (127/117/107/97), pattern 2 has trigs on steps 5 and 7 (note 0 = C4, velocity 100),
# loop 1-8. Merge Shape's additions at 5 and 7 carry its Add accent 70; the legacy All merge
# plays pattern 2's own velocity 100 there.
_SHAPE_PHRASE = [(1, [144, n, v]) for n, v in ((60, 127), (62, 117), (64, 107), (65, 97), (60, 70), (60, 70))]
_ALL_PHRASE = [(1, [144, n, v]) for n, v in ((60, 127), (62, 117), (64, 107), (65, 97), (60, 100), (60, 100))]


def live_ui_merge_shape_trig_mode(c):
    """README Merge Shape: while Foundation is on it decides the channel's trigs; Merge modes
    shows the trig mode as SHAPE (<mode>) and the trig merge button's tooltip says Merge Shape
    is in use; the saved trig mode applies again when Merge Shape is off."""
    from contract.foundation_workflow import setup_foundation
    ui = c.ui
    setup_foundation(c)  # Foundation applied through the Merge Shape editor (M02 -> M03 -> K3)
    ui.tap_control('channel_editor')
    ui.open_channel_task('merge')
    ui.expect_header('merge_detail', channel=1)
    c.enc(2, -6); c.enc(2, 1)
    ui.expect_selected_field('detail', 'Trig mode', 'SHAPE (SKIP)')
    c.key(2)
    for mode, value, led in (('only', 'ONLY', 5), ('all', 'ALL', 8)):
        ui.expect_header('masks', channel=1)
        ui.tap_control('trig_merge_mode')
        ui.expect_header('merge_detail', channel=1)
        ui.expect_selected_field('detail', 'Trig mode', 'SHAPE (%s)' % value)
        _expect_footer(c, 'Trig merge %s: Merge Shape in use' % mode)
        c.led_values([(14, 8)], [led])
        c.results.append(dict(kind='shape-trig-mode', value=value, passed=True))
        c.key(2)
    # Merge Shape still decides the trigs with the saved mode at All.
    c.playback(_SHAPE_PHRASE, cycles=2)
    # Mode Off on Merge Shape (applied): the saved All applies and reads plainly.
    ui.channel_page('merge_shape', channel=1)
    ui.select_row('mode', 0)
    ui.set_value(-1)
    ui.expect_selected_field('focused', 'Mode', 'OFF', art=True)
    ui.press_key(3)
    ui.open_channel_task('merge')
    ui.expect_header('merge_detail', channel=1)
    c.enc(2, -6); c.enc(2, 1)
    ui.expect_selected_field('detail', 'Trig mode', 'ALL')
    c.playback(_ALL_PHRASE, cycles=2)
    c.key(2)
    ui.expect_header('masks', channel=1)
    ui.tap_control('trig_merge_mode')
    ui.expect_selected_field('detail', 'Trig mode', 'SKIP')
    _expect_footer(c, 'Skip trig merge mode')
    c.led_values([(14, 8)], [2])
    c.results.append(dict(kind='live-ui-merge-shape-trig-mode-summary', passed=True))
