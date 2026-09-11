"""Held-step mask entry with a second held key outside the sequencer rows (README 595: "press
and hold the step you wish to modify, then input the desired value as a trig lock"; README 597:
the channel-wide mask value is set "without holding down a step" and applies to steps without
a step lock).

Human decision 2026-09-11 (suspected-defects S27): held keys outside rows 4-7 are ignored by
the mask handlers. Channel 1 plays C D E F at velocities 127/117/107/97 on steps 1-4. With a
pattern-row key (2, 2) held as well, a velocity turned on the Masks page must lock only the
held step, whichever of the two keys went down first; no channel-wide velocity is set.
"""


def held_mask_extra_key(c):
    c.configure(); c.enc(1, -4); c.enc(2, 1)                     # Masks page, Vel selector

    def hold_two(first, second, turns):
        c.action(type='grid', x=first[0], y=first[1], state=1); c.elapse(.06)
        c.action(type='grid', x=second[0], y=second[1], state=1); c.elapse(.06)
        try: c.enc(3, turns)
        finally:
            c.action(type='grid', x=second[0], y=second[1], state=0); c.elapse(.06)
            c.action(type='grid', x=first[0], y=first[1], state=0); c.elapse(.3)

    # Step 1 held first, then the pattern-row key: step 1 locked to velocity 50 (X + 51).
    hold_two((1, 4), (2, 2), 51)
    expected = [(1, [144, 60, 50]), (1, [144, 62, 117]), (1, [144, 64, 107]), (1, [144, 65, 97])]
    c.playback(expected, cycles=2, timeout=4)
    c.results.append(dict(kind='held-mask-extra-key', order='step-first', passed=True))

    # The pattern-row key first, then step 2: step 2 alone is locked to velocity 40 (X + 41);
    # steps 3 and 4 keep their pattern velocities (README 595/597).
    hold_two((2, 2), (2, 4), 41)
    before = c.snapshot()['midi_count']
    expected = [(1, [144, 60, 50]), (1, [144, 62, 40]), (1, [144, 64, 107]), (1, [144, 65, 97])]
    try:
        c.playback(expected, cycles=2, timeout=4)
    except AssertionError:
        state = c.snapshot()
        heard = [m['bytes'] for m in state['midi'] if m['index'] > before and m['bytes'][0] == 144 and m['bytes'][2] > 0][:4]
        raise AssertionError('Pattern-row key held first: the velocity turn did not lock only step 2', dict(expected=[e[1] for e in expected], heard=heard))
    c.results.append(dict(kind='held-mask-extra-key', order='pattern-row-key-first', passed=True))
    c.results.append(dict(kind='held-mask-extra-key-summary', passed=True))
