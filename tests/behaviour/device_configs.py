"""Device configuration discovery and invalid files (README setup, derived SETUP-DEVICE-INVALID).

Each seed is a project data directory whose config/ folder holds the files
under test next to the valid emulator test device. A bad file must not stop
Mosaic from booting and must not appear as a device; the valid device must
still work.
"""
import base64,shutil
from driver import Driver,REPO

VALID='Emulator test device'

def picker_names(e,candidates):
    """Walk the device picker from its first entry and record which candidate is selected."""
    from frame_oracle import render
    patterns={name:render([(10,35,15,name)]) for name in candidates}
    indices=[(y*128+x)*4+k for y in range(27,37) for x in range(10,58) for k in range(3)]
    e.enc(3,-40);seen=[]
    for _ in range(len(candidates)+4):
        pixels=base64.b64decode(e.snapshot()['frame']['pixels_base64'])
        hit=[n for n,p in patterns.items() if all(pixels[i]==p[i] for i in indices)]
        if hit and (not seen or seen[-1]!=hit[0]):seen.append(hit[0])
        e.enc(3,1)
    e.key(2) # leave the pending device selection unconfirmed
    return seen

def boot_with(c,label,files):
    seed=c.out/(label+'-seed');(seed/'config').mkdir(parents=True)
    shutil.copy(REPO/'tests/behaviour/config/emu-midi.json',seed/'config/emu-midi.json')
    for name,text in files.items():(seed/'config'/name).write_text(text)
    out=c.out/label;out.mkdir()
    return Driver(out,project_seed=seed,**c.launch_options)

def invalid_device_configs(c,scenario):
    c.configure();c.finish()
    files={'malformed':{'aa-broken.json':'[{"name": "Broken", "id": ','ab-empty.json':'','ac-object.json':'{"name": "Object", "id": "object", "type": "midi", "params": []}'},
           'missing-id':{'aa-noid.json':'[{"name": "No Id", "type": "midi", "polyphonic": true, "params": []}]'}}[scenario]
    e=boot_with(c,scenario,files)
    try:
        e.configure() # full ordinary workflow on the valid configuration
        e.playback([(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107),(65,97)]])
        names=picker_names(e,[VALID,'CC Device','Broken','Object','No Id'])
        assert VALID in names and not {'Broken','Object','No Id'}&set(names),('Picker entries',names)
        e.results.append(dict(kind='device-config-discovery',scenario=scenario,picker=names,passed=True))
    finally:e.finish()
    c.results.append(dict(kind='device-config-session',scenario=scenario,passed=True))

CUSTOM={'ba-custom-drum.json':'[{"name": "Custom Drum", "id": "custom-drum", "type": "midi", "polyphonic": false, "default_midi_device": 2, "default_midi_channel": 10, "fixed_note": 36, "params": []}]',
        'bb-custom-poly.json':'[{"name": "Custom Poly", "id": "custom-poly", "type": "midi", "polyphonic": true, "default_midi_channel": 5, "params": []}]'}

def device_config_defaults(c):
    from elektron_program_changes import pick_device
    c.configure();c.finish()
    e=boot_with(c,'defaults',CUSTOM)
    try:
        e.configure()
        pick_device(e,'Custom Drum') # defaults: port 2, MIDI channel 10, fixed note 36
        e.tap(2,1);e.screen_header('Ch. 2 Device Config',selected=5)
        pick_device(e,'Custom Poly') # default MIDI channel 5; port from the selector (first output)
        e.tap(1,2);e.hold_tap((1,4),(4,4));e.tap(1,1)
        marker=e.snapshot()['midi_count'];e.tap(1,8)
        state=e.wait(lambda s:sum(1 for m in s['midi'] if m['index']>marker and m['bytes'][0]&240==144 and m['bytes'][2]>0)>=16,timeout=4)
        e.tap(1,8);e.wait(lambda s:not s['midi_capture']['outstanding'])
        ons=[(m['port'],m['bytes']) for m in state['midi'] if m['index']>marker and m['bytes'][0]&240==144 and m['bytes'][2]>0]
        velocity=[127,117,107,97]
        drum=[x for x in ons if x[0]==2];poly=[x for x in ons if x[0]==1]
        assert len(drum)>=8 and drum==[(2,[153,36,velocity[i%4]]) for i in range(len(drum))],('Custom Drum defaults',drum)
        assert len(poly)>=8 and poly==[(1,[148,[60,62,64,65][i%4],velocity[i%4]]) for i in range(len(poly))],('Custom Poly defaults',poly)
        assert len(drum)+len(poly)==len(ons),('Unexpected route',ons)
        e.results.append(dict(kind='device-config-defaults',drum=drum[:4],poly=poly[:4],passed=True))
    finally:e.finish()
    c.results.append(dict(kind='device-config-session',scenario='defaults',passed=True))
