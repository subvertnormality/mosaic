"""Many scale saves in one session (README "Scale editor", line 850-854).

README: saving changes to the scale used by playback changes that scale. The
quantiser caches processed scales per saved version (an optimisation, not manual
text); a session that saves the playing scale more than 100 times must keep
quantising exactly. While playing, slot 1's root alternates C / C# with a K3
save; the first onset after each save plays its step's degree in the new root.
"""
CYCLES = 110
MAJOR = [0, 2, 4, 5]; VELOCITY = [127, 117, 107, 97]


def scale_cache_saves(c):
    c.configure()
    c.tap(4, 8); c.tap(3, 3); c.tap(1, 3)                         # slot 1 applied and selected for editing
    c.enc(2, -1)                                                  # root selector
    before = c.snapshot()['midi_count']; c.tap(1, 8)
    def onsets(s): return [m for m in s['midi'] if m['index'] > before and m['bytes'][0] == 144 and m['bytes'][2] > 0]
    checked = []
    for cycle in range(CYCLES):
        root = 1 if cycle % 2 == 0 else 0
        c.enc(3, 1 if root else -1); c.key(3)                     # save slot 1 with the new root while playing
        seen = len(onsets(c.snapshot()))
        state = c.wait(lambda s: len(onsets(s)) > seen, timeout=2)
        note = onsets(state)[seen]
        degree = seen % 4                                         # the channel phrase steps 1..4
        assert (note['port'], note['bytes']) == (1, [144, 60 + root + MAJOR[degree], VELOCITY[degree]]), \
            dict(cycle=cycle, root=root, degree=degree, actual=note['bytes'])
        checked.append((cycle, root, note['bytes'][1]))
    c.tap(1, 8); c.wait(lambda s: not s['midi_capture']['outstanding'])
    c.results.append(dict(kind='scale-cache-saves', saves=CYCLES, first_onsets_after_save=checked, passed=True))
