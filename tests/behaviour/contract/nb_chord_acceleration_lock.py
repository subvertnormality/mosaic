"""A Chord Accel Mod step lock on a channel routed to an n.b. device (user decision 2026-09-11
on suspected defect S47: fix; reproduce in the nb-audio profile).

README 542: n.b. devices are picked from the device picker. README 749-756 and 937-940: a
trig parameter is assigned to a slot with K2, and holding a step while turning E3 locks its
value to that step. README 807-809: Chord Acceleration is a sequencer parameter that changes
the spacing of an enabled Strum or Arpeggio. Channel 1 plays the Doubledecker n.b. voice; slot
1 is replaced by Chord Accel Mod and step 1 is locked to +2. Playing across the locked step
must not raise a Lua error (the driver fails on native errors). The baseline passes the lock to
norns as a parameter named "chord_acceleration", which norns does not have, and raises
"invalid paramset index" at the locked step. The emulator does not expose Doubledecker's
sound, so the acceleration itself is not asserted here (MIDI cases cover its timing).
"""
import base64


def nb_chord_acceleration_lock(c):
    from cases import assign_trig_parameter
    from frame_oracle import render
    assert c.profile == 'nb-audio', 'nb-audio profile required'
    c.configure(); c.screen_header('Ch. 1 Device Config')
    # The selected Device row (C05) shows the name exactly; K3 applies it.
    c.ui.pick_device('Doubledecker');c.elapse(13)                                        # device applied; upstream startup tone ends
    c.ui.turn(1, -3); c.screen_header('Ch. 1 Trig Locks', selected=2)
    assign_trig_parameter(c, 'Chord Accel Mod')                   # slot 1 (README 749-756)
    c.action(type='grid', x=1, y=4, state=1)
    try: c.elapse(.05); c.enc(3, 2)                               # step 1 lock +2 (README 937-940)
    finally: c.action(type='grid', x=1, y=4, state=0)
    c.tap(1, 8)
    for _ in range(8): c.elapse(.25); c.snapshot()            # two cycles across the locked step
    c.tap(1, 8); c.elapse(.3); c.snapshot()
    # No Lua error while playing across the lock: checked by the driver at finish
    # (README 937-940 and 807-809; user decision S47).
    c.results.append(dict(kind='nb-chord-acceleration-step-lock', param='chord_acceleration', value=2, cycles=2, passed=True))
