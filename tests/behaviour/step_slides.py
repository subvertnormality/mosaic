"""Held-step K3 slides (README "Parameter slides" / step slides) beyond M-PATCH-033/034.

CC 1 locks: step 1 = 24, step 3 = 96, step 4 = 48; global slides stay off.
Only manual-stated properties are asserted: a toggled-off step slide jumps,
the last lock has nothing to slide to unless "Wrap param slides" is on, and
with wrap on it moves linearly to the wrapped first lock, arriving with it.
"""

def step_slide_variants(c):
    from cases import assign_trig_parameter,set_mosaic_options
    from patch_params import open_patch_control,turn
    from cases import menu_value
    open_patch_control(c);turn(c,63);turn(c,1);menu_value(c,'63');c.key(1)
    c.enc(1,-3);assign_trig_parameter(c,'CC 1')
    for step,value in [(1,24),(3,96),(4,48)]:
        c.action(type='grid',x=step,y=4,state=1)
        try:c.elapse(.05);c.action(type='enc',n=3,delta=-126);c.enc(3,value+1)
        finally:c.action(type='grid',x=step,y=4,state=0)
    def step_k3(step):
        c.action(type='grid',x=step,y=4,state=1)
        try:c.key(3)
        finally:c.action(type='grid',x=step,y=4,state=0)
        c.elapse(.1)
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    phrase=[(1,[144,n,v]) for n,v in ((60,127),(62,117),(64,107),(65,97))]
    def run():
        before=c.snapshot()['midi_count'];notes=c.playback(phrase,cycles=2)
        events=[m for m in c.snapshot()['midi'] if m['index']>before]
        return notes,events
    def between(events,a,b):return [m for m in events if a['index']<m['index']<b['index'] and m['bytes'][:2]==[176,1]]
    # 1) Toggle a step slide on and off: the source jumps straight to its destination.
    step_k3(1);step_k3(1)
    notes,events=run()
    for cycle in range(2):
        inner=[m['bytes'][2] for m in between(events,notes[4*cycle],notes[4*cycle+2])]
        assert not [v for v in inner if 24<v<96 and v!=63],('Toggled-off slide still interpolates',inner)
        arrival=[m for m in events if notes[4*cycle+1]['index']<m['index']<notes[4*cycle+2]['index'] and m['bytes'][:2]==[176,1]]
        assert arrival and arrival[-1]['bytes'][2]==96,('Destination lock missing',arrival)
    c.results.append(dict(kind='step-slide',stage='toggled-off-jumps',passed=True))
    # 2) A step slide on the last lock, wrap off: nothing to slide toward.
    step_k3(4)
    notes,events=run()
    for cycle in range(1):
        inner=[m['bytes'][2] for m in between(events,notes[4*cycle+3],notes[4*cycle+4])]
        assert not [v for v in inner if 24<v<48],('Last lock slid without wrap',inner)
        assert inner and inner[-1]==24,('First lock not recalled at wrap',inner)
    c.results.append(dict(kind='step-slide',stage='last-lock-no-wrap',passed=True))
    # 3) Wrap on: the last lock moves linearly to the wrapped first lock.
    # norns reopens the menu inside the patch group; return to its top level first.
    from cases import menu_label
    c.key(1);c.key(2);c.enc(2,-60);menu_label(c,'LEVELS >');c.key(2);c.key(1)
    set_mosaic_options(c,[('Wrap param slides',True)])
    notes,events=run()
    samples=[]
    for cycle in range(1):
        source,destination=notes[4*cycle+3],notes[4*cycle+4]
        ramp=between(events,source,destination);duration=(destination[field]-source[field])/1e9
        assert abs(duration-1/6)<=tolerance
        assert len(ramp)>=3 and ramp[-1]['bytes'][2]==24,('Wrapped slide ramp',[m['bytes'][2] for m in ramp])
        values=[m['bytes'][2] for m in ramp]
        assert values==sorted(values,reverse=True) and not any(v>48 for v in values),values
        for m in ramp:
            elapsed=(m[field]-source[field])/1e9
            ideal=48-24*max(0,min(1,elapsed/duration))
            assert abs(m['bytes'][2]-ideal)<=1+24/duration*tolerance,(m['bytes'][2],ideal,elapsed)
            samples.append(dict(value=m['bytes'][2],ideal=round(ideal,3),elapsed=round(elapsed,6)))
        assert abs((ramp[-1][field]-destination[field])/1e9)<=tolerance,'Wrapped destination not with its note'
    c.results.append(dict(kind='step-slide',stage='last-lock-wraps',samples=samples,passed=True))
