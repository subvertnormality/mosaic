"""Fixed-channel mask maps and held steps (README 197-211: "channel parameters" control a
specific channel "regardless of which channel is selected"; arbitrated 2026-09-11,
fixed-map-ignores-held-steps, decisions.md SEM-017).

Channel 1 (selected, velocity mask 50) and channel 2 (port 2) play the same phrase.
With channel 1's step 2 held, the fixed channel-2 velocity map edits channel 2's
channel mask from its own value (X + 3 = 2); channel 1 is unchanged. A selected-channel
map with the same step held still edits channel 1's step 2 (50 + 2 = 52).
"""
import shutil
from driver import Driver, REPO
from midi_mapping import pmap_line


def midi_mapping_held_step(c):
    c.configure(); c.finish()
    seed = c.out/'mapping-seed'; (seed/'config').mkdir(parents=True)
    shutil.copy(REPO/'tests/behaviour/config/emu-midi.json', seed/'config/emu-midi.json')
    (seed/'mosaic.pmap').write_text(pmap_line('ch2_vel', 21) + pmap_line('sel_ch_vel', 20))
    out = c.out/'mapping'; out.mkdir()
    e = Driver(out, project_seed=seed, **c.launch_options)
    try:
        e.configure()
        e.tap(2, 1); e.enc(3, 1); e.enc(2, 1); e.enc(3, 1); e.enc(2, 1); e.enc(3, 1); e.key(3)
        e.tap(1, 2); e.hold_tap((1, 4), (4, 4)); e.tap(1, 1)        # channel 2 plays pattern 1 on port 2
        def velocities(stage, expected):
            marker = e.snapshot()['midi_count']; e.tap(1, 8); e.elapse(1.4); e.tap(1, 8)
            state = e.wait(lambda s: not s['midi_capture']['outstanding'])
            ons = [m for m in state['midi'] if m['index'] > marker and m['bytes'][0] in (144, 145) and m['bytes'][2] > 0]
            actual = {port: [m['bytes'][2] for m in ons if m['port'] == port][:4] for port in (1, 2)}
            assert actual == expected, (stage, actual, expected)
            e.results.append(dict(kind='mapping-held-step', stage=stage, velocities=actual, passed=True))
        def cc(number, times):
            for _ in range(times): e.action(type='midi', port=1, bytes=[176, number, 65]); e.elapse(.2)
        pattern = [127, 117, 107, 97]
        e.enc(1, -4); e.enc(2, -5); e.enc(2, 2); e.enc(3, 51)           # Note Masks, Vel: channel 1 mask 50
        velocities('channel-1-mask-50', {1: [50] * 4, 2: pattern})
        e.action(type='grid', x=2, y=4, state=1); e.elapse(.05)
        try: cc(21, 3)
        finally: e.action(type='grid', x=2, y=4, state=0)
        e.elapse(.1); velocities('fixed-map-with-held-step', {1: [50] * 4, 2: [2] * 4})
        e.action(type='grid', x=2, y=4, state=1); e.elapse(.05)
        try: cc(20, 2)
        finally: e.action(type='grid', x=2, y=4, state=0)
        e.elapse(.1); velocities('selected-map-with-held-step', {1: [50, 52, 50, 50], 2: [2] * 4})
    finally: e.finish()
    c.results.append(dict(kind='mapping-held-step-session', nested=str(out), passed=True))
