"""A new project starts with no memory (README Memory, lines 698-707; "+ New" in the
project parameters).

README: memory retains the mask and trig lock actions made in the project, and E3
moves through them. Two note-mask actions are recorded, then "+ New" replaces the
project. The new project must show an empty history, and E3 back and forward must not
replay the previous project's actions onto it.
"""
BASELINE = [(60, 127), (62, 117), (64, 107), (65, 97)]


def memory_new_project(c):
    ui = c.ui

    def counter(current, total):
        ui.expect_memory_position(current, total)

    def record(step, note, velocity):
        ui.channel_page("masks", "memory", confirm=False)
        ui.expect_header("masks", channel=1)
        ui.record_key(step, note, velocity, hold_seconds=.05)
        c.elapse(.1)
        ui.channel_page("memory", "masks", confirm=False)
        ui.expect_header("memory", channel=1)

    ui.configure()
    ui.channel_page("memory", "midi_config", confirm=False)
    ui.expect_header("memory", channel=1)
    record(1, 72, 90); record(2, 76, 80); counter(2, 2)
    c.playback([(1, [144, 72, 90]), (1, [144, 76, 80]),
                *[(1, [144, n, v]) for n, v in BASELINE[2:]]], cycles=2)
    ui.select_project_action("new")                               # "+ New"
    ui.press_key(1)                                                # close native menu
    ui.turn(1, -5)                                               # preserve configure()'s reset recipe
    ui.configure()
    ui.channel_page("memory", "midi_config", confirm=False)
    ui.expect_header("memory", channel=1)
    counter(0, 0)
    ui.turn(3, -1); ui.turn(3, 1); counter(0, 0)
    c.playback([(1, [144, n, v]) for n, v in BASELINE], cycles=2)
    c.results.append(dict(kind="memory-new-project", recorded_before_new=2,
                          history_after_new=0, passed=True))
