"""The "Autosaved" tooltip (README "Tooltips", line 306; autosave, line 1054).

Characterisation, as M-TOOLTIP-001: a tooltip clears about 3 s after it appears.
After several tooltips (page changes), an idle autosave shows "Autosaved"; it must
clear like any other tooltip, and a later tooltip must still clear.
"""
import time

# Live footer (frame_oracle.footer): the tooltip at (1,63) level 9 while it
# lasts; cleared means the footer shows exactly the screen's own hints again.
HINTS = {'scale': ('< Root', 'Degree >'), 'masks': 'E2 MASK  E3 SET'}


def tooltip_autosave(c):
    from frame_oracle import footer_matches
    controlled = c.clock_mode == 'controlled-experimental'
    def now(): return c.logical_ns if controlled else time.monotonic_ns()
    def tip(stage, text, within=0):
        if controlled:
            for _ in range(int(within / .25)):
                if footer_matches(c.snapshot(), text): break
                c.elapse(.25)
        c.wait(lambda s: footer_matches(s, text), timeout=within + 5)
        c.results.append(dict(kind='tooltip', stage=stage, text=text, passed=True)); return now()
    def cleared(stage, shown_at, screen):
        hints = HINTS[screen]
        if controlled:
            for _ in range(10):
                if footer_matches(c.snapshot(), hints): break
                c.elapse(.5)
        c.wait(lambda s: footer_matches(s, hints), timeout=5)
        lifetime = (now() - shown_at) / 1e9
        assert lifetime <= 4, (stage, lifetime)
        c.results.append(dict(kind='tooltip-cleared', stage=stage, measured_lifetime_seconds=round(lifetime, 3), passed=True))
    c.configure()
    for x, name in ((4, 'Scale Editor'), (6, 'Song Editor'), (3, 'Channel Editor')):
        c.tap(x, 8); tip('page-' + name, name)
    # The Channel button shows the remembered family: Masks (Channel tasks opens straight
    # from Masks, so Trig params was never shown).
    cleared('channel-editor', now(), 'masks')
    ptn = c.data_directory/'autosave.ptn'
    c.elapse(30); c.elapse(25)                                    # idle since the last page tap, below 60 s
    shown = tip('autosaved', 'Autosaved', within=10)
    assert ptn.is_file(), 'Idle autosave missing'
    cleared('autosaved', shown, 'masks')
    c.tap(4, 8); shown = tip('after-autosave', 'Scale Editor'); cleared('after-autosave', shown, 'scale')
