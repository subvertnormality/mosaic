"""Literal screen-layout contract for the pattern grid viewer."""


def pattern_grid_viewer(c):
    import base64
    from frame_oracle import live_header_matches
    # Independent layout contract (lib/ui_render.lua pattern64): 16x4 cells, 4x4 px
    # at x=2+8*col, y=24+8*row. `levels` are the viewed channel's step levels, from
    # the authored phrase and declared channel range only. The pattern editor
    # (P01/P03/P04) draws the edited pattern's trigs (pattern 1: steps 1-4) at 15
    # over the viewed channel's steps capped at 3, and its scope names the pattern
    # and the viewed channel (PAT01 CH16); Channel view (P05) draws the channel
    # alone at its own levels with scope CH16 (usability audit 25 September 2026).
    titles={'trigger':'PATTERN TRIG','note':'PATTERN NOTE','velocity':'PATTERN VELOCITY','channel_view':'CHANNEL VIEW'}
    view={'page':'trigger'}
    PATTERN_ONE={1,2,3,4}
    def viewer(channel,levels,label):
        assert len(levels)==64
        title=titles[view['page']]
        if view['page']=='channel_view':
            shown,scope=list(levels),'CH%02d'%channel
        else:
            shown=[15 if k+1 in PATTERN_ONE else min(level,3) for k,level in enumerate(levels)]
            scope='PAT01 CH%02d'%channel
        def matches(state):
            actual=base64.b64decode(state['frame']['pixels_base64'])
            for k,level in enumerate(shown):
                x=2+(k%16)*8;y=24+(k//16)*8
                if any(actual[((y+dy)*128+x+dx)*4]!=level*17 for dy in range(4) for dx in range(4)):return False
            return live_header_matches(state,title,scope,'pattern64')
        row=dict(kind='grid-viewer-frame',page=view['page'],channel=channel,label=label,expected_levels=levels,
                 shown_levels=shown,scope=scope,passed=False)
        c.results.append(row);c.wait(matches);row['passed']=True
    def channel_view(channel,levels,label):
        """Channel view (P05, Trig context) shares the Trig viewer: the channel alone."""
        c.ui.open_task('Trig','channel_view');view['page']='channel_view'
        viewer(channel,levels,label)
        c.ui.open_task('Trig','pattern');view['page']='trigger' 
    def page(name,from_view=None):
        c.ui.pattern_editor(view=name,from_view=from_view);view['page']=name
    baseline=[(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107),(65,97)]]
    c.ui.configure();c.ui.set_range(1,64);page('trigger')
    viewer(1,[15]*4+[2]*60,'wide-range-positive-oracle')
    channel_view(1,[15]*4+[2]*60,'wide-range-channel-alone')
    c.ui.tap_control('channel_editor');c.ui.set_range(1,4);page('trigger')
    viewer(1,[15]*4+[0]*60,'shortened-range-clears-outside')
    c.playback(baseline,cycles=2,timeout=3,settle_seconds=4/3-.1)
    for channel in range(2,17):
        c.ui.view_channel(1);viewer(channel,[2]*64,'unassigned-channel')
    c.ui.view_channel(1);viewer(16,[2]*64,'upper-channel-clamp')
    channel_view(16,[2]*64,'unassigned-channel-alone')
    c.ui.view_channel(-15);viewer(1,[15]*4+[0]*60,'return-to-short-channel')
    c.ui.view_channel(-1);viewer(1,[15]*4+[0]*60,'lower-channel-clamp')
    channel_view(1,[15]*4+[0]*60,'short-channel-alone')
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
