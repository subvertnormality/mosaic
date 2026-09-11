"""Keyboard step entry after a lost Note Off and a transport Stop (suspected defect S14,
bugs.json keyboard-chord-state-after-lost-release; human decision 2026-09-11: "reset
keyboard chord state on Stop").

README 193: "while holding the desired step, press the corresponding key on your
keyboard" enters that key's note on the step; README 601 adds chord voices by holding the
step and selecting each note of the chord. A key whose Note Off never arrives (its MIDI
port is removed while the key and the step are held, a native hotplug) keeps its chord
open. After a Play/Stop, holding step 1 and pressing one key must enter that key as the
step's note, not add it as a chord voice over the lost key.
"""

PHRASE = [(62, 117), (64, 107), (65, 97)]      # steps 2-4 from configure()


def keyboard_chord_after_stop(c):
    c.configure(); c.enc(1, -2); c.screen_header('Ch. 1 Memory')
    c.enc(1, -2); c.screen_header('Ch. 1 Note Masks', selected=1)

    def enter(note, lose_release=False):
        c.action(type='grid', x=1, y=4, state=1)
        try:
            c.action(type='midi', port=1, bytes=[144, note, 90]); c.elapse(.05)
            if lose_release: c.action(type='midi_connection', port=1, connected=False); c.elapse(.1)
            else: c.action(type='midi', port=1, bytes=[128, note, 0])
        finally: c.action(type='grid', x=1, y=4, state=0)
        c.elapse(.1)
        if lose_release: c.action(type='midi_connection', port=1, connected=True); c.elapse(.3)

    def step_one(stage, expected):
        # Play/Stop through the grid (README "Sequencer Start and Stop"); listen to step 1.
        marker = c.snapshot()['midi_count']; c.tap(1, 8); c.elapse(1.4); c.tap(1, 8)
        state = c.wait(lambda s: not s['midi_capture']['outstanding'])
        ons = [(m['port'], m['bytes']) for m in state['midi'] if m['index'] > marker and m['bytes'][0] == 144 and m['bytes'][2] > 0]
        loop = [(1, [144, *p]) for p in expected + PHRASE]
        wanted = [loop[i % len(loop)] for i in range(len(ons))]
        c.results.append(dict(kind='step-one-after-entry', stage=stage, expected=wanted, actual=ons))
        assert len(ons) >= len(loop) and ons == wanted, dict(stage=stage, expected=wanted, actual=ons)

    # README 193: a single key entered on held step 1 is its note. The lost release is
    # modelled by removing the input port before the key's Note Off.
    enter(72, lose_release=True)
    step_one('after-lost-release', [(72, 90)])      # this Play/Stop is the transport Stop under test
    # Human decision S14: Stop resets keyboard chord state, so the next single key on
    # step 1 is entered as the step's note (README 193), not as a chord voice over 72.
    enter(76)
    step_one('after-stop-next-entry', [(76, 90)])
    enter(79)
    step_one('after-stop-third-entry', [(79, 90)])
    c.results.append(dict(kind='keyboard-chord-after-stop-summary', passed=True))
