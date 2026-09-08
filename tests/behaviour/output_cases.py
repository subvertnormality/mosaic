"""Mosaic-owned output workflows through public native controls and capture."""
import base64,json,time
from frame_oracle import render
from jf_oracle import verify_unplayed,verify_session_export

def jf_mono_phrase(c):
    assert c.profile in ('crow-jf','mixed-outputs'), 'JF output profile required'
    c.configure();c.screen_header('Ch. 1 Device Config')
    expected=render([(10,35,15,'Jf N 1')])
    indices=[(y*128+x)*4+k for y in range(27,37) for x in range(10,62) for k in range(3)]
    def selected(state):
        pixels=base64.b64decode(state['frame']['pixels_base64'])
        return all(pixels[i]==expected[i] for i in indices)
    for attempt in range(40):
        if selected(c.snapshot()):break
        c.enc(3,1)
    else:raise AssertionError('JF mono voice1 not visible in device picker')
    c.results.append(dict(kind='device-picker-frame',label='Jf N 1',matched=True))
    c.key(3)
    cursor=0;seen=[]
    def drain():
        nonlocal cursor
        while True:
            page=c.runtime.crow_ii_read(cursor)
            seen.extend(page['records']);cursor=page['cursor']
            if not page['has_more']:break
    drain();verify_unplayed(seen,'startup');assert any(p['bytes']==[6,1] for p in seen),'JF mode setup missing'
    start=len(seen);midi_start=c.snapshot()['midi_count'];c.tap(1,8)
    deadline=time.monotonic()+5
    while True:
        drain()
        if sum(p['bytes'][0]==8 for p in seen[start:])>=8:break
        assert time.monotonic()<deadline,'Missing complete two-cycle JF phrase'
        c.elapse(.02)
    c.tap(1,8);c.elapse(.3);drain()
    packets=seen[start:];notes=[p for p in packets if p['bytes'][0]==8]
    assert len(notes)==8,('Unexpected JF note count',len(notes))
    pitches=[60,62,64,65]*2;levels=[]
    for packet,note in zip(notes,pitches):
        b=packet['bytes'];assert packet['address']==0x70 and len(b)==6 and b[1]==1,packet
        pitch=int.from_bytes(bytes(b[2:4]),'big',signed=True)
        # Player reference: C4 is0V, octave is1V; pinned Crow wire unit is1638.3/V.
        assert abs(pitch-(note-60)*1638.3/12)<=1.1,(note,pitch)
        levels.append(int.from_bytes(bytes(b[4:6]),'big',signed=True))
    for offset in (0,4):
        assert abs(levels[offset]-5*1638.3)<=1.1,'Full velocity must reach5V'
        assert all(a>b>0 for a,b in zip(levels[offset:offset+3],levels[offset+1:offset+4]))
    assert levels[:4]==levels[4:],'Repeated phrase velocity changed'
    assert any(p['bytes']==[1,1,0] for p in packets),'Missing voice1 release'
    assert packets[-1]['bytes'] in ([1,1,0],[1,0,0]),'Final packet must release voice(s)'
    assert all(p['bytes'][0] in (1,6,8) for p in packets),'Unexpected JF command'
    assert not any(e['index']>midi_start and e['bytes'][0]&240==144 and e['bytes'][2]>0 for e in c.snapshot()['midi']), 'JF phrase leaked to MIDI'
    c.finish()
    full=[json.loads(line) for line in (c.out/'native/crow-ii.jsonl').read_text().splitlines()]
    assert [p['sequence'] for p in full]==list(range(1,len(full)+1)),'Incomplete ii export'
    verify_session_export(full,seen)
    c.results.append(dict(kind='mosaic-jf-mono-phrase',notes=8,pitches=pitches,levels=levels,passed=True,
        limits='Pitch/route/release and monotonic velocity only; full velocity mapping, voice lifecycle and musical timing matrices remain pending'))
    (c.out/'results.json').write_text(json.dumps(c.results,indent=2)+'\n')


