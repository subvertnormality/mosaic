"""Literal manual random domains with a separate native PRNG oracle."""
def random_note_domains(c,twos=False):
    import subprocess,json
    from cases import assign_trig_parameter,set_mosaic_options,assert_durations
    domains=[[0],[0,1],[-1,0,1],[-1,0,1,2],[-2,-1,0,1,2]]
    stages=[(0,value) if twos else (value,0) for value in range(5)]+[(4,4),(0,0)]
    # Use independently authored domain lists, not Mosaic transforms. Lua's
    # platform PRNG supplies an index; never fit an offset to captured output.
    code=['math.randomseed(42)']
    for a,b in stages:
        for _ in range(33):
            expr=[]
            for value,multiplier in [(a,1),(b,2)]:
                domain=[n*multiplier for n in domains[value]]
                expr.append('0' if value==0 else '({'+','.join(map(str,domain))+'})[math.random(1,'+str(len(domain))+')]')
            code.append('print('+ '+'.join(expr)+')')
    proc=subprocess.run(['lua5.3','-e',';'.join(code)],capture_output=True,text=True,check=True)
    offsets=[int(line) for line in proc.stdout.splitlines()];assert len(offsets)==33*len(stages)
    c.configure();set_mosaic_options(c,[('Lock random to pent.',False),('Lock merged to pent.',False)])
    c.enc(1,-3);assign_trig_parameter(c,'Random Note')
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
            pitches.append(60+12*(degree//7)+[0,2,4,5,7,9,11][degree%7])
        before=c.snapshot()['midi_count'];c.tap(1,8)
        def onsets(state):return [m for m in state['midi'] if m['index']>before and m['bytes'][0]&240==144 and m['bytes'][2]>0]
        state=c.wait(lambda state:len(onsets(state))>=33,timeout=8)
        notes=onsets(state)
        expected=[(1,[144,p,[127,117,107,97][i%4]]) for i,p in enumerate(pitches)]
        assert [(n['port'],n['bytes']) for n in notes]==expected,dict(expected=expected,actual=[(n['port'],n['bytes']) for n in notes])
        c.tap(1,8);c.wait(lambda state:state['midi_capture']['outstanding']==[])
        assert_durations(c,notes,[1]*32)
        for i,note in enumerate(notes):assert abs((note[field]-notes[0][field])/1e9-i/6)<=tolerance
        c.results.append(dict(kind='random-note-domain',random=a,twos=b,seed=42,offsets=shifts,allowed=sorted(allowed),pitches=pitches,passed=True))
