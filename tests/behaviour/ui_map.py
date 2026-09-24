"""Stable UI keys and the concrete Mosaic 1.4.0 layout they resolve to.

Behaviour cases import keys from here through :mod:`ui`; rendered labels,
coordinates and LED levels do not belong in musical case code.
"""

from collections import OrderedDict


MENU = {
    "play_stop": (1, 8),
    "record": (2, 8),
    "channel_editor": (3, 8),
    "scale_editor": (4, 8),
    "pattern_editor": (5, 8),
    "song_editor": (6, 8),
    "shift_left": (10, 8),
    "shift_reset": (11, 8),
    "shift_right": (12, 8),
    "cancel": (14, 8),
    "panic": (15, 8),
    "paint": (16, 8),
}

# Rhythm Doctor's own page has a deliberately separate control vocabulary:
# the same grid cells mean different things while that algorithm is active.
RHYTHM_DOCTOR_CONTROLS = {
    "legacy_drum_algorithm": (12, 2),
    "legacy_tresillo_algorithm": (13, 2),
    "legacy_euclidean_algorithm": (14, 2),
    # Euclidean workflow names retain the raw recipe's cells on this page.
    "euclidean_tool": (14, 2),
    "euclidean_fill_minimum": (2, 2),
    "euclidean_fill_maximum": (10, 2),
    "euclidean_fill_boundary": (9, 2),
    "euclidean_rotation_minimum": (2, 3),
    "euclidean_rotation_maximum": (10, 3),
    "legacy_numeric_repetitor_algorithm": (15, 2),
    "algorithm": (16, 2),
    "reserved_lane": (2, 2),
    "lane_bd": (3, 2),
    "lane_sd": (4, 2),
    "lane_cym": (5, 2),
    "withdrawn_lane_bass": (6, 2),
    "retired_lane": (7, 2),
    "capture": (1, 2),
    "phrase_left": (10, 8),
    "phrase_centre": (11, 8),
    "phrase_right": (12, 8),
}

# Pattern-algorithm workflow names share physical cells with some chooser
# controls above, but refer to the legacy grid workflow under test.
ALGORITHM_WORKFLOW_CONTROLS = {
    "tresillo_tool": (13, 2),
    "drum_pattern_two": (12, 2),
    "rhythm_fill_minimum": (2, 2),
    "rhythm_fill_maximum": (10, 2),
    "rhythm_factor_minimum": (2, 3),
    "rhythm_factor_maximum": (10, 3),
    "numeric_prime_one": (15, 2),
}
RHYTHM_DOCTOR_SCREEN = {
    "header": {"bottom": 10},
    "tooltip": {"left": 0, "right": 100, "top": 55, "bottom": 64},
    "status": {"left": 0, "right": 97, "top": 15, "bottom": 26},
}
CHANNEL_COUNT = 16

# Stable pitch keys for the authored C4-F4 notes on the pattern note grid.
# These preserve the established note-entry gestures used by the Euclidean
# workflow cases while keeping their physical cells in this map.
PATTERN_NOTE_PITCHES = {
    "pattern_note_c": (5, 3),
    "pattern_note_d": (6, 2),
    "pattern_note_e": (7, 1),
    "pattern_note_f": (8, 6),
}

CHANNEL_PAGES = OrderedDict([
    ("masks", {"title": "Note Masks"}),
    ("trig_locks", {"title": "Trig Locks"}),
    ("memory", {"title": "Memory"}),
    ("clock_mods", {"title": "Clocks"}),
    ("midi_config", {"title": "Device Config"}),
    ("note_dashboard", {"title": "Note Dashboard"}),
    ("merge_shape", {"title": "Merge Shape"}),
    ("harmony", {"title": "Harmony"}),
])

