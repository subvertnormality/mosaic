"""Literal screen-layout contract for the pattern grid viewer."""


def pattern_grid_viewer(c):
    import base64
    from frame_oracle import live_header_matches
    # Independent layout contract (lib/ui_render.lua pattern64): 16x4 cells, 4x4 px
    # at x=2+8*col, y=24+8*row, drawn at the viewer's step level. Levels come only
    # from the authored phrase and declared channel range. The title row names the
    # viewed channel.
    titles={'trigger':'PATTERN TRIG','note':'PATTERN NOTE','velocity':'PATTERN VELOCITY'}
    view={'page':'trigger'}
    def viewer(channel,levels,label):
        assert len(levels)==64
        title=titles[view['page']]
        def matches(state):
            actual=base64.b64decode(state['frame']['pixels_base64'])
            for k,level in enumerate(levels):
                x=2+(k%16)*8;y=24+(k//16)*8
                if any(actual[((y+dy)*128+x+dx)*4]!=level*17 for dy in range(4) for dx in range(4)):return False
            return live_header_matches(state,title,'CH%02d'%channel,'pattern64')
        row=dict(kind='grid-viewer-frame',channel=channel,label=label,expected_levels=levels,passed=False)
        c.results.append(row);c.wait(matches);row['passed']=True
    def page(name,from_view=None):
        c.ui.pattern_editor(view=name,from_view=from_view);view['page']=name
    baseline=[(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107),(65,97)]]
    c.ui.configure();c.ui.set_range(1,64);page('trigger')
    viewer(1,[15]*4+[2]*60,'wide-range-positive-oracle')
    c.ui.tap_control('channel_editor');c.ui.set_range(1,4);page('trigger')
    viewer(1,[15]*4+[0]*60,'shortened-range-clears-outside')
    c.playback(baseline,cycles=2,timeout=3,settle_seconds=4/3-.1)
    for channel in range(2,17):
        c.ui.view_channel(1);viewer(channel,[2]*64,'unassigned-channel')
    c.ui.view_channel(1);viewer(16,[2]*64,'upper-channel-clamp')
    c.ui.view_channel(-15);viewer(1,[15]*4+[0]*60,'return-to-short-channel')
    c.ui.view_channel(-1);viewer(1,[15]*4+[0]*60,'lower-channel-clamp')
    # Note and velocity editors have separate viewer selections but share the
    # same drawing/cache component. Page changes must not leak the previous view.
    page('note','trigger');viewer(1,[15]*4+[0]*60,'note-page-short-channel')
    c.ui.view_channel(15);viewer(16,[2]*64,'note-page-channel16')
    page('velocity','note');viewer(1,[15]*4+[0]*60,'velocity-page-short-channel')
    c.ui.view_channel(15);viewer(16,[2]*64,'velocity-page-channel16')
    page('trigger','velocity');viewer(1,[15]*4+[0]*60,'trig-page-retains-own-selection')
    page('note','trigger');viewer(16,[2]*64,'note-page-retains-own-selection')
    c.ui.tap_control('channel_editor');page('trigger');viewer(1,[15]*4+[0]*60,'return-from-channel-page')
    # Viewer selection is independent of the channel's pattern data and route.
    c.led_values([((s-1)%16+1,(s-1)//16+4) for s in range(1,65)],[15]*4+[2]*60)
    c.playback(baseline,cycles=2,timeout=3,settle_seconds=4/3-.1)
