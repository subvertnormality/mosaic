"""Transport messages for the explicitly configured panic fixture.

The fixture starts from a fresh project (no autosave), which sends no transport at
startup (arbitrated 2026-09-11, SEM-018 no-stop-without-project; before b1afcc5 boot
always sent Stop). The user's Play sends Start and Stop on each clock-output port."""
def verify_panic_transport(events, *, field, start_bounds, stop_bounds):
    transport=[e for e in events if e['bytes'][0]>=248]
    expected=[(port,[status]) for status in (250,252) for port in (1,2,3)]
    assert [(e['port'],e['bytes']) for e in transport]==expected,'Unexpected, missing or reordered transport message'
    assert 0<=start_bounds[0]<=start_bounds[1]<stop_bounds[0]<=stop_bounds[1]
    for i,event in enumerate(transport):
        timestamp=event[field];assert type(timestamp) is int
        lower,upper=start_bounds if i<3 else stop_bounds
        assert lower<=timestamp<=upper,('Transport message outside its control boundary',event,lower,upper)
    return dict(kind='panic-transport-boundaries',initial_stops=0,starts=3,stops=3,unexpected=0,passed=True)
