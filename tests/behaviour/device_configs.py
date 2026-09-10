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
