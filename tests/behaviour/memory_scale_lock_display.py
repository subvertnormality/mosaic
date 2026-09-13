"""A channel scale lock remains visible on the Memory page (issue #85).

The user makes the lock through the normal held-step + scale-slot grid gesture,
then navigates to Memory with E1. The channel sequencer represents a locked
trigger by blinking it at 12 while an otherwise identical unlocked neighbour
stays at 15. The Trig Locks page is the page-level control for the same lock.
This is display characterisation; README/cheat sheet only promise that scale
locks are created by the gesture, not which editor pages show their indicator.
"""

def memory_scale_lock_display(c):
    c.configure()
    # Select scale slot 3 and create its channel lock on step 3 through the
    # physical grid path. The slot need not be musically edited for this
    # display contract: the selected lock value is itself the observable state.
    c.tap(4, 8); c.tap(3, 3); c.tap(3, 8)
    c.hold_tap((3, 4), (3, 3)); c.elapse(.1)

    # E1 from Device Config selects Memory. Step 2 remains an unlocked trigger.
    c.enc(1, -2); c.screen_header('Ch. 1 Memory')
    c.led_values([(3, 4)], [12])
    c.led_values([(2, 4)], [15])

    # The established Trig Locks page representation is a user-visible control
    # that distinguishes a missing Memory-page indicator from a missing lock.
    c.enc(1, -1); c.screen_header('Ch. 1 Trig Locks', selected=2)
    c.led_values([(3, 4)], [12])
    c.led_values([(2, 4)], [15])
    c.results.append(dict(kind='memory-scale-lock-display', locked_step=3,
                          unlocked_step=2, pages=['Memory', 'Trig Locks'], passed=True))
