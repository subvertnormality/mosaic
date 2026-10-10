"""Native scale-slot ownership and highest-slot lock precedence."""
def scale_slot_matrix(c):
    from cases import assert_durations
    ui = c.ui
    ui.configure(); ui.scale_editor(); ui.turn(2, -1)
    def selected(slot, applied):
        ui.expect_scale_slot_header(slot)
        ui.expect_leds({
            ("scale_slot", n): (
                "selected" if n == applied else
                "blink_low" if n == slot else "off"
            ) for n in range(1, 17)
        })
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    def verify(pitches,label):
        notes=c.playback([(1,[144,p,v]) for p,v in zip(pitches,[127,117,107,97])],cycles=2,timeout=4)
        assert_durations(c,notes,[1]*8)
        for i,note in enumerate(notes):assert abs((note[field]-notes[0][field])/1e9-i/6)<=tolerance
        c.results.append(dict(kind='scale-slot-matrix',stage=label,pitches=pitches,passed=True))
    # Adjacent slots use distinct chromatic roots; slots 13..16 repeat roots
    # but are edited and read independently in reverse order as well.
    roots=[0,1,2,3,4,5,6,7,8,9,10,11,0,1,2,3]
    for slot,root in enumerate(roots,1):
        with ui.hold_keys(1):
            c.elapse(.3); ui.tap_control('scale_slot',slot)
        selected(slot,1)
        if root: ui.set_value(root)
        ui.press_key(3); selected(slot,1)
        verify([60,62,64,65],'edit-only-slot-'+str(slot))
    applied=1
    for order in [list(range(1,17)),list(range(16,0,-1))]:
        for slot in order:
            if slot==applied:
                ui.tap_control('scale_slot',slot); selected(slot,0)
                verify([60,61,62,63],'short-reselect-disables-slot-'+str(slot))
            ui.tap_control('scale_slot',slot); selected(slot,slot); applied=slot
            root=roots[slot-1]
            verify([60+root,62+root,64+root,65+root],'apply-slot-'+str(slot))
    # Highest global and channel scale references must use their own saved
    # settings, persist for the stated lifetime, and clear independently.
    ui.hold_control_tap('step','scale_slot',held_index=1,target_index=16); ui.menu('channel_editor')
    ui.hold_control_tap('step','channel_scale_slot',held_index=2,target_index=15)
    verify([63,64,66,67],'global16-channel15-precedence')
    ui.hold_control_tap('step','channel_scale_slot',held_index=2,target_index=15)
    verify([63,65,67,68],'clear-channel15-reveals-global16')
    ui.scale_editor(); ui.hold_control_tap('step','scale_slot',held_index=1,target_index=16)
    verify([60,62,64,65],'clear-global16-restores-default1')
    selected(1,1)
