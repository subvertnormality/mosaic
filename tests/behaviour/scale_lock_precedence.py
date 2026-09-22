"""Channel versus global scale locks and "Scales lock until ptn end" (README Scale Locks, MAN option).

Slots: 2 D major (applied), 3 E major, 4 G major. Channel 1 plays degrees
I..IV on steps 1-4; the scale track is also 4 steps, so every cycle repeats.
A global lock sets slot 4 on scale-track step 2; a channel lock sets slot 3
on step 1. Pitches come from these independent interval tables.
"""
MAJOR=[0,2,4,5,7,9,11]
ROOT={2:62,3:64,4:67} # slot -> middle-C-octave root

def pitch(slot,degree):return ROOT[slot]+MAJOR[degree]
VELOCITY=[127,117,107,97]

def scale_lock_precedence(c):
    ui=c.ui
    def edit_root(semitones):ui.turn(2,-1);ui.set_value(semitones);ui.press_key(3);ui.turn(2,1)
    def hold_slot(step,slot):
        with ui.hold_step(step):ui.tap_control('scale_slot',slot)
        c.elapse(.1)
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    def phrase(stage,slots):
        """slots[i] is the active slot for step i+1, or None for a silent step."""
        steps=[i+1 for i,s in enumerate(slots) if s]
        expected=[(1,[144,pitch(slots[s-1],s-1),VELOCITY[s-1]]) for s in steps]
        notes=c.playback(expected,cycles=2)
        for i,(a,b) in enumerate(zip(notes,notes[1:])):
            left=steps[i%len(steps)];right=steps[(i+1)%len(steps)]
            assert abs((b[field]-a[field])/1e9-((right-left)%4 or 4)/6)<=tolerance,(stage,i)
        c.results.append(dict(kind='scale-lock-precedence',stage=stage,slots=slots,pitches=[e[1][1] for e in expected],passed=True))
    c.configure()
    ui.scale_editor()
    with ui.hold_step(1):ui.tap_step(4)                     # scale track steps 1-4
    ui.tap_control('scale_slot',3);edit_root(4);ui.tap_control('scale_slot',4);edit_root(7);ui.tap_control('scale_slot',2);edit_root(2)
    hold_slot(2,4)                                           # global lock: step 2 -> G major
    ui.tap_control('channel_editor');hold_slot(1,3)          # channel lock: step 1 -> E major
    phrase('hold-on-channel-over-global',[3,3,3,3])
    ui.set_mosaic_option_keys([('scale_lock_until_pattern_end',False)])
    phrase('hold-off-next-trig-clears',[3,4,4,4])
    # A probability-rejected trig does not clear the channel lock.
    ui.turn(1,-3);ui.assign_trig_parameter_key('trig_probability')
    with ui.hold_step(2):
        c.elapse(.05);ui.encoder_event(3,-126);c.elapse(.15);ui.turn(3,1) # step 2 probability 0
    c.elapse(.15)
    phrase('hold-off-rejected-trig-keeps-lock',[3,None,4,4])
    with ui.hold_step(2):
        c.elapse(.05);ui.press_key(2)                        # clear step-2 trig locks
    c.elapse(.15)
    phrase('hold-off-probability-cleared',[3,4,4,4])
    # A rest (no trig on step 2) does not clear it either.
    ui.pattern_editor();ui.tap_control('pattern_select',1);ui.tap_step(2);ui.tap_control('channel_editor')
    phrase('hold-off-rest-keeps-lock',[3,None,4,4])
    ui.pattern_editor();ui.tap_control('pattern_select',1);ui.tap_step(2);ui.tap_control('channel_editor')
    # A new channel lock on step 3 replaces the old one and applies normally.
    hold_slot(3,2)
    phrase('hold-off-replacement',[3,4,2,4])
    ui.set_mosaic_option_keys([('scale_lock_until_pattern_end',True)])
    phrase('hold-on-replacement',[3,3,2,2])
