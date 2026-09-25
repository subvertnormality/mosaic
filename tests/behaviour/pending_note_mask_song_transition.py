"""Cross-song held note-mask ownership.

README.md:597 says a held step accepts a mask value. README.md:696-707 says that
mask action is retained in Memory. The manual does not state the target when a
song transition occurs before the held gesture is released; this is a
characterisation: it remains the song that owned the gesture at first press.

Slot 2 is copied from slot 1 then given an octave fingerprint. A one-detent
note-mask edit from X to note 0 is completed on slot 1 step 4 immediately before
the automatic transition. Release happens after slot 2 starts. Slot 1 must own
the mask and its undo/redo entry; slot 2 remains untouched.
"""

import time


def pending_note_mask_song_transition(c):
    ui = c.ui
    ui.configure()

    def select_slot(slot):
        ui.song_editor()
        ui.tap_control("song_pattern_slot", slot)
        ui.expect_leds(
            {
                ("song_pattern_slot", 1): "selected" if slot == 1 else "alternate",
                ("song_pattern_slot", 2): "selected" if slot == 2 else "alternate",
            }
        )
        ui.menu("channel_editor")
        # Preserve the source's explicit screen_header result rather than
        # replacing it with channel_page's ui-confirm result.
        ui.channel_page("masks", "midi_config", channel=1, confirm=False)
        # The live scope names a song slot other than 1 (CH01 S02).
        ui.expect_header("masks", channel=1, song_slot=slot)

    def onsets(state, after):
        return [
            event
            for event in state["midi"]
            if event["index"] > after
            and event["bytes"][0] == 144
            and event["bytes"][2] > 0
        ]

    def replay(slot, expected, stage):
        select_slot(slot)
        marker = c.snapshot()["midi_count"]
        ui.play()
        state = c.wait(lambda s: len(onsets(s, marker)) >= 4, timeout=8)
        notes = [event["bytes"] for event in onsets(state, marker)[:4]]
        ui.stop()
        c.wait(lambda s: not s["midi_capture"]["outstanding"])
        expected_notes = [
            [144, pitch, velocity]
            for pitch, velocity in zip(expected, (127, 117, 107, 97))
        ]
        assert notes == expected_notes, (stage, notes, expected_notes)
        c.results.append(
            dict(
                kind="pending-note-mask-song-transition-replay",
                stage=stage,
                slot=slot,
                pitches=expected,
                passed=True,
            )
        )

    # Two four-step song slots make the automatic boundary close enough to
    # verify that both press and encoder callbacks completed before it.
    ui.song_editor()
    ui.tap_control("global_pattern_length", 2)
    for _ in range(3):
        ui.tap_control("global_pattern_length", 8)
    ui.hold_control_tap(
        "song_pattern_slot",
        "song_pattern_slot",
        held_index=1,
        target_index=2,
    )
    ui.tap_control("song_pattern_slot", 2)
    ui.expect_leds(
        {
            ("song_pattern_slot", 1): "alternate",
            ("song_pattern_slot", 2): "selected",
        }
    )
    ui.menu("channel_editor")
    ui.tap_control("channel_octave", 1)  # Slot 2 octave fingerprint.

    select_slot(1)
    controlled = c.clock_mode == "controlled-experimental"
    field = "logical_ns" if controlled else "monotonic_ns"
    marker = c.snapshot()["midi_count"]
    ui.play()
    first = c.wait(lambda s: len(onsets(s, marker)) >= 1, timeout=3)
    first_onset = onsets(first, marker)[0]
    assert first_onset["bytes"] == [144, 60, 127]
    boundary = first_onset[field] + round(4 / 6 * 1e9)
    press_at, turn_at = boundary - 31_000_000, boundary - 30_000_000

    # Keep the direct user recipe and the input-validity evidence separate from
    # the musical oracle. A one-detent E3 turn writes note 0 from X; do not
    # saturate the encoder or rely on its processing spanning the boundary.
    # Delay to the original press time before pressing the step. The hold then
    # remains active through the boundary wait and is released only after slot 2
    # has produced its fingerprinted onset.
    if controlled:
        c.elapse((press_at - c.logical_ns) / 1e9)
    else:
        # This runtime accepts synchronous device inputs. Leave enough time
        # for both round trips and reject a late gesture as an invalid setup.
        press_at = boundary - 200_000_000
        delay = (press_at - time.monotonic_ns()) / 1e9
        assert delay > 0, dict(press_at=press_at, now=time.monotonic_ns())
        time.sleep(delay)

    with ui.hold_step(4):
        pressed = c.logical_ns if controlled else time.monotonic_ns()
        if controlled:
            c.elapse((turn_at - c.logical_ns) / 1e9)
            ui.encoder_event(3, 2)
            turned = c.logical_ns
            validity = dict(
                kind="pending-note-mask-song-transition-input-validity",
                lane="controlled-experimental",
                boundary_ns=boundary,
                planned_ns=[press_at, turn_at],
                callback_completed_ns=[pressed, turned],
                press_and_encoder_completed_before_boundary=pressed < boundary and turned < boundary,
            )
        else:
            ui.encoder_event(3, 2)
            turned = time.monotonic_ns()
            validity = dict(
                kind="pending-note-mask-song-transition-input-validity",
                lane="real-time",
                boundary_ns=boundary,
                planned_press_ns=press_at,
                callback_completed_ns=[pressed, turned],
                press_and_encoder_completed_before_boundary=pressed < boundary and turned < boundary,
            )

        c.results.append(validity)
        assert validity["press_and_encoder_completed_before_boundary"], validity
        crossed = c.wait(
            lambda s: any(
                event["bytes"] == [144, 72, 127]
                for event in onsets(s, marker)
            ),
            timeout=3,
        )
        assert any(
            event["bytes"] == [144, 72, 127] for event in onsets(crossed, marker)
        )
    ui.stop()
    c.wait(lambda s: not s["midi_capture"]["outstanding"])

    # Grid slot indicators and the page header make the post-transition selected
    # slot observable before the separate user-level replays below.
    ui.song_editor()
    ui.expect_leds(
        {
            ("song_pattern_slot", 1): "alternate",
            ("song_pattern_slot", 2): "selected",
        }
    )
    ui.menu("channel_editor")
    ui.channel_page("masks", "midi_config", channel=1, confirm=False)
    # The live scope also shows the post-transition song slot and slot 2's
    # channel octave fingerprint (CH01 S02 OCT+1).
    ui.expect_header("masks", channel=1, song_slot=2, octave=1)

    # Required fingerprints: the held step belongs to song A, while song B
    # retains its copied octave fingerprint. The unfixed target leak writes 0
    # into song B instead of song A.
    replay(1, [60, 62, 64, 0], "gesture-owner-song-a")
    replay(2, [72, 74, 76, 77], "song-b-unchanged")

    # README 696-707: Memory retains the held mask action. Undo/redo on song A
    # is the observable model/history oracle and must not be redirected to song B.
    select_slot(1)
    ui.channel_page("memory", "masks", channel=1, confirm=False)
    ui.expect_header("memory", channel=1)
    ui.set_value(-1)
    replay(1, [60, 62, 64, 65], "song-a-history-undo")
    select_slot(1)
    ui.channel_page("memory", "masks", channel=1, confirm=False)
    ui.expect_header("memory", channel=1)
    ui.set_value(1)
    replay(1, [60, 62, 64, 0], "song-a-history-redo")
    replay(2, [72, 74, 76, 77], "song-b-after-song-a-undo-redo")
    c.results.append(
        dict(
            kind="pending-note-mask-song-transition",
            held_step=4,
            mask_note=0,
            owner_song=1,
            selected_after_transition=2,
            passed=True,
        )
    )
