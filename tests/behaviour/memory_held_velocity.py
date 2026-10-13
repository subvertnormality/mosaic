"""Undoing a held-step velocity lock (README Memory 697-702: memory "retains all masks
and trig lock actions"; E3 scrolls left to past actions). Gap-scan item 16: the
held-step velocity increment writes the step's velocity mask while the step is still
held, before the release commits the action to memory, whereas note and decrement
edits wait for the release.

Channel 1 plays velocities 127/117/107/97. Holding step 2 on the Note Masks page and
turning E3 locks velocity 50 on step 2; stepping memory back must restore 117, also
after a later working-pattern rebuild (a tap on step 4). A note lock on step 2 made first
(undone, then rebuilt) is the control. Redo is checked separately (M-MEMORY-009).
"""

PATTERN = [127, 117, 107, 97]


def memory_held_velocity(c):
    ui = c.ui
    ui.configure()

    def heard(stage, expected_velocities=None, expected_notes=None):
        marker = c.snapshot()['midi_count']
        ui.play()
        c.elapse(1.4)
        ui.stop()
        state = c.wait(lambda s: not s['midi_capture']['outstanding'])
        ons = [m['bytes'] for m in state['midi'] if m['index'] > marker and m['bytes'][0] == 144 and m['bytes'][2] > 0][:4]
        actual = dict(notes=[b[1] for b in ons], velocities=[b[2] for b in ons])
        c.results.append(dict(kind='memory-held-velocity', stage=stage, **actual))
        if expected_velocities is not None: assert actual['velocities'] == expected_velocities, (stage, actual)
        if expected_notes is not None: assert actual['notes'] == expected_notes, (stage, actual)
        return actual

    def held_edit(field_offset, turns):
        ui.channel_page('masks', 'memory', channel=1, confirm=False)
        ui.expect_header('masks', channel=1)
        ui.select_field('trig', offset=-5)
        field_name = {1: 'note', 2: 'velocity'}[field_offset]
        ui.select_field(field_name, offset=field_offset)
        with ui.hold_step(2):
            c.elapse(.05)
            ui.set_value(turns)
        c.elapse(.1)
        ui.channel_page('memory', 'masks', channel=1, confirm=False)
        ui.expect_header('memory', channel=1)

    def rebuild():
        ui.channel_page('masks', 'memory', channel=1, confirm=False)
        ui.expect_header('masks', channel=1)
        ui.tap_step(4)
        c.elapse(.2)
        ui.channel_page('memory', 'masks', channel=1, confirm=False)
        ui.expect_header('memory', channel=1)

    ui.channel_page('memory', 'midi_config', channel=1, confirm=False)
    ui.expect_header('memory', channel=1)
    original = heard('original', PATTERN)

    held_edit(1, 5)                                            # control: note lock on step 2
    locked = heard('note-locked', PATTERN)
    assert locked['notes'] != original['notes'], ('Note lock not heard', locked)
    ui.set_value(-1)
    heard('note-undone', PATTERN, original['notes'])
    rebuild(); heard('note-undone-after-rebuild', PATTERN, original['notes'])

    held_edit(2, 51)                                           # velocity lock 50 on step 2 (new action)
    heard('velocity-locked', [127, 50, 107, 97], original['notes'])
    ui.set_value(-1)
    heard('velocity-undone', PATTERN, original['notes'])
    rebuild(); heard('velocity-undone-after-rebuild', PATTERN, original['notes'])
    c.results.append(dict(kind='memory-held-velocity-summary', passed=True))
