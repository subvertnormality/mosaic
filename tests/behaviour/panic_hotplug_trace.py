"""Literal panic output contract around native MIDI connection boundaries."""
def verify_hotplug_sweep(events, removed_before, reconnect_during):
    transitions=[e for e in events if e.get('kind')==18]
    assert [(e['port'],e['connected']) for e in transitions]==[(1,False),(1,True)]
    off,on=[e['monotonic_ns'] for e in transitions];assert off<on
    midi=[e for e in events if e.get('kind') in (3,11)]
    expected=[[128+channel,note,0] for note in range(128) for channel in range(16)]
    assert all(e['port'] in (1,2,3) and e['bytes'] in expected for e in midi),'Unexpected panic MIDI'
    for port in (2,3):assert [e['bytes'] for e in midi if e['port']==port]==expected,'Unaffected port sweep differs'
    other=[e for e in midi if e['port']==3]
    assert (off<other[0]['monotonic_ns'])==removed_before,'Removal missed intended panic interval'
    assert (on<other[-1]['monotonic_ns'])==reconnect_during,'Reconnection missed intended panic interval'
    own=[e for e in midi if e['port']==1]
    assert not [e for e in own if off<=e['monotonic_ns']<on],'Output while port absent'
    prefix=[e for e in own if e['monotonic_ns']<off];suffix=[e for e in own if e['monotonic_ns']>=on]
    if removed_before:
        assert not own,'Panic scheduled new work for a port absent at invocation'
    else:
        assert 16<=len(prefix)<1024 and [e['bytes'] for e in prefix]==expected[:len(prefix)],'Incomplete/changed connected prefix'
        # Each independent port coroutine advances one pitch per scheduler tick.
        # A transition can interleave within its 16-message pitch group, so bind
        # the edge to the neighbouring port with at most one pitch of ambiguity.
        reference=[e for e in midi if e['port']==2 and e['monotonic_ns']<off]
        assert 0<=len(prefix)-len(reference)<=16,'Prefix ended away from removal boundary'
        if reconnect_during:
            assert 16<=len(suffix)<1536 and [e['bytes'] for e in suffix]==expected[-len(suffix):],'Incomplete/changed restored suffix'
            reference=[e for e in midi if e['port']==2 and e['monotonic_ns']>=on]
            assert abs(len(suffix)-len(reference))<=16,'Suffix started away from reconnection boundary'
            assert len(prefix)+len(suffix)<2048,'Missed sweep work was replayed'
        else:assert not suffix,'Completed sweep replayed on reconnection'
    return dict(kind='panic-hotplug-sweep',removed_before=removed_before,reconnect_during=reconnect_during,prefix=len(prefix),suffix=len(suffix),unaffected_port_events=2048,passed=True)
