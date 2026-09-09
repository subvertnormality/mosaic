"""External input clock, Mosaic notes and a second independent receiver."""
def forwarded_clock(c,warm_ticks):
    import time,base64
    from cases import menu_label,menu_value
    from midi_window import MidiWindow
    from note_schedule import assert_schedule
    c.configure();c.key(1);c.enc(1,4);c.key(3);menu_label(c,'LEVELS >')
    position=next(i for i,v in enumerate(c.snapshot()['diagnostics']['parameter_roots']) if v['name']=='CLOCK')
    c.enc(2,position);c.key(3);menu_label(c,'source');menu_value(c,'internal')
    c.enc(3,1);menu_value(c,'midi')
    c.enc(2,8);menu_label(c,'2. Second MIDI')
    def enabled(state):
        pixels=base64.b64decode(state['frame']['pixels_base64'])
        return all(pixels[(y*128+x)*4+k]==255 for y in range(26,29) for x in range(124,127) for k in range(3))
    assert not enabled(c.snapshot());c.enc(3,1);c.wait(enabled)
    controlled=c.clock_mode=='controlled-experimental';domain='logical' if controlled else 'monotonic'
    origin=(c.logical_ns if controlled else time.monotonic_ns())+500_000_000
    first=origin+(warm_ticks+1)*25_000_000;stop=first+1_475_000_000
    packets=[(origin+i*25_000_000,248) for i in range(1,warm_ticks+1)]
    packets+=[(first,250)]+[(first+i*25_000_000,248) for i in range(60)]+[(stop,252)]
    packets.sort(key=lambda x:x[0])
    stimulus=[dict(port=1,bytes=[value],**{'at_'+domain+'_ns':at}) for at,value in packets]
    capture=MidiWindow(c.snapshot()['midi_count'])
    request=dict(type='midi_schedule',schedule_id=300+warm_ticks,events=stimulus)
    if controlled:request['time_domain']='logical'
    c.action(**request)
    state=c.wait(lambda state:capture.extend(state) and len(state['midi_input_schedule']['delivered'])==len(stimulus),timeout=5)
    c.wait(lambda state:capture.extend(state) and not state['midi_capture']['outstanding'])
    c.results.append(dict(kind='forwarded-clock-diagnostic',warm_ticks=warm_ticks,first_clock_deadline_ns=first,events=capture.events,stimulus=stimulus,delivered=state['midi_input_schedule']['delivered']))
    field='logical_ns' if controlled else 'monotonic_ns';tolerance=2e-9 if controlled else .01
    onsets=[(6*i,(60,62,64,65)[i%4],(127,117,107,97)[i%4]) for i in range(10)]
    assert len(capture.note_ons())==10
    assert_schedule(capture.events,onsets,[6]*10,field=field,origin=first,stop_bounds=(stop,stop),pulse_rate=40,tolerance=tolerance)
    active=False;tick=-1;notes=0;clocks=[];starts=0
    for event in capture.events:
        data=event['bytes']
        if event['port']==2:
            if data==[250]:active=True;tick=-1;starts+=1
            elif data==[252]:active=False
            elif data==[248] and active:tick+=1;clocks.append(event)
        elif event['port']==1 and len(data)==3 and data[0]==144 and data[2]>0:
            assert active and tick==notes*6,('Forwarded receiver note phase',notes,tick,active)
            notes+=1
    assert starts==1 and notes==10 and clocks
    for i,event in enumerate(clocks):
        assert abs((event[field]-first)/1e9-i/40)<=tolerance,('Forwarded absolute clock phase',i)
    assert not any(e['port'] in (1,3) and e['bytes']==[248] for e in capture.events),'Clock leaked to input/disabled port'
    c.results.append(dict(kind='forwarded-clock-independent-receiver',warm_ticks=warm_ticks,notes=notes,clock_ticks=len(clocks),passed=True))
def cold_forwarded_clock(c):return forwarded_clock(c,0)
def warm_forwarded_clock(c):return forwarded_clock(c,49)
