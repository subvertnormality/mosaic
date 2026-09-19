"""MIDI-mapped mask, trig-param and memory controls act like their page controls
(README "MIDI Controller Mapping", line 211: "Trig params, masks and channel memory are
all able to be mapped to your MIDI device", with the documented relative map settings).

The same edits are made in two sessions: once by mapped CCs (selected-channel note
mask +13, length mask +8, trig param slot 1 (CC 1) +2, memory -1 after two recorded
actions) and once with the page encoders. The played notes, CC 1 values and memory
position must match. Characterisation of equivalence, not of each control's values.
"""
import shutil, base64
from driver import Driver, REPO
from midi_mapping import pmap_line

MAP = [('sel_ch_note', 22), ('sel_ch_len', 23), ('sel_ch_trig_param_1', 24), ('sel_ch_memory', 25)]


def midi_mapping_targets(c):
    from cases import assign_trig_parameter
    from patch_params import open_patch_control, turn
    from cases import menu_value
    from frame_oracle import render
    c.configure(); c.finish()
    seed = c.out/'mapping-seed'; (seed/'config').mkdir(parents=True)
    shutil.copy(REPO/'tests/behaviour/config/emu-midi.json', seed/'config/emu-midi.json')
    (seed/'mosaic.pmap').write_text(''.join(pmap_line(param, cc) for param, cc in MAP))

    def session(label, mapped):
        out = c.out/label; out.mkdir()
        e = Driver(out, project_seed=seed, **c.launch_options)
        try:
            e.configure()
            open_patch_control(e, setup=False); turn(e, 63); turn(e, 1); menu_value(e, '63'); e.key(1)
            e.enc(1, -3); assign_trig_parameter(e, 'CC 1')
            e.enc(1, -1); e.screen_header('Ch. 1 Note Masks')
            for step, note in ((1, 72), (2, 76)):                  # two memory actions
                e.action(type='grid', x=step, y=4, state=1)
                try: e.action(type='midi', port=1, bytes=[144, note, 90]); e.elapse(.05); e.action(type='midi', port=1, bytes=[128, note, 0])
                finally: e.action(type='grid', x=step, y=4, state=0)
                e.elapse(.1)
            marker = e.snapshot()['midi_count']
            def cc(number, value, times):
                for _ in range(times): e.action(type='midi', port=1, bytes=[176, number, value]); e.elapse(.2)
            if mapped:
                cc(22, 65, 13); cc(23, 65, 8); cc(24, 65, 2); e.elapse(2.5); cc(25, 63, 1); e.elapse(2.5)
            else:
                e.enc(2, -5); e.enc(2, 1); e.enc(3, 13); e.enc(2, 2); e.enc(3, 8)   # Note, then Len
                e.enc(1, 1); e.screen_header('Ch. 1 Trig Locks', selected=2); e.enc(2, -10); e.enc(3, 2)
                e.enc(1, 1); e.screen_header('Ch. 1 Memory'); e.enc(3, -1)
            e.tap(3, 8); e.enc(1, -5); e.enc(1, 2); e.screen_header('Ch. 1 Memory')
            frame = base64.b64decode(e.snapshot()['frame']['pixels_base64'])
            counter = bytes(frame[(y*128+x)*4] for y in list(range(13, 26))+list(range(39, 52)) for x in range(16))
            edits = [m['bytes'] for m in e.snapshot()['midi'] if m['index'] > marker and m['bytes'][0] == 176]
            before = e.snapshot()['midi_count']; e.tap(1, 8); e.elapse(1.4); e.tap(1, 8)
            state = e.wait(lambda s: not s['midi_capture']['outstanding'])
            field = 'logical_ns' if e.clock_mode == 'controlled-experimental' else 'monotonic_ns'
            played = [m for m in state['midi'] if m['index'] > before and m['bytes'][0] in (144, 128, 176)]
            first = next(m[field] for m in played if m['bytes'][0] == 144)
            stream = [(round((m[field] - first) / 1e9, 2), m['bytes']) for m in played]
            e.results.append(dict(kind='mapping-target-session', mapped=mapped, edits=edits, stream=stream))
            return dict(edits=edits, stream=stream, counter=counter)
        finally: e.finish()

    mapped, encoders = session('mapped', True), session('encoders', False)
    assert mapped['edits'] == encoders['edits'], dict(mapped=mapped['edits'], encoders=encoders['edits'])
    assert mapped['counter'] == encoders['counter'], 'Memory position differs'
    notes = lambda r: [b for _, b in r['stream'] if b[0] == 144]
    assert notes(mapped) and notes(mapped) == notes(encoders), dict(mapped=notes(mapped), encoders=notes(encoders))
    if c.clock_mode == 'controlled-experimental':
        assert mapped['stream'] == encoders['stream'], 'Timed note/CC streams differ'
    c.results.append(dict(kind='midi-mapping-targets', targets=[p for p, _ in MAP], notes=[b[1] for b in notes(mapped)][:8], passed=True))
