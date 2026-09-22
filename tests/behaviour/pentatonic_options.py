"""Lock all to pentatonic: default, every scale and degree, disable (MAN-100)."""

# Independent interval fixtures in Mosaic's scale-type order, and the README
# MAN-102 five-degree selections (one-based degrees of each named scale).
SCALES=[('major',[0,2,4,5,7,9,11],[1,2,3,5,6]),('harmonic-major',[0,2,4,5,7,8,11],[1,2,3,5,6]),
        ('minor',[0,2,3,5,7,8,10],[1,3,4,5,7]),('harmonic-minor',[0,2,3,5,7,8,11],[1,3,4,5,7]),
        ('melodic-minor',[0,2,3,5,7,9,11],[1,3,4,5,7]),('dorian',[0,2,3,5,7,9,10],[1,2,4,5,7]),
        ('phrygian',[0,1,3,5,7,8,10],[1,3,4,6,7]),('lydian',[0,2,4,6,7,9,11],[2,3,5,6,7]),
        ('mixolydian',[0,2,4,5,7,9,10],[1,2,4,5,6]),('locrian',[0,1,3,5,6,8,10],[2,3,4,6,7])]
DEGREES=list(range(7))
VELOCITY=[127,117,107,97,127,117,107]

def plain(intervals):return [60+intervals[d] for d in DEGREES]

def snapped(intervals,selection):
    """Nearest selected pitch repeated across octaves; exact tie takes the lower."""
    available=[12*octave+intervals[d-1] for octave in range(11) for d in selection]
    return [min(available,key=lambda n:(abs(n-p),n)) for p in plain(intervals)]

def lock_all_to_pentatonic(c):
    from cases import assert_durations
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    # Hand-worked anchors for the table above, including both README examples.
    assert snapped(SCALES[0][1],SCALES[0][2])==[60,62,64,64,67,69,72]
    assert snapped(SCALES[2][1],SCALES[2][2])==[60,63,63,65,67,67,70]
    assert snapped(SCALES[7][1],SCALES[7][2])==[59,62,64,67,67,69,71] # README: Lydian C -> B below
    assert snapped(SCALES[4][1],SCALES[4][2])==[60,63,63,65,67,67,71] # README: melodic-minor A -> G on a tie
    ui = c.ui
    ui.configure()
    # Extend pattern 1 and channel 1 to seven steps holding degrees I..VII.
    ui.tap_control("pattern_editor")
    ui.tap_control("pattern_select", 1)
    for step in (5, 6, 7):ui.tap_step(step)
    ui.tap_control("pattern_editor")
    for x,degree in enumerate(DEGREES,1):
        ui.tap_control("pattern_note_fader", (x, 7 - degree))
    # Row 1 doubles as the pattern-selector row; degree VII is checked by MIDI.
    ui.expect_leds({("pattern_note_fader", (x, 7 - d)): "active"
                    for x,d in enumerate(DEGREES[:6],1)})
    ui.tap_control("pattern_editor")
    for x,y in ((5,1),(6,2),(7,3)):
        ui.tap_control("pattern_note_fader", (x, y))
    ui.tap_control("channel_editor")
    ui.set_range(1, 7)
    def verify(label,pitches):
        notes=c.playback([(1,[144,n,v]) for n,v in zip(pitches,VELOCITY)],cycles=2,timeout=6)
        assert_durations(c,notes,[1]*14)
        for i,note in enumerate(notes):assert abs((note[field]-notes[0][field])/1e9-i/6)<=tolerance
        c.results.append(dict(kind='lock-all-to-pentatonic',stage=label,degrees=DEGREES,pitches=pitches,passed=True))
    # No option input yet: the fresh default must leave non-members unsnapped.
    verify('default-off-major',plain(SCALES[0][1]))
    # Random/merged switches off: only Lock all can move these unmodified notes.
    ui.set_mosaic_options([('Lock all to pentatonic',True),('Lock random to pent.',False),('Lock merged to pent.',False)])
    for number,(name,intervals,selection) in enumerate(SCALES):
        if number:
            ui.tap_control("scale_editor")
            ui.set_value(1)
            ui.press_key(3)
            ui.tap_control("channel_editor")
        verify('on-'+name,snapped(intervals,selection))
    ui.set_mosaic_options([('Lock all to pentatonic',False)])
    verify('off-'+SCALES[-1][0],plain(SCALES[-1][1]))
