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
    c.configure()
    c.tap(6, 8); c.tap(2, 7)
    for _ in range(3): c.tap(8, 7)                                # global length 4 (scale track wraps too)
    c.tap(4, 8)
    c.tap(3, 3); c.enc(2, -1); c.enc(3, 4); c.key(3)              # slot 3: E major (root E)
    c.tap(2, 3); c.enc(3, 7); c.key(3)                            # slot 2: G major (root G)
    c.tap(1, 3)                                                   # slot 1 C major applied
    def phrase(stage, notes):
        c.playback([(1, [144, n, v]) for n, v in zip(notes, PHRASE_VELOCITY)], cycles=2)
        c.results.append(dict(kind='scale-lock-order', stage=stage, notes=notes, passed=True))
    phrase('no-locks', [60, 62, 64, 65])
    c.action(type='grid', x=3, y=4, state=1)                      # scale page: global lock at step 3
    try: c.tap(3, 3)
    finally: c.action(type='grid', x=3, y=4, state=0)
    c.tap(3, 8)
    phrase('global-lock-step-3', [60, 62, 68, 69])
    c.action(type='grid', x=3, y=4, state=1)                      # channel page: channel lock at step 3
    try: c.tap(2, 3)
    finally: c.action(type='grid', x=3, y=4, state=0)
    phrase('channel-lock-overrides', [60, 62, 71, 72])
