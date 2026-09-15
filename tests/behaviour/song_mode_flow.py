"""Song mode progression, empty-slot loops and queued selection (README Song Mode Operations).

Global length 2: slot k plays notes 60/62 shifted by its channel-1 octave.
Filled slots 1 (0), 2 (+1), 4 (+2), 5 (-1); slots 3 and 6 are empty, so the
groups are {1,2} and {4,5}.
"""
OCTAVE={1:0,2:1,4:2,5:-1}
def slot_notes(slot):return [60+12*OCTAVE[slot],62+12*OCTAVE[slot]]

def song_mode_flow(c):
    from cases import set_mosaic_options
    c.configure()
    c.tap(6,8);c.tap(2,7);c.tap(8,7)                         # global length 2
    for target,x in ((2,11),(4,12),(5,9)):                   # copy slot 1, then set that copy's octave
        c.tap(6,8);c.tap(1,1);c.hold_tap((1,1),(target,1));c.tap(target,1);c.tap(3,8);c.tap(1,1);c.tap(x,8)
    c.tap(6,8);c.tap(1,1)
    def onsets(state,marker):return [m['bytes'][1] for m in state['midi'] if m['index']>marker and m['bytes'][0]==144 and m['bytes'][2]>0]
    def play(stage,slots,start=None,after_first=None):
        """Play from the selected slot; optionally tap slots after the first onset."""
        if start:c.tap(start,1)
        expected=[n for s in slots for n in slot_notes(s)]
        marker=c.snapshot()['midi_count'];c.tap(1,8)
        if after_first:
            c.wait(lambda s:len(onsets(s,marker))>=1,timeout=2)
            for slot in after_first:c.tap(slot,1)
        state=c.wait(lambda s:len(onsets(s,marker))>=len(expected),timeout=6)
        c.tap(1,8);c.wait(lambda s:not s['midi_capture']['outstanding'])
        actual=onsets(state,marker)[:len(expected)]
        assert actual==expected,(stage,actual,expected)
        c.results.append(dict(kind='song-mode-flow',stage=stage,slots=slots,notes=expected,passed=True))
    # Song mode is on by default: each group loops back at its empty slot.
    play('default-on-group-1',[1,2,1,2],start=1)
    play('default-on-group-2',[4,5,4,5],start=4)
    # A live selection is queued until the current sequence completes.
    play('queued-selection',[4,2,1,2],start=4,after_first=[2])
    # Two selections before the boundary: the later one is executed (characterised).
    play('two-queued-selections',[1,5,4,5],start=1,after_first=[4,5])
    # Song mode off: no automatic progression; a manual selection still takes over at the boundary.
    set_mosaic_options(c,[('Song mode',False)])
    play('off-holds-slot',[1,1,1,1],start=1)
    play('off-manual-selection',[1,2,2,2],start=1,after_first=[2])
    # Re-enabled: progression resumes from the current slot's group.
    set_mosaic_options(c,[('Song mode',True)])
    play('on-again',[2,1,2,1],start=2)
