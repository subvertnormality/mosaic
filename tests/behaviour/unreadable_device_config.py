"""One device config entry that cannot be opened (README 170-179 setup; user decision
2026-09-11 on suspected defect S7: skip an unreadable file and load the rest).

README 174-177: copy the device configuration files into `data > mosaic > config`; "Mosaic
will automatically load the device configurations you've selected, and they will be available
in the device picker on the channel page." The user decided that one file Mosaic cannot open
(for example a broken symlink) is skipped and every other configuration still loads.

The project seed cannot hold a dangling symlink: the emulator's seed copy follows links and
refuses one whose target is missing. The seeded config folder therefore holds a file whose
name spans a line break ("mm-broken" newline "mm-missing.json"). Mosaic lists the folder one
name per line, so it is offered an entry "mm-missing.json" that does not exist, and opening
it fails exactly as opening a broken symlink does (no such file). Next to it are the valid
emulator test device (listed before it) and a valid custom config (listed after it).
"""
from device_configs import VALID, boot_with, picker_names

AFTER = 'Zz Custom Poly'
FILES = {'mm-broken\nmm-missing.json': '[{"name": "Unreachable", "id": "unreachable", "type": "midi", "params": []}]',
         'zz-custom.json': '[{"name": "%s", "id": "zz-custom", "type": "midi", "polyphonic": true, "params": []}]' % AFTER}


def unreadable_device_config(c):
    c.configure(); c.finish()
    # Baseline: this boot raises "Cannot open file: .../mm-missing.json" from device loading and
    # Mosaic never starts (the defect). (README 177; user decision S7)
    e = boot_with(c, 'unreadable', FILES)
    try:
        e.configure()  # the ordinary workflow on the valid emulator test device (README 177)
        e.playback([(1, [144, n, v]) for n, v in [(60, 127), (62, 117), (64, 107), (65, 97)]])
        names = picker_names(e, [VALID, 'CC Device', AFTER, 'Unreachable'])
        # Both valid configurations, before and after the unreadable entry, are offered, and the
        # unopenable entry is not (README 177; user decision S7: skip it and load the rest).
        assert VALID in names and AFTER in names and 'Unreachable' not in names, ('Picker entries', names)
        e.results.append(dict(kind='device-config-discovery', scenario='unreadable', picker=names, passed=True))
    finally: e.finish()
    c.results.append(dict(kind='device-config-session', scenario='unreadable', passed=True))
