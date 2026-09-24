"""Finite generic CC parameter matrix with compact verified screen evidence."""
import json,base64,zlib,hashlib
from patch_params import open_patch_control,turn
def patch_cc_matrix(c):
    from cases import menu_label,menu_value
    open_patch_control(c);before=c.snapshot()['midi_count'];expected=[];frames=[]
    def value_frame(cc,value):
        menu_value(c,'X' if value==-1 else str(value))
        raw=base64.b64decode(c.observations[-1]['state']['frame']['pixels_base64'])
        frames.append(dict(cc=cc,value=value,sha256=hashlib.sha256(raw).hexdigest(),bgra_zlib_base64=base64.b64encode(zlib.compress(raw)).decode()))
        # Preserve every asserted framebuffer separately, not thousands of
        # copies of the growing MIDI tail. Full native MIDI remains exported.
        if len(c.observations)>4:del c.observations[2:-2]
    try:
        for cc in range(1,128):
            menu_label(c,'CC '+str(cc));value=-1;value_frame(cc,value)
            for delta in (-1,1,63,63,1,1,-63,-63,-2,-1):
                wanted=max(-1,min(127,value+delta));turn(c,delta)
                if wanted!=value and wanted!=-1:expected.append((1,[176,cc,wanted]))
                value=wanted;value_frame(cc,value)
                actual=[(e['port'],e['bytes']) for e in c.snapshot()['midi'] if e['index']>before]
                assert actual==expected,dict(cc=cc,value=value,expected=expected,actual=actual)
            if cc<127:c.enc(2,1)
        after=c.snapshot()['midi_count'];assert not c.snapshot()['midi_capture']['outstanding']
        c.finish()
        events=[json.loads(line) for line in (c.out/'native/native-events.jsonl').read_text().splitlines()]
        midi=[e for e in events if e.get('kind') in (3,11)]
        assert [e['sequence'] for e in midi]==list(range(1,len(midi)+1))
        assert [(e['port'],e['bytes']) for e in midi[before:after]]==expected
        assert not [e for e in midi[:before]+midi[after:] if e['bytes'][0]&240==176],'Unexpected CC outside authored edits'
        c.results.append(dict(kind='all-generic-cc-patch-boundaries',ccs=list(range(1,128)),values=[-1,0,1,63,64,126,127],below_above_bound_attempts=True,midi_messages=len(expected),screen_assertions=len(frames),passed=True))
    finally:
        (c.out/'patch-value-frames.json').write_text(json.dumps(frames,separators=(',',':'))+'\n')
        (c.out/'results.json').write_text(json.dumps(c.results,indent=2)+'\n')
