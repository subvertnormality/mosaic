"""README "Typical Workflow" as one executable composition (MAN-020..027).

Every expectation is derived here from interval tables and the manual's merge
rules; nothing is read back from Mosaic's model.
"""
from driver import Driver

D_MAJOR=[62,64,66,67,69,71,73]         # slot 2: root D
D_PENT={62,64,66,69,71}                  # README MAN-102: major degrees 1/2/3/5/6
def deg(d):return D_MAJOR[d%7]+12*(d//7)

# Pattern 1 steps 1-4 degrees 0/1/2/3 (vel 127/117/107/97); pattern 2 steps 1 and 3 degrees 4/6 (vel 100).
CH1_SKIP={2:(deg(1),117),4:(deg(3),97)}                        # overlaps deactivate (default Skip)
CH1_ALL={1:(deg(2),127),2:(deg(1),117),3:(deg(4),107),4:(deg(3),97)} # Average of 0,4 -> 2 and 2,6 -> 4, pattern-1 velocity
assert all(CH1_ALL[s][0] in D_PENT for s in (1,3))                 # merged results already pentatonic
CH2={1:(deg(4),100),3:(76,90)}                                     # pattern 2, step 3 replaced by keyboard E4 (in D major)

def expected_stream(slots):
    """[(port,status,note,velocity,step_index)] over consecutive 4-step song slots."""
    rows=[]
    for index,(ch1,ch2,octave) in enumerate(slots):
        for step in range(1,5):
            if step in ch1:rows.append((1,144,ch1[step][0]+12*octave,ch1[step][1],index*4+step-1))
            if step in ch2:rows.append((2,145,ch2[step][0],ch2[step][1],index*4+step-1))
    return rows

def verify(d,stage,slots,cycles=2):
    expected=expected_stream(slots);length=4*len(slots)
    marker=d.snapshot()['midi_count'];d.tap(1,8)
    want=len(expected)*cycles+1
    state=d.wait(lambda s:sum(1 for m in s['midi'] if m['index']>marker and m['bytes'][0] in (144,145) and m['bytes'][2]>0)>=want,timeout=3+length*cycles/6)
    d.tap(1,8);d.wait(lambda s:not s['midi_capture']['outstanding'])
    ons=[m for m in state['midi'] if m['index']>marker and m['bytes'][0] in (144,145) and m['bytes'][2]>0][:len(expected)*cycles]
    field='logical_ns' if d.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if d.clock_mode=='controlled-experimental' else .01
    for port in (1,2):
        wanted=[r for i in range(cycles) for r in [(p,s,n,v,t+i*length) for p,s,n,v,t in expected if p==port]]
        actual=[m for m in ons if m['port']==port]
        assert [(m['bytes'][0],m['bytes'][1],m['bytes'][2]) for m in actual]==[(s,n,v) for _,s,n,v,_ in wanted],(stage,port,[m['bytes'] for m in actual],wanted)
        if not wanted:continue # silent port, proven by the equality above
        origin=actual[0][field]-wanted[0][4]/6*1e9
        for m,row in zip(actual,wanted):assert abs((m[field]-origin)/1e9-row[4]/6)<=tolerance,(stage,port,row)
    d.results.append(dict(kind='composition-workflow',stage=stage,expected=expected,cycles=cycles,passed=True))

def build_composition(c,check=None):
    """The workflow project; check(stage, slots) runs after each workflow stage when given."""
    check=check or (lambda stage,slots:None)
    def edit_root(semitones):c.enc(2,-1);c.enc(3,semitones);c.key(3);c.enc(2,1)
    c.configure()
    c.tap(5,8);c.tap(2,1);c.tap(1,4);c.tap(3,4);c.tap(5,8);c.tap(1,3);c.tap(3,1);c.tap(3,8)
    c.tap(4,8);c.tap(2,3);edit_root(2);c.tap(3,8)
    c.tap(2,2);check('default-skip',[(CH1_SKIP,{},0)])
    c.tap(14,8);c.tap(14,8);c.led_values([(14,8)],[8])
    c.hold_tap((16,8),(1,2))
    check('merge-all-average',[(CH1_ALL,{},0)])
    c.tap(2,1);c.enc(3,1);c.enc(2,1);c.enc(3,1);c.enc(2,1);c.enc(3,1);c.key(3)
    c.tap(2,2);c.hold_tap((1,4),(4,4))
    c.enc(1,-4);c.screen_header('Ch. 2 Note Masks',selected=1)
    c.action(type='grid',x=3,y=4,state=1)
    try:c.action(type='midi',port=1,bytes=[144,76,90]);c.elapse(.05);c.action(type='midi',port=1,bytes=[128,76,0])
    finally:c.action(type='grid',x=3,y=4,state=0)
    c.elapse(.1);c.tap(1,1)
    check('two-channels-with-melody',[(CH1_ALL,CH2,0)])
    c.tap(6,8);c.tap(2,7)
    for _ in range(3):c.tap(8,7)
    c.hold_tap((1,1),(2,1));c.tap(2,1);c.tap(3,8);c.tap(1,1);c.tap(11,8);c.tap(6,8);c.tap(1,1);c.tap(3,8)
    return [(CH1_ALL,CH2,0),(CH1_ALL,CH2,1)]

def composition_workflow(c):
    song=build_composition(c,lambda stage,slots:verify(c,stage,slots))
    verify(c,'chained-song',song)
    # Keep it: idle autosave, then a fresh process plays the same song.
    for _ in range(3):c.elapse(21)
    c.wait(lambda _:(c.data_directory/'autosave.ptn').is_file() and (c.data_directory/'autosave.pset').is_file())
    c.finish()
    out=c.out/'reloaded';out.mkdir()
    loaded=Driver(out,project_seed=c.data_directory,**c.launch_options)
    try:
        loaded.tap(3,8);verify(loaded,'reloaded-song',song)
    finally:loaded.finish()
    c.results.append(dict(kind='composition-workflow-session',nested=str(out),passed=True))
