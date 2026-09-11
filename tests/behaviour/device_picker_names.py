"""Stock device names in the device picker (README 170: "Elektron Digitone, Digitakt 2,
Syntakt, and the Nord Drum 2 are first class citizens"; Digitakt and Digitakt 2 are
different devices, confirmed by the user 2026-09-11).

With the Digitakt, Digitakt 2 and Digitone configurations in the data config directory, the
Ch. 1 device picker, stepped from its first entry, shows None, CC Device, Digitakt,
Digitakt 2 and Digitone in that order, each name once (rendered name column of the frame).
"""
import base64, shutil
from driver import Driver, REPO

NAMES = ['None', 'CC Device', 'Digitakt', 'Digitakt 2', 'Digitone']


def device_picker_names(c):
    from frame_oracle import render
    seed = c.out/'seed'; (seed/'config').mkdir(parents=True)
    shutil.copy(REPO/'tests/behaviour/config/emu-midi.json', seed/'config/emu-midi.json')
    for f in ('elektron_digitakt.json', 'elektron_digitakt_2.json', 'elektron_digitone.json'):
        shutil.copy(REPO/'lib/config'/f, seed/'config'/f)
    c.configure(); c.finish()
    out = c.out/'picker'; out.mkdir()
    e = Driver(out, project_seed=seed, **c.launch_options)
    try:
        e.configure()
        indices = [(y*128+x)*4+k for y in range(27, 37) for x in range(10, 58) for k in range(3)]
        expected = {n: render([(10, 35, 15, n)]) for n in NAMES}
        e.enc(3, -40)
        seen = []
        for _ in range(len(NAMES)):
            pixels = base64.b64decode(e.snapshot()['frame']['pixels_base64'])
            hit = [n for n, ex in expected.items() if all(pixels[i] == ex[i] for i in indices)]
            seen.append(hit[0] if len(hit) == 1 else '?')
            e.enc(3, 1)
        e.results.append(dict(kind='device-picker-names', expected=NAMES, seen=seen))
        assert seen == NAMES, ('Device picker entries', seen)
    finally: e.finish()
    c.results.append(dict(kind='device-picker-names-summary', passed=True))
