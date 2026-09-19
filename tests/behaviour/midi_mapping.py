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

def midi_map_entry(c):
    """Create the documented map through the native norns menu, then use it."""
    from cases import menu_label
    from frame_oracle import selected_line
    c.configure()
    def hold_k1(n):
        c.action(type='key',n=1,state=1)
        try:c.elapse(.4);c.key(n) # menu receives K1 after its 0.25 s threshold
        finally:c.action(type='key',n=1,state=0)
        c.elapse(.1)
    c.key(1);c.enc(1,4);c.key(3);menu_label(c,'LEVELS >')
    position=next(i for i,v in enumerate(c.snapshot()['diagnostics']['parameter_roots']) if v['id']=='mosaic_mask_midi_maps')
    c.enc(2,position);c.key(3)
    for _ in range(12):
        if selected_line(c.snapshot(),'Selected Ch. Velocity',top=23) or selected_line(c.snapshot(),'Selected Ch. Velocity'):break
        c.enc(2,1)
    else:raise AssertionError('Mapping parameter not reached')
    hold_k1(3)          # EDIT -> MAP mode
    c.key(3)            # open the parameter's map editor on "learn"
    c.key(3)            # arm learn
    c.action(type='midi',port=1,bytes=[176,20,63]);c.elapse(.2) # learned CC 20 (consumed by learn)
    c.enc(2,5);c.enc(3,1)      # in lo 0 -> 1
    c.enc(2,1);c.enc(3,-125)   # in hi 127 -> 2
    c.enc(2,3);c.enc(3,1)      # accum yes
    c.key(2)                   # assign and write the PMAP
    hold_k1(3)                 # back to EDIT mode
    c.key(2);c.key(2);c.key(1) # leave the group and the menu
    pmap=(c.data_directory/'mosaic.pmap').read_text()
    line=[l for l in pmap.splitlines() if l.startswith('"sel_ch_vel"')]
    assert len(line)==1 and all(t in line[0] for t in ('cc=20','ch=1','dev=1','in_lo=1','in_hi=2','accum=true')),pmap
    c.results.append(dict(kind='pmap-entry',line=line[0],passed=True))
    def cc(value):c.action(type='midi',port=1,bytes=[176,20,value]);c.elapse(.2)
    # A fresh map starts below its input range; begin with a decrease (Off stays Off),
    # then five increases reach velocity mask 4 and one decrease gives 3.
    cc(63)
    for _ in range(5):cc(65)
    marker=c.snapshot()['midi_count']
    c.playback([(1,[144,n,4]) for n in (60,62,64,65)])
    cc(63);c.playback([(1,[144,n,3]) for n in (60,62,64,65)])
    c.results.append(dict(kind='pmap-entry-control',velocities=[4,3],passed=True))
