"""Raw framebuffer/grid contracts for numeric note merging."""


def _expect_selected_pattern_top_note_blink(c, slot):
    c.wait(lambda state: state['grid'][slot-1] in (11,13))
    c.results.append(dict(kind='selected-pattern-top-note-blink',slot=slot,
                          levels=[11,13],passed=True))


def numeric_note_merge(c,foreign_velocity=False,pentatonic=False,
                       all_scales=False,harmony=False):
    """Keep the exact historical selected-pattern blink oracle in contract scope."""
    from numeric_merging import numeric_note_merge as run_numeric_note_merge

    return run_numeric_note_merge(
        c, foreign_velocity, pentatonic, all_scales, harmony,
        blink_observer=_expect_selected_pattern_top_note_blink,
    )


def numeric_note_merge_exclude_foreign_velocity(c):
    return numeric_note_merge(c, True)


def numeric_note_merge_pentatonic_velocity(c):
    return numeric_note_merge(c, True, True)


def numeric_note_merge_all_scales(c):
    return numeric_note_merge(c, True, False, True)


def numeric_note_merge_all_pentatonic_scales(c):
    return numeric_note_merge(c, True, True, True)


def numeric_note_merge_harmony(c):
    return numeric_note_merge(c, True, False, harmony=True)


def numeric_note_merge_harmony_pentatonic(c):
    return numeric_note_merge(c, True, True, harmony=True)
