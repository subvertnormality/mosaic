"""Global tempo bounds and cross-slot persistence through real norns controls."""
def song_tempo_bounds(c):
    import base64,time
    from cases import set_mosaic_options
    from frame_oracle import render
    from midi_window import MidiWindow
    from note_schedule import assert_schedule
    c.configure();c.tap(6,8);c.hold_tap((1,1),(2,1))
    c.tap(2,1);c.tap(3,8);c.tap(11,8);c.tap(6,8);c.tap(1,1)
    set_mosaic_options(c,[('Song mode',False)])
    c.enc(1,1) # Global settings, Tempo selected.
    def extreme(direction):
        for _ in range(5):c.action(type='enc',n=3,delta=126*direction);c.elapse(.03)
        c.key(3)
    for label,slot,bpm,edit in [('minimum',1,30,-1),('minimum-other-slot',2,30,0),('maximum',2,300,1),('maximum-other-slot',1,300,0),('restore',1,90,2),('restored-other-slot',2,90,0)]:
        c.tap(slot,1)
        if edit in (-1,1):extreme(edit)
        elif edit==2:extreme(-1);c.enc(3,60);c.key(3)
        expected=render([(0,26,15,str(bpm))])
        def feedback(state):
            actual=base64.b64decode(state['frame']['pixels_base64'])
            return all(actual[(y*128+x)*4+k]==expected[(y*128+x)*4+k] for y in range(20,28) for x in range(0,36) for k in range(3))
        c.wait(feedback)
        capture=MidiWindow(c.snapshot()['midi_count']);c.tap(1,8)
        c.wait(lambda state:capture.extend(state) and len(capture.note_ons())>=9,timeout=7)
        controlled=c.clock_mode=='controlled-experimental';lower=c.logical_ns if controlled else time.monotonic_ns()
        c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
        upper=c.logical_ns if controlled else time.monotonic_ns()
        c.elapse(.06);c.wait(lambda state:capture.extend(state) and not state['midi_capture']['outstanding'])
        notes=capture.note_ons();assert len(notes)>=9
        onsets=[(24*i,(60,62,64,65)[i%4]+12*(slot-1),(127,117,107,97)[i%4]) for i in range(len(notes))]
        field='logical_ns' if controlled else 'monotonic_ns'
        checks=assert_schedule(capture.events,onsets,[24]*len(notes),field=field,origin=notes[0][field],stop_bounds=(lower,upper),pulse_rate=bpm*96/60,tolerance=2e-9 if controlled else .01)
        c.results.append(dict(kind='song-global-tempo',stage=label,slot=slot,bpm=bpm,onsets=len(notes),release_checks=len(checks),passed=True))
