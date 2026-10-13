"""Global and channel scale locks on the same step (README "Scale locks", line 856).

README: a scale lock activates at its designated step; global locks persist until
another global lock or the global scale track wraps; channel-specific scale locks
override global scales and locks. Global length 4 makes the scale track wrap with
channel 1's phrase (degrees 0..3, slot 1 C major applied).

1. A global lock at step 3 (slot 3, E major) must already quantise channel 1's
   step-3 note: 60 62 68 69 (the scale track and channel steps coincide).
2. Adding a channel lock at step 3 (slot 2, G major) overrides it; with "Scales lock
   until ptn end" (default On) it holds through step 4: 60 62 71 72.
"""
PHRASE_VELOCITY = [127, 117, 107, 97]


def scale_lock_order(c):
    ui = c.ui
    ui.configure()
    ui.song_editor()
    ui.tap_control('global_pattern_length', 2)
    for _ in range(3):
        ui.tap_control('global_pattern_length', 8)                # global length 4 (scale track wraps too)
    ui.scale_editor()
    ui.tap_control('scale_slot', 3)
    ui.select_field('root', offset=-1)
    ui.set_value(4)
    ui.press_key(3)                                               # slot 3: E major (root E)
    ui.tap_control('scale_slot', 2)
    ui.set_value(7)
    ui.press_key(3)                                               # slot 2: G major (root G)
    ui.tap_control('scale_slot', 1)                               # slot 1 C major applied

    def phrase(stage, notes):
        c.playback([(1, [144, n, v]) for n, v in zip(notes, PHRASE_VELOCITY)], cycles=2)
        c.results.append(dict(kind='scale-lock-order', stage=stage, notes=notes, passed=True))

    phrase('no-locks', [60, 62, 64, 65])
    with ui.hold_step(3):                                        # scale page: global lock at step 3
        ui.tap_control('scale_slot', 3)
    ui.menu('channel_editor')
    phrase('global-lock-step-3', [60, 62, 68, 69])
    with ui.hold_step(3):                                        # channel page: channel lock at step 3
        ui.tap_control('channel_scale_slot', 2)
    phrase('channel-lock-overrides', [60, 62, 71, 72])
