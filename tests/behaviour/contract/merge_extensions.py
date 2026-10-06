"""README "Merge Shape" extensions through physical grid/norns input.

Fragments, Interlock and Structure (docs/musical-merge-extensions-plan.md §2,
§3, §4 and the MM-11 screens of §5). Every oracle is literal: emitted MIDI
(pitch, velocity, MIDI channel and loop-relative onset step), channel-page grid
LEDs and the native framebuffer. No Mosaic Lua state is read to manufacture an
expectation. Timing is exact in the controlled lane and within 20 ms in real
time; every onset is also placed on its exact loop step.
"""
import base64

from contract.harmony_merge_visual import documentation_frame

# configure(): Pattern 1 holds C4 D4 E4 F4 at steps 1-4 with velocities
# 127/117/107/97. A new trig is C4 (degree 0) at velocity 100.
P1 = {1: (60, 127), 2: (62, 117), 3: (64, 107), 4: (65, 97)}
STEP_SECONDS = 1 / 6  # a /1 step at the 90 BPM fixture
LOOP = 8


def _note_ons(state, before):
    result = []
    for packet in state['midi']:
        if packet['index'] <= before:
            continue
        for message in packet['decoded']:
            if message['type'] == 'note_on' and message['data'][1] > 0:
                event = dict(packet)
                event['bytes'] = [143 + message['channel']] + message['data']
                result.append(event)
    return result


