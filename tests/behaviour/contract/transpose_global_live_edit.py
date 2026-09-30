from contract.duration_assertions import assert_durations

def transpose_global_live_edit(c):
    """Live global edits affect the next onset without cutting the held note."""
    import time
    from midi_window import MidiWindow
    from note_accounting import note_pairs
    c.configure();c.ui.scale_editor()
    capture=MidiWindow(c.snapshot()['midi_count'])
    c.ui.control_edge("play_stop", True);c.ui.control_edge("play_stop", False)
    c.wait(lambda state:capture.extend(state) and len(capture.note_ons())>=1)
    c.elapse(.04)
    def now():
        return c.logical_ns if c.clock_mode=='controlled-experimental' else time.monotonic_ns()
    edit1_lower=now();c.ui.control_edge("global_transpose_increment", True);c.ui.control_edge("global_transpose_increment", False);edit1_upper=now()
    c.wait(lambda state:capture.extend(state) and len(capture.note_ons())>=5)
    c.elapse(.04)
    before_second=len(capture.note_ons());assert 5<=before_second<=6
    edit2_lower=now();c.ui.control_edge("global_transpose_minimum", True);c.ui.control_edge("global_transpose_minimum", False);edit2_upper=now()
    c.elapse(1);capture.extend(c.snapshot())
    c.ui.control_edge("play_stop", True)
    stop_lower=now();c.ui.control_edge("play_stop", False);stop_upper=now()
    c.wait(lambda state:capture.extend(state) and not state['midi_capture']['outstanding'])
    notes=capture.note_ons();assert len(notes)>=10
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    edits=((edit1_lower,edit1_upper,1),(edit2_lower,edit2_upper,-12))
    transposes=[]
    for note in notes:
        stamp=note[field]
        assert not any(lower<=stamp<=upper for lower,upper,value in edits),'Onset occurred inside edit-observation window'
        transposes.append(0 if stamp<edit1_lower else 1 if stamp<edit2_lower else -12)
    assert 0 in transposes and 1 in transposes and -12 in transposes
    bases=(60,62,64,65);velocities=(127,117,107,97)
    expected=[(1,[144,bases[i%4]+value,velocities[i%4]]) for i,value in enumerate(transposes)]
    assert [(e['port'],e['bytes']) for e in notes]==expected
    pairs=note_pairs(capture.events);assert len(pairs)==len(notes) and [on for on,off in pairs]==notes
    assert all((off['port'],off['bytes'])==(1,[128,on['bytes'][1],on['bytes'][2]]) for on,off in pairs)
    assert_durations(c,notes[:-1],[1]*(len(notes)-1),events=capture.events)
    for lower,upper,value in edits:
        candidates=[pair for pair in pairs if pair[0][field]<lower<pair[1][field]]
        assert len(candidates)==1 and candidates[0][1][field]>upper
    nonnotes=[e for e in capture.events if e['bytes'][0]&240 not in (128,144)]
    assert [(e['port'],e['bytes']) for e in nonnotes[:3]]==[(1,[250]),(2,[250]),(3,[250])]
    assert [(e['port'],e['bytes']) for e in nonnotes[-3:]]==[(1,[252]),(2,[252]),(3,[252])]
    programs=nonnotes[3:-3];assert len(programs)==4*len(notes)
    wanted_programs=[]
    for value in transposes:wanted_programs.extend(([192,0],[193,0],[194,3],[195,value+64]))
    assert [(e['port'],e['bytes']) for e in programs]==[(3,b) for b in wanted_programs]
    for i,note in enumerate(notes):
        group=programs[4*i:4*i+4]
        assert group[-1]['index']<note['index'] and (i==0 or group[0]['index']>notes[i-1]['index'])
        deltas=[note[field]-e[field] for e in group]
        assert (deltas==[0]*4 if c.clock_mode=='controlled-experimental' else all(0<=d<=2_000_000 for d in deltas))
    assert len(capture.events)==6*len(notes)+6
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    errors=[(note[field]-notes[0][field])/1e9-i/6 for i,note in enumerate(notes)]
    assert max(abs(error) for error in errors)<=tolerance,errors
    assert stop_lower<=pairs[-1][1][field]<=stop_upper+int(tolerance*1e9)
    c.results.append(dict(kind='transpose-global-live-edit',onsets=len(notes),releases=len(pairs),
                          transposes=transposes,second_edit_after_onsets=before_second,
                          maximum_phase_error_seconds=max(abs(error) for error in errors),passed=True))