def doubledecker_audition(c):
    from pcm_oracle import read_wav,verify_timeline,analyse
    from pathlib import Path
    import hashlib
    assert c.profile in ('nb-audio','mixed-outputs'),'Audio output profile required'
    c.configure();c.screen_header('Ch. 1 Device Config')
    expected=render([(10,35,15,'Doubledecker')])
    indices=[(y*128+x)*4+k for y in range(27,37) for x in range(10,62) for k in range(3)]
    def selected(state):
        pixels=base64.b64decode(state['frame']['pixels_base64'])
        return all(pixels[i]==expected[i] for i in indices)
    for attempt in range(40):
        if selected(c.snapshot()):break
        c.enc(3,1)
    else:raise AssertionError('Doubledecker not visible in device picker')
    c.key(3);c.elapse(13) # Upstream startup diagnostic tone is outside measurement.
    def capture(label):
        job=c.runtime.capture_start(1)
        deadline=time.monotonic()+5
        while job['status']=='capturing':
            assert time.monotonic()<deadline,'Capture did not finish'
            c.elapse(.03);job=c.runtime.capture_status(job['job_id'])
        assert job['status']=='complete',job
        path=Path(job['output']);assert hashlib.sha256(path.read_bytes()).hexdigest()==job['sha256']
        rate,channels=read_wav(path)
        assert len(channels)==2 and all(len(ch)==rate for ch in channels)
        c.results.append(dict(kind='native-audio-capture',label=label,job=job))
        return rate,channels
    rate,channels=capture('stopped-baseline')
    for channel in channels:
        frames,_,_=analyse(channel,rate)
        assert all(f['note'] is None for f in frames),'Unexpected baseline sound'
    before=c.snapshot()['midi_count']
    for note in (60,64,67):
        c.action(type='midi',port=1,bytes=[144,note,127])
        try:
            c.elapse(1.2) # Default50ms attack +1s decay; steady sustain window.
            rate,channels=capture('held-'+str(note))
            contract=[dict(channel=i,note=note,onset=0,offset=1) for i in (0,1)]
            result=verify_timeline(channels,rate,contract)
            c.results.append(dict(kind='held-note-PCM',note=note,result=result))
        finally:c.action(type='midi',port=1,bytes=[128,note,0])
        c.elapse(6) # Bounded release/effect-tail contract; not exact note-off latency.
        rate,channels=capture('released-'+str(note))
        for channel in channels:
            frames,_,_=analyse(channel,rate)
            assert all(f['note'] is None for f in frames),('Sound remains after release',note)
    assert not any(e['index']>before and e['bytes'][0]&240==144 and e['bytes'][2]>0 for e in c.snapshot()['midi']),'Audio audition leaked MIDI notes'
    c.results.append(dict(kind='doubledecker-audition',notes=[60,64,67],stereo=True,release_bound_seconds=6,passed=True,
        limitations='Steady held-note pitch/activity and bounded release only; onset/duration/absolute latency and sequenced/polyphonic audio remain pending'))


def select_visible_player(c,label):
    """Select by independently rendered display text, never a saved option index."""
    expected=render([(10,35,15,label)])
    indices=[(y*128+x)*4+k for y in range(27,37) for x in range(10,62) for k in range(3)]
    def selected():
        pixels=base64.b64decode(c.snapshot()['frame']['pixels_base64'])
        return all(pixels[i]==expected[i] for i in indices)
    # Return to the first device using the same encoder as a user.
    c.enc(3,-40)
    for _ in range(40):
        if selected():break
        c.enc(3,1)
    else:raise AssertionError('Player not visible: '+label)
    c.results.append(dict(kind='device-picker-frame',label=label,matched=True))
    c.key(3);c.elapse(.3)