HEADERS = {
    **{
        key: {
            "template": "Ch. {channel} " + value["title"],
            "selected": index,
            "tabs": len(CHANNEL_PAGES),
        }
        for index, (key, value) in enumerate(CHANNEL_PAGES.items(), 1)
    },
    "trigger_editor": {"template": "Trig editor options", "selected": 1, "tabs": 2},
    "trigger_editor_confirmation": {"template": "Trig editor options", "selected": 2, "tabs": 2},
    "note_editor": {"template": "Note editor options", "selected": 1, "tabs": 2},
    "velocity_editor": {"template": "Velocity editor options", "selected": 1, "tabs": 2},
}

SCREEN = {
    "header_rows": (0, 10),
    "tab_pitch": 10,
    "tab_baseline": 1,
    "title": (0, 9, 10),
    "brand": (120, 9, 10, "m"),
    "selected_row": {"baseline": 30, "level": 15, "top": 22, "bottom": 32},
    "selected_value": {"left": 108, "right": 128},
    "menu_option_row": {"left": 0, "right": 128, "top": 22, "bottom": 32},
    "length_field": {
        "label": "Len", "x": 75, "label_baseline": 18, "value_baseline": 26,
        "level": 15, "left": 75, "right": 100, "top": 11, "bottom": 29,
    },
    "parameter_list": {
        "x": 35, "baseline": 35, "level": 5,
        "left": 35, "right": 128, "top": 27, "bottom": 37,
    },
    "device_picker": {
        "x": 10, "baseline": 35, "level": 15,
        "left": 10, "right": 58, "top": 27, "bottom": 37,
    },
    "menu_label": {"x": 0, "width": 70, "top": 22},
    "memory_position": {
        "frame_width": 128,
        "frame_height": 64,
        "channels": 3,
        "bytes_per_pixel": 4,
        "font_size": 10,
        "antialias": 1,
        "level": 15,
        "bands": {
            "current": {
                "left": 0, "right": 16, "top": 13, "bottom": 26,
                "x": 0, "baseline": 23,
            },
            "total": {
                "left": 0, "right": 16, "top": 39, "bottom": 52,
                "x": 0, "baseline": 49,
            },
        },
    },
    "project_menu": {
        "root_id": "mosaic",
        "actions": {
            "save": {
                "label": "< Save project", "offset": 0,
                "x": 0, "width": 70, "top": 23,
            },
            "load": {
                "label": "> Load project", "offset": 1,
                "x": 0, "width": 70, "top": 22,
            },
            "new": {
                "label": "+ New", "offset": 2,
                "x": 0, "width": 70, "top": 22,
            },
        },
    },
}

NATIVE_MENU = {
    "levels_root": "LEVELS >",
    "mod_devices_root": "DEVICES > ",
    "mod_mods_root": "MODS >",
    "mod_matrix_root": "MATRIX >",
    "mod_rhythm_1": "rhythm 1",
    "mod_macro_1": "macro 1",
    "mod_active": "active",
    "mod_value": "value",
    "mod_beats": "beats",
    "mod_shape": "shape",
    "mod_clocked": "clocked",
    "mod_fixed_note": "Fixed Note",
    "mod_source_rhythm_1": "rhythm 1",
    "mod_source_lfo_1": "lfo 1",
    "clock_root_name": "CLOCK",
    "clock_source": "source",
    "clock_tempo": "tempo",
    "elektron_program_change_channel": "Elektron p.change channel",
    "patch_control_default": "CC 1",
    "patch_control_configured": "Control 1",
}

NATIVE_MENU_LABEL_GEOMETRY = {
    "mod_matrix_root": {"x": 4},
}

NATIVE_MENU_VALUES = {
    "clock_source": {
        "internal": "internal",
        "midi": "midi",
    },
    "modulation_control_1": {
        "off": "X",
        "base_32": "32",
        "positive_half": "0.50",
        "full_depth": "1.0",
        "base_96": "96",
        "base_97": "97",
        "clear_depth": "-",
        "negative_quarter": "-0.25",
    },
}

NATIVE_MODULATION_SOURCES = {
    "lfo_1": {"offset": 4, "menu_label": "mod_source_lfo_1"},
    "macro_1": {"offset": 12, "menu_label": "mod_macro_1"},
}

