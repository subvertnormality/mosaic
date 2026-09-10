"""The "Autosaved" tooltip (README "Tooltips", line 306; autosave, line 1054).

Characterisation, as M-TOOLTIP-001: a tooltip clears about 3 s after it appears.
After several tooltips (page changes), an idle autosave shows "Autosaved"; it must
clear like any other tooltip, and a later tooltip must still clear.
"""
import base64, time

REGION = [(y*128+x)*4+k for y in range(55, 64) for x in range(128) for k in range(3)]


def tooltip_autosave(c):
    from frame_oracle import render
    controlled = c.clock_mode == 'controlled-experimental'
    def now(): return c.logical_ns if controlled else time.monotonic_ns()
    def bottom(state):
        pixels = base64.b64decode(state['frame']['pixels_base64']); return [pixels[i] for i in REGION]
    def tip(stage, text, within=0):
        wanted = [render([(0, 62, 10, text)])[i] for i in REGION]
        if controlled:
            for _ in range(int(within / .25)):
                if bottom(c.snapshot()) == wanted: break
                c.elapse(.25)
        c.wait(lambda s: bottom(s) == wanted, timeout=within + 5)
        c.results.append(dict(kind='tooltip', stage=stage, text=text, passed=True)); return now()
    def cleared(stage, shown_at):
        if controlled:
            for _ in range(10):
                if not any(bottom(c.snapshot())): break
                c.elapse(.5)
        c.wait(lambda s: not any(bottom(s)), timeout=5)
        lifetime = (now() - shown_at) / 1e9
        assert lifetime <= 4, (stage, lifetime)
        c.results.append(dict(kind='tooltip-cleared', stage=stage, measured_lifetime_seconds=round(lifetime, 3), passed=True))
    c.configure()
    for x, name in ((4, 'Scale Editor'), (6, 'Song Editor'), (3, 'Channel Editor')):
        c.tap(x, 8); tip('page-' + name, name)
    cleared('channel-editor', now())
    ptn = c.data_directory/'autosave.ptn'
    c.elapse(30); c.elapse(25)                                    # idle since the last page tap, below 60 s
    shown = tip('autosaved', 'Autosaved', within=10)
    assert ptn.is_file(), 'Idle autosave missing'
    cleared('autosaved', shown)
    c.tap(4, 8); shown = tip('after-autosave', 'Scale Editor'); cleared('after-autosave', shown)
