"""Independent exact-wire oracle for declared JF command recipes.

Command expectations come from the scenario's musical contract, not captured
output. Monotonic ordering is checked; absolute timing is not claimed here.
"""
def verify_packets(records,expected,first_sequence=1):
    assert len(records)==len(expected),dict(expected_count=len(expected),actual_count=len(records))
    previous=None
    for index,(record,command) in enumerate(zip(records,expected)):
        assert record['sequence']==first_sequence+index,'JF sequence gap or duplicate'
        assert record['address']==0x70,'Wrong ii address'
        timestamp=record['monotonic_ns']
        assert type(timestamp) is int and timestamp>=0,'Invalid ii timestamp'
        assert previous is None or timestamp>=previous,'Reordered ii timestamps'
        previous=timestamp
        assert all(type(byte) is int and 0<=byte<=255 for byte in record['bytes']),'Invalid ii byte'
        assert record['bytes']==command,dict(index=index,expected=command,actual=record['bytes'])
    return dict(commands=len(records),exact_wire_match=True,absolute_timing_verified=False)


def verify_unplayed(records,phase):
    """Quiet intervals allow music-mode setup and all-voice reset only.

    Call only while no input/sequence voice is held. A voice-specific release,
    pitch/level write or note in these intervals is unexpected. Cleanup may
    reset voices; it cannot change mode or play a new note.
    """
    assert phase in ('startup','selection','cleanup')
    permitted=([1,0,0],) if phase=='cleanup' else ([1,0,0],[6,1])
    for packet in records:
        assert packet['address']==0x70,'Wrong quiet-interval ii address'
        assert packet['bytes'] in permitted,('Unexpected '+phase+' JF command',packet)


def verify_session_export(full,observed):
    # Validate metadata separately from the scenario's already checked commands.
    assert full[:len(observed)]==observed,'Observed ii prefix changed in export'
    assert [p['sequence'] for p in full]==list(range(1,len(full)+1)),'Incomplete ii export'
    assert all(type(p['monotonic_ns']) is int and p['monotonic_ns']>=0 for p in full)
    assert all(a['monotonic_ns']<=b['monotonic_ns'] for a,b in zip(full,full[1:])),'Reordered ii export'
    verify_unplayed(full[len(observed):],'cleanup')