def _placed(c, ons, loop=LOOP):
    """Each onset as (loop, step, midi channel, pitch, velocity): its nominal
    position counted from the first onset, which is step 1 of loop 0 after a
    Start. An onset off the step lattice fails."""
    controlled = c.clock_mode == 'controlled-experimental'
    field = 'logical_ns' if controlled else 'monotonic_ns'
    tolerance = 2e-9 if controlled else .02
    placed, errors = [], []
    for m in ons:
        seconds = (m[field] - ons[0][field]) / 1e9
        index = round(seconds / STEP_SECONDS)
        errors.append(seconds - index * STEP_SECONDS)
        placed.append((index // loop, index % loop + 1, m['bytes'][0] - 143, m['bytes'][1], m['bytes'][2]))
    assert all(abs(e) <= tolerance for e in errors), dict(errors=errors, tolerance=tolerance)
    return placed, tolerance


def _loop_events(events, loop):
    return [(loop, step, channel, pitch, velocity) for step, channel, pitch, velocity in sorted(events)]


def play_loops(c, events, loops=2, kind='merge-extension-loops', loop=LOOP, **record):
    """From stopped: exactly ``loops`` loops of ``events`` ((step, midi channel,
    pitch, velocity) per loop) and the next loop's first onset, in order, on
    their exact steps; then Stop with every note released."""
    expected = [e for n in range(loops) for e in _loop_events(events, n)] + _loop_events(events, loops)[:1]
    before = c.snapshot()['midi_count']
    c.ui.play()
    state = c.wait(lambda value: len(_note_ons(value, before)) >= len(expected),
                   timeout=2 + (loops + 1) * loop * STEP_SECONDS * 2)
    ons = _note_ons(state, before)[:len(expected)]
    placed, tolerance = _placed(c, ons, loop=loop)
    # The first onset defines step 1: shift when the loop starts later.
    first = expected[0][1]
    placed = [(lp + (st + first - 2) // loop, (st + first - 2) % loop + 1, ch, p, v) for lp, st, ch, p, v in placed]
    assert placed == expected, dict(expected=expected, actual=placed)
    c.ui.stop()
    c.wait(lambda value: value['midi_capture']['outstanding'] == [])
    c.results.append(dict(kind=kind, loops=loops, loop_steps=loop, expected=[list(e) for e in expected],
                          tolerance_seconds=tolerance, passed=True, **record))


def loop_leds(c, lit):
    """Channel-page grid: exactly the ``lit`` steps of the 8-step loop show a trig."""
    c.ui.expect_steps({step: "selected" if step in lit else "off" if step <= LOOP else "dark"
                       for step in range(1, 17)})


def expect_detail_row(c, row, label, value):
    """Unselected detail-layout row ``row`` (0-based) shows ``label`` and
    ``value`` exactly as lib/ui_render.lua draws it (label x7 level 6, value
    right at x126 level 8)."""
    from frame_oracle import fit, render, text_width, variants
    y = 27 + row * 9
    room = min(72, 119 - text_width(value) - 4)
    frames = variants(lambda: render([(7, y, 6, fit(label, room)), ((None, 126), y, 8, value)]))
    indices = [(yy * 128 + x) * 4 + k for yy in range(y - 7, y + 2) for x in range(128) for k in range(3)]
    c.wait(lambda s: any(all(base64.b64decode(s['frame']['pixels_base64'])[i] == f[i] for i in indices)
                         for f in frames))
    c.results.append(dict(kind='detail-row', row=row, label=label, value=value, passed=True))


def two_patterns(c, second):
    """configure(), an 8-step channel 1 loop and Pattern 2 (trigs at
    ``second``) assigned beside Pattern 1."""
    c.configure()
    c.ui.hold_control_tap("step", "step", held_index=1, target_index=LOOP)
    c.ui.tap_control("pattern_editor"); c.ui.select_channel(2)
    for step in second:
        c.ui.tap_step(step)
    c.ui.tap_control("channel_editor"); c.ui.tap_control("pattern_slot", 2)


def foundation_on(c, channel):
    """Merge Shape Foundation on the selected channel with its first assigned
    pattern as Anchor, applied; Rhythm (M03) stays open."""
    from merge_strategy_routes import foundation_rhythm
    foundation_rhythm(c,channel)


# Fragments ------------------------------------------------------------------------

def fragments_workflow(c, capture=False):
    """README Merge Shape "Fragments". ``capture`` stops at the README frame
    (tools/docs_capture.py), skipping the playback before it."""
    two_patterns(c, (3, 6))
    from merge_strategy_routes import select_strategy
    select_strategy(c,"FRAGMENTS")
    c.ui.channel_page("merge_shape", channel=1)
    c.ui.select_row("rhythm",1);c.ui.press_key(3)  # Rhythm opens Fragments
    c.ui.expect_header("merge_fragments", channel=1)
    c.ui.turn(3, -1)                             # Size 8 -> 4
    c.ui.expect_selected_field("detail", "Size", "4")
    c.ui.press_key(3)                            # K3 applies the whole draft
    c.ui.expect_footer_text("APPLIED")
    # Seed 0 plays P02 in steps 1-4 and P01 in steps 5-8. P01 has nothing in
    # 5-8, so only P02's own step 3 sounds: C4 at its authored 100 (P01's E4
    # at that step is not averaged in: legacy note/velocity merging does not
    # apply inside a fragment). The grid shows the same one trig.
    loop_leds(c, {3})
    if not capture:
        play_loops(c, [(3, 1, 60, 100)], kind='fragments-seed-0', seed=0)
        loop_leds(c, {3})
    # Seed 1 plays P01 then P02: P01's whole first half and P02's step 6.
    c.ui.select_row("seed", 2); c.ui.turn(3, 1)
    c.ui.expect_selected_field("detail", "Seed", "1")
    c.ui.press_key(3)
    c.ui.expect_footer_text("APPLIED")
    loop_leds(c, {1, 2, 3, 4, 6})
    if capture:
        return
    documentation_frame(c, FRAGMENTS_FRAME, 'images/merge-shape-fragments.png', stable_rows=55)
    play_loops(c, [(s, 1, n, v) for s, (n, v) in P1.items()] + [(6, 1, 60, 100)],
               kind='fragments-seed-1', seed=1)
    loop_leds(c, {1, 2, 3, 4, 6})


def fragments_short_loop_workflow(c):
    """README Fragments: a loop shorter than Size is one fragment; Keep anchor
    fills only empty trig positions and the fragment source wins on overlap."""
    two_patterns(c, (3, 6))
    c.ui.hold_control_tap("step", "step", held_index=1, target_index=6)
    from merge_strategy_routes import select_strategy
    select_strategy(c,"FRAGMENTS")
    c.ui.channel_page("merge_shape", channel=1)
    c.ui.select_row("rhythm", 1); c.ui.press_key(3)
    c.ui.expect_header("merge_fragments", channel=1)
    c.ui.expect_selected_field("detail", "Size", "8")
    c.ui.press_key(3)
    c.ui.expect_footer_text("APPLIED")
    c.ui.expect_steps({step: "selected" if step in (3, 6) else "off" if step <= 6 else "dark"
                       for step in range(1, 17)})
    play_loops(c, [(3, 1, 60, 100), (6, 1, 60, 100)], loop=6,
               kind="fragments-short-loop", size=8, keep_anchor=False)
    c.ui.select_row("keep_anchor", 1); c.ui.turn(3, 1)
    c.ui.expect_selected_field("detail", "Keep anchor", "ON")
    c.ui.select_row("anchor", 2)
    c.ui.expect_selected_field("detail", "Anchor", "NONE")
    c.ui.turn(3, 1)
    c.ui.expect_selected_field("detail", "Anchor", "1")
    c.ui.press_key(3)
    c.ui.expect_footer_text("APPLIED")
    expected = [(1, 1, 60, 127), (2, 1, 62, 117), (3, 1, 60, 100),
                (4, 1, 65, 97), (6, 1, 60, 100)]
    c.ui.expect_steps({step: "selected" if step in (1, 2, 3, 4, 6) else "off" if step <= 6 else "dark"
                       for step in range(1, 17)})
    play_loops(c, expected, loop=6, kind="fragments-short-loop-keep-anchor",
               size=8, keep_anchor=True)


# Interlock -------------------------------------------------------------------------

FOLLOWER = [(s, 1, n, v) for s, (n, v) in P1.items()]
LEADER = (5, 2, 60, 100)   # channel 2 on MIDI channel 2: its anchor at step 5
ADDITION_7 = (7, 1, 60, 70)


def interlock_workflow(c, capture=False):
    """README Merge Shape "Interlock". ``capture`` stops at the README frame."""
    two_patterns(c, (5, 7))
    # Leader: channel 2 on MIDI channel 2, an 8-step loop, Pattern 3 (a trig
    # at step 5) as its Foundation anchor.
    c.ui.tap_control("pattern_editor"); c.ui.select_channel(3); c.ui.tap_step(5)
    c.ui.tap_control("channel_editor")
    c.ui.select_channel(2)
    c.ui.channel_page("midi_config", channel=2)
    c.ui.set_value(1); c.ui.turn(2, 1); c.ui.set_value(1); c.ui.press_key(3)
    c.ui.tap_control("pattern_slot", 3)
    c.ui.hold_control_tap("step", "step", held_index=1, target_index=LOOP)
    foundation_on(c, 2)
    # Follower: channel 1, Foundation anchored on P01, additions P02 at 5 and 7.
    c.ui.select_channel(1)
    foundation_on(c, 1)
    loop_leds(c, {1, 2, 3, 4, 5, 7})
    # Rhythm > Interlock: Leader CH02, Window 0 (exactly coincident onsets).
    c.ui.select_row("interlock", 6); c.ui.press_key(3)
    c.ui.expect_header("merge_interlock", channel=1)
    c.ui.select_row("interlock_leader", 0); c.ui.turn(3, 1)
    c.ui.expect_selected_field("detail", "Leader", "CH02")
    c.ui.press_key(3)
    c.ui.expect_footer_text("APPLIED")
    # The addition at step 5 meets the leader's anchor and is removed; step 7
    # stays. Anchors are never removed. The grid shows what MIDI plays.
    loop_leds(c, {1, 2, 3, 4, 7})
    expect_detail_row(c, 2, "Status", "ON")
    if capture:
        return
    documentation_frame(c, INTERLOCK_FRAME, 'images/merge-shape-interlock.png', stable_rows=55)
    play_loops(c, FOLLOWER + [LEADER, ADDITION_7], kind='interlock-window-0', window=0)

    # While playing, Window 2 (|7 - 5| = 2 also avoids step 7) queues for the
    # channel's next loop; a later draft (Window 0) cancelled with K2 does not
    # retract the accepted queue.
    before = c.snapshot()['midi_count']
    c.ui.play()
    c.wait(lambda value: len(_note_ons(value, before)) >= 7, timeout=6)
    c.ui.select_row("interlock_window", 1); c.ui.turn(3, 2)
    c.ui.expect_selected_field("detail", "Window", "2")
    c.ui.press_key(3)
    c.ui.expect_footer_text("NEXT CYCLE")
    c.ui.turn(3, -2)
    c.ui.expect_selected_field("detail", "Window", "0")
    c.ui.press_key(2)                               # K2 discards the draft and returns
    c.ui.expect_header("merge_rhythm", channel=1)
    c.ui.press_key(3)                               # the accepted queue is still Window 2
    c.ui.expect_header("merge_interlock", channel=1)
    c.ui.expect_selected_field("detail", "Window", "2")
    c.elapse(5 * LOOP * STEP_SECONDS)
    c.ui.stop()
    c.wait(lambda value: value['midi_capture']['outstanding'] == [])
    loop_leds(c, {1, 2, 3, 4})
    placed, tolerance = _placed(c, _note_ons(c.snapshot(), before))
    loops = {}
    for loop, step, channel, pitch, velocity in placed:
        loops.setdefault(loop, []).append((step, channel, pitch, velocity))
    complete = [loops[n] for n in sorted(loops)][:-1]   # Stop may cut the last loop
    with_seven = sorted(FOLLOWER + [LEADER, ADDITION_7])
    without = sorted(FOLLOWER + [LEADER])
    kinds = ['7' if sorted(l) == with_seven else '-' if sorted(l) == without else '?' for l in complete]
    # Every loop is whole: the change lands on a loop boundary, once, and stays.
    assert '?' not in kinds and kinds[0] == '7' and kinds[-2:] == ['-', '-'], dict(kinds=kinds, loops=loops)
    assert kinds == sorted(kinds, key=lambda k: k == '-'), dict(kinds=kinds)
    c.results.append(dict(kind='interlock-queued-window', loops=kinds, tolerance_seconds=tolerance, passed=True))

    # Channel 2 is a leader: making it follow channel 1 would chain, so Apply
    # refuses and says why; nothing changes.
    c.ui.select_channel(2)
    c.ui.expect_header("merge_shape", channel=2)
    c.ui.select_row("rhythm", 1); c.ui.press_key(3)
    c.ui.select_row("interlock", 6); c.ui.press_key(3)
    c.ui.expect_header("merge_interlock", channel=2)
    c.ui.select_row("interlock_leader", 0); c.ui.turn(3, 1)
    c.ui.expect_selected_field("detail", "Leader", "CH01")
    c.ui.press_key(3)
    c.ui.expect_footer_text("INVALID CHANNEL IS A LEADER")
    c.ui.press_key(2)                               # K2 discards the refused draft
    c.ui.select_channel(1)
    loop_leds(c, {1, 2, 3, 4})
    play_loops(c, FOLLOWER + [LEADER], kind='interlock-after-refusal', window=2)


# Structure -------------------------------------------------------------------------

def structure_workflow(c, capture=False):
    """README Merge Shape "Structure". ``capture`` stops at the README frame."""
    two_patterns(c, (5, 7))
    # Voice leading > Groups: a group whose chord is scale degrees 0, 2 and 4
    # (C E G in C major), enabled.
    c.ui.channel_page("harmony", channel=1)
    c.ui.select_row("groups", 5); c.ui.press_key(3)
    c.ui.expect_header("harmony_ensemble", channel=1)
    c.ui.select_row("create_group", 1); c.ui.press_key(3)
    c.ui.select_row("source", 4); c.ui.press_key(3)
    # README.md#structure: the group chord is scale degrees 0, 2 and 4 (C E G in C major).
    c.ui.select_row("template_count", 1); c.ui.turn(3, 2)
    c.ui.expect_selected_field("detail", "Template count", "3")
    c.ui.select_row("tone_2", 3); c.ui.turn(3, 2)
    c.ui.expect_selected_field("detail", "Tone 2", "2")
    c.ui.select_row("tone_3", 4); c.ui.turn(3, 4)
    c.ui.expect_selected_field("detail", "Tone 3", "4")
    c.ui.press_key(3)
    c.ui.expect_footer_text("APPLIED")
    c.ui.press_key(2)
    c.ui.select_row("members", 3); c.ui.press_key(3)
    c.ui.expect_header("harmony_members", channel=1)
    c.ui.select_row("group_enabled", 2); c.ui.turn(3, 1)
    c.ui.press_key(3)
    c.ui.expect_footer_text("APPLIED")
    # Merge Shape: Foundation on P01, then Pitch > Structure: Markers
    # Anchors with Chord group 1.
    foundation_on(c, 1)
    c.ui.feature_root()
    c.ui.select_row("pitch", 3); c.ui.press_key(3)
    c.ui.expect_header("merge_pitch", channel=1)
    c.ui.select_row("structure", 3); c.ui.press_key(3)
    c.ui.expect_header("merge_structure", channel=1)
    c.ui.select_row("structure_markers", 0); c.ui.turn(3, 1)
    c.ui.expect_selected_field("detail", "Markers", "ANCHORS")
    expect_detail_row(c, 1, "Chord group", "1")
    c.ui.press_key(3)
    c.ui.expect_footer_text("APPLIED")
    if capture:
        return
    documentation_frame(c, STRUCTURE_FRAME, 'images/merge-shape-structure.png', stable_rows=55)
    # Every anchor is a marker: C D E F snap to the nearest C, E or G (a tie
    # takes the lower pitch): C, C, E, E. Additions between markers keep C.
    snapped = {1: (60, 127), 2: (60, 117), 3: (64, 107), 4: (64, 97)}
    assert all(pitch % 12 in (0, 4, 7) for pitch, _ in snapped.values())
    additions = [(5, 1, 60, 70), (7, 1, 60, 70)]
    play_loops(c, [(s, 1, n, v) for s, (n, v) in snapped.items()] + additions,
               kind='structure-anchor-markers', markers='anchors')
    # Deleting the group asks first and names every channel it changes; the
    # deletion turns the markers Off in the same transaction, and the anchors
    # play their own pitches again.
    c.ui.channel_page("harmony", channel=1)
    c.ui.select_row("groups", 5); c.ui.press_key(3)
    c.ui.select_row("delete_group", 8); c.ui.press_key(3)
    c.ui.expect_header("harmony_delete_group", channel=1)
    expect_detail_row(c, 1, "Affected", "1")
    c.ui.press_key(3)
    c.ui.channel_page("merge_shape", channel=1)
    c.ui.select_row("pitch", 3); c.ui.press_key(3)
    c.ui.select_row("structure", 3); c.ui.press_key(3)
    c.ui.expect_selected_field("detail", "Markers", "OFF")
    play_loops(c, [(s, 1, n, v) for s, (n, v) in P1.items()] + additions,
               kind='structure-group-deleted', markers='off')


# README image frames: sha256 of the first 55 framebuffer rows
# (tools/docs_capture.py prints them; the footer carries lane-dependent tooltips).
FRAGMENTS_FRAME = '760b9f276791a959a98a73441d88f534d9f77730fad051d93dd890841581689b'
INTERLOCK_FRAME = 'de6e77eb93ebd84d696def4c0862dd49140f3447b745fd92d445ab3c014615a7'
STRUCTURE_FRAME = 'f2250df79def76419e0054c5295e2183b3f889513bc2bce77bed46af702f8095'


def fragments_offset_mask_workflow(c):
    """README Fragments: count Size from an offset loop start, then let an
    explicit trig mask suppress a chosen source onset and X restore it."""
    two_patterns(c, (3, 6, 9))
    c.ui.set_range(3, 10)
    from merge_strategy_routes import select_strategy
    select_strategy(c,'FRAGMENTS')
    c.ui.channel_page('merge_shape', channel=1)
    c.ui.select_row('rhythm', 1); c.ui.press_key(3)
    c.ui.expect_header('merge_fragments', channel=1)
    c.ui.select_row('size', 0); c.ui.turn(3, -1)
    c.ui.select_row('seed', 2); c.ui.turn(3, 1); c.ui.press_key(3)
    c.ui.expect_selected_field('detail', 'Seed', '1')
    def check(events, kind, **record):
        # Channel range 3..10: compare absolute step and MIDI, then the next
        # loop's step 3. The ordinary play_loops helper assumes start step 1.
        wanted = [(cycle, step, pitch, velocity)
                  for cycle in range(2) for step, _, pitch, velocity in events]
        wanted += [(2, events[0][0], events[0][2], events[0][3])]
        before = c.snapshot()['midi_count']
        c.ui.play()
        state = c.wait(lambda value: len(_note_ons(value, before)) >= len(wanted), timeout=7)
        ons = _note_ons(state, before)[:len(wanted)]
        key = 'logical_ns' if c.clock_mode == 'controlled-experimental' else 'monotonic_ns'
        allowed = 2e-9 if c.clock_mode == 'controlled-experimental' else .02
        origin = ons[0][key]
        for event, (cycle, step, pitch, velocity) in zip(ons, wanted):
            assert event['bytes'] == [144, pitch, velocity], dict(event=event, expected=(pitch, velocity))
            seconds = (event[key] - origin) / 1e9
            assert abs(seconds - (cycle * 8 + step - 3) * STEP_SECONDS) <= allowed, dict(
                cycle=cycle, step=step, seconds=seconds)
        c.ui.stop()
        c.wait(lambda value: value['midi_capture']['outstanding'] == [])
        c.results.append(dict(kind=kind, expected=[list(e) for e in wanted],
                              tolerance_seconds=allowed, passed=True, **record))

    # Seed 1 chooses P01 for 3..6 and P02 for 7..10. The source note and
    # velocity survive; the fragment boundary follows the channel start.
    original = [(3, 1, 64, 107), (4, 1, 65, 97), (9, 1, 60, 100)]
    c.ui.expect_steps({3: 'selected', 4: 'selected', 9: 'selected',
                       6: 'off', 7: 'off', 8: 'off'})
    check(original, 'fragments-offset-loop', start=3, size=4, seed=1)
    c.ui.channel_page('masks', channel=1)
    c.ui.select_field('trig', offset=-1)
    with c.ui.hold_step(4): c.ui.set_value(1)  # X -> N (README Masks)
    c.ui.expect_steps({3: 'selected', 4: 'off', 9: 'selected'})
    check([original[0], original[2]], 'fragments-explicit-trig-mask', masked_step=4)
    with c.ui.hold_step(4): c.ui.set_value(-1)  # N -> X
    c.ui.expect_steps({3: 'selected', 4: 'selected', 9: 'selected'})
    check(original, 'fragments-mask-cleared', masked_step=None)
