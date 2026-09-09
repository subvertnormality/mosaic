"""Native stock-parameter precedence; literal MIDI and musical-time oracles."""

def fixed_note_domain(c,start=0,count=16):
    from cases import assign_trig_parameter,assert_durations
    assert 0<=start<128 and 1<=count<=16 and start+count<=128
    c.configure();c.enc(1,-3)
    assign_trig_parameter(c,'Fixed Note')
    for label,value in [('Quantised Fixed Note',7),('Random Note',4),('Twos Random Note',4)]:
        c.enc(2,1);assign_trig_parameter(c,label)
        c.enc(3,value+(1 if label=='Quantised Fixed Note' else 0))
    c.enc(2,-3);c.enc(3,start+1)
    def phrase(pitches,label):
        notes=c.playback([(1,[144,pitch,velocity]) for pitch,velocity in zip(pitches,(127,117,107,97))],cycles=2)
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        origin=notes[0][field]
        errors=[(note[field]-origin)/1e9-i/6 for i,note in enumerate(notes)]
        assert all(abs(error)<=tolerance for error in errors),errors
        assert_durations(c,notes,[1]*(len(notes)-1))
        c.results.append(dict(kind='fixed-note-precedence',phase=label,pitches=pitches,other_sources=['pattern','quantised-fixed7','random4','twos4'],timing_errors=errors,passed=True))
    for pitch in range(start,start+count):
        if pitch>start:c.enc(3,1)
        phrase([pitch]*4,str(pitch))
    if start+count==128:
        c.enc(3,3);phrase([127]*4,'upper-clamp')
    # Disable all four sources using real encoder saturation, then require the
    # original four-note/velocity phrase. No inferred random-output golden.
    for slot in (1,2,3,4):
        if slot>1:c.enc(2,1)
        c.elapse(.05);c.action(type='enc',n=3,delta=-126);c.elapse(.15)
    phrase([60,62,64,65],'all-overrides-off')


def quantised_fixed_table(c,profile='major'):
    from cases import assign_trig_parameter,assert_durations
    # Literal musical tables, independent of Mosaic's quantiser. Root shifts
    # retain the scale's lower endpoint; ties choose the lower legal pitch.
    tables={
        'major':[(0,0),(1,0),(3,2),(6,5),(7,7),(11,11),(12,12),
                 (60,60),(61,60),(63,62),(66,65),(70,69),(126,125),(127,127)],
        'd-major':[(0,2),(1,2),(60,59),(61,61),(63,62),(127,127)],
        'a-harmonic-minor':[(125,125),(126,125),(127,125)],
    }
    assert profile in tables
    c.configure()
    if profile!='major':
        c.tap(4,8)
        if profile=='a-harmonic-minor':c.enc(3,3) # Major -> Harmonic Minor
        c.enc(2,-1);c.enc(3,9 if profile=='a-harmonic-minor' else 2)
        c.key(3);c.tap(3,8)
    c.enc(1,-3);assign_trig_parameter(c,'Quantised Fixed Note')
    previous=-1
    for value,pitch in tables[profile]:
        c.enc(3,value-previous);previous=value
        notes=c.playback([(1,[144,pitch,v]) for v in (127,117,107,97)],cycles=2)
        assert_durations(c,notes,[1]*(len(notes)-1))
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        errors=[(note[field]-notes[0][field])/1e9-i/6 for i,note in enumerate(notes)]
        assert all(abs(error)<=tolerance for error in errors),errors
        c.results.append(dict(kind='quantised-fixed-musical-table',profile=profile,input=value,pitch=pitch,timing_errors=errors,passed=True))
