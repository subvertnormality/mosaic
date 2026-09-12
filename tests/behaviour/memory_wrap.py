"""Memory after its bounded history wraps (README Memory, lines 698-707).

README: memory retains mask actions in order; E3 moves through them and a new
action after moving back continues from the displayed position (M-MEMORY-003).
Characterisation, not manual text: history keeps the latest 5000 actions per
channel (`memory.max_history_size`), so the counter stops at 5000.

Each held-step keyboard entry records one note-mask action (M-MEMORY-001); 5003
entries on step 1 wrap the history. E3 back two, a new step-2 action, then E3
back one must restore step 2's pattern note and keep step 1 at the note shown.
"""
import base64

NOTES = [60, 62, 64, 65, 67, 69, 71, 72]
BASELINE = [(60, 127), (62, 117), (64, 107), (65, 97)]
CAP = 5000; KEYS = CAP + 3


def memory_wrap(c):
    from frame_oracle import render
    c.configure(); c.enc(1, -2); c.screen_header('Ch. 1 Memory')

    def counter(current, total):
        expected = render([(0, 23, 15, str(current)), (0, 49, 15, str(total))], font_size=10, antialias=1)
        indexes = [(y*128+x)*4+k for y in list(range(13, 26))+list(range(39, 52)) for x in range(40) for k in range(3)]
        c.wait(lambda s: all(base64.b64decode(s['frame']['pixels_base64'])[i] == expected[i] for i in indexes))
        c.results.append(dict(kind='memory-position', current=current, total=total, frame_matched=True))

    def phrase(label, first, second):
        values = [first, second, *BASELINE[2:]]
        c.playback([(1, [144, n, v]) for n, v in values], cycles=2)
        c.results.append(dict(kind='memory-wrap-phrase', stage=label, notes=values, passed=True))

    # One held-step keyboard entry is one memory action (a hold merges its keys).
    c.enc(1, -2); c.screen_header('Ch. 1 Note Masks')
    for i in range(KEYS):
        note = NOTES[i % len(NOTES)]
        c.action(type='grid', x=1, y=4, state=1)
        try: c.action(type='midi', port=1, bytes=[144, note, 100]); c.action(type='midi', port=1, bytes=[128, note, 0])
        finally: c.action(type='grid', x=1, y=4, state=0)
    c.elapse(.1); c.enc(1, 2); c.screen_header('Ch. 1 Memory')
    last = NOTES[(KEYS - 1) % len(NOTES)]
    counter(CAP, CAP); phrase('wrapped-latest', (last, 100), BASELINE[1])
    c.enc(3, -2)
    shown = NOTES[(KEYS - 3) % len(NOTES)]
    counter(CAP - 2, CAP); phrase('wrapped-back-two', (shown, 100), BASELINE[1])
    # A new action after moving back continues from the displayed position.
    c.enc(1, -2); c.screen_header('Ch. 1 Note Masks')
    c.action(type='grid', x=2, y=4, state=1)
    try: c.action(type='midi', port=1, bytes=[144, 84, 60]); c.elapse(.05); c.action(type='midi', port=1, bytes=[128, 84, 0])
    finally: c.action(type='grid', x=2, y=4, state=0)
    c.elapse(.1); c.enc(1, 2); c.screen_header('Ch. 1 Memory')
    counter(CAP - 1, CAP - 1); phrase('new-action', (shown, 100), (84, 60))
    c.enc(3, -1)
    counter(CAP - 2, CAP - 1); phrase('new-action-undone', (shown, 100), BASELINE[1])
    c.enc(3, 1)
    counter(CAP - 1, CAP - 1); phrase('new-action-redone', (shown, 100), (84, 60))



def memory_retained_floor(c):
    """README 698-705: K2 returns to the beginning of bounded Memory.

    Characterisation at the production 5000-action bound: when the oldest action
    rolls out, beginning means the state immediately before the oldest retained
    action. The first edit is deliberately 72 while the untouched source is 60,
    so restoring nil cannot produce a false pass.
    """
    from frame_oracle import render
    c.configure(); c.enc(1, -2); c.screen_header('Ch. 1 Memory')
    c.enc(1, -2); c.screen_header('Ch. 1 Note Masks')
    notes = [72, 74, 76, 77]
    for i in range(CAP + 1):
        note = notes[i % len(notes)]
        c.action(type='grid', x=1, y=4, state=1)
        try:
            c.action(type='midi', port=1, bytes=[144, note, 100])
            c.action(type='midi', port=1, bytes=[128, note, 0])
        finally:
            c.action(type='grid', x=1, y=4, state=0)
    c.elapse(.1); c.enc(1, 2); c.screen_header('Ch. 1 Memory')

    def counter(current, total):
        expected = render([(0, 23, 15, str(current)), (0, 49, 15, str(total))], font_size=10, antialias=1)
        indexes = [(y*128+x)*4+k for y in list(range(13, 26))+list(range(39, 52)) for x in range(40) for k in range(3)]
        c.wait(lambda s: all(base64.b64decode(s['frame']['pixels_base64'])[i] == expected[i] for i in indexes))
        c.results.append(dict(kind='memory-position', current=current, total=total, frame_matched=True))

    counter(CAP, CAP)
    c.key(2)
    counter(0, CAP)
    c.playback([(1, [144, 72, 100]), *[(1, [144, n, v]) for n, v in BASELINE[1:]]], cycles=2)
    c.results.append(dict(kind='memory-retained-floor', capacity=CAP, dropped_actions=1,
                          expected_floor_note=72, untouched_source_note=60, passed=True))
