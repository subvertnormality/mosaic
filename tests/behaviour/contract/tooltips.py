"""Tooltips (README "Tooltips"): shown at the bottom of the screen when a function is activated.

The manual lists no texts. The exact strings asserted here are characterised
implementation messages, pinned so a refactor cannot silently change them.
"""
import base64,time

# The live screen's footer line (lib/ui_render.lua: text at (1,63), level 9)
# shows the tooltip while it lasts, then the screen's control hints again.
REGION=[(y*128+x)*4+k for y in range(56,64) for x in range(128) for k in range(3)]
HINTS={'scale':'E3 SET  K3 APPLY  K2 CANCEL','masks':'E2 MASK  E3 SET',
       'trig_locks':'E2 SLOT  E3 SET  K2 ASSIGN','memory':'E3 MOVE  K2 UNDO  K3 REDO'}

def tooltip_messages(c):
    from frame_oracle import render
    controlled=c.clock_mode=='controlled-experimental'
    def now():return c.logical_ns if controlled else time.monotonic_ns()
    def bottom(state):
        pixels=base64.b64decode(state['frame']['pixels_base64']);return [pixels[i] for i in REGION]
    def footer(text):
        expected=render([(1,63,9,text)]);return [expected[i] for i in REGION]
    def tip(stage,text):
        wanted=footer(text)
        c.wait(lambda s:bottom(s)==wanted)
        c.results.append(dict(kind='tooltip',stage=stage,text=text,passed=True))
    def cleared(stage,shown_at,screen):
        # Cleared means the footer shows exactly the screen's own hints again.
        wanted=footer(HINTS[screen])
        c.wait(lambda s:bottom(s)==wanted,timeout=5)
        lifetime=(now()-shown_at)/1e9
        c.results.append(dict(kind='tooltip-cleared',stage=stage,measured_lifetime_seconds=round(lifetime,3),passed=True))
        return lifetime
    c.configure()
    for x,name in ((4,'Scale Editor'),(6,'Song Editor'),(3,'Channel Editor')):
        c.tap(x,8);tip('page-'+name,name)
    c.tap(2,1);tip('select-channel-2','Channel 2 selected')
    c.tap(1,1);tip('select-channel-1','Channel 1 selected')
    c.tap(2,8);tip('record-on','Recording started')
    c.tap(2,8);tip('record-off','Recording stopped')
    c.ui.channel_page('memory');c.screen_header('Ch. 1 Memory')
    c.key(3);tip('memory-apply','Ch. 1 memory applied')
    c.key(2);tip('memory-undo','Ch. 1 memory undone')
    c.ui.channel_page('midi_config')
    # Expiry without input, measured from the last activation.
    c.tap(4,8);shown=now();tip('before-expiry','Scale Editor')
    cleared('idle-expiry',shown,'scale')
    # Replacement: an immediate second activation replaces the first and owns the expiry.
    c.tap(3,8);c.tap(2,1);shown=now();tip('replaced','Channel 2 selected')
    cleared('replacement-expiry',shown,'trig_locks')
    c.tap(1,1);tip('select-channel-1-again','Channel 1 selected')
    # While playing, transport tooltips appear and a later one still clears.
    c.tap(1,8);tip('play','Starting playback')
    c.tap(2,1);shown=now();tip('select-while-playing','Channel 2 selected')
    cleared('playing-expiry',shown,'trig_locks')
    c.tap(1,1);c.tap(1,8);tip('stop','Stopping playback')
    c.wait(lambda s:not s['midi_capture']['outstanding'])
