"""Named-save/cold-load acceptance for slot-specific Strum.

The native case uses only public Mosaic inputs and screen/MIDI observations.
Assertions cite stable manual features: save-and-load, trig-parameters and
chord-spread.
"""
import hashlib
import json


def _file_identity(path):
    raw = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), size=len(raw))


def trig_param_strum_persistence(c):
    from cases import (
        STRUM_SLOT_PITCHES,
        STRUM_SLOT_VELOCITY,
        strum_slot_chord_channel,
        strum_slot_play_and_check,
    )
    from driver import Driver, write

    strum_label = c.ui.trig_parameter_label("chord_note_strum")
    spread_label = c.ui.trig_parameter_label("chord_spread")

    def trig_page(d):
        d.ui.channel_page("trig_locks", channel=1, confirm=False)
        d.ui.select_field("param_slot", saturate=-12, then=0)

    def song_slot(d, slot):
        d.ui.song_editor()
        d.ui.tap_control("song_pattern_slot", slot)
        d.ui.channel_editor()

    # manual:trig-parameters and manual:chord-spread. Make a two-step,
    # three-voice chord in slot 1, with both stock controls assigned and Off.
    strum_slot_chord_channel(c, 18, strum=0, mask_turns=(2, 4))
    c.ui.turn(2, 1)
    c.ui.assign_trig_parameter_key("chord_spread")
    c.ui.expect_selected_field("overview_params", spread_label, "X")
    c.ui.song_editor()
    c.ui.copy_slot(1, 2, control="song_pattern_slot")
    c.ui.tap_control("song_pattern_slot", 2)
    c.ui.channel_editor()
    trig_page(c)
    c.ui.set_value(8)  # Strum 1/2
    c.ui.expect_selected_field("overview_params", strum_label, "1/2")
    c.ui.turn(2, 1)
    c.ui.set_value(5)  # Spread 1/4
    c.ui.expect_selected_field("overview_params", spread_label, "1/4")
    song_slot(c, 1)
    trig_page(c)
    c.ui.expect_selected_field("overview_params", strum_label, "X")
    c.ui.turn(2, 1)
    c.ui.expect_selected_field("overview_params", spread_label, "X")

    # manual:save-and-load. Save with slot 1 selected so its Off values exercise
    # the companion pset while slot 2's distinct stock params stay in the ptn.
    c.ui.select_project_action("save")
    c.ui.press_key(3)
    c.ui.press_key(1)
    named_ptn = c.data_directory / "new.ptn"
    named_pset = c.data_directory / "new.pset"
    c.wait(lambda _: named_ptn.is_file() and named_pset.is_file(), timeout=5)
    assert named_ptn.is_file() and named_pset.is_file(), (
        "manual:save-and-load: named project pair was not saved"
    )
    saved_files = [_file_identity(named_ptn), _file_identity(named_pset)]

    # Cold-start a fresh native process from the saved directory, then load the
    # named project through the public project menu.
    c.finish()
    out = c.out / "restarted"
    out.mkdir()
    d = Driver(out, project_seed=c.data_directory, **c.launch_options)
    try:
        d.ui.menu("channel_editor")
        d.ui.select_project_file("new.ptn")
        d.ui.press_key(3)
        d.ui.press_key(1)
        d.ui.menu("channel_editor")

        trig_page(d)
        d.ui.expect_selected_field("overview_params", strum_label, "X")
        d.ui.turn(2, 1)
        d.ui.expect_selected_field("overview_params", spread_label, "X")
        block = [
            (0, pitch, STRUM_SLOT_VELOCITY)
            for pitch in STRUM_SLOT_PITCHES[:3]
        ]
        block_rows = strum_slot_play_and_check(
            d, 3.5, block, [432] * len(block), "slot-strum-persist-1-block"
        )
        assert not any(row["truncated"] for row in block_rows), (
            "manual:chord-spread: slot 1 two-step gates were cut by Stop"
        )

        # One native channel step is 216 ticks; Length 2 means 432-tick gates.
        # Strum 1/2 + Spread 1/4 yields 162-tick gaps for the three voices.
        # The default song period is 64 steps (visible in the Song dashboard);
        # the 6 s capture exceeds the last 5.25 s release but ends before the
        # next cycle can retrigger this one-trig pattern.
        d.ui.song_editor()
        d.ui.expect_dashboard_row("Global length", "64")
        d.ui.channel_editor()
        song_slot(d, 2)
        trig_page(d)
        d.ui.expect_selected_field("overview_params", strum_label, "1/2")
        d.ui.turn(2, 1)
        d.ui.expect_selected_field("overview_params", spread_label, "1/4")
        onsets = [0, 162, 324]
        strum = [
            (tick, STRUM_SLOT_PITCHES[i], STRUM_SLOT_VELOCITY)
            for i, tick in enumerate(onsets)
        ]
        strum_seconds = 6
        final_release_tick = onsets[-1] + 432
        period_ticks = 64 * 216
        assert final_release_tick / 144 < strum_seconds < period_ticks / 144, (
            "characterisation: play window must include every full gate and end before the 64-step retrigger"
        )
        strum_rows = strum_slot_play_and_check(
            d, strum_seconds, strum, [432] * len(strum), "slot-strum-persist-2-strum"
        )
        assert not any(row["truncated"] for row in strum_rows), (
            "manual:chord-spread: slot 2 two-step gates were cut by Stop"
        )

        song_slot(d, 1)
        trig_page(d)
        d.ui.expect_selected_field("overview_params", strum_label, "X")
        d.ui.turn(2, 1)
        d.ui.expect_selected_field("overview_params", spread_label, "X")
        block_rows = strum_slot_play_and_check(
            d, 3.5, block, [432] * len(block), "slot-strum-persist-1-again"
        )
        assert not any(row["truncated"] for row in block_rows), (
            "manual:chord-spread: slot 1 two-step gates were cut by Stop"
        )
    finally:
        d.finish()

    # The parent report carries the full child assertions and hash-linked
    # observations/identity; the nested files remain available for inspection.
    child_results_path = out / "results.json"
    child_observations_path = out / "observations.json"
    child_identity_path = out / "native" / "identity.json"
    child_results = json.loads(child_results_path.read_text())
    child_observations = json.loads(child_observations_path.read_text())
    child_identity = json.loads(child_identity_path.read_text())
    root_identity_path = c.out / "native" / "identity.json"
    parent_record = dict(
        kind="slot-strum-named-cold-load",
        named_files=saved_files,
        slot1_onsets=[0] * len(block),
        slot1_releases=[432] * len(block),
        slot2_onsets=onsets,
        slot2_releases=[tick + 432 for tick in onsets],
        slot2_capture_seconds=strum_seconds,
        slot2_period_ticks=period_ticks,
        nested_session=dict(
            path="restarted",
            result_file=_file_identity(child_results_path),
            observation_file=_file_identity(child_observations_path),
            observation_count=len(child_observations),
            identity_file=_file_identity(child_identity_path),
            application_identity=child_identity.get("application_identity"),
            results=child_results,
        ),
        root_identity_file=_file_identity(root_identity_path),
        passed=True,
    )
    c.results.append(parent_record)
    # Driver.finish() already closed the root session. Rewrite only its evidence
    # summary so the runner's final manifest includes this cold-load assertion.
    write(c.out / "results.json", c.results)
    write(c.out / "nested-session-evidence.json", dict(
        root_identity=parent_record["root_identity_file"],
        child=parent_record["nested_session"],
    ))
