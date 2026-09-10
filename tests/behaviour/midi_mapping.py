"""Mosaic MIDI mapping through the native norns parameter map (README "MIDI Controller Mapping").

The map is supplied as the project's saved PMAP with the documented settings
(input 1..2, output -1..1, accumulation on); entering it through the norns
menu is SETUP-MIDI-MAP-ENTRY and is not claimed here. Inputs are relative
binary-offset CCs on the emulator MIDI input; outputs are note velocities.
"""
import shutil
from driver import Driver,REPO

def pmap_line(param,cc,value=2):
    return '"%s":"{cc=%d, ch=1, dev=1, in_lo=1, in_hi=2, out_lo=-1, out_hi=1, accum=true, echo=false, value=%d}"\n'%(param,cc,value)

def midi_mapping(c):
    c.configure();c.finish()
    seed=c.out/'mapping-seed';(seed/'config').mkdir(parents=True)
    shutil.copy(REPO/'tests/behaviour/config/emu-midi.json',seed/'config/emu-midi.json')
    # Upper accumulator position: the next increase maps to +1, as after any increase.
    (seed/'mosaic.pmap').write_text(pmap_line('sel_ch_vel',20)+pmap_line('ch2_vel',21))
    out=c.out/'mapping';out.mkdir()
    e=Driver(out,project_seed=seed,**c.launch_options)
    try:
        e.configure()
        # Channel 2 on port 2 / MIDI channel 2 playing pattern 1 over steps 1-4.
        e.tap(2,1);e.enc(3,1);e.enc(2,1);e.enc(3,1);e.enc(2,1);e.enc(3,1);e.key(3)
        e.tap(1,2);e.hold_tap((1,4),(4,4));e.tap(1,1)
        def cc(number,value):e.action(type='midi',port=1,bytes=[176,number,value]);e.elapse(.2) # slower than the 0.15 s acceleration window
        def velocities(stage,expected):
            marker=e.snapshot()['midi_count'];e.tap(1,8)
            state=e.wait(lambda s:sum(1 for m in s['midi'] if m['index']>marker and m['bytes'][0] in (144,145) and m['bytes'][2]>0)>=8,timeout=4)
            e.tap(1,8);e.wait(lambda s:not s['midi_capture']['outstanding'])
            ons=[m for m in state['midi'] if m['index']>marker and m['bytes'][0] in (144,145) and m['bytes'][2]>0]
            for port,wanted in expected.items():
                seen=[m['bytes'][2] for m in ons if m['port']==port]
                assert seen and all(v==(wanted[i%4] if isinstance(wanted,list) else wanted) for i,v in enumerate(seen)),(stage,port,seen,wanted)
            e.results.append(dict(kind='midi-mapping',stage=stage,expected=expected,passed=True))
        pattern=[127,117,107,97]
        velocities('unmapped',{1:pattern,2:pattern})
        # Selected channel 1: from Off, eleven increases give velocity mask 10; two decreases give 8.
        for _ in range(11):cc(20,65)
        velocities('selected-ch1-plus-11',{1:10,2:pattern})
        cc(20,63);cc(20,63);velocities('selected-ch1-minus-2',{1:8,2:pattern})
        # Selection moves the selected-channel map to channel 2; channel 1 keeps 8.
        e.tap(2,1);cc(20,65);cc(20,65);cc(20,65);velocities('selected-ch2-plus-3',{1:8,2:2})
        # The fixed channel-2 map ignores selection.
        e.tap(1,1);cc(21,65);cc(21,65);velocities('fixed-ch2-plus-2',{1:8,2:4})
        cc(21,0);velocities('fixed-ch2-value-0-decreases',{1:8,2:3})
    finally:e.finish()
    c.results.append(dict(kind='midi-mapping-session',nested=str(out),passed=True))
