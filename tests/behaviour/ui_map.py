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
CHANNEL_COUNT = 16

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
}

NATIVE_MENU = {
    "levels_root": "LEVELS >",
    "clock_source": "source",
}

NATIVE_MENU_VALUES = {
    "clock_source": {
        "internal": "internal",
        "midi": "midi",
    },
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
    if control == "step":
        return step_cell(index)
    if control == "channel":
        if not 1 <= index <= CHANNEL_COUNT:
            raise ValueError("channel must be in 1..%d" % CHANNEL_COUNT)
        return index, 1
    if control == "pattern_slot":
        return index, 2
    if control == "pattern_select":
        if not 1 <= index <= CHANNEL_COUNT:
            raise ValueError("pattern selection must be in 1..%d" % CHANNEL_COUNT)
        return index, 1
    if control == "pattern_note_fader":
        if not (isinstance(index, tuple) and len(index) == 2):
            raise ValueError("pattern note fader needs an (x, y) value cell")
        return index
    if control == "song_slot":
        return index, 3
    if control == "song_pattern_slot":
        return index, 1
    if control == "scale_slot":
        return index, 3
    if control == "channel_scale_slot":
        return index, 3
    if control == "channel_octave":
        if not -2 <= index <= 2:
            raise ValueError("channel octave must be in -2..2")
        return 10 + index, 8
    if control == "trig_merge_mode":
        if index is not None:
            raise ValueError("trig merge mode does not take an index")
        return 14, 8
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
    if control in MENU:
        if index is not None:
            raise ValueError("menu controls do not take an index")
        return MENU[control]
    if control == "cell":
        if not (isinstance(index, tuple) and len(index) == 2):
            raise ValueError("cell index must be an (x, y) tuple")
        return index
    raise KeyError("unknown UI control: " + str(control))


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
            if y >= 4:
                owner = ("step", (y - 4) * 16 + x)
            elif page == "channel_editor" and y == 1:
                owner = ("channel", x)
            elif page == "song_editor" and y == 1:
                owner = ("song_pattern_slot", x)
            elif y == 2:
                owner = ("pattern_slot", x)
            elif y == 3 and page == "song_editor":
                owner = ("song_slot", x)
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
