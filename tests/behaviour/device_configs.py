"""Device configuration discovery and invalid files (README setup, derived SETUP-DEVICE-INVALID).

Each seed is a project data directory whose config/ folder holds the files
under test next to the valid emulator test device. A bad file must not stop
Mosaic from booting and must not appear as a device; the valid device must
still work.
"""
import shutil
from driver import Driver,REPO

VALID='Emulator test device'

def boot_with(c,label,files,**options):
    seed=c.out/(label+'-seed');(seed/'config').mkdir(parents=True)
    shutil.copy(REPO/'tests/behaviour/config/emu-midi.json',seed/'config/emu-midi.json')
    for name,text in files.items():(seed/'config'/name).write_text(text)
    out=c.out/label;out.mkdir()
    return Driver(out,project_seed=seed,**dict(c.launch_options,**options))

CUSTOM={'ba-custom-drum.json':'[{"name": "Custom Drum", "id": "custom-drum", "type": "midi", "polyphonic": false, "default_midi_device": 2, "default_midi_channel": 10, "fixed_note": 36, "params": []}]',
        'bb-custom-poly.json':'[{"name": "Custom Poly", "id": "custom-poly", "type": "midi", "polyphonic": true, "default_midi_channel": 5, "params": []}]'}

def device_config_defaults(c):
    from elektron_program_changes import pick_device
    c.ui.configure();c.finish()
    e=boot_with(c,'defaults',CUSTOM)
    try:
        ui=e.ui
        ui.configure()
        pick_device(e,'Custom Drum') # defaults: port 2, MIDI channel 10, fixed note 36
        ui.select_channel(2);ui.expect_header('midi_config',channel=2)
        pick_device(e,'Custom Poly') # default MIDI channel 5; port from the selector (first output)
        ui.tap_control('pattern_slot',1);ui.set_range(1,4);ui.select_channel(1)
        marker=e.snapshot()['midi_count'];ui.play()
        state=e.wait(lambda s:sum(1 for m in s['midi'] if m['index']>marker and m['bytes'][0]&240==144 and m['bytes'][2]>0)>=16,timeout=4)
        ui.stop();e.wait(lambda s:not s['midi_capture']['outstanding'])
        ons=[(m['port'],m['bytes']) for m in state['midi'] if m['index']>marker and m['bytes'][0]&240==144 and m['bytes'][2]>0]
        velocity=[127,117,107,97]
        drum=[x for x in ons if x[0]==2];poly=[x for x in ons if x[0]==1]
        assert len(drum)>=8 and drum==[(2,[153,36,velocity[i%4]]) for i in range(len(drum))],('Custom Drum defaults',drum)
        assert len(poly)>=8 and poly==[(1,[148,[60,62,64,65][i%4],velocity[i%4]]) for i in range(len(poly))],('Custom Poly defaults',poly)
        assert len(drum)+len(poly)==len(ons),('Unexpected route',ons)
        e.results.append(dict(kind='device-config-defaults',drum=drum[:4],poly=poly[:4],passed=True))
    finally:e.finish()
    c.results.append(dict(kind='device-config-session',scenario='defaults',passed=True))
