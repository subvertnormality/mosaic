"""Literal clock-rate rendering and NAV-TRANSPORT patch contracts.
README: Param Slides, clock edits and transport; exact pixels are characterisation.
"""
import json
from patch_params import open_patch_control, turn

def patch_slide_live_division(c,type_switch=False,reset=False,repeated_edits=False):
    assert not (type_switch and reset)
    """Queued /3 -> /6 edit crosses an active slide at the pattern boundary."""
    import math
    from cases import menu_value,assign_trig_parameter
    from frame_oracle import header,matches
    if reset:
        c.configure();c.ui.set_mosaic_options([('Song mode',True),('Reset on pattern repeat',True),('Wrap param slides',True)])
    open_patch_control(c,setup=not reset);turn(c,63);turn(c,1);menu_value(c,'63');c.key(1)
    c.ui.turn(1, -3);assign_trig_parameter(c,'CC 1')
    for step,value in [(4 if reset else 1,24),(3,96)]:
        c.action(type='grid',x=step,y=4,state=1)
        try:
            c.elapse(.05);c.action(type='enc',n=3,delta=-126);c.enc(3,value+1)
        finally:c.action(type='grid',x=step,y=4,state=0)
    c.key(3)
    c.ui.turn(1, 2);c.wait(lambda state:matches(state,header('Ch. 1 Clocks',selected=4)))
    c.enc(3,-4);c.key(3) # Initial /3 (index17), committed while stopped.
    if type_switch:
        # Store Heavy6 at100%, then return to Swing before playback.
        c.enc(2,1);c.enc(3,2);c.key(3)
        c.enc(2,1);c.enc(3,3);c.key(3)
        c.enc(2,1);c.enc(3,4);c.key(3)
        c.enc(2,1);c.enc(3,100);c.key(3)
        c.enc(2,-3);c.enc(3,-1);c.key(3)
    before=c.snapshot()['midi_count']
    c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
    c.enc(3,1 if type_switch else -4) # Queue Shuffle, or /3 index17 -> /6 index21.
    c.key(3)
    if repeated_edits:
        assert not type_switch and not reset
        # Several confirmed edits queue before the same global boundary.
        # /6 -> /4 -> /6 -> /4 -> /6: only final /6 governs future onsets.
        for delta in (1,-1,1,-1):
            c.enc(3,delta);c.key(3)
    import base64
    from frame_oracle import render
    label='Shuffle' if type_switch else '/6'
    xpos=70 if type_switch else 0
    expected_rate=render([(xpos,26,15,label)])
    pixels=[(y*128+x)*4+k for y in range(20,30) for x in range(xpos,128 if type_switch else 48) for k in range(3)]
    def rate_readback(state):
        frame=base64.b64decode(state['frame']['pixels_base64'])
        return all(frame[i]==expected_rate[i] for i in pixels)
    c.wait(rate_readback)
    c.results.append(dict(kind='clock-rate-readback',value=label,passed=True))
    def notes(state):
        return [e for e in state['midi'] if e['index']>before and e['bytes'][0]==144 and e['bytes'][2]>0]
    c.wait(lambda state:len(notes(state))>=(25 if reset else 23),timeout=15)
    c.elapse(.12)
    after=c.snapshot()['midi_count']
    c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
    c.wait(lambda state:not state['midi_capture']['outstanding']);c.finish()
    checks=[]
    try:
        all_events=[json.loads(line) for line in (c.out/'native/native-events.jsonl').read_text().splitlines()]
        events=[e for e in all_events if e.get('kind') in (3,11)][before:after]
        onsets=[e for e in events if e['bytes'][0]==144 and e['bytes'][2]>0]
        assert len(onsets)>=(25 if reset else 23)
        for i,note in enumerate(onsets):
            slot=(i-22)%4 if reset and i>=22 else i%4
            assert (note['port'],note['bytes'])==(1,[144,(60,62,64,65)[slot],(127,117,107,97)[slot]])
        controlled=c.clock_mode!='real-time';field='logical_ns' if controlled else 'monotonic_ns'
        start=onsets[0][field]
        # The default64-step global pattern commits queued controls at1536
        # pulses. Channel /3 starts steps1,2,3 at1440,1512,1584 before editing.
        # At1536 the remaining48 pulses stretch to96: destination becomes1632.
        effective_pulse=1536
        source_pulse=1368 if reset else 1440
        target_pulse=1824 if reset else (1568 if type_switch else 1632)
        source_index=19 if reset else 20
        target_index=24 if reset else 22
        tolerance=2e-9 if controlled else .01
        for index,note in enumerate(onsets):
            pulse=index*72 if index<=21 else (1536+(index-22)*144 if reset else target_pulse+(index-22)*(48 if type_switch else 144))
            assert abs((note[field]-start)/1e9-pulse/144)<=tolerance,dict(index=index,expected_pulse=pulse,actual=(note[field]-start)*144/1e9)
        ramp=[e for e in events if onsets[source_index]['sequence']<e['sequence']<onsets[target_index]['sequence'] and e['bytes'][:2]==[176,1]]
        assert len(ramp)>=4
        value_at_edit=80 if reset else 72
        old_duration=216 if reset else 144
        for event in ramp:
            pulse=(event[field]-start)*144/1e9
            ideal=24+72*(pulse-source_pulse)/old_duration if pulse<=effective_pulse else value_at_edit+(96-value_at_edit)*(pulse-effective_pulse)/(target_pulse-effective_pulse)
            error=abs(event['bytes'][2]-ideal)
            checks.append(dict(pulse=pulse,value=event['bytes'][2],ideal=ideal,error=error))
            assert error<=1+216*tolerance,checks[-1]
        assert ramp[-1]['bytes'][2]==96
        assert abs((ramp[-1][field]-onsets[target_index][field])/1e9)<=tolerance
        c.results.append(dict(kind='live-slide-rate-edit',type_switch=type_switch,reset=reset,repeated_edits=repeated_edits,edit_pulse=effective_pulse,source_pulse=source_pulse,target_pulse=target_pulse,checks=checks,passed=True))
    finally:
        c.results.append(dict(kind='live-slide-rate-samples',checks=checks))
        (c.out/'results.json').write_text(json.dumps(c.results,indent=2)+'\n')


def patch_slide_live_division_type_switch(c):
    return patch_slide_live_division(c, type_switch=True)


def patch_slide_live_division_reset(c):
    return patch_slide_live_division(c, reset=True)


def patch_slide_live_division_repeated_edits(c):
    return patch_slide_live_division(c, repeated_edits=True)


def patch_slide_stop_restarts(c):
    from patch_params import patch_slide_timing
    return patch_slide_timing(c, stop_restarts=3)
