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
