"""Literal manual random domains with a separate native PRNG oracle."""
def random_note_domains(c,twos=False,pentatonic=False,mask=None):
    import subprocess,json
    from cases import assign_trig_parameter,set_mosaic_options,assert_durations
    domains=[[0],[0,1],[-1,0,1],[-1,0,1,2],[-2,-1,0,1,2]]
    stages=[(0,value) if twos else (value,0) for value in range(5)]+[(4,4),(0,0)]
    if pentatonic:stages=[(4,0),(0,4),(4,4),(0,0)]
    # Use independently authored domain lists, not Mosaic transforms. Lua's
    # platform PRNG supplies an index; never fit an offset to captured output.
    code=['math.randomseed(42)']
    for a,b in stages:
        for _ in range(33):
            expr=[]
            for value,multiplier in [(a,1),(b,2)]:
                domain=[n*multiplier for n in domains[value]]
                expr.append('0' if value==0 else '({'+','.join(map(str,domain))+'})[math.random(1,'+str(len(domain))+')]')
            code.append('do local a='+expr[0]+';local b='+expr[1]+';print(a,b,a+b) end')
    proc=subprocess.run(['lua5.3','-e',';'.join(code)],capture_output=True,text=True,check=True)
    components=[tuple(map(int,line.split())) for line in proc.stdout.splitlines()];offsets=[row[2] for row in components];assert len(offsets)==33*len(stages)
    c.configure();set_mosaic_options(c,[('Lock random to pent.',pentatonic),('Lock merged to pent.',False)])
    if mask:
        assert mask in ('full','snap','raw')
        set_mosaic_options(c,[('Quantise note masks',mask=='full'),('Snap note masks to scale',mask=='snap')])
        c.enc(1,-4)
        for step,pitch in enumerate([60,62,64,65],1):
            c.action(type='grid',x=step,y=4,state=1)
            try:c.enc(3,pitch+1)
            finally:c.action(type='grid',x=step,y=4,state=0)
            c.elapse(.06)
        c.enc(1,1)
    else:c.enc(1,-3)
    assign_trig_parameter(c,'Random Note')
    c.enc(2,1);assign_trig_parameter(c,'Twos Random Note');c.enc(2,-1)
    previous=(0,0);field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    for stage,(a,b) in enumerate(stages):
        c.enc(3,a-previous[0]);c.enc(2,1);c.enc(3,b-previous[1]);c.enc(2,-1);previous=(a,b)
        shifts=offsets[33*stage:33*(stage+1)]
        allowed={x+2*y for x in domains[a] for y in domains[b]}
        assert set(shifts)<=allowed
        if (a==0)!=(b==0):assert set(shifts)==allowed,'Seed must exercise every documented single-param offset'
        pitches=[]
        for i,shift in enumerate(shifts):
            degree=i%4+shift
            pitch=60+12*(degree//7)+[0,2,4,5,7,9,11][degree%7]
            if pentatonic and shift!=0 and mask not in ('raw','snap'):
                # Codex-arbitrated nonzero sum: both signs snap; sampled zero
                # and cancellation preserve the unmodified note.
                available=[12*octave+n for octave in range(11) for n in [0,2,4,7,9]]
                pitch=min(available,key=lambda n:(abs(n-pitch),n))
            if mask in ('raw','snap'):
                pitch=[60,62,64,65][i%4]+shift
                if mask=='snap':
                    available=[12*octave+n for octave in range(11) for n in [0,2,4,5,7,9,11]]
                    pitch=min(available,key=lambda n:(abs(n-pitch),n))
            pitches.append(pitch)
        before=c.snapshot()['midi_count'];c.tap(1,8)
        def onsets(state):return [m for m in state['midi'] if m['index']>before and m['bytes'][0]&240==144 and m['bytes'][2]>0]
        state=c.wait(lambda state:len(onsets(state))>=33,timeout=8)
        notes=onsets(state)
        expected=[(1,[144,p,[127,117,107,97][i%4]]) for i,p in enumerate(pitches)]
        assert [(n['port'],n['bytes']) for n in notes]==expected,dict(expected=expected,actual=[(n['port'],n['bytes']) for n in notes])
        c.tap(1,8);c.wait(lambda state:state['midi_capture']['outstanding']==[])
        assert_durations(c,notes,[1]*32)
        for i,note in enumerate(notes):assert abs((note[field]-notes[0][field])/1e9-i/6)<=tolerance
        c.results.append(dict(kind='random-note-domain',pentatonic=pentatonic,random=a,twos=b,seed=42,mask=mask,components=components[33*stage:33*(stage+1)],offsets=shifts,allowed=sorted(allowed),pitches=pitches,passed=True))