PATCH_PARAMETERS = {
    "nrpn14": {
        "label": "NRPN14",
        "failure": "NRPN14 control not reachable",
    },
    "sparse_high": {"label": "SparseHigh", "failure": "Sparse control not reachable: SparseHigh"},
    "sparse_low": {"label": "SparseLow", "failure": "Sparse control not reachable: SparseLow"},
    "cc_default": {"label": "CCdefault", "failure": "Default-Off CC control unreachable"},
    "nrpn_old": {"label": "NRPNold", "failure": "NRPN slide control unreachable"},
    "nrpn_default": {"label": "NRPNdef", "failure": "NRPN slide control unreachable"},
    **{
        'nrpn_%s_%d' % (mode, index): {
            'label': prefix + str(index), 'failure': 'Boundary NRPN controls unreachable',
        }
        for mode, prefix in [('standard', 'NS'), ('legacy', 'NL')]
        for index in range(7)
    },
}

PATCH_PARAMETER_VALUES = {
    "off": "X",
}

TRIG_PARAMETERS = {
    "stored_patch_control1": "Control 1",
    "stored_patch_nrpn14": "NRPN14",
    "configured_control_1": "Control 1",
    "ns0": "NS0",
    "ns6": "NS6",
    "fixed_note": "Fixed Note",
    "quantised_fixed_note": "Quantised Fixed Note",
    "trig_probability": "Trig Probability",
    "random_note": "Random Note",
    "twos_random_note": "Twos Random Note",
    "chord_note_arpeggio": "Chord Note Arpeggio",
    "chord_note_strum": "Chord Note Strum",
    "chord_spread": "Chord Spread",
    "chord_accel_mod": "Chord Accel Mod",
    "mute_chord_root": "Mute Chord Root",
    "chord_pattern": "Chord Pattern",
    "none": "None",
    **{'stored_patch_cc%d' % number: 'CC %d' % number for number in range(1, 11)},
    **{key: value['label'] for key, value in PATCH_PARAMETERS.items()},
}

MIDI_MAPPING_PARAMETERS = {
    "selected_channel_velocity": {
        "root_id": "mosaic_mask_midi_maps",
        "label": "Selected Ch. Velocity",
        "scan_limit": 12,
        "first_row_top": 23,
    },
}

MOSAIC_OPTIONS = {
    "scale_lock_until_pattern_end": "Scales lock until ptn end",
    "lock_merged_to_pentatonic": "Lock merged to pent.",
    "elektron_program_changes": "Elektron program changes",
    "trigless_locks": "Trigless locks",
    "wrap_param_slides": "Wrap param slides",
    "song_mode": "Song mode",
    "reset_on_song_seq_change": "Reset on song seq change",
    "reset_on_pattern_repeat": "Reset on pattern repeat",
}

# Every distinct level has a distinct semantic name. Controls may narrow this
# vocabulary after captured-baseline domain generation; keeping it injective is
# the invariant that prevents an assertion from becoming weaker.
LED_LEVELS = {
    "dark": 0,
    "trace": 1,
    "off": 2,
    "inactive": 3,
    "blink_low": 4,
    "in_range": 5,
    "alternate": 7,
    "medium": 8,
    "active": 12,
    "selected": 15,
}


