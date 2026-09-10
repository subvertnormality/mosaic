"""High-risk triple: live parameter recording (a lock edit while armed) across a song
transition (BEHAVIOUR_PLAN "recording + lock edit + song transition").

Channel 1 keeps its default phrase; CC 1 is assigned with stored patch value 63
and locks step 1 = 24, step 3 = 96, then slot 1 is copied to slot 2 (global
length 4, song mode 1 -> 2 -> 1). At 30 BPM (0.5 s steps) with recording
armed, E3 raises CC 1 to 64 during slot 1 step 1. README "Arm live record":
the edited value records on subsequent eligible steps through the channel's
final step, overwriting their locks, and recording clears before the next
starting step (README 241). So slot 1 steps 2..4 become 64 and slot 2 keeps
24/-/96/-. E3 on the Trig Locks page also sets the stored value (README 756-758),
which unlocked steps send (README 759). Characterisation, not manual text:
Play sends the stored value before step 1's lock.
A disarmed replay with the stored patch at 65 separates locks from recalls.
"""

PHRASE = [(60, 127), (62, 117), (64, 107), (65, 97)]


def recording_lock_song(c, persist=False):
    from cases import assign_trig_parameter, menu_label, menu_value
    from patch_params import open_patch_control, turn
    c.configure()
    open_patch_control(c, setup=False); turn(c, 63); turn(c, 1); menu_value(c, '63'); c.key(1)
    c.enc(1, -3); assign_trig_parameter(c, 'CC 1')
    for step, value in [(1, 24), (3, 96)]:
        c.action(type='grid', x=step, y=4, state=1)
        try: c.elapse(.05); c.action(type='enc', n=3, delta=-126); c.enc(3, value + 1)
        finally: c.action(type='grid', x=step, y=4, state=0)
    c.tap(6, 8); c.tap(2, 7)
    for _ in range(3): c.tap(8, 7)                               # global length 4
    # Song editor page 2: tempo 90 -> 30 (its minimum), before the copy.
    import base64
    from frame_oracle import render
    c.enc(1, 1); c.enc(3, -60); c.key(3)
    expected = render([(0, 26, 15, '30')])
    c.wait(lambda s: all(base64.b64decode(s['frame']['pixels_base64'])[(y*128+x)*4+k] == expected[(y*128+x)*4+k]
                         for y in range(20, 28) for x in range(36) for k in range(3)))
    assert c.snapshot()['diagnostics']['tempo'] == 30
    c.enc(1, -1)
    c.hold_tap((1, 1), (2, 1)); c.tap(1, 1); c.tap(3, 8)         # slot 2 = copy of slot 1; play from slot 1
    c.screen_header('Ch. 1 Trig Locks', selected=2)               # still on the trig lock page, CC 1 slot
    c.tap(2, 8)                                                    # arm recording
    def run(expected_cycles, edit=False, c=c, step_seconds=.5):
        """Play from slot 1 and return the CC 1/note stream through 17 onsets."""
        before = c.snapshot()['midi_count']; c.tap(1, 8)
        def onsets(state): return [e for e in state['midi'] if e['index'] > before and e['bytes'][0] == 144 and e['bytes'][2] > 0]
        if edit:
            c.wait(lambda s: len(onsets(s)) == 1, timeout=3)
            c.elapse(.3); c.enc(3, 1)                              # 63 -> 64 while slot 1 step 1 plays
        state = c.wait(lambda s: len(onsets(s)) >= 17, timeout=16)
        c.tap(1, 8); c.wait(lambda s: not s['midi_capture']['outstanding'])
        stream = [('note', e['bytes'][1]) if e['bytes'][0] == 144 else ('cc', e['bytes'][2]) for e in state['midi']
                  if e['index'] > before and ((e['bytes'][0] == 144 and e['bytes'][2] > 0) or e['bytes'][:2] == [176, 1])]
        expected = [('cc', expected_cycles[0][1])]                 # Play recalls the stored patch
        for cycle, (locks, _) in enumerate(expected_cycles):
            for step in range(4):
                expected += [('cc', locks[step]), ('note', PHRASE[step][0])]
                if edit and cycle == 0 and step == 0: expected += [('cc', 64)]  # the E3 edit sends immediately
        expected += [('cc', 24), ('note', 60)]                     # next slot 1 onset before Stop
        actual = stream[:len(expected)]
        assert actual == expected, dict(expected=expected, actual=actual)
        notes = onsets(state)
        assert [e['bytes'][2] for e in notes[:16]] == [v for _, v in PHRASE] * 4
        field = 'logical_ns' if c.clock_mode == 'controlled-experimental' else 'monotonic_ns'
        tolerance = 2e-9 if c.clock_mode == 'controlled-experimental' else .01
        gaps = [(b[field] - a[field]) / 1e9 for a, b in zip(notes, notes[1:17])]
        assert all(abs(g - step_seconds) <= tolerance for g in gaps), gaps
        return actual
    # E3 on the Trig Locks page edits the stored patch value as well (M-REC-PARAM-001), so
    # unlocked steps recall 64 in both slots. Recording shows where locks changed: slot 1
    # step 3's 96 becomes 64; slot 2 keeps 24 and 96.
    live = run([([24, 64, 64, 64], 63), ([24, 64, 96, 64], 64), ([24, 64, 64, 64], 64), ([24, 64, 96, 64], 64)], edit=True)
    c.tap(2, 8)                                                    # disarm
    # A distinct stored patch value separates recorded locks from recalls on replay.
    c.tap(6, 8); c.tap(1, 1); c.tap(3, 8); c.screen_header('Ch. 1 Trig Locks', selected=2); c.enc(3, 1)
    replay = run([([24, 64, 64, 64], 65), ([24, 65, 96, 65], 65), ([24, 64, 64, 64], 65), ([24, 65, 96, 65], 65)])
    c.results.append(dict(kind='recording-lock-across-song-transition', live=live, replay=replay,
                          slot1_locks=[24, 64, 64, 64], slot2_locks=[24, None, 96, None], passed=True))
    if not persist: return
    # The combined state survives an idle autosave and a cold restart (SAVE-AUTO): the
    # recorded slot 1 locks, the copied slot 2 and the stored patch 65. Tempo is norns system
    # state (clock_tempo has save=false, outside the script pset); a cold emulator process
    # starts from fresh norns state, so the restored replay runs at the tempo it reports.
    from driver import Driver
    before = {p.name: p.stat().st_mtime_ns for p in c.data_directory.glob('autosave.*')}
    for _ in range(3): c.elapse(21)
    c.wait(lambda _: all((c.data_directory/n).is_file() and (c.data_directory/n).stat().st_mtime_ns != before.get(n)
                         for n in ('autosave.ptn', 'autosave.pset')))
    c.finish()
    out = c.out/'restarted'; out.mkdir()
    d = Driver(out, project_seed=c.data_directory, **c.launch_options)
    d.tap(6, 8); d.tap(1, 1); d.tap(3, 8)
    tempo = d.snapshot()['diagnostics']['tempo']
    restored = run([([24, 64, 64, 64], 65), ([24, 65, 96, 65], 65), ([24, 64, 64, 64], 65), ([24, 65, 96, 65], 65)], c=d, step_seconds=15/tempo)
    d.results.append(dict(kind='recording-lock-across-song-transition-restored', replay=restored, restored_tempo=tempo, passed=True))
    d.finish()
    c.results.append(dict(kind='recording-lock-across-song-transition-restored', replay=restored, restored_tempo=tempo, passed=True))
