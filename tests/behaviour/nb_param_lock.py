"""A step lock on an nb (norns-parameter) device parameter (README "Trig Parameters":
holding a step and turning E3 creates a trig lock that overrides the default for
that step). Doubledecker maps its default parameters automatically, so slot 1 is
Shape 1, a norns parameter. Playing across the locked step must not raise a Lua
error (the driver fails on native errors). Lock application and restoration of the
norns value are pinned by Lua units (norns_param_lock_tests.lua); the emulator
does not expose norns parameter values.
"""
import base64


def nb_param_lock(c):
    from frame_oracle import render
    assert c.profile == 'nb-audio', 'nb-audio profile required'
    c.configure(); c.screen_header('Ch. 1 Device Config')
    expected = render([(10, 35, 15, 'Doubledecker')])
    indices = [(y*128+x)*4+k for y in range(27, 37) for x in range(10, 62) for k in range(3)]
    for _ in range(40):
        if all(base64.b64decode(c.snapshot()['frame']['pixels_base64'])[i] == expected[i] for i in indices): break
        c.enc(3, 1)
    else: raise AssertionError('Doubledecker not visible in device picker')
    c.key(3); c.elapse(13)                                        # device applied; upstream startup tone ends
    c.enc(1, -3); c.screen_header('Ch. 1 Trig Locks', selected=2)
    c.action(type='grid', x=1, y=4, state=1)
    try: c.elapse(.05); c.enc(3, 5)                               # step 1 lock on slot 1 (Shape 1)
    finally: c.action(type='grid', x=1, y=4, state=0)
    c.tap(1, 8)
    for _ in range(8): c.elapse(.25); c.snapshot()            # two cycles across the locked step
    c.tap(1, 8); c.elapse(.3); c.snapshot()
    c.results.append(dict(kind='nb-param-step-lock', param='doubledecker_shape_1', cycles=2, passed=True))
