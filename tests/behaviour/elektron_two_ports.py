"""Elektron program changes with two Elektron devices on different MIDI ports (README
"Elektron Program Changes": "your Elektron devices will automatically adjust their
patterns ... each song pattern change on Mosaic mirrored by your Elektron devices").

Channel 1 plays a Digitakt on port 1. Channel 2 uses the repository's Syntakt
configuration with its default MIDI device set to 2 (Second MIDI), as a user
configures it. With Elektron program changes On, selecting slot 2 then slot 1 while
stopped must reach each device on its own port, once per change, on channel 10.
"""
import json, shutil
from driver import Driver, REPO


def elektron_two_ports(c):
    from cases import set_mosaic_options
    from elektron_program_changes import pick_device, program_changes
    seed = c.out/'elektron-seed'; (seed/'config').mkdir(parents=True)
    shutil.copy(REPO/'tests/behaviour/config/emu-midi.json', seed/'config/emu-midi.json')
    shutil.copy(REPO/'lib/config/elektron_digitakt.json', seed/'config/elektron_digitakt.json')
    syntakt = json.loads((REPO/'lib/config/elektron_syntakt.json').read_text())
    for device in (syntakt if isinstance(syntakt, list) else [syntakt]): device['default_midi_device'] = 2
    (seed/'config/elektron_syntakt.json').write_text(json.dumps(syntakt))
    c.configure(); c.finish()
    out = c.out/'elektron-two-ports'; out.mkdir()
    e = Driver(out, project_seed=seed, **c.launch_options)
    try:
        e.configure(); pick_device(e, 'Digitakt')
        e.tap(2, 1); e.screen_header('Ch. 2 Device Config', selected=5); pick_device(e, 'Syntakt')
        e.tap(1, 1)
        e.tap(6, 8); e.hold_tap((1, 1), (2, 1)); e.tap(1, 1)        # slot 2 = copy of slot 1
        set_mosaic_options(e, [('Elektron program changes', True)])
        marker = e.snapshot()['midi_count']; e.tap(2, 1); e.elapse(.2); e.tap(1, 1); e.elapse(.2)
        sent = sorted(program_changes(e.snapshot(), marker))
        expected = sorted([(1, [201, 1]), (2, [201, 1]), (1, [201, 0]), (2, [201, 0])])
        e.results.append(dict(kind='elektron-two-ports', expected=expected, actual=sent))
        assert sent == expected, dict(expected=expected, actual=sent)
    finally: e.finish()
    c.results.append(dict(kind='elektron-two-ports', nested=str(out), passed=True))
