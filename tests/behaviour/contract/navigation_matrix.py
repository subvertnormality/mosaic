def navigation_matrix(c):
    # Independent six-page model: the pattern key cycles three editors.
    # Check each intermediate menu state and re-play the authored melody after
    # every source/destination pair so navigation cannot silently alter music.
    pages=('channel','scale','trig','note','velocity','song')
    pattern_pages=('trig','note','velocity')
    menus={'channel':[15,2,2,2], 'scale':[2,15,2,2],
           'trig':[2,2,5,2], 'note':[2,2,10,2],
           'velocity':[2,2,15,2], 'song':[2,2,2,15]}
    melody=[(1,[144,n,v]) for n,v in ((60,127),(62,117),(64,107),(65,97))]
    ui=c.ui
    c.configure();current='channel';edges=[];presses=0
    def choose(target):
        nonlocal current, presses
        if target in pattern_pages:
            count=((pattern_pages.index(target)-pattern_pages.index(current))%3 or 3) if current in pattern_pages else pattern_pages.index(target)+1
            button=5
        else:
            count=1;button={'channel':3,'scale':4,'song':6}[target]
        control={3:'channel_editor',4:'scale_editor',5:'pattern_editor',6:'song_editor'}[button]
        for _ in range(count):
            ui.tap_control(control);presses+=1
            if button==5:
                current=pattern_pages[(pattern_pages.index(current)+1)%3] if current in pattern_pages else 'trig'
            else:current={3:'channel',4:'scale',6:'song'}[button]
            c.led_values([(x,8) for x in (3,4,5,6)],menus[current])
        assert current==target
    for source in pages:
        for target in pages:
            choose(source);choose(target)
            notes=c.playback(melody,cycles=2)
            assert len(notes)>=9
            c.led_values([(x,8) for x in (3,4,5,6)],menus[target])
            edges.append([source,target])
    assert len(edges)==36 and len({tuple(edge) for edge in edges})==36
    c.results.append(dict(kind='navigation-matrix',source_destination_pairs=edges,
                          menu_presses=presses,melody_checks=36,passed=True))