def step_cell(step):
    if not 1 <= step <= 64:
        raise ValueError("step must be in 1..64")
    return ((step - 1) % 16 + 1, (step - 1) // 16 + 4)


def control_cell(control, index=None):
    if control in PATTERN_NOTE_PITCHES:
        if index is not None:
            raise ValueError("pattern note pitch controls do not take an index")
        return PATTERN_NOTE_PITCHES[control]
    if control in RHYTHM_DOCTOR_CONTROLS:
        if index is not None:
            raise ValueError("Rhythm Doctor control %s does not take an index" % control)
        return RHYTHM_DOCTOR_CONTROLS[control]
    if control in ALGORITHM_WORKFLOW_CONTROLS:
        if index is not None:
            raise ValueError("algorithm workflow control %s does not take an index" % control)
        return ALGORITHM_WORKFLOW_CONTROLS[control]
    if control == "step":
        return step_cell(index)
    if control == "channel":
        if not 1 <= index <= CHANNEL_COUNT:
            raise ValueError("channel must be in 1..%d" % CHANNEL_COUNT)
        return index, 1
    if control == "pattern_slot":
        return index, 2
    if control == "drum_bank":
        if type(index) is not int or not 1 <= index <= 5:
            raise ValueError("drum bank must be an integer in 1..5")
        return 11 + index, 3
    if control == "numeric_mask":
        if type(index) is not int or not 1 <= index <= 4:
            raise ValueError("numeric mask must be an integer in 1..4")
        return 11 + index, 3
    if control == "pattern_select":
        if not 1 <= index <= CHANNEL_COUNT:
            raise ValueError("pattern selection must be in 1..%d" % CHANNEL_COUNT)
        return index, 1
    if control == "pattern_group":
        if type(index) is not int or not 1 <= index <= 4:
            raise ValueError("pattern group must be an integer in 1..4")
        return 8 + index, 8
    if control in ("pattern_velocity_range_down", "pattern_velocity_range_reset"):
        if index is not None:
            raise ValueError("velocity range controls do not take an index")
        return (16, 8) if control.endswith("down") else (15, 8)
    if control == "pattern_length_merge_mode":
        if index is not None:
            raise ValueError("pattern length merge mode does not take an index")
        return 16, 8
    if control == "pattern_note_fader":
        if not (isinstance(index, tuple) and len(index) == 2):
            raise ValueError("pattern note fader needs an (x, y) value cell")
        return index
    if control == "pattern_note":
        if not (isinstance(index, tuple) and len(index) == 2
                and all(type(value) is int for value in index)
                and 1 <= index[0] <= CHANNEL_COUNT and 1 <= index[1] <= 7):
            raise ValueError("pattern note needs (step 1..16, row 1..7)")
        return index
    if control == "pattern_note_degree":
        if not (isinstance(index, tuple) and len(index) == 2
                and all(isinstance(value, int) for value in index)
                and 1 <= index[0] <= CHANNEL_COUNT and 0 <= index[1] <= 6):
            raise ValueError("pattern note degree needs (step 1..16, degree 0..6)")
        return index[0], 7 - index[1]
    if control == "pattern_note_position":
        if not (isinstance(index, tuple) and len(index) == 2
                and all(type(value) is int for value in index)
                and 1 <= index[0] <= CHANNEL_COUNT and 1 <= index[1] <= 7):
            raise ValueError("pattern note position needs an (x, y) cell in rows 1..7")
        return index
    if control == "pattern_velocity_level":
        if not (isinstance(index, tuple) and len(index) == 2
                and all(type(value) is int for value in index)
                and 1 <= index[0] <= CHANNEL_COUNT and 1 <= index[1] <= 7):
            raise ValueError("pattern velocity level needs (step 1..16, level 1..7)")
        return index[0], 8 - index[1]
    if control == "pattern_note_octave_down":
        if index is not None:
            raise ValueError("pattern note octave down does not take an index")
        return 16, 8
    if control == "pattern_note_octave_reset":
        if index is not None:
            raise ValueError("pattern note octave reset does not take an index")
        return 15, 8
    if control == "pattern_note_octave_up":
        if index is not None:
            raise ValueError("pattern note octave up does not take an index")
        return 14, 8
    if control == "song_slot":
        return index, 3
    if control == "song_pattern_slot":
        if type(index) is not int or not 1 <= index <= 96:
            raise ValueError("song pattern slot must be an integer in 1..96")
        return (index - 1) % CHANNEL_COUNT + 1, (index - 1) // CHANNEL_COUNT + 1
    if control == "scale_slot":
        return index, 3
    if control == "channel_scale_slot":
        return index, 3
    if control == "channel_octave":
        if not -2 <= index <= 2:
            raise ValueError("channel octave must be in -2..2")
        return 10 + index, 8
    if control == "pattern_note_page":
        if type(index) is not int or not 1 <= index <= 4:
            raise ValueError("pattern note page must be an integer in 1..4")
        return 8 + index, 8
    if control == "trig_merge_mode":
        if index is not None:
            raise ValueError("trig merge mode does not take an index")
        return 14, 8
    if control == "note_merge_mode":
        if index is not None:
            raise ValueError("note merge mode does not take an index")
        return 15, 8
    if control == "velocity_merge_mode":
        if index is not None:
            raise ValueError("velocity merge mode does not take an index")
        return 16, 8
    if control == "global_pattern_length":
        if not 1 <= index <= CHANNEL_COUNT:
            raise ValueError("global pattern length must be in 1..%d" % CHANNEL_COUNT)
        return index, 7
    if control == "global_transpose_minimum":
        if index is not None:
            raise ValueError("global transpose minimum does not take an index")
        return 9, 8
    if control == "global_transpose_increment":
        if index is not None:
            raise ValueError("global transpose increment does not take an index")
        return 16, 8
    if control == "global_transpose_plus_four":
        if index is not None:
            raise ValueError("global transpose +4 does not take an index")
        return 13, 8
    if control == "step_transpose_minimum":
        if index is not None:
            raise ValueError("step transpose minimum does not take an index")
        return 9, 8
    if control == "step_transpose_increment":
        if index is not None:
            raise ValueError("step transpose increment does not take an index")
        return 16, 8
    if control == "step_transpose_zero":
        if index is not None:
            raise ValueError("step transpose zero does not take an index")
        return 12, 8
    if control == "step_transpose_plus_twelve":
        if index is not None:
            raise ValueError("step transpose +12 does not take an index")
        return 15, 8
    if control in MENU:
        if index is not None:
            raise ValueError("menu controls do not take an index")
        return MENU[control]
    if control == "cell":
        if not (isinstance(index, tuple) and len(index) == 2):
            raise ValueError("cell index must be an (x, y) tuple")
        return index
    raise KeyError("unknown UI control: " + str(control))


def performance_gesture_recipe(gesture):
    """Resolve a semantic performance stimulus to its legacy evidence tuple."""
    kind, a, b = gesture
    if kind == 'control':
        return ('grid', *control_cell(a, b))
    if kind == 'encoder':
        return ('enc', a, b)
    raise ValueError('unknown performance gesture: ' + str(kind))


# Safe non-musical controls, every 250 ms; physical and emulator lanes share
# this recipe. Output evidence resolves these keys to the original raw tuple.
PERFORMANCE_RENDER_PRESSURE_SCHEDULE = [
    (.25, 'page-channel', ('control', 'channel_editor', None)),
    (.50, 'channel-16', ('control', 'channel', 16)),
    (.75, 'browse-forward', ('encoder', 1, 2)),
    (1.00, 'page-trig', ('control', 'pattern_editor', None)),
    (1.25, 'page-song', ('control', 'song_editor', None)),
    (1.50, 'page-channel', ('control', 'channel_editor', None)),
    (1.75, 'channel-1', ('control', 'channel', 1)),
    (2.00, 'browse-back', ('encoder', 1, -2)),
    (2.25, 'page-trig', ('control', 'pattern_editor', None)),
    (2.50, 'page-song', ('control', 'song_editor', None)),
    (2.75, 'page-channel', ('control', 'channel_editor', None)),
    (3.00, 'channel-16', ('control', 'channel', 16)),
    (3.25, 'browse-forward', ('encoder', 1, 2)),
    (3.50, 'page-trig', ('control', 'pattern_editor', None)),
    (3.75, 'page-song', ('control', 'song_editor', None)),
    (4.00, 'page-channel', ('control', 'channel_editor', None)),
    (4.25, 'channel-1', ('control', 'channel', 1)),
    (4.50, 'browse-back', ('encoder', 1, -2)),
    (4.75, 'page-trig', ('control', 'pattern_editor', None)),
    (5.00, 'page-song', ('control', 'song_editor', None)),
    (5.25, 'page-channel', ('control', 'channel_editor', None)),
    (5.50, 'channel-16', ('control', 'channel', 16)),
    (5.75, 'browse-forward', ('encoder', 1, 2)),
    (6.00, 'page-trig', ('control', 'pattern_editor', None)),
    (6.25, 'page-song', ('control', 'song_editor', None)),
    (6.50, 'page-channel', ('control', 'channel_editor', None)),
    (6.75, 'channel-1', ('control', 'channel', 1)),
    (7.00, 'browse-back', ('encoder', 1, -2)),
    (7.25, 'page-trig', ('control', 'pattern_editor', None)),
    (7.50, 'page-song', ('control', 'song_editor', None)),
]


def grid_partition(page):
    """Return the page's 128 cells mapped once to their owning control.

    The values are descriptive; the coordinate keys are the executable
    partition and therefore must remain unique and complete.
    """
    if page not in {"trigger_editor", "channel_editor", "song_editor", "scale_editor"}:
        raise KeyError(page)
    cells = {}
    for y in range(1, 9):
        for x in range(1, CHANNEL_COUNT + 1):
            if page == "song_editor" and y <= 6:
                owner = ("song_pattern_slot", (y - 1) * CHANNEL_COUNT + x)
            elif y >= 4:
                owner = ("step", (y - 4) * 16 + x)
            elif page == "channel_editor" and y == 1:
                owner = ("channel", x)
            elif y == 2:
                owner = ("pattern_slot", x)
            elif y == 3 and page == "scale_editor":
                owner = ("scale_slot", x)
            else:
                owner = ("page_control", (x, y))
            cells[(x, y)] = owner
    for name, cell in MENU.items():
        cells[cell] = (name, None)
    if page == "trigger_editor":
        for pattern in range(1, CHANNEL_COUNT + 1):
            cells[(pattern, 1)] = ("pattern_select", pattern)
    if page == "channel_editor":
        for scale in range(1, CHANNEL_COUNT + 1):
            cells[(scale, 3)] = ("channel_scale_slot", scale)
        for octave in range(-2, 3):
            cells[(10 + octave, 8)] = ("channel_octave", octave)
        cells[(14, 8)] = ("trig_merge_mode", None)
        cells[(15, 8)] = ("note_merge_mode", None)
        cells[(16, 8)] = ("velocity_merge_mode", None)
    if page == "song_editor":
        for length in range(1, CHANNEL_COUNT + 1):
            cells[(length, 7)] = ("global_pattern_length", length)
    if page == "scale_editor":
        cells[(9, 8)] = ("global_transpose_minimum", None)
        cells[(16, 8)] = ("global_transpose_increment", None)
    return cells


def header_text(page, **params):
    try:
        return HEADERS[page]["template"].format(**params)
    except KeyError as error:
        raise KeyError("unknown or incomplete header key %r: %s" % (page, error)) from error
NATIVE_PARAMETER_ROOTS = {
    "mosaic": {"field": "id", "value": "mosaic"},
    "channel_1_device_parameters": {
        "field": "id",
        "value": "midi_device_params_group_channel_1",
    },
    "macro_1": {"field": "name", "value": "macro 1"},
    "lfo_1": {"field": "name", "value": "lfo 1"},
    "clock": {"field": "name", "value": "CLOCK"},
}

NATIVE_MENU_PARAMETERS = {
    "configured_control_1": {
        "label": "Control 1",
        "failure": "Configured Control 1 unavailable in Matrix target group",
    },
}

MOSAIC_OPTION_ROWS = {"trigless_locks": 23}
MOSAIC_OPTION_VALUES = {False: "Off", True: "On"}