def jf_keyboard_ownership(c):
    assert c.profile in ('crow-jf','mixed-outputs'),'JF profile required'
    c.configure()
    cursor=0;trace=[];accounted=0
    def drain():
        nonlocal cursor
        while True:
            page=c.runtime.crow_ii_read(cursor);trace.extend(page['records']);cursor=page['cursor']
            if not page['has_more']:break
    def check(expected,start):
        deadline=time.monotonic()+2
        while True:
            drain();actual=[p['bytes'] for p in trace[start:]]
            if len(actual)>=len(expected):break
            assert time.monotonic()<deadline,dict(expected=expected,actual=actual)
            c.elapse(.02)
        from jf_oracle import verify_packets
        verify_packets(trace[start:],expected,first_sequence=trace[start-1]['sequence']+1 if start else 1)
    midi_start=c.snapshot()['midi_count']
    for voices in ((1,2),(3,4),(5,6)):
        for channel,voice in zip((1,16),voices):
            c.tap(channel,1);c.screen_header('Ch. '+str(channel)+' Device Config',selected=5)
            select_visible_player(c,'Jf N '+str(voice))
        # Both selectors are compatible music-mode mono voices. No transport/recording.
        c.elapse(.5);drain();verify_unplayed(trace[accounted:],'startup' if accounted==0 else 'selection');accounted=len(trace)
        for order in ((0,1),(1,0)):
            start=len(trace);expected=[]
            for channel,voice,port,status in ((1,voices[0],1,144),(16,voices[1],2,159)):
                c.tap(channel,1)
                c.action(type='midi',port=port,bytes=[status,72,127])
                # C5=+1V and maximum velocity=5V, pinned Crow fixed-point units.
                expected.append([8,voice,6,102,31,255])
                check(expected,start)
            # Selection must not own a release. Both source releases occur on channel8.
            c.tap(8,1)
            for owner in order:
                c.action(type='midi',port=owner+1,bytes=[128 if owner==0 else 159,72,0])
                expected.append([1,voices[owner],0]);check(expected,start)
            c.elapse(.08);check(expected,start)
            accounted=len(trace)
            c.results.append(dict(kind='JF-keyboard-source-ownership',voices=voices,mosaic_channels=[1,16],pitch=72,release_order=order,expected=expected,passed=True))
    state=c.snapshot()
    assert not any(e['index']>midi_start and 128<=e['bytes'][0]<=159 for e in state['midi']),'JF keyboard leaked MIDI notes/releases'
    c.finish()
    full=[json.loads(line) for line in (c.out/'native/crow-ii.jsonl').read_text().splitlines()]
    assert [p['sequence'] for p in full]==list(range(1,len(full)+1))
    verify_session_export(full,trace)
    c.results.append(dict(kind='JF-keyboard-ownership-summary',finite_mono_voices=6,release_orders=2,passed=True,limitations='Disarmed same-pitch source ownership and selected-channel changes only; reassignment during hold, transport overlap and incompatible modes remain separate cases'))
    (c.out/'results.json').write_text(json.dumps(c.results,indent=2)+'\n')


def jf_same_voice_overlap(c):
    from jf_oracle import verify_packets
    assert c.profile in ('crow-jf','mixed-outputs'),'JF profile required'
    c.configure();cursor=0;trace=[];accounted=0
    def drain():
        nonlocal cursor
        while True:
            page=c.runtime.crow_ii_read(cursor);trace.extend(page['records']);cursor=page['cursor']
            if not page['has_more']:break
    def check(expected,start):
        c.elapse(.08);drain()
        verify_packets(trace[start:],expected,first_sequence=trace[start-1]['sequence']+1 if start else 1)
    marker=c.snapshot()['midi_count']
    for voice in range(1,7):
        c.tap(1,1);select_visible_player(c,'Jf N '+str(voice));c.elapse(.5);drain();verify_unplayed(trace[accounted:],'startup' if accounted==0 else 'selection');accounted=len(trace)
        for order in ((0,1),(1,0)):
            c.tap(1,1);start=len(trace);expected=[]
            for port,status in ((1,144),(2,159)):
                c.action(type='midi',port=port,bytes=[status,72,127])
                expected.append([8,voice,6,102,31,255]);check(expected,start)
            c.tap(16,1)
            for index,owner in enumerate(order):
                c.action(type='midi',port=owner+1,bytes=[128 if owner==0 else 159,72,0])
                # Pinned mono player gates until its last outstanding note releases.
                # First input release must not stop the second owner's held sound.
                if index==1:expected.append([1,voice,0])
                check(expected,start)
            accounted=len(trace)
            c.results.append(dict(kind='JF-same-voice-source-overlap',voice=voice,pitch=72,release_order=order,expected=expected,passed=True))
    assert not any(e['index']>marker and 128<=e['bytes'][0]<=159 for e in c.snapshot()['midi']),'JF overlap leaked MIDI'
    c.finish()
    full=[json.loads(line) for line in (c.out/'native/crow-ii.jsonl').read_text().splitlines()]
    verify_session_export(full,trace)
    c.results.append(dict(kind='JF-same-voice-summary',voices=6,release_orders=2,passed=True,limitations='Two distinct keyboard sources on one assigned mono player; sequenced/live overlap, stealing and repeated note-on from one source remain separate cases'))
    (c.out/'results.json').write_text(json.dumps(c.results,indent=2)+'\n')
