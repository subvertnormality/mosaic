"""External controlled native-capture proposals. Public inputs and public observations only."""
import base64
import copy
import hashlib

RESET_CITATION = "manual:reset-at-pattern-repeat"
MASK_CITATION = "manual:snap-note-masks-to-scale"
MOTION_CITATION = "manual:ui-motion"
# C04 is the CLOCK screen; ui_mini_atlas.lua pins its 20x8 animated header.
# ui_mini.region places it at x=108..127 for CLOCK title width, y=0..7.
CLOCK_MINI_ROI = (108, 0, 128, 8)
MOTION_SAMPLE_COUNT = 19  # 1.5 controlled seconds at 12 Hz covers the 2-beat loop.


class CitationAppendingResults:
    """Preserve each native result, then synchronously forward a cited copy."""
    CITED_KINDS = frozenset(("selected-menu-option-row", "selected-mask", "midi"))

    def __init__(self, target, citation, metadata=None):
        self.target = target
        self.citation = citation
        self.metadata = copy.deepcopy(metadata or {})

    def append(self, row):
        self.target.append(row)
        if isinstance(row, dict) and row.get("kind") in self.CITED_KINDS:
            raw_index = len(self.target) - 1
            cited = copy.deepcopy(row)
            cited["citation"] = self.citation
            cited["source_assertion_index"] = raw_index
            cited["source_assertion_raw"] = copy.deepcopy(row)
            cited.update(copy.deepcopy(self.metadata))
            self.target.append(cited)

    def __len__(self):
        return len(self.target)

    def __iter__(self):
        return iter(self.target)

    def __getitem__(self, key):
        return self.target[key]

    def __getattr__(self, name):
        return getattr(self.target, name)


def _with_citation(c, citation, action, metadata=None):
    raw_results = c.results
    c.results = CitationAppendingResults(raw_results, citation, metadata)
    try:
        return action()
    finally:
        c.results = raw_results


def _set_options(c, values, citation):
    # The cited follow-up is appended while each native row is still current;
    # the original row remains byte-for-byte/source-value intact.
    return _with_citation(c, citation, lambda: c.ui.set_mosaic_options(values))


def _playback(c, expected, citation, **kwargs):
    # Preserve the harness's raw MIDI result and synchronously add its cited twin.
    return _with_citation(c, citation,
                          lambda: c.playback(expected, **kwargs))

def _window(c, seconds, interval=.25):
    from midi_window import MidiWindow
    result = MidiWindow(c.snapshot()["midi_count"])
    c.ui.play()
    for _ in range(round(seconds / interval)):
        c.elapse(interval)
        result.extend(c.snapshot())
    remainder = seconds - round(seconds / interval) * interval
    if remainder > 1e-9:
        c.elapse(remainder)
        result.extend(c.snapshot())
    c.ui.stop()
    c.wait(lambda state: result.extend(state)
           and not state["midi_capture"]["outstanding"])
    return result


def _full_channel_midi(window):
    return [{"index": e["index"], "port": e["port"], "bytes": list(e["bytes"]),
             "logical_ns": e["logical_ns"]}
            for e in window.events if e["port"] == 1 and e["bytes"]
            and 0x80 <= e["bytes"][0] < 0xF0]


