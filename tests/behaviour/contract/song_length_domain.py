"""Every global-length fader value checked through public screen/grid feedback."""
def song_length_domain(c):
    import base64
    from frame_oracle import render
    c.configure();c.hold_tap((1,4),(16,7));c.tap(6,8);c.tap(2,7)
    cells=[((i-1)%16+1,(i-1)//16+4) for i in range(1,65)]
    def verify(length):
        expected=render([(0,62,10,'Global pattern length: '+str(length))])
        def feedback(state):
            actual=base64.b64decode(state['frame']['pixels_base64'])
            return all(actual[(y*128+x)*4+k]==expected[(y*128+x)*4+k] for y in range(55,64) for x in range(128) for k in range(3))
        c.wait(feedback);c.tap(3,8)
        c.led_values(cells,[(15 if i<=4 else 2) if i<=length else 0 for i in range(1,65)])
        c.tap(6,8)
        c.results.append(dict(kind='song-length-domain',length=length,checked_cells=64,passed=True))
    for length in range(1,65):
        if length>1:c.tap(8,7)
        verify(length)
    # Boundary attempts clamp rather than wrap; shrinking and regrowing must
    # reveal the preserved64-step selected channel range.
    c.tap(8,7);verify(64)
    c.tap(2,7);c.tap(1,7);verify(1)
    c.tap(7,7);verify(64)
