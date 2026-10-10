"""A channel scale lock remains visible on the Memory page (issue #85).

The user makes the lock through the normal held-step + scale-slot grid gesture,
then navigates to Memory with E1. The channel sequencer represents a locked
trigger by blinking it at 12 while an otherwise identical unlocked neighbour
stays at 15. The Trig Locks page is the page-level control for the same lock.
This is display characterisation; README/cheat sheet only promise that scale
locks are created by the gesture, not which editor pages show their indicator.
"""


def memory_scale_lock_display(c):
    ui = c.ui
    ui.configure()
    # Select scale slot 3 and create its channel lock on step 3 through the
    # physical grid path. The slot need not be musically edited for this
    # display contract: the selected lock value is itself the observable state.
    ui.scale_editor()
    ui.tap_control("scale_slot", 3)
    ui.menu("channel_editor")
    ui.hold_control_tap(
        "step", "channel_scale_slot", held_index=3, target_index=3
    )
    c.elapse(.1)

    # E1 from Device Config selects Memory. Step 2 remains an unlocked trigger.
    ui.channel_page("memory", "midi_config", confirm=False)
    ui.expect_header("memory", channel=1)
    # A user grid gesture requests the page's current LED frame in controlled time.
    ui.tap_step(16)
    c.elapse(.1)
    ui.expect_leds({("step", 3): "active"})
    ui.expect_leds({("step", 2): "selected"})

    # The established Trig Locks page representation is a user-visible control
    # that distinguishes a missing Memory-page indicator from a missing lock.
    ui.channel_page("trig_locks", "memory", confirm=False)
    ui.expect_header("trig_locks", channel=1)
    ui.expect_leds({("step", 3): "active"})
    ui.expect_leds({("step", 2): "selected"})
    c.results.append(dict(kind="memory-scale-lock-display", locked_step=3,
                          unlocked_step=2, pages=["Memory", "Trig Locks"], passed=True))
