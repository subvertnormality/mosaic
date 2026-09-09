"""Independent MIDI receiver for Mosaic master Start/Clock/note phase."""
def assert_master_receiver(events,field,tolerance):
    selected=[e for e in events if e['port']==1]
    active=False;tick=-1;clocks=[];notes=[];starts=[];stops=[]
    for event in selected:
        data=event['bytes']
        if data==[250]:
            starts.append(event);active=True;tick=-1
        elif data==[252]:
            stops.append(event);active=False
        elif data==[248] and active:
            tick+=1;clocks.append(event)
        elif len(data)==3 and data[0]==144 and data[2]>0:
            assert active,'Master emitted Note On before Start'
            assert tick==6*len(notes),('Receiver step/clock mismatch',len(notes),tick)
            notes.append(event)
    assert len(starts)==1 and len(stops)==1
    assert len(notes)==8 and clocks
    first=clocks[0][field]
    for i,note in enumerate(notes):
        assert note['bytes']==[144,(60,62,64,65)[i%4],(127,117,107,97)[i%4]]
        assert abs((note[field]-first)/1e9-i/6)<=tolerance,('Master absolute note phase',i)
    for i,clock in enumerate(clocks):
        assert abs((clock[field]-first)/1e9-i/36)<=tolerance,('Master clock cadence',i)
    return dict(notes=len(notes),clock_ticks=len(clocks),first_clock_ns=first)

def master_clock(c):
    from cases import menu_label,menu_value
    from midi_window import MidiWindow
    c.configure();c.key(1);c.enc(1,4);c.key(3);menu_label(c,'LEVELS >')
    position=next(i for i,v in enumerate(c.snapshot()['diagnostics']['parameter_roots']) if v['name']=='CLOCK')
    c.enc(2,position);c.key(3);menu_label(c,'source');menu_value(c,'internal')
    from frame_oracle import selected_line
    import base64
    c.enc(2,7)
    # The separator above this row draws at y=22.5; label glyphs start at24.
    c.wait(lambda state:selected_line(state,'1. Emulator MIDI',top=24))
    def output_enabled(state):
        pixels=base64.b64decode(state['frame']['pixels_base64'])
        return all(pixels[(y*128+x)*4+k]==255
                   for y in range(26,29) for x in range(124,127) for k in range(3))
    assert not output_enabled(c.snapshot())
    c.enc(3,1);c.wait(output_enabled)
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    for phase in (0,.001,.009,.025):
        c.elapse(phase)
        capture=MidiWindow(c.snapshot()['midi_count'])
        c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
        c.elapse(1.2);capture.extend(c.snapshot())
        c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
        c.wait(lambda state:capture.extend(state) and not state['midi_capture']['outstanding'])
        c.results.append(dict(kind='master-output-diagnostic',phase_delay_seconds=phase,events=capture.events))
        check=assert_master_receiver(capture.events,field,2e-9 if c.clock_mode=='controlled-experimental' else .01)
        c.results.append(dict(kind='master-independent-receiver',phase_delay_seconds=phase,passed=True,**check))
