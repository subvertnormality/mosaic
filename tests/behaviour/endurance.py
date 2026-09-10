"""Ten-minute mixed endurance (BEHAVIOUR_PLAN central gates: 120 BPM, p99 <= 10 ms,
max <= 50 ms, final phase <= 20 ms, exact events, no stuck notes).

The workload is the README typical-workflow song: two instruments, merged
patterns, a melody mask and a two-slot song chain. The complete native export
is checked after the session closes; nothing is sampled or sorted away.
"""
import json

BPM=120;STEP=60/BPM/4;DURATION=600

def nearest_rank(values,percent):
    ordered=sorted(values);return ordered[(percent*len(ordered)+99)//100-1]

def endurance_mixed(c,duration=DURATION):
    from composition_workflow import build_composition,expected_stream
    import base64
    from frame_oracle import render
    song=build_composition(c)
    # Global tempo 90 -> 120 on the song page's second screen.
    c.tap(6,8);c.enc(1,1);c.enc(3,BPM-90);c.key(3)
    expected=render([(0,26,15,str(BPM))])
    c.wait(lambda s:all(base64.b64decode(s['frame']['pixels_base64'])[(y*128+x)*4+k]==expected[(y*128+x)*4+k] for y in range(20,28) for x in range(36) for k in range(3)))
    c.enc(1,-1);c.tap(3,8)
    marker=c.snapshot()['midi_count'] # build-phase keyboard monitoring precedes Play
    c.tap(1,8)
    remaining=duration
    while remaining>0:
        chunk=min(30,remaining);c.elapse(chunk);remaining-=chunk
        state=c.snapshot() # periodic liveness: runtime errors raise here
    c.tap(1,8);c.wait(lambda s:not s['midi_capture']['outstanding'],timeout=5)
    c.finish()
    events=[json.loads(line) for line in (c.out/'native/native-events.jsonl').read_text().splitlines()]
    emitted=[e for e in events if 'index' in e and 'bytes' in e]
    assert [e['index'] for e in emitted]==list(range(1,len(emitted)+1)),'Non-contiguous native export'
    emitted=[e for e in emitted if e['index']>marker]
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    plan=expected_stream(song);length=8 # two 4-step slots
    report=dict(kind='endurance',bpm=BPM,duration_seconds=duration,ports={})
    for port,status in ((1,144),(2,145)):
        ons=[e for e in emitted if e['port']==port and e['bytes'][0]==status and e['bytes'][2]>0]
        offs=[e for e in emitted if e['port']==port and (e['bytes'][0]==status-16 or (e['bytes'][0]==status and e['bytes'][2]==0))]
        cycle=[(n,v,t) for p,s,n,v,t in plan if p==port]
        wanted=[(cycle[i%len(cycle)][0],cycle[i%len(cycle)][1],cycle[i%len(cycle)][2]+length*(i//len(cycle))) for i in range(len(ons))]
        assert [(e['bytes'][1],e['bytes'][2]) for e in ons]==[(n,v) for n,v,_ in wanted],('Event stream',port)
        full_cycles=len(ons)//len(cycle);expected_cycles=duration/(length*STEP)
        assert full_cycles>=expected_cycles-2,('Lost cycles',port,full_cycles,expected_cycles)
        assert len(offs)==len(ons),('Unbalanced releases',port,len(ons),len(offs))
        origin=ons[0][field]-wanted[0][2]*STEP*1e9
        errors=[e[field]-(origin+t*STEP*1e9) for e,(_,_,t) in zip(ons,wanted)]
        absolute=[abs(x) for x in errors]
        p99,maximum,final=nearest_rank(absolute,99),max(absolute),errors[-1]
        report['ports'][port]=dict(note_ons=len(ons),full_cycles=full_cycles,p99_ns=p99,max_ns=maximum,final_phase_ns=final)
        assert p99<=10_000_000 and maximum<=50_000_000 and abs(final)<=20_000_000,('Central timing gates',port,report['ports'][port])
    report['passed']=True
    results=json.loads((c.out/'results.json').read_text())+[report]
    (c.out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
