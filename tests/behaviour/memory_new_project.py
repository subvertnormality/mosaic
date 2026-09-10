"""A new project starts with no memory (README Memory, lines 698-707; "+ New" in the
project parameters).

README: memory retains the mask and trig lock actions made in the project, and E3
moves through them. Two note-mask actions are recorded, then "+ New" replaces the
project. The new project must show an empty history, and E3 back and forward must not
replay the previous project's actions onto it.
"""
import base64
BASELINE = [(60, 127), (62, 117), (64, 107), (65, 97)]


def memory_new_project(c):
    from frame_oracle import render
    from persisted_ranges import select_project_action

    def counter(current, total):
        expected = render([(0, 23, 15, str(current)), (0, 49, 15, str(total))], font_size=10, antialias=1)
        indexes = [(y*128+x)*4+k for y in list(range(13, 26))+list(range(39, 52)) for x in range(16) for k in range(3)]
        c.wait(lambda s: all(base64.b64decode(s['frame']['pixels_base64'])[i] == expected[i] for i in indexes))
        c.results.append(dict(kind='memory-position', current=current, total=total, frame_matched=True))

    def record(step, note, velocity):
        c.enc(1, -2); c.screen_header('Ch. 1 Note Masks')
        c.action(type='grid', x=step, y=4, state=1)
        try: c.action(type='midi', port=1, bytes=[144, note, velocity]); c.elapse(.05); c.action(type='midi', port=1, bytes=[128, note, 0])
        finally: c.action(type='grid', x=step, y=4, state=0)
        c.elapse(.1); c.enc(1, 2); c.screen_header('Ch. 1 Memory')

    c.configure(); c.enc(1, -2); c.screen_header('Ch. 1 Memory')
    record(1, 72, 90); record(2, 76, 80); counter(2, 2)
    c.playback([(1, [144, 72, 90]), (1, [144, 76, 80]), *[(1, [144, n, v]) for n, v in BASELINE[2:]]], cycles=2)
    select_project_action(c, 2); c.key(1)                        # "+ New"
    c.enc(1, -5)                                                  # configure() starts from the first page
    c.configure(); c.enc(1, -2); c.screen_header('Ch. 1 Memory')
    counter(0, 0)
    c.enc(3, -1); c.enc(3, 1); counter(0, 0)
    c.playback([(1, [144, n, v]) for n, v in BASELINE], cycles=2)
    c.results.append(dict(kind='memory-new-project', recorded_before_new=2, history_after_new=0, passed=True))
