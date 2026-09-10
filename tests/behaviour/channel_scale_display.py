"""Channel page scale slots row (cheat sheet: "Displays currently active scale slot")."""

def row(lit):return [15 if n==lit else 2 for n in range(1,17)]

def channel_active_scale_display(c):
    cells=[(n,3) for n in range(1,17)]
    def shows(stage,lit):
        c.led_values(cells,row(lit));c.results.append(dict(kind='channel-scale-row',stage=stage,lit=lit,passed=True))
    def edit_root(semitones):c.enc(2,-1);c.enc(3,semitones);c.key(3);c.enc(2,1)
    c.configure()
    # Slot 2: D major (applied). Slot 3: E major, used only by a step-3 lock.
    c.tap(4,8);c.tap(3,3);edit_root(4);c.tap(2,3);edit_root(2)
    c.tap(3,8);shows('stopped-applied-slot-2',2)
    c.action(type='grid',x=3,y=4,state=1)
    try:c.tap(3,3)
    finally:c.action(type='grid',x=3,y=4,state=0)
    shows('stopped-after-step-lock',2)
    # Degrees I..IV in D major 62/64/66/67. The step-3 lock selects E major (III = G# 68)
    # and, with "Scales lock until ptn end" at its default On, holds until the
    # channel wraps, so step 4 is E major IV (A 69) and the display keeps slot 3.
    marker=c.snapshot()['midi_count'];c.tap(1,8)
    shows('playing-slot-2',2);shows('playing-step-3-slot-3',3);shows('playing-back-to-slot-2',2)
    c.tap(1,8);c.wait(lambda s:not s['midi_capture']['outstanding'])
    notes=[m['bytes'] for m in c.snapshot()['midi'] if m['index']>marker and m['bytes'][0]==144 and m['bytes'][2]>0]
    phrase=[[144,n,v] for n,v in [(62,127),(64,117),(68,107),(69,97)]]
    assert len(notes)>=4 and notes==[phrase[i%4] for i in range(len(notes))],notes
    shows('stopped-restored-slot-2',2)
    # Global scale off (long press on the applied slot): no slot lit while stopped;
    # while playing only the locked step lights its slot.
    c.tap(4,8)
    c.action(type='grid',x=2,y=3,state=1)
    try:c.elapse(1.1)
    finally:c.action(type='grid',x=2,y=3,state=0)
    c.elapse(.06);c.tap(3,8);shows('stopped-global-off',None)
    c.tap(1,8);shows('playing-global-off-step-3',3);shows('playing-global-off-unlocked',None)
    c.tap(1,8);c.wait(lambda s:not s['midi_capture']['outstanding']);shows('stopped-global-off-again',None)
