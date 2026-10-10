"""Two-key gestures other than song slot copy keep release-order resolution
(arbitrated SEM-016: press order applies to slot copy only; decisions.md). Range
gestures are pinned by range_rejection.py. This case pins the channel scale lock:
README 856 "hold a step and press the desired scale slot button". Holding step 3 and
tapping slot 3 (E major) locks step 3; pressing step 3, pressing slot 3 and
releasing the step first resolves as (slot, step) and sets no lock
(characterisation, not manual text).
"""
PHRASE_VELOCITY = [127, 117, 107, 97]


def gesture_release_order(c):
    c.configure()
    c.ui.scale_editor()
    c.ui.tap_control("scale_slot", 3)
    c.ui.turn(2, -1)
    c.ui.set_value(4)
    c.ui.press_key(3)
    c.ui.tap_control("scale_slot", 1)
    c.ui.menu("channel_editor")   # slot 3 E major; slot 1 applied
    def phrase(stage, notes):
        c.playback([(1, [144, n, v]) for n, v in zip(notes, PHRASE_VELOCITY)], cycles=2)
        c.results.append(dict(kind='gesture-release-order', stage=stage, notes=notes, passed=True))
    phrase('no-lock', [60, 62, 64, 65])
    c.ui.gesture([("step", 3)], []); c.elapse(.05)                 # press step 3
    c.ui.gesture([("scale_slot", 3)], []); c.elapse(.05)           # press slot 3
    c.ui.gesture([], [("step", 3)]); c.elapse(.05)                 # release the step first
    c.ui.gesture([], [("scale_slot", 3)]); c.elapse(.1)
    phrase('step-released-first-sets-no-lock', [60, 62, 64, 65])
    with c.ui.hold_step(3):
        c.ui.tap_control("scale_slot", 3)                           # hold step 3, tap slot 3
    c.elapse(.1)
    phrase('hold-step-tap-slot-locks', [60, 62, 68, 69])
