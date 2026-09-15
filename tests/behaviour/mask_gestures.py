"""Shift-grid trig mask gestures with independent whole-grid and MIDI oracles."""

def trig_gesture_all_steps(c):
    from cases import assert_durations
    c.configure();c.tap(1,2);c.hold_tap((1,4),(16,7));c.enc(1,-4)
    # No assigned pattern. Required defaults make newly added trigs audible.
    c.enc(3,61);c.enc(2,1);c.enc(3,101);c.enc(2,1);c.enc(3,14)
    def toggle(steps):
        c.action(type='key',n=1,state=1);c.elapse(.3)
        try:
            for step in steps:c.tap((step-1)%16+1,(step-1)//16+4)
        finally:c.action(type='key',n=1,state=0)
        c.elapse(.1)
    def verify(active,stage):
        def grid_matches(state):
            for step in range(1,65):
                level=state['grid'][(step-1)//16*16+(step-1)%16+48]
                if level not in ((12,15) if step in active else (1,2)):return False
            return True
        c.wait(grid_matches)
        phrase=[(1,[144,60,100]) for _ in active]
        notes=c.playback(phrase,cycles=2,timeout=26)
        assert_durations(c,notes,[1]*(len(active)*2))
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        for i,note in enumerate(notes):
            steps=(i//len(active))*64+active[i%len(active)]-active[0]
            assert abs((note[field]-notes[0][field])/1e9-steps/6)<=tolerance
        c.results.append(dict(kind='trig-mask-all64-gesture',stage=stage,active_steps=active,grid_cells=64,passed=True))
    all_steps=list(range(1,65));odd=list(range(1,65,2));even=list(range(2,65,2))
    toggle(all_steps);verify(all_steps,'all64-added-without-pattern')
    toggle(odd);verify(even,'odd-steps-removed-even-preserved')
    toggle(all_steps);verify(odd,'all64-toggled-odd-only')
    toggle(even);verify(all_steps,'even-restored-all64')


def held_keyboard_chord(c,grid_first=False,extra_note=False,rearticulate=False):
    from cases import assert_durations
    c.configure();c.enc(1,-4)
    pitches=[72,76,79,83,86];velocities=[90,80,70,60,50]
    if extra_note:pitches.append(88);velocities.append(40)
    marker=c.snapshot()['midi_count']
    c.action(type='grid',x=2,y=4,state=1)
    for pitch,velocity in zip(pitches,velocities):c.action(type='midi',port=1,bytes=[144,pitch,velocity])
    if rearticulate:
        c.action(type='midi',port=1,bytes=[128,72,0]);c.elapse(.05)
        c.action(type='midi',port=1,bytes=[144,72,45])
    if grid_first:c.action(type='grid',x=2,y=4,state=0)
    for pitch in pitches:c.action(type='midi',port=1,bytes=[128,pitch,0])
    if not grid_first:c.action(type='grid',x=2,y=4,state=0)
    c.elapse(.15);state=c.wait(lambda state:not state['midi_capture']['outstanding'])
    preview=[(m['port'],m['bytes']) for m in state['midi'] if m['index']>marker and 128<=m['bytes'][0]<=159]
    expected=[(1,[144,p,v]) for p,v in zip(pitches,velocities)]
    if rearticulate:expected += [(1,[128,72,0]),(1,[144,72,45])]
    expected += [(1,[128,p,0]) for p in pitches]
    assert preview==expected,dict(expected=expected,actual=preview)
    def verify(chord,velocity,stage):
        phrase=[(1,[144,60,127])]+[(1,[144,p,velocity]) for p in chord]+[(1,[144,64,107]),(1,[144,65,97])]
        positions=[0]+[1]*len(chord)+[2,3]
        notes=c.playback(phrase,cycles=2,timeout=4);assert_durations(c,notes,[1]*(len(phrase)*2))
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        for i,note in enumerate(notes):
            wanted=((i//len(phrase))*4+positions[i%len(phrase)])/6
            assert abs((note[field]-notes[0][field])/1e9-wanted)<=tolerance
        c.results.append(dict(kind='held-keyboard-mask',stage=stage,grid_released_first=grid_first,extra_note=extra_note,rearticulate=rearticulate,chord=chord,velocity=velocity,passed=True))
    verify(pitches[:5],90,'five-voice-chord-committed')
    c.action(type='grid',x=2,y=4,state=1)
    c.action(type='midi',port=1,bytes=[144,67,55]);c.action(type='midi',port=1,bytes=[128,67,0])
    c.action(type='grid',x=2,y=4,state=0);c.elapse(.15)
    verify([67],55,'single-note-replaces-old-chord')


def multiheld_keyboard(c,release_first=True):
    from cases import assert_durations
    c.configure();c.enc(1,-4)
    marker=c.snapshot()['midi_count']
    c.action(type='grid',x=2,y=4,state=1);c.action(type='grid',x=4,y=4,state=1)
    c.action(type='midi',port=1,bytes=[144,72,90]);c.action(type='midi',port=1,bytes=[128,72,0])
    released=2 if release_first else 4;remaining=4 if release_first else 2
    c.action(type='grid',x=released,y=4,state=0);c.elapse(.1)
    c.action(type='midi',port=1,bytes=[144,79,55]);c.action(type='midi',port=1,bytes=[128,79,0])
    c.action(type='grid',x=remaining,y=4,state=0);c.elapse(.15)
    state=c.wait(lambda state:not state['midi_capture']['outstanding'])
    preview=[(m['port'],m['bytes']) for m in state['midi'] if m['index']>marker and 128<=m['bytes'][0]<=159]
    assert preview==[(1,[144,72,90]),(1,[128,72,0]),(1,[144,79,55]),(1,[128,79,0])],preview
    phrase=[(1,[144,72,90]),(1,[144,64,107]),(1,[144,79,55])] if release_first else [(1,[144,79,55]),(1,[144,64,107]),(1,[144,65,97])]
    # The remaining held key defines range start on a dual release. Restore
    # a valid range explicitly to isolate keyboard targeting from reversed ranges.
    c.hold_tap((2,4),(4,4))
    notes=c.playback(phrase,cycles=3,timeout=4);assert_durations(c,notes,[1]*9)
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    for i,note in enumerate(notes):assert abs((note[field]-notes[0][field])/1e9-i/6)<=tolerance
    c.led_values([(1,4),(5,4),(16,7)],[0,0,0])
    c.results.append(dict(kind='multiheld-keyboard',first_released=release_first,range=[2,4],expected=phrase,passed=True))
