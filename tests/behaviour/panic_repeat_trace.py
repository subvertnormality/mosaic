"""Ordered MIDI oracle for panic restarted before the prior sweep completes."""
def verify_restarted_sweeps(events, repeats):
    assert repeats in (2,3)
    expected=[[128+channel,note,0] for note in range(128) for channel in range(16)]
    assert events and all(e['port'] in (1,2,3) for e in events),'Unexpected/missing port'
    lengths=[]
    for port in (1,2,3):
        actual=[e['bytes'] for e in events if e['port']==port]
        starts=[i for i,data in enumerate(actual) if data==[128,0,0]]
        assert len(starts)==repeats and starts[0]==0,'Missing/extra panic restart'
        ends=starts[1:]+[len(actual)]
        segments=[actual[start:end] for start,end in zip(starts,ends)]
        for prefix in segments[:-1]:
            assert 16<=len(prefix)<2048 and len(prefix)%16==0,'Previous sweep did not stop mid-job'
            assert prefix==expected[:len(prefix)],'Dropped/reordered/extra prefix output'
        assert segments[-1]==expected,'Final restarted sweep incomplete or changed'
        lengths.append([len(segment) for segment in segments])
    assert lengths[0]==lengths[1]==lengths[2],'Ports diverged at restart'
    return dict(kind='panic-in-flight-restarts',repeats=repeats,segment_lengths=lengths,passed=True)
