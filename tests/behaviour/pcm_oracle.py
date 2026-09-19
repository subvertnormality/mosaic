"""Independent windowed oracle for dry monophonic PCM, not arbitrary synthesis.

Expected sample times come from an independently established capture timeline.
This module never estimates a time offset or learns a golden from actual output.
Short events without an observable interior are rejected, not silently ignored.
"""
import array,cmath,math,struct,sys
from pathlib import Path

def read_wav(path):
    data=Path(path).read_bytes()
    assert len(data)>=12 and data[:4]==b'RIFF' and data[8:12]==b'WAVE','Invalid WAV header'
    assert struct.unpack_from('<I',data,4)[0]+8==len(data),'WAV length mismatch'
    chunks={};offset=12
    while offset<len(data):
        assert offset+8<=len(data),'Truncated chunk header'
        name,size=struct.unpack_from('<4sI',data,offset);offset+=8
        assert offset+size<=len(data),'Truncated WAV chunk'
        if name in (b'fmt ',b'data'):
            assert name not in chunks,'Duplicate WAV audio chunk'
            chunks[name]=data[offset:offset+size]
        offset+=size+(size%2)
    assert offset==len(data) and b'fmt ' in chunks and b'data' in chunks,'Missing WAV chunk'
    assert len(chunks[b'fmt '])>=16,'Short WAV format'
    encoding,channels,rate,byte_rate,align,bits=struct.unpack_from('<HHIIHH',chunks[b'fmt '])
    assert channels in (1,2) and 8000<=rate<=192000,'Unsupported channel count or sample rate'
    assert (encoding,bits) in ((1,16),(3,32)),'Unsupported PCM format'
    assert align==channels*bits//8 and byte_rate==rate*align,'Inconsistent WAV format'
    assert len(chunks[b'data'])>0 and len(chunks[b'data'])%align==0,'Partial or empty PCM frame'
    values=array.array('h' if encoding==1 else 'f',chunks[b'data'])
    if sys.byteorder!='little':values.byteswap()
    values=[v/32768 if encoding==1 else float(v) for v in values]
    assert all(math.isfinite(v) for v in values),'Nonfinite PCM'
    assert max(abs(v) for v in values)<.999,'Clipped PCM'
    return rate,[values[ch::channels] for ch in range(channels)]

def analyse(samples,rate,*,notes=range(48,85),window_seconds=.04,hop_seconds=.01,silence_rms=.001):
    assert rate>0 and samples and all(math.isfinite(x) for x in samples),'Invalid samples'
    size=round(window_seconds*rate);hop=round(hop_seconds*rate)
    assert size>=16 and 0<hop<=size and len(samples)>=size,'Unobservable capture'
    weights=[.5-.5*math.cos(2*math.pi*i/(size-1)) for i in range(size)]
    kernels={note:[w*cmath.exp(-2j*math.pi*(440*2**((note-69)/12))*i/rate) for i,w in enumerate(weights)] for note in notes}
    assert kernels,'Empty pitch domain'
    frames=[]
    for start in range(0,len(samples)-size+1,hop):
        section=samples[start:start+size]
        rms=math.sqrt(sum(x*x for x in section)/size)
        if rms<silence_rms:note=None;confidence=None
        else:
            mean=sum(section)/size;centered=[x-mean for x in section]
            powers={n:abs(sum(x*k for x,k in zip(centered,kernel)))**2 for n,kernel in kernels.items()}
            note=max(powers,key=powers.get)
            total=sum((x*w)**2 for x,w in zip(centered,weights))
            confidence=powers[note]/(size*total) if total else 0
            # Attack/release windows can contain too little periodic signal.
            # Preserve an explicit non-silence label; timeline validation decides
            # whether this frame is inside its predeclared boundary exclusion.
            if confidence<=.08:note='unclassified'
        frames.append(dict(time=(start+size/2)/rate,note=note,rms=rms,confidence=confidence))
    return frames,size/(2*rate),hop/rate

def verify_timeline(channels,rate,events,*,timing_tolerance=.01,silence_rms=.001):
    """Events: channel(0-based), note48..84, onset/offset in capture seconds.

    Every measurable frame on every channel is checked, including rests and tail.
    Only fixed window-halfwidth + timing-tolerance boundary bands are excluded.
    This is a windowed pitch/activity contract, not sample-accurate attack timing.
    """
    assert channels and len({len(c) for c in channels})==1,'Unequal channel lengths'
    duration=len(channels[0])/rate
    assert timing_tolerance>=0 and silence_rms>0 and events,'Invalid oracle contract'
    for e in events:
        assert type(e['channel']) is int and 0<=e['channel']<len(channels),'Invalid event channel'
        assert type(e['note']) is int and 48<=e['note']<=84,'Pitch outside calibrated domain'
        assert 0<=e['onset']<e['offset']<=duration,'Invalid event interval'
    checks=[]
    for channel,samples in enumerate(channels):
        frames,half,hop=analyse(samples,rate,silence_rms=silence_rms)
        selected=sorted([e for e in events if e['channel']==channel],key=lambda e:e['onset'])
        assert all(a['offset']<=b['onset'] for a,b in zip(selected,selected[1:])),'Polyphony outside this oracle contract'
        margin=half+timing_tolerance
        assert all(e['offset']-e['onset']>2*margin+hop for e in selected),'Event too short for observable interior'
        interiors=[0]*len(selected);guarded=0;verified=0
        for frame in frames:
            t=frame['time']
            if any(abs(t-e[k])<=margin for e in selected for k in ('onset','offset')):
                guarded+=1;continue
            active=[i for i,e in enumerate(selected) if e['onset']<t<e['offset']]
            expected=selected[active[0]]['note'] if active else None
            assert frame['note']==expected,dict(channel=channel,time=t,expected=expected,actual=frame['note'],rms=frame['rms'])
            if active:interiors[active[0]]+=1
            verified+=1
        assert verified>0 and all(interiors),'No observable event interior'
        checks.append(dict(channel=channel,verified_frames=verified,boundary_frames=guarded,event_interior_frames=interiors,margin_seconds=margin))
    return dict(passed=True,checks=checks,events=events,domain='dry-monophonic-MIDI48..84',absolute_latency_verified=False)
