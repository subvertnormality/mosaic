"""Channel page scale slots row (cheat sheet: "Displays currently active scale slot")."""

def row(lit):return [15 if n==lit else 2 for n in range(1,17)]

def channel_active_scale_display(c):
    ui = c.ui
    def shows(stage,lit):
        ui.expect_leds({("scale_slot", n): ("selected" if n == lit else "off") for n in range(1,17)})
        c.results.append(dict(kind='channel-scale-row',stage=stage,lit=lit,passed=True))
    def edit_root(semitones):ui.turn(2,-1);ui.set_value(semitones);ui.press_key(3);ui.turn(2,1)
    ui.configure()
    # Slot 2: D major (applied). Slot 3: E major, used only by a step-3 lock.
    ui.tap_control('scale_editor');ui.tap_control('scale_slot',3);edit_root(4);ui.tap_control('scale_slot',2);edit_root(2)
    ui.tap_control('channel_editor');shows('stopped-applied-slot-2',2)
    with ui.hold_step(3):
        ui.tap_control('scale_slot',3)
    shows('stopped-after-step-lock',2)
    # Degrees I..IV in D major 62/64/66/67. The step-3 lock selects E major (III = G# 68)
    # and, with "Scales lock until ptn end" at its default On, holds until the
    # channel wraps, so step 4 is E major IV (A 69) and the display keeps slot 3.
    marker=c.snapshot()['midi_count'];ui.play()
    shows('playing-slot-2',2);shows('playing-step-3-slot-3',3);shows('playing-back-to-slot-2',2)
    ui.stop();c.wait(lambda s:not s['midi_capture']['outstanding'])
    notes=[m['bytes'] for m in c.snapshot()['midi'] if m['index']>marker and m['bytes'][0]==144 and m['bytes'][2]>0]
    phrase=[[144,n,v] for n,v in [(62,127),(64,117),(68,107),(69,97)]]
    assert len(notes)>=4 and notes==[phrase[i%4] for i in range(len(notes))],notes
    shows('stopped-restored-slot-2',2)
    # Global scale off (long press on the applied slot): no slot lit while stopped;
    # while playing only the locked step lights its slot.
    ui.scale_editor()
    ui.gesture([('scale_slot', 2)], [])
    try:
        c.elapse(1.1)
    finally:
        ui.gesture([], [('scale_slot', 2)])
    c.elapse(.06);ui.menu('channel_editor');shows('stopped-global-off',None)
    ui.play();shows('playing-global-off-step-3',3);shows('playing-global-off-unlocked',None)
    ui.stop();c.wait(lambda s:not s['midi_capture']['outstanding']);shows('stopped-global-off-again',None)
