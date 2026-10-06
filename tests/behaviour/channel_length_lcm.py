"""Two channels with ranges of 16 and 5 steps start together and meet again after 80 steps.

README "Channel Length" (a channel loops its own start to end range; ranges are per channel) and
"Typical Workflow". The expected onsets are plain arithmetic, not read back from Mosaic: a loop of
N steps plays its trigs again every N steps, so channel 1 (trigs 1, 5, 9, 13 of a 16-step range) hits
on steps s with s % 16 in {0, 4, 8, 12} and channel 2 (trigs 1, 3, 4 of a 5-step range) on steps s with
s % 5 in {0, 2, 3}, counting from the first step as 0. Both channels are on their first step together
at step 0 and again at lcm(16, 5) = 80, and at no step in between. One step is a sixth of a second at
the default 90 BPM and Rate /1.
"""

DRUM = (1, 5, 9, 13)
FIGURE = (1, 3, 4)
DRUM_RANGE = 16
FIGURE_RANGE = 5
CYCLE = 80            # lcm(16, 5)
STEP_SECONDS = 1 / 6


def drum_steps(count=CYCLE + 1):
    return [s for s in range(count) if (s % DRUM_RANGE) + 1 in DRUM]


def figure_steps(count=CYCLE + 1):
    return [s for s in range(count) if (s % FIGURE_RANGE) + 1 in FIGURE]


def channel_length_sixteen_and_five(c):
    ui = c.ui
    ui.configure()
    # Channel 2: its own MIDI route (port 2, MIDI channel 2), as the other multi-channel cases set it.
    ui.select_channel_on_page(2, 'midi_config')
    ui.set_value(1)
    ui.select_field('midi_channel', offset=1)
    ui.set_value(1)
    ui.select_field('default_velocity', offset=1)
    ui.set_value(1)
    ui.press_key(3)
    # Audible notes (README Masks: a channel's defaults): a low drum note on channel 1, a higher figure
    # note on channel 2. Set on each channel's Masks page.
    ui.channel_page('masks', 'midi_config', channel=2)
    ui.select_field('note', saturate=-10, then=1)    # the Masks cursor keeps its row: go to the top, then Note
    ui.set_value(73)                                  # MIDI 72
    ui.select_field('velocity', offset=1)
    ui.set_value(91)                                  # velocity 90
    ui.select_field('length', offset=1)
    ui.set_value(8)                                   # half a step
    ui.select_channel(1)
    ui.channel_page('masks', 'midi_config', channel=1)
    ui.select_field('note', saturate=-10, then=1)    # the Masks cursor keeps its row: go to the top, then Note
    ui.set_value(37)                                  # MIDI 36
    ui.select_field('velocity', offset=1)
    ui.set_value(101)                                 # velocity 100
    ui.select_field('length', offset=1)
    ui.set_value(8)
    ui.expect_header('masks', channel=1)
    # Pattern 1 becomes the drum figure (trigs 1, 5, 9, 13) and pattern 2 the short figure (1, 3, 4).
    ui.tap_control('pattern_editor')
    ui.tap_control('pattern_select', 1)
    for step in (2, 3, 4, 5, 9, 13):                  # configure() left trigs on 1-4: drop 2-4, add 5, 9, 13
        ui.tap_step(step)
    ui.expect_steps({1: 'selected', 5: 'selected', 9: 'selected', 13: 'selected', 2: 'off', 3: 'off', 4: 'off'})
    c.results.append(dict(kind='channel-pattern-set', pattern=1, trigs=list(DRUM), passed=True))
    ui.tap_control('pattern_select', 2)
    for step in FIGURE:
        ui.tap_step(step)
    ui.expect_steps({1: 'selected', 3: 'selected', 4: 'selected', 2: 'off'})
    c.results.append(dict(kind='channel-pattern-set', pattern=2, trigs=list(FIGURE), passed=True))
    # Channel 1: pattern 1 and steps 1-16; channel 2: pattern 2 and steps 1-5.
    ui.tap_control('channel_editor')
    ui.select_channel(1)                              # configure() already gave channel 1 pattern 1
    ui.set_range(1, DRUM_RANGE)
    ui.expect_steps({s: 'selected' for s in DRUM})
    c.results.append(dict(kind='channel-range-set', channel=1, ranges=[1, DRUM_RANGE], passed=True))
    ui.select_channel(2)
    ui.tap_control('pattern_slot', 2)
    ui.set_range(1, FIGURE_RANGE)
    ui.expect_steps({s: 'selected' for s in FIGURE})
    c.results.append(dict(kind='channel-range-set', channel=2, ranges=[1, FIGURE_RANGE], passed=True))
    # Play for 80 steps and the first note of the next cycle.
    ui.select_channel(1)
    marker = c.snapshot()['midi_count']
    ui.tap_control('play_stop')

    def sounded(state, port):
        return [m for m in state['midi'] if m['index'] > marker and m['port'] == port
                and 144 <= m['bytes'][0] <= 159 and m['bytes'][2] > 0]
    drum, figure = drum_steps(), figure_steps()
    state = c.wait(lambda s: len(sounded(s, 1)) >= len(drum) and len(sounded(s, 2)) >= len(figure),
                   timeout=CYCLE * STEP_SECONDS * 2 + 5)
    field = 'logical_ns' if c.clock_mode == 'controlled-experimental' else 'monotonic_ns'
    tolerance = 2e-9 if c.clock_mode == 'controlled-experimental' else .01
    ports = {1: sounded(state, 1)[:len(drum)], 2: sounded(state, 2)[:len(figure)]}
    origin = ports[1][0][field]
    for port, steps, note, velocity, status in ((1, drum, 36, 100, 144), (2, figure, 72, 90, 145)):
        for onset, step in zip(ports[port], steps):
            assert onset['bytes'] == [status, note, velocity], (port, step, onset['bytes'])
            assert abs((onset[field] - origin) / 1e9 - step * STEP_SECONDS) <= tolerance, (port, step)
    # Both loops are on their first step together at step 0 and 80, and the two channels never
    # play their first notes together in between.
    first_together = [s for s in range(CYCLE + 1) if s % DRUM_RANGE == 0 and s % FIGURE_RANGE == 0]
    assert first_together == [0, CYCLE]
    onsets = {port: {s: o for s, o in zip(steps, ports[port])}
              for port, steps in ((1, drum), (2, figure))}
    for step in first_together:
        assert abs(onsets[1][step][field] - onsets[2][step][field]) / 1e9 <= tolerance, step
    c.results.append(dict(kind='channel-range-realignment', ranges=[[1, DRUM_RANGE], [1, FIGURE_RANGE]],
                          cycle_steps=CYCLE, drum_steps=drum, figure_steps=figure,
                          coincident_first_steps=first_together, tolerance_seconds=tolerance, passed=True))
    ui.tap_control('play_stop')
    c.wait(lambda s: not s['midi_capture']['outstanding'])
