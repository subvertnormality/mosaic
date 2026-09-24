"""Literal screen-layout contract for the pattern grid viewer."""


def pattern_grid_viewer(c):
    import base64
    from frame_oracle import render
    # Independent layout contract:16x4 sequencer dots,7px spacing,35px font.
    # Levels come only from the authored phrase and declared channel range.
    def viewer(channel,levels,label):
        assert len(levels)==64
        dots=render([(-3+x*7,-2+y*7,levels[(y-4)*16+x-1],'.') for y in range(4,8) for x in range(1,17)],font_size=35,antialias=1)
        # Official norns core/script.lua resets screen.aa(0) on script load.
        title=render([(0,9,10,'Channel '+str(channel)+' grid viewer')],antialias=1)
        def matches(state):
            actual=base64.b64decode(state['frame']['pixels_base64'])
            return (all(actual[(y*128+x)*4+k]==dots[(y*128+x)*4+k] for y in range(20,57) for x in range(120) for k in range(3))
              and all(actual[(y*128+x)*4+k]==title[(y*128+x)*4+k] for y in range(2,11) for x in range(114) for k in range(3)))
        row=dict(kind='grid-viewer-frame',channel=channel,label=label,expected_levels=levels,passed=False)
        c.results.append(row);c.wait(matches);row['passed']=True
    baseline=[(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107),(65,97)]]
    c.ui.configure();c.ui.set_range(1,64);c.ui.pattern_editor(view='trigger')
    viewer(1,[15]*4+[2]*60,'wide-range-positive-oracle')
    c.ui.tap_control('channel_editor');c.ui.set_range(1,4);c.ui.pattern_editor(view='trigger')
    viewer(1,[15]*4+[0]*60,'shortened-range-clears-outside')
    c.playback(baseline,cycles=2,timeout=3,settle_seconds=4/3-.1)
    for channel in range(2,17):
        c.ui.select_field('pattern_channel',offset=1);viewer(channel,[2]*64,'unassigned-channel')
    c.ui.select_field('pattern_channel',offset=1);viewer(16,[2]*64,'upper-channel-clamp')
    c.ui.select_field('pattern_channel',offset=-15);viewer(1,[15]*4+[0]*60,'return-to-short-channel')
    c.ui.select_field('pattern_channel',offset=-1);viewer(1,[15]*4+[0]*60,'lower-channel-clamp')
    # Note and velocity editors have separate viewer selections but share the
    # same drawing/cache component. Page changes must not leak the previous view.
    c.ui.pattern_editor(view='note',from_view='trigger');viewer(1,[15]*4+[0]*60,'note-page-short-channel')
    c.ui.select_field('pattern_channel',offset=15);viewer(16,[2]*64,'note-page-channel16')
    c.ui.pattern_editor(view='velocity',from_view='note');viewer(1,[15]*4+[0]*60,'velocity-page-short-channel')
    c.ui.select_field('pattern_channel',offset=15);viewer(16,[2]*64,'velocity-page-channel16')
    c.ui.pattern_editor(view='trigger',from_view='velocity');viewer(1,[15]*4+[0]*60,'trig-page-retains-own-selection')
    c.ui.pattern_editor(view='note',from_view='trigger');viewer(16,[2]*64,'note-page-retains-own-selection')
    c.ui.tap_control('channel_editor');c.ui.pattern_editor(view='trigger');viewer(1,[15]*4+[0]*60,'return-from-channel-page')
    # Viewer selection is independent of the channel's pattern data and route.
    c.led_values([((s-1)%16+1,(s-1)//16+4) for s in range(1,65)],[15]*4+[2]*60)
    c.playback(baseline,cycles=2,timeout=3,settle_seconds=4/3-.1)
