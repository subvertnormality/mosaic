"""Raw device-picker rendering contracts for invalid configuration discovery."""
from device_configs import VALID,boot_with


def picker_names(e,candidates):
    """Walk the device picker and identify entries by the selected Device row
    of the live Device screen (C05), whose whole value is the entry's name."""
    e.enc(3,-40);seen=[]
    for _ in range(len(candidates)+4):
        hit=e.ui.shown_device(candidates)
        if hit!='?' and (not seen or seen[-1]!=hit):seen.append(hit)
        e.enc(3,1)
    e.key(2) # leave the pending device selection unconfirmed
    return seen


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


def malformed_device_configs(c):
    return invalid_device_configs(c, 'malformed')


def missing_id_device_configs(c):
    return invalid_device_configs(c, 'missing-id')
