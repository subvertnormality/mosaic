"""Stock device names in the device picker (README 170: "Elektron Digitone, Digitakt 2,
Syntakt, and the Nord Drum 2 are first class citizens"; Digitakt and Digitakt 2 are
different devices, confirmed by the user 2026-09-11).

With the Digitakt, Digitakt 2 and Digitone configurations in the data config directory, the
Ch. 1 device picker, stepped from its first entry, shows None, CC Device, Digitakt,
Digitakt 2 and Digitone in that order, each name once (the Device row's whole value on the live
Device screen).
"""
import shutil
from driver import Driver, REPO

NAMES = ['None', 'CC Device', 'Digitakt', 'Digitakt 2', 'Digitone']


def device_picker_names(c):
    seed = c.out/'seed'; (seed/'config').mkdir(parents=True)
    shutil.copy(REPO/'tests/behaviour/config/emu-midi.json', seed/'config/emu-midi.json')
    for f in ('elektron_digitakt.json', 'elektron_digitakt_2.json', 'elektron_digitone.json'):
        shutil.copy(REPO/'lib/config'/f, seed/'config'/f)
    c.configure(); c.finish()
    out = c.out/'picker'; out.mkdir()
    e = Driver(out, project_seed=seed, **c.launch_options)
    try:
        e.configure()
        # The Device screen (C05) shows the picked entry as its selected Device
        # row's whole value; each entry is identified exactly on that row.
        e.enc(3, -40)
        seen = []
        for _ in range(len(NAMES)):
            seen.append(e.ui.shown_device(NAMES))
            e.enc(3, 1)
        e.results.append(dict(kind='device-picker-names', expected=NAMES, seen=seen))
        assert seen == NAMES, ('Device picker entries', seen)
    finally: e.finish()
    c.results.append(dict(kind='device-picker-names-summary', passed=True))
