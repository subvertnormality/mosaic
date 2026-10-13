"""README Lock lead time: public UI, configured device, raw MIDI timestamps.

A lead is achieved by sending a step's values early, not by delaying anything, so
notes, clock and gates keep the timing they have at lead 0 and the wait between a
lock and its note is the lead. A value leaves on a clock pulse, so that wait is
the setting rounded up to a whole pulse: at least what was asked for and less than
one pulse more. The first note of a play is the exception, and gets no lead at
all, because its lock resolves on the transport's own first pulse and there is no
earlier pulse for it to leave in.

Controlled time proves those bounds exactly; real time checks ordering, cadence
and preserved gates within the existing 10 ms host scheduling tolerance.
"""
import json
from device_configs import boot_with
from master_clock import configure_master_output
from midi_window import MidiWindow

def lock_lead_time(c):
    from cases import assign_trig_parameter
    from patch_params import turn
    c.finish()
    observations=[]
    for lead in (0,5,10,25):
        e=boot_with(c,'lead-'+str(lead),{},midi_lead_time_ms=None)
        try:
            e._set_midi_lead_time(lead,expected=25,capture=lead==25)
            configure_master_output(e)
            e.key(1);e.ui.turn(1, -3);assign_trig_parameter(e,'CC 1')
            for step,value in ((1,24),(2,48),(3,24),(4,48)):
                e.action(type='grid',x=step,y=4,state=1)
                try:e.elapse(.05);e.action(type='enc',n=3,delta=-126);e.enc(3,value+1)
                finally:e.action(type='grid',x=step,y=4,state=0)
            capture=MidiWindow(e.snapshot()['midi_count'])
            e.action(type='grid',x=1,y=8,state=1);e.action(type='grid',x=1,y=8,state=0)
            e.elapse(1.2);capture.extend(e.snapshot())
            e.action(type='grid',x=1,y=8,state=1);e.action(type='grid',x=1,y=8,state=0)
            e.elapse(.06);capture.extend(e.snapshot())
            field='logical_ns' if e.clock_mode=='controlled-experimental' else 'monotonic_ns'
            tolerance=2 if e.clock_mode=='controlled-experimental' else 10_000_000
            events=[v for v in capture.events if v['port']==1]
            notes=[v for v in events if v['bytes'][0]==144 and v['bytes'][2]>0]
            locks=[v for v in events if v['bytes'] in ([176,1,24],[176,1,48])]
            clocks=[v for v in events if v['bytes']==[248]]
            starts=[v for v in events if v['bytes']==[250]]
            stops=[v for v in events if v['bytes']==[252]]
            # Stop drains queued output, so a lead can add a note after the window's
            # eight (README Lock lead time); check the eight the window plays.
            assert len(notes)>=8 and len(locks)>=8 and len(starts)==len(stops)==1,(lead,len(notes),len(locks),len(starts),len(stops))
            notes,locks=notes[:8],locks[:8]
            assert [v['bytes'][2] for v in locks]==[24,48]*4
            assert events.index(starts[0])<events.index(notes[0])
            assert not [v for v in events[events.index(stops[0])+1:] if v['bytes'][0]==144]
            # The last note is drained by the Stop tap (README Lock lead time), so its
            # lead is deliberately shortened; check the pairs before it.
            # A 1/16 step is 24 pulses at 96 PPQN, so the step cadence the locks
            # already prove gives the pulse the values leave on.
            pulse_ns=(1e9/6)/24
            for index,(note,lock) in enumerate(zip(notes[:-1],locks[:-1])):
                assert events.index(lock)<events.index(note),('Lock order',lead,index)
                wait=note[field]-lock[field]
                if index==0:
                    # Nothing is delayed to give the first step a lead it cannot
                    # have, so its value leaves with its note.
                    assert abs(wait)<=tolerance,('First note lead',lead,index,note,lock)
                else:
                    assert lead*1_000_000-tolerance<=wait<lead*1_000_000+pulse_ns+tolerance,('Lead',lead,index,wait,note,lock)
                # The first lock leaves with its note and the rest leave a lead
                # early, so the first interval is shorter by exactly that lead and
                # every interval after it is a step. Measuring from the second
                # lock keeps the cadence exact instead of absorbing the startup.
                if index>=1:
                    expected_lead=0 if lead==0 else -(-lead*1_000_000//pulse_ns)*pulse_ns
                    assert abs((lock[field]-locks[0][field])-(index*1e9/6-expected_lead))<=tolerance,('Lock cadence',lead,index,lock[field]-locks[0][field])
                assert min(abs(tick[field]-note[field]) for tick in clocks)<=tolerance,('Clock alignment',lead,index)
            # Exclude the gates the Stop tap shortens: it drains pending output, so
            # with a lead the last sounding note is released early (README Lock lead
            # time). A 25 ms lead reaches the gate before the final one.
            gates=[]
            for note in notes[:-2]:
                release=next(v for v in events if v['bytes'][0]==128 and v['bytes'][1]==note['bytes'][1] and v['index']>note['index'])
                gates.append(release[field]-note[field])
            observations.append(gates)
            e.results.append(dict(kind='lock-lead-time',lead_time_ms=lead,notes=len(notes),gates_ns=gates,passed=True))
        finally:e.finish()
    tolerance=2 if c.clock_mode=='controlled-experimental' else 10_000_000
    assert all(max(gates)-min(gates)<=tolerance for gates in zip(*observations)),('Gate lengths changed',observations)
    c.results.append(dict(kind='lock-lead-time-comparison',passed=True))
