"""Syntakt Sustain and Sostenuto trig parameters (the Syntakt device configuration maps
them to CC 64 and CC 66, the MIDI 1.0 sustain and sostenuto controllers; README 546: "all
CC parameters are accessible for editing ... Any other value entered will send that MIDI
value directly to your MIDI device").

Syntakt on channel 1. Each parameter is assigned to trig-parameter slot 1 on the Trig Locks
page and E3 is turned up five detents: the value must change on screen and the channel's
output must receive CC 64 (or 66) with increasing values and no NRPN. Mute, an NRPN
parameter of the same device, is the control.
"""
import shutil
from driver import Driver, REPO


def syntakt_pedal_params(c):
    from elektron_program_changes import pick_device
    from cases import parameter_list_label
    seed = c.out/'seed'; (seed/'config').mkdir(parents=True)
    shutil.copy(REPO/'tests/behaviour/config/emu-midi.json', seed/'config/emu-midi.json')
    shutil.copy(REPO/'lib/config/elektron_syntakt.json', seed/'config/elektron_syntakt.json')
    c.configure(); c.finish()
    out = c.out/'syntakt'; out.mkdir()
    e = Driver(out, project_seed=seed, **c.launch_options)
    try:
        e.configure(); pick_device(e, 'Syntakt')
        e.enc(1, -3); e.screen_header('Ch. 1 Trig Locks', selected=2)

        def assign(label):
            e.key(2); e.enc(3, -150)
            for _ in range(150):
                if parameter_list_label(e, label, wait=False): break
                e.enc(3, 1)
            else: raise AssertionError('Parameter unavailable through native UI: ' + label)
            parameter_list_label(e, label); e.key(3); e.key(2)

        def turn(label):
            assign(label)
            before = e.snapshot()['midi_count']; frame0 = e.snapshot()['frame']['sha256']
            e.enc(3, 5); e.elapse(.3)
            s = e.snapshot()
            sent = [m['bytes'] for m in s['midi'] if m['index'] > before and m['bytes'][0] & 0xF0 == 0xB0]
            e.results.append(dict(kind='syntakt-param-turn', label=label, sent=sent, frame_changed=s['frame']['sha256'] != frame0))
            return sent, s['frame']['sha256'] != frame0

        sent, changed = turn('Mute')                              # control: NRPN parameter
        assert changed and any(b[1] == 99 for b in sent), ('Control parameter did not respond', sent)
        for label, cc in (('Sustain', 64), ('Sostenuto', 66)):
            sent, changed = turn(label)
            assert changed, (label + ' value did not change on screen', sent)
            values = [b[2] for b in sent if b[1] == cc]
            assert values and all(b[1] == cc for b in sent), (label + ' must send only CC %d' % cc, sent)
            assert values == sorted(values) and len(set(values)) == len(values), (label + ' values', values)
    finally: e.finish()
    c.results.append(dict(kind='syntakt-pedal-params', passed=True))
