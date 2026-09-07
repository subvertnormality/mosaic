"""Mosaic-owned physical-input regressions; independent literal musical oracles."""
from driver import REPO,Driver,digest

def four_notes(c):
    c.configure()
    c.playback([(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107),(65,97)]])
    c.tap(5,8);c.tap(5,8);c.tap(4,3)
    c.led_values([(4,3)],[12])
    c.playback([(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107),(67,97)]])

def next_trig_cutoff(c):
    c.configure();c.hold_tap((1,4),(8,4));c.tap(5,8)
    for x in (2,3,4):c.tap(x,4)
    c.tap(5,4);c.tap(5,8);c.tap(5,3);c.tap(3,8);c.tap(5,8)
    c.hold_tap((1,4),(4,4));c.tap(3,4)
    c.led_values([(x,4) for x in range(1,6)],[15,5,15,2,15])
    notes=c.playback([(1,[144,n,v]) for n,v in [(60,127),(64,107),(67,100)]],timeout=6)
    assert_durations(c,notes,[2,1,1]*2)

def assert_durations(c,notes,lengths):
    assert lengths and len(notes)>=len(lengths),'Missing duration observations'
    state=c.snapshot();rows=[]
    for note,length in zip(notes,lengths):
        off=next(m for m in state['midi'] if m['index']>note['index'] and m['port']==1 and m['bytes']==[128,note['bytes'][1],note['bytes'][2]])
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        actual=(off[field]-note[field])/1e9
        rows.append(dict(pitch=note['bytes'][1],expected_seconds=length/6,actual_seconds=actual,error_ms=1000*(actual-length/6)))
    c.results.append(dict(kind='duration',rows=rows))
    # Two nanoseconds cover native integer deadline rounding; no wall jitter in D.
    tolerance_ms=.000002 if c.clock_mode=='controlled-experimental' else 10
    assert all(abs(row['error_ms'])<=tolerance_ms for row in rows),rows

def restore_length(c):
    # The source length must survive temporary interruption by an inserted trig.
    next_trig_cutoff(c)
    c.tap(3,4)
    c.led_values([(x,4) for x in range(1,6)],[15,5,5,5,15])
    notes=c.playback([(1,[144,60,127]),(1,[144,67,100])],timeout=6)
    assert_durations(c,notes,[4,1]*2)
    # Reinsert the collision: the same authored length must shorten again.
    c.tap(3,4)
    c.led_values([(x,4) for x in range(1,6)],[15,5,15,2,15])
    notes=c.playback([(1,[144,60,127]),(1,[144,64,107]),(1,[144,67,100])],timeout=6)
    assert_durations(c,notes,[2,1,1]*2)

def wrapped_length(c,same_pitch=False):
    c.configure();c.hold_tap((1,4),(16,7));c.tap(5,8)
    for x in (2,3,4):c.tap(x,4)
    c.tap(15,7);c.hold_tap((15,7),(2,4))
    c.led_values([(15,7),(16,7),(1,4),(2,4)],[15,5,15,2])
    if not same_pitch:
        c.tap(5,8);c.tap(12,8);c.tap(15,3)
        c.led_values([(15,3)],[12])
    notes=c.playback([(1,[144,60,127]),(1,[144,60 if same_pitch else 67,100])],timeout=38)
    assert_durations(c,notes,[1,2]*2)


def autosave_restart(c):
    c.configure()
    saved=c.data_directory/'autosave.ptn';pset=c.data_directory/'autosave.pset'
    assert not saved.exists() and not pset.exists(),'Fresh fixture unexpectedly contains autosave'
    c.elapse(59)
    assert not saved.exists(),'Autosave occurred before the documented60-second idle period'
    c.elapse(2)
    c.wait(lambda _:saved.is_file() and pset.is_file(),timeout=2)
    assert saved.stat().st_size>0 and pset.stat().st_size>0
    c.results.append(dict(kind='saved-project',files=[dict(name=p.name,sha256=digest(p)) for p in (saved,pset)]))
    c.finish()
    out=c.out/'reloaded';out.mkdir()
    loaded=Driver(out,project_seed=c.data_directory,**c.launch_options)
    try:
        # Read the restored pattern through the visible grid and complete MIDI
        # phrases. Do not re-create notes or inspect the serialized model.
        loaded.tap(3,8);loaded.tap(5,8)
        loaded.led_values([(x,4) for x in range(1,5)],[15,15,15,15])
        loaded.playback([(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107),(65,97)]])
    finally:loaded.finish()

CASES={
 'M-SAVE-001':dict(run=autosave_restart,requirements=['PERSIST-AUTO-001'],description='Create notes through the grid; idle autosave; boot a fresh native process from saved data and verify restored LEDs and MIDI'),
 'M-MIDI-001':dict(run=lambda c:wrapped_length(c,same_pitch=True),requirements=['MIDI-RELEASE-001'],description='Repeated pitch at wrapped duration boundary emits balanced note releases and drains after stop'),
 'M-LEN-003':dict(run=wrapped_length,requirements=['PAT-LENGTH-003'],description='A length crossing step64 ends at the next trig on step1; verify complete64-step MIDI loops and LEDs'),
 'M-LEN-002':dict(run=restore_length,requirements=['PAT-LENGTH-002'],description='Delete and reinsert an interrupting trig; MIDI duration and grid restore the authored length'),
 'M-PAT-001':dict(run=four_notes,requirements=['PAT-EDIT-001'],description='Create four notes; edit through grid; verify screen, LEDs and complete MIDI phrases'),
 'M-LEN-001':dict(run=next_trig_cutoff,requirements=['PAT-LENGTH-001'],description='A later trig cuts off preceding MIDI duration, matching manual and grid')}
