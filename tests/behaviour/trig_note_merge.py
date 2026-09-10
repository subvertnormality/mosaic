"""Trig merge modes x note merge modes over overlapping patterns (README merge modes).

P1 trigs steps 1-3 with degrees 0/2/4 (step 4 holds degree 6 without a trig);
P2 trigs steps 2-4 with degrees 4/2/3. Only patterns with a trig on a step
contribute to its note merge; a single contributor passes through unchanged.
Velocity uses pattern 1 priority, so velocities are P1's 127/117/107/97.
"Lock merged to pent." defaults On: a result with two or more contributors
snaps to the C major selection (README MAN-102: degrees 1/2/3/5/6); a single
contributor is not a merge and is not snapped.
"""
MAJOR=[0,2,4,5,7,9,11]
P1={1:0,2:2,3:4};P2={2:4,3:2,4:3}
VELOCITY={1:127,2:117,3:107,4:97}
PENT=[0,2,4,7,9]

def merged_degree(step,mode):
    values=sorted(v for p in (P1,P2) for s,v in p.items() if s==step)
    if len(values)==1:return values[0]
    mean=sum(values)/len(values);average=int(mean//1+(1 if mean%1>=.5 else 0)) # greater integer at a half
    return {'average':average,'higher':average+values[-1]-values[0],'lower':2*values[0]-average}[mode]

def pitch(step,mode,pentatonic):
    value=60+MAJOR[merged_degree(step,mode)]
    if pentatonic and sum(step in p for p in (P1,P2))>1:
        available=[12*o+n for o in range(11) for n in PENT];value=min(available,key=lambda n:(abs(n-value),n))
    return value

def trig_steps(mode):
    counts={s:sum(s in p for p in (P1,P2)) for s in range(1,5)}
    return [s for s,n in counts.items() if n>0 and {'all':True,'skip':n==1,'only':n>1}[mode]]

def trig_note_merge_matrix(c):
    # Hand-worked anchors: step 2 and 3 average 3, higher 5, lower 1.
    assert [merged_degree(2,m) for m in ('average','higher','lower')]==[3,5,1]
    assert trig_steps('skip')==[1,4] and trig_steps('only')==[2,3] and trig_steps('all')==[1,2,3,4]
    c.configure()
    c.tap(5,8);c.tap(1,1);c.tap(4,4)                   # P1: remove the step-4 trig
    c.tap(5,8);c.tap(2,5);c.tap(3,3);c.tap(4,1)        # P1 degrees 0/2/4/6
    c.tap(5,8);c.tap(5,8);c.tap(2,1)                   # trig editor, pattern 2
    for x in (2,3,4):c.tap(x,4)
    c.tap(5,8)
    for x,degree in P2.items():c.tap(x,7-degree)
    c.tap(3,8);c.tap(2,2)                              # assign P2 to channel 1
    c.hold_tap((16,8),(1,2))                           # velocity priority: pattern 1
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    def phrase(trig_mode,note_mode,pentatonic=True):
        steps=trig_steps(trig_mode)
        expected=[(1,[144,pitch(s,note_mode,pentatonic),VELOCITY[s]]) for s in steps]
        notes=c.playback(expected,cycles=2)
        for i,(a,b) in enumerate(zip(notes,notes[1:])):
            left=steps[i%len(steps)];right=steps[(i+1)%len(steps)]
            assert abs((b[field]-a[field])/1e9-((right-left)%4 or 4)/6)<=tolerance,(trig_mode,note_mode,i)
        c.results.append(dict(kind='trig-note-merge',trig_mode=trig_mode,note_mode=note_mode,pentatonic=pentatonic,steps=steps,
                              pitches=[e[1][1] for e in expected],passed=True))
    # Trig button (14,8): Skip 2 -> Only 5 -> All 8. Note button (15,8): Average 2 -> Higher 5 -> Lower 8.
    for trig_mode,trig_level in (('skip',2),('only',5),('all',8)):
        if trig_mode!='skip':c.tap(14,8)
        c.led_values([(14,8)],[trig_level])
        for note_mode,note_level in (('average',2),('higher',5),('lower',8)):
            if note_mode!='average':c.tap(15,8)
            c.led_values([(15,8)],[note_level])
            phrase(trig_mode,note_mode)
        c.tap(15,8);c.led_values([(15,8)],[2])         # Lower -> Average
    # Merged-pentatonic Off: the same All matrix plays the unsnapped merge results.
    from cases import set_mosaic_options
    set_mosaic_options(c,[('Lock merged to pent.',False)])
    c.led_values([(14,8)],[8])
    for note_mode,note_level in (('average',2),('higher',5),('lower',8)):
        if note_mode!='average':c.tap(15,8)
        c.led_values([(15,8)],[note_level])
        phrase('all',note_mode,pentatonic=False)