def _repeat_policy_onsets(reset, last_tick=1548):
    """First-boundary schedule copied from repeated_pattern_reset_policy()."""
    expected = []
    for tick in range(last_tick + 1):
        origin = (tick // 1536) * 1536 if reset else 0
        if (tick - origin) % 216 == 0:
            step = ((tick - origin) // 216) % 3
            expected.append((tick, [144, [60, 62, 64][step], [127, 117, 107][step]]))
    return expected


def repeat_reset_public_boundary(c):
    c.ui.configure()
    c.ui.set_range(1, 3)
    c.ui.channel_page("clock_mods", "midi_config")
    c.ui.turn(3, -11)
    c.ui.press_key(3)  # Clock Mod /9; three-note cycle is 4.5 seconds.
    for reset in (False, True):
        _set_options(c, [
            ("Song mode", True), ("Reset on song seq change", False),
            ("Reset on pattern repeat", reset),
        ], RESET_CITATION)
        window = _window(c, 10.75)
        notes = window.note_ons()
        expected = _repeat_policy_onsets(reset)
        assert len(notes) == len(expected), (reset, len(notes), len(expected))
        assert [(event["port"], event["bytes"]) for event in notes] == [
            (1, message) for tick, message in expected]
        ticks = [tick for tick, message in expected]
        origin = notes[0]["logical_ns"]
        phase_errors_ns = [abs(event["logical_ns"] - origin - round(tick * 1e9 / 144))
                           for event, tick in zip(notes, ticks)]
        assert all(error <= 2 for error in phase_errors_ns), phase_errors_ns
        from note_accounting import note_pairs
        pairs = note_pairs(window.events)
        assert len(pairs) == len(expected), (reset, len(pairs), len(expected))
        complete = _full_channel_midi(window)
        assert len(complete) == 2 * len(expected), (reset, len(complete), len(expected))
        c.results.append(dict(
            kind="manual-repeat-reset-public-midi", citation=RESET_CITATION,
            repeat_reset=reset, option_label="Reset on pattern repeat",
            option_value="On" if reset else "Off", expected_ticks=ticks,
            expected_note_on_count=len(expected), note_on_count=len(notes),
            complete_channel_midi_count=len(complete), complete_note_pair_count=len(pairs),
            complete_midi_stream=True, dropped=0,
            timing_tolerance_ns=2, max_phase_error_ns=max(phase_errors_ns),
            exact_note_ons=[{"port": event["port"], "bytes": list(event["bytes"])}
                            for event in notes],
            complete_channel_midi=complete, passed=True))


def _author_mask_notes(c, pitches, names):
    for step, (pitch, name) in enumerate(zip(pitches, names), 1):
        cell = list(c.ui.step(step))
        with c.ui.hold_step(step):
            c.ui.set_value(pitch + 1)
            c.elapse(.06)
            _with_citation(
                c, MASK_CITATION,
                lambda name=name: c.ui.expect_selected_mask("note", name),
                metadata={"held_step": step, "held_cell": cell})


def snap_note_masks_public_pair(c):
    from cases import assert_durations
    from midi_window import MidiWindow
    raw = [61, 63, 66, 70]
    names_table = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
    names = [names_table[p % 12] + str(p // 12 - 2) for p in raw]
    c.ui.configure()
    _set_options(c, [
        ("Lock merged to pent.", False), ("Quantise note masks", False),
        ("Snap note masks to scale", True)], MASK_CITATION)
    c.ui.channel_page("masks", "midi_config", confirm=False)
    _author_mask_notes(c, raw, names)
    for enabled, pitches in ((True, [60, 62, 65, 69]), (False, raw)):
        if not enabled:
            _set_options(c, [("Snap note masks to scale", False)], MASK_CITATION)
        window = MidiWindow(c.snapshot()["midi_count"])
        notes = _playback(c,
            [(1, [144, p, v]) for p, v in zip(pitches, [127, 117, 107, 97])],
            MASK_CITATION, cycles=2, timeout=4)
        assert_durations(c, notes[:8], [1] * 8)
        window.extend(c.snapshot())
        expected = [(1, [144, p, v]) for _ in range(2)
                    for p, v in zip(pitches, [127, 117, 107, 97])]
        expected.append((1, [144, pitches[0], 127]))
        assert [(e["port"], e["bytes"]) for e in notes] == expected
        c.results.append(dict(
            kind="manual-snap-mask-public-midi", citation=MASK_CITATION,
            snap=enabled, option_label="Snap note masks to scale",
            option_value="On" if enabled else "Off", authored_masks=names,
            output_pitches=pitches,
            exact_note_ons=[{"port": e["port"], "bytes": list(e["bytes"])} for e in notes],
            complete_channel_midi=_full_channel_midi(window), dropped=0, passed=True))



# Exact C04 source atlas. The renderer's level map is a=7,b=11,c=15.
# Tests pin these eight literal frames to the authoritative Lua source.
C04_SOURCE_FRAMES = (
    ("....................","..........c.........",".........c.c........",".........cbc........","........c.b.c.......","........c.c.c.......",".......ccccccc......","...................."),
    ("....................","..........c.........",".........c.c........",".........cbc........","........cb..c.......","........cc..c.......",".......ccccccc......","...................."),
    ("....................","..........c.........",".........c.c........",".........cbc........","........cb..c.......","........c...c.......",".......ccccccc......","...................."),
    ("....................","..........c.........",".........c.c........",".........cbc........","........cb..c.......","........cc..c.......",".......ccccccc......","...................."),
    ("....................","..........c.........",".........c.c........",".........cbc........","........c.b.c.......","........c.c.c.......",".......ccccccc......","...................."),
    ("....................","..........c.........",".........c.c........",".........cbc........","........c..bc.......","........c..cc.......",".......ccccccc......","...................."),
    ("....................","..........c.........",".........c.c........",".........cbc........","........c..bc.......","........c...c.......",".......ccccccc......","...................."),
    ("....................","..........c.........",".........c.c........",".........cbc........","........c..bc.......","........c..cc.......",".......ccccccc......","...................."),
)
MOTION_TEMPO_BPM = 90
MOTION_LOOP_BEATS = 2
MOTION_SAMPLE_PERIOD_NS = 83333333


def _c04_rasters():
    assert len(C04_SOURCE_FRAMES) == 8
    masks = []
    for frame in C04_SOURCE_FRAMES:
        assert len(frame) == 8 and all(len(row) == 20 for row in frame)
        assert all(set(row) <= {".", "a", "b", "c"} for row in frame)
        level_bytes = {".": 0, "a": 119, "b": 187, "c": 255}
        masks.append(tuple(level_bytes[char] for row in frame for char in row))
    return tuple(masks)


def _raster_hash(raster):
    return hashlib.sha256(bytes(raster)).hexdigest()


def _unique_atlas_hashes():
    result = []
    for raster in _c04_rasters():
        digest = _raster_hash(raster)
        if digest not in result:
            result.append(digest)
    return result


def _clock_frame_parts(c):
    state = c.snapshot()
    frame = state["frame"]
    rgba = base64.b64decode(frame["pixels_base64"])
    assert len(rgba) == 128 * 64 * 4, "Expected the actual native 128x64 framebuffer"
    assert hashlib.sha256(rgba).hexdigest() == frame["sha256"], "Native frame hash does not match its public pixels"
    x0, y0, x1, y1 = CLOCK_MINI_ROI
    roi = tuple(rgba[(y * 128 + x) * 4]
                for y in range(y0, y1) for x in range(x0, x1))
    outside = bytearray()
    for y in range(64):
        for x in range(128):
            if not (x0 <= x < x1 and y0 <= y < y1):
                i = (y * 128 + x) * 4
                outside.extend(rgba[i:i + 4])
    observation = c.observations[-1]
    return dict(
        roi=roi, outside_roi_sha256=hashlib.sha256(outside).hexdigest(),
        observation_index=len(c.observations) - 1,
        monotonic_ns=observation["monotonic_ns"],
        logical_ns=state["clock"]["logical_ns"],
        frame_revision=observation["frame_revision"],
        frame_sha256=frame["sha256"])


def _sample_clock_mini(c):
    c.elapse(.75)  # settle navigation before controlled 12 Hz public frame samples
    samples = [_clock_frame_parts(c)]
    for _ in range(MOTION_SAMPLE_COUNT - 1):
        c.elapse(1 / 12)
        samples.append(_clock_frame_parts(c))
    assert len(set(sample["outside_roi_sha256"] for sample in samples)) == 1,         "CLOCK screen outside the mini-header changed during sampling"
    assert all(len(sample["roi"]) == 160 for sample in samples)
    assert all(sample["frame_sha256"] for sample in samples)
    assert all(samples[i + 1]["observation_index"] == samples[i]["observation_index"] + 1
               for i in range(len(samples) - 1))
    assert all(samples[i + 1]["logical_ns"] - samples[i]["logical_ns"] == MOTION_SAMPLE_PERIOD_NS
               for i in range(len(samples) - 1)), "sample times must follow controlled 12 Hz clock advances"
    assert all(samples[i + 1]["monotonic_ns"] > samples[i]["monotonic_ns"]
               for i in range(len(samples) - 1))
    return samples


def _sample_rasters(samples):
    return [tuple(sample["roi"]) for sample in samples]


def _source_render(pose, background):
    mask = _c04_rasters()[pose]
    return tuple(mask[index] if mask[index] else background[index] for index in range(160))


def _paired_background(off_samples, on_samples):
    # The pinned C04 ROI is pure monochrome sprite art on black.
    # Never learn a permissive background from captured output.
    return (0,) * 160


def _verify_motion_frames(off_samples, on_samples):
    assert len(off_samples) == len(on_samples) == MOTION_SAMPLE_COUNT
    for samples in (off_samples, on_samples):
        assert all(len(sample["roi"]) == 160 for sample in samples)
        assert all(samples[i + 1]["observation_index"] == samples[i]["observation_index"] + 1
                   for i in range(len(samples) - 1))
        assert all(samples[i + 1]["logical_ns"] - samples[i]["logical_ns"] == MOTION_SAMPLE_PERIOD_NS
                   for i in range(len(samples) - 1))
        assert all(samples[i + 1]["monotonic_ns"] > samples[i]["monotonic_ns"]
                   for i in range(len(samples) - 1))
        assert all(len(sample["frame_sha256"]) == 64 for sample in samples)
    off_backgrounds = {sample["outside_roi_sha256"] for sample in off_samples}
    on_backgrounds = {sample["outside_roi_sha256"] for sample in on_samples}
    assert len(off_backgrounds) == len(on_backgrounds) == 1
    assert off_backgrounds == on_backgrounds, "same CLOCK screen and controls must stay stable outside the animation ROI"
    background = _paired_background(off_samples, on_samples)
    off_expected = _source_render(0, background)
    assert all(tuple(sample["roi"]) == off_expected for sample in off_samples),         "UI motion Off must render the exact source default pose 0"
    assert len(set(_sample_rasters(off_samples))) == 1

    rasters = _c04_rasters()
    frame_rate = MOTION_TEMPO_BPM / 60 * len(rasters) / MOTION_LOOP_BEATS
    phase_solution = None
    pose_indices = None
    # The initial beat phase is unspecified; find a single source-clock phase
    # that explains every exact public raster at its observed controlled time.
    for milli in range(8000):
        anchor = milli / 1000
        candidate = [
            int(anchor + (sample["logical_ns"] - on_samples[0]["logical_ns"]) / 1e9 * frame_rate + 1e-7) % len(rasters)
            for sample in on_samples
        ]
        if not set(candidate) == set(range(len(rasters))):
            continue
        if all(tuple(sample["roi"]) == _source_render(pose, background)
               for sample, pose in zip(on_samples, candidate)):
            phase_solution = anchor
            pose_indices = candidate
            break
    assert phase_solution is not None, "native public pixels do not follow the source C04 clock-phase sequence"
    on_rasters = _sample_rasters(on_samples)
    assert len(set(on_rasters)) == len(_unique_atlas_hashes()) == 5
    expected_set = {_source_render(pose, background) for pose in range(len(rasters))}
    assert set(on_rasters) == expected_set, "On must expose every distinct exact source raster"
    atlas_hashes = _unique_atlas_hashes()
    common = dict(
        atlas_frame_count=8, atlas_loop_beats=2, atlas_unique_pose_count=5,
        atlas_pose_raster_sha256=atlas_hashes,
        sample_hz=12, sample_count=MOTION_SAMPLE_COUNT,
        sample_duration_seconds=1.5, region=dict(x0=108, y0=0, x1=128, y1=8),
        screen="C04", feature="animated CLOCK mini-header",
        outside_roi_sha256=next(iter(off_backgrounds)), outside_roi_stable=True,
        frame_hashes_verified=True, frame_observations_linked=True,
        source_clock_logical_ns_linked=True,
        clock_sample_period_ns=MOTION_SAMPLE_PERIOD_NS,
        source_clock_tempo_bpm=MOTION_TEMPO_BPM,
        source_phase_consistent=True,
        frames=[list(frame) for frame in on_rasters],
        frame_sha256s=[sample["frame_sha256"] for sample in on_samples],
        observation_indices=[sample["observation_index"] for sample in on_samples],
        clock_logical_ns=[sample["logical_ns"] for sample in on_samples],
        source_pose_indices=pose_indices,
        source_pose_coverage=sorted(set(pose_indices)),
        source_phase_anchor_frames=phase_solution,
        distinct_public_frames=len(set(on_rasters)), passed=True)
    return common


def _off_motion_row(samples):
    rasters = _sample_rasters(samples)
    assert len(rasters) == MOTION_SAMPLE_COUNT and len(set(rasters)) == 1
    masks = _c04_rasters()
    # The frame is source pose 0; exact background-relative verification is
    # repeated with the On pair before its citation-linked result is accepted.
    assert rasters[0] == masks[0], "Off pixels must equal the exact source pose-0 raster on black"
    assert len({sample["outside_roi_sha256"] for sample in samples}) == 1
    return dict(
        kind="manual-ui-motion-public-frames", citation=MOTION_CITATION,
        enabled=False, default_pose_index=0, atlas_frame_count=8,
        atlas_loop_beats=2, atlas_unique_pose_count=5,
        atlas_pose_raster_sha256=_unique_atlas_hashes(),
        source_pose_coverage=[0], source_default_pose_exact=True,
        screen="C04", feature="animated CLOCK mini-header",
        region=dict(x0=108, y0=0, x1=128, y1=8),
        sample_hz=12, sample_count=MOTION_SAMPLE_COUNT,
        sample_duration_seconds=1.5, distinct_public_frames=1,
        outside_roi_sha256=samples[0]["outside_roi_sha256"],
        outside_roi_stable=True, frame_hashes_verified=True,
        frame_observations_linked=True, source_clock_logical_ns_linked=True,
        clock_sample_period_ns=MOTION_SAMPLE_PERIOD_NS,
        source_clock_tempo_bpm=MOTION_TEMPO_BPM,
        frames=[list(frame) for frame in rasters],
        frame_sha256s=[sample["frame_sha256"] for sample in samples],
        observation_indices=[sample["observation_index"] for sample in samples],
        clock_logical_ns=[sample["logical_ns"] for sample in samples], passed=True)


def _verify_motion_midi_evidence(notes, events, expected, stop_press_count):
    """Verify full sixteenth-note gates and the extra-onset public Stop boundary."""
    from note_accounting import note_pairs
    expected = list(expected)
    assert len(expected) == 9
    assert [(event["port"], event["bytes"]) for event in notes] == expected
    note_ons = [event for event in events
                if event["bytes"] and 144 <= event["bytes"][0] <= 159
                and event["bytes"][2] > 0]
    assert [(event["port"], event["bytes"]) for event in note_ons] == expected
    assert stop_press_count == 2, "public Driver playback must start and then stop at the same grid cell"
    pairs = note_pairs(events)
    assert len(pairs) == len(expected), (len(pairs), len(expected))
    channel = [event for event in events if event["port"] == 1 and event["bytes"]
               and 0x80 <= event["bytes"][0] < 0xF0]
    assert len(channel) == 18, len(channel)
    origin = notes[0]["logical_ns"]
    onset_ticks = [24 * i for i in range(9)]
    onset_errors = [abs(event["logical_ns"] - origin - round(tick * 1e9 / 144))
                    for event, tick in zip(notes, onset_ticks)]
    assert all(error <= 2 for error in onset_errors), onset_errors
    natural_gate_errors = []
    for index, (on, off) in enumerate(pairs[:8]):
        expected_on = round(index * 24 * 1e9 / 144)
        expected_off = round((index + 1) * 24 * 1e9 / 144)
        natural_gate_errors.extend((abs(on["logical_ns"] - origin - expected_on),
                                    abs(off["logical_ns"] - origin - expected_off)))
    assert all(error <= 2 for error in natural_gate_errors), natural_gate_errors
    stop_events = [event for event in events if event["port"] == 1
                   and event["bytes"] == [252]]
    assert len(stop_events) == 1, "the public Stop input must produce one captured MIDI Stop"
    stop_logical_ns = stop_events[0]["logical_ns"]
    final_on, final_off = pairs[-1]
    final_gate_ns = final_off["logical_ns"] - final_on["logical_ns"]
    normal_gate_ns = round(24 * 1e9 / 144)
    assert final_off["logical_ns"] == stop_logical_ns, (final_off, stop_events[0])
    assert 0 < final_gate_ns < normal_gate_ns, final_gate_ns
    assert final_on["logical_ns"] == notes[-1]["logical_ns"]
    return dict(
        origin=origin, onset_ticks=onset_ticks, onset_errors=onset_errors,
        natural_gate_errors=natural_gate_errors, pairs=pairs, channel=channel,
        final_gate_ns=final_gate_ns, stop_logical_ns=stop_logical_ns,
        normal_gate_ns=normal_gate_ns)


def _motion_midi(c, phrase, enabled):
    from midi_window import MidiWindow
    before = c.snapshot()
    window = MidiWindow(before["midi_count"])
    window.extend(before)
    recipe_start = len(c.recipe)
    notes = _playback(c, phrase, MOTION_CITATION, cycles=2, timeout=4)
    playback_recipe = c.recipe[recipe_start:]
    stop_presses = [action for action in playback_recipe
                    if action.get("type") == "grid" and action.get("x") == 1
                    and action.get("y") == 8 and action.get("state") == 1]
    window.extend(c.snapshot())
    expected = phrase * 2 + [phrase[0]]
    checked = _verify_motion_midi_evidence(notes, window.events, expected, len(stop_presses))
    full = _full_channel_midi(window)
    relative = [{"port": row["port"], "bytes": row["bytes"],
                 "logical_ns": row["logical_ns"] - checked["origin"]} for row in full]
    assert len(full) == 18
    max_error = max(checked["onset_errors"] + checked["natural_gate_errors"])
    return dict(
        kind="manual-ui-motion-public-midi", citation=MOTION_CITATION,
        enabled=enabled, expected_note_on_ticks=checked["onset_ticks"],
        exact_note_ons=[{"port": event["port"], "bytes": list(event["bytes"])}
                        for event in notes],
        note_on_count=len(notes), complete_channel_midi_count=len(full),
        complete_note_pair_count=len(checked["pairs"]), complete_midi_stream=True,
        natural_gate_count=8, gate_ticks=[24] * 8,
        final_gate_policy="stopped-after-extra-onset",
        final_gate_truncated_by_stop=True, final_gate_stop_event_bytes=[252],
        final_gate_matches_stop_logical_ns=True,
        final_gate_duration_ns=checked["final_gate_ns"],
        final_gate_duration_less_than_one_tick=checked["final_gate_ns"] < round(1e9 / 144),
        stop_grid_press_count=len(stop_presses),
        timing_tolerance_ns=2, max_phase_error_ns=max_error, dropped=0,
        relative_channel_midi=relative, passed=True), relative


def ui_motion_public_frames(c):
    phrase = [(1, [144, n, v]) for n, v in
              [(60, 127), (62, 117), (64, 107), (65, 97)]]
    c.ui.configure()
    c.ui.channel_page("clock_mods", "midi_config")
    c.ui.expect_selected_field("vertical_list", "Rate", "/1")
    midi_rows = []
    for enabled in (False, True):
        _set_options(c, [("UI motion", enabled)], MOTION_CITATION)
        c.ui.channel_page("clock_mods", confirm=False)
        c.ui.turn(3, 2)
        c.ui.press_key(3)
        samples = _sample_clock_mini(c)
        if not enabled:
            off_samples = samples
            c.results.append(_off_motion_row(samples))
        else:
            on_row = _verify_motion_frames(off_samples, samples)
            on_row.update(kind="manual-ui-motion-public-frames",
                          citation=MOTION_CITATION, enabled=True)
            c.results.append(on_row)
        c.ui.turn(3, -2)
        c.ui.press_key(3)
        c.ui.expect_selected_field("vertical_list", "Rate", "/1")
        row, relative = _motion_midi(c, phrase, enabled)
        midi_rows.append(row)
        c.results.append(row)
    assert midi_rows[0]["exact_note_ons"] == midi_rows[1]["exact_note_ons"]
    assert midi_rows[0]["gate_ticks"] == midi_rows[1]["gate_ticks"] == [24] * 8
    assert midi_rows[0]["final_gate_policy"] == midi_rows[1]["final_gate_policy"]
    assert midi_rows[0]["relative_channel_midi"] == midi_rows[1]["relative_channel_midi"]
    # The pair publishes the stop-boundary facts each run verified, and only
    # where Off and On agree on them.
    stop_keys = ("final_gate_truncated_by_stop", "final_gate_stop_event_bytes",
                 "final_gate_matches_stop_logical_ns",
                 "final_gate_duration_less_than_one_tick", "stop_grid_press_count")
    assert all(midi_rows[0][key] == midi_rows[1][key] for key in stop_keys)
    c.results.append(dict(
        kind="manual-ui-motion-midi-pair", citation=MOTION_CITATION,
        option_values=["Off", "On"], same_exact_note_ons=True,
        same_complete_channel_midi=True, same_natural_gates=True,
        same_stop_truncated_gate=True, same_controlled_timing=True,
        note_on_count=9, complete_channel_midi_count=18,
        complete_note_pair_count=9, natural_gate_count=8,
        gate_ticks=[24] * 8,
        final_gate_policy="stopped-after-extra-onset",
        **{key: midi_rows[0][key] for key in stop_keys},
        timing_tolerance_ns=2, passed=True))


CASES = {
    "M-MANUAL-RESET-REPEAT-PUBLIC-001": dict(
        run=repeat_reset_public_boundary,
        requirements=["CH-TEMPO", "OPT-REPEAT-RESET", "OPT-SEQUENCE-RESET", "OPT-SONG-MODE"],
        description="Public repeat-reset option rows and complete exact controlled MIDI through the first 64-step song boundary (manual:reset-at-pattern-repeat)"),
    "M-MANUAL-SNAP-MASK-PUBLIC-001": dict(
        run=snap_note_masks_public_pair, requirements=["MAN-097", "OPT-MASK-SNAP"],
        description="Authored masks, public Snap Note Masks On/Off rows, and exact resulting MIDI (manual:snap-note-masks-to-scale)"),
    "M-MANUAL-UI-MOTION-FRAME-001": dict(
        run=ui_motion_public_frames, requirements=["MAN-118"],
        description="The exact source CLOCK mini-header pixel poses progress On and remain at default pose Off; complete controlled MIDI and note gates match both settings (manual:ui-motion)"),
}
