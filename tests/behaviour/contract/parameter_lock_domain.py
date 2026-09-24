"""Parameter fine-gesture characterisation contract."""

def parameter_fine_gesture(c):
    """Characterise README K1 fine control against cheat-sheet K3 wording."""
    from cases import assign_trig_parameter
    c.configure();c.enc(3,1);c.key(3);c.enc(1,-3);assign_trig_parameter(c,'NRPN14')
    before=c.snapshot()['midi_count']
    # K1 held: one physical detent retains the small raw delta.
    c.action(type='key',n=1,state=1);c.elapse(.3)
    try:c.enc(3,1)
    finally:c.action(type='key',n=1,state=0)
    c.elapse(.15)
    # Neither held: the same detent uses the wide NRPN coarse multiplier.
    c.enc(3,1)
    # K3 fires its existing Trig Locks page action before E3; it does not set
    # the global K1 fine-state, so the same E3 detent remains coarse.
    c.action(type='key',n=3,state=1);c.elapse(.3)
    try:c.enc(3,1)
    finally:c.action(type='key',n=3,state=0)
    c.elapse(.15)
    events=[e for e in c.snapshot()['midi'] if e['index']>before]
    cc=[e for e in events if e['bytes'][0]&240==176]
    values=[]
    assert len(cc)==12
    for offset in range(0,len(cc),4):
        group=cc[offset:offset+4]
        assert [(e['port'],e['bytes'][:2]) for e in group]==[(1,[176,99]),(1,[176,98]),(1,[176,6]),(1,[176,38])]
        assert [e['bytes'][2] for e in group[:2]]==[4,5]
        values.append(group[2]['bytes'][2]*128+group[3]['bytes'][2])
    assert values==[0,129,258],values
    # Final value is user-visible at the MIDI boundary as normal patch recall.
    c.key(1);start=c.snapshot()['midi_count'];c.tap(1,8)
    state=c.wait(lambda state:any(e['index']>start and e['bytes'][0]&240==144 and e['bytes'][2]>0 for e in state['midi']))
    recall=[e for e in state['midi'] if e['index']>start and e['bytes'][0]&240==176]
    expected_recall=[(1,[176,99,4]),(1,[176,98,5]),(1,[176,6,2]),(1,[176,38,2])]*2
    assert [(e['port'],e['bytes']) for e in recall]==expected_recall # Patch recall, then step1 default.
    note=next(e for e in state['midi'] if e['index']>start and e['bytes'][0]&240==144 and e['bytes'][2]>0)
    assert all(event['index']<note['index'] for event in recall)
    c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])
    c.results.append(dict(kind='parameter-fine-gesture',k1_values=[0],plain_values=[129],
                          k3_values=[258],k3_is_not_fine=True,final_recall=258,passed=True))
