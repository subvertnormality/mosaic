"""Literal grid playhead redraw and MIDI timing contract."""


def live_playhead_feedback(c,clock_delta=0):
    import time
    ui=c.ui
    c.configure()
    if clock_delta:
        ui.turn(1,-1);ui.expect_header('clock_mods',channel=1)
        ui.set_value(clock_delta);ui.press_key(3)
    marker=c.snapshot()['midi_count']
    ui.control_edge('play_stop',True);ui.control_edge('play_stop',False)
    controlled=c.clock_mode=='controlled-experimental'
    field='logical_ns' if controlled else 'monotonic_ns'
    started=c.logical_ns if controlled else time.monotonic_ns()
    samples=[];settled=set();last_rows=[]
    # Grid redraw sleeps50ms. D permits only integer-nanosecond rounding;
    # R adds the existing10ms scheduler allowance, not a whole extra step.
    limit=50000002 if controlled else 60000000
    while (c.logical_ns if controlled else time.monotonic_ns())-started<3000000000:
        before=c.logical_ns if controlled else time.monotonic_ns()
        state=c.snapshot()
        after=c.logical_ns if controlled else time.monotonic_ns()
        rows=[m for m in state['midi'] if m['index']>marker and m['port']==1 and m['bytes'][0]==144 and m['bytes'][2]>0]
        if rows:
            expected=[[144,n,v] for n,v in [(60,127),(62,117),(64,107),(65,97)]]
            assert [m['bytes'] for m in rows]==[expected[i%4] for i in range(len(rows))]
            current=(len(rows)-1)%4+1;previous=(current-2)%4+1
            visible=[step for step in range(1,65) if state['grid'][48+step-1]==10]
            assert len(visible)<=1,visible
            age_low=before-rows[-1][field];age_high=after-rows[-1][field]
            if visible:assert visible[0] in (current,previous),dict(current=current,visible=visible)
            if age_low>limit:assert visible==[current],dict(current=current,visible=visible,age_low_ns=age_low,age_high_ns=age_high)
            if visible==[current]:settled.add(len(rows))
            samples.append(dict(note_ordinal=len(rows),current_step=current,visible=visible,age_lower_ns=age_low,age_upper_ns=age_high))
            last_rows=rows
            if len(rows)>=9 and 9 in settled:break
        c.elapse(.01 if controlled else .005)
    assert len(last_rows)>=9 and set(range(1,10))<=settled,dict(notes=len(last_rows),settled=sorted(settled))
    stale=[x for x in samples if x['visible']!=[x['current_step']]]
    c.results.append(dict(kind='live-playhead-latency',redraw_period_ns=50000000,maximum_allowed_stale_ns=limit,samples=samples,max_observed_stale_lower_ns=max([x['age_lower_ns'] for x in stale],default=0)))
    ui.stop();c.wait(lambda state:not state['midi_capture']['outstanding'])
    c.led_values([(x,4) for x in range(1,5)],[15]*4)


def live_playhead_feedback_twice_rate(c):
    return live_playhead_feedback(c, clock_delta=3)
