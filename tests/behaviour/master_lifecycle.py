"""Cancel pending/active master playback and prove independent restart alignment."""
def master_lifecycle(c):
    from master_clock import configure_master_output,assert_master_receiver
    from midi_window import MidiWindow
    configure_master_output(c)
    def play_toggle():
        c.action(type='grid',x=1,y=8,state=1)
        c.action(type='grid',x=1,y=8,state=0)
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    for delay in (0,.001,.025):
        cancelled=MidiWindow(c.snapshot()['midi_count'])
        play_toggle()
        if delay:c.elapse(delay)
        play_toggle()
        c.elapse(.12)
        state=c.snapshot();cancelled.extend(state)
        events=[e for e in cancelled.events if e['port']==1]
        stops=[i for i,e in enumerate(events) if e['bytes']==[252]]
        assert len(stops)==1,stops
        after=events[stops[0]+1:]
        assert len([e for e in after if e['bytes']==[248]])>=2
        assert all(e['bytes']==[248] for e in after),'Cancelled transport emitted after Stop'
        assert not state['midi_capture']['outstanding'],'Stop left held notes'
        if c.clock_mode=='controlled-experimental' and delay==0:
            assert all(e['bytes'] in ([248],[252]) for e in events),'Pending Start escaped cancellation'
        c.results.append(dict(kind='master-cancelled-start',delay_seconds=delay,events=cancelled.events,passed=True))
        restarted=MidiWindow(c.snapshot()['midi_count'])
        play_toggle();c.elapse(1.2);restarted.extend(c.snapshot())
        play_toggle()
        c.wait(lambda state:restarted.extend(state) and not state['midi_capture']['outstanding'])
        check=assert_master_receiver(restarted.events,field,2e-9 if c.clock_mode=='controlled-experimental' else .01)
        c.results.append(dict(kind='master-restart-after-cancel',delay_seconds=delay,events=restarted.events,passed=True,**check))
