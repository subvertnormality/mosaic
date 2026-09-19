"""Idle autosave (README "save and load"): input restarts the idle period; no save while playing."""
from driver import Driver,digest

def autosave_idle_lifecycle(c):
    c.configure()
    ptn=c.data_directory/'autosave.ptn';pset=c.data_directory/'autosave.pset'
    def saved():return (digest(ptn),digest(pset)) if ptn.is_file() and pset.is_file() else None
    def idle(seconds):
        # One controlled advance is bounded by the action schema; split long idles.
        while seconds>0:
            step=min(30,seconds);c.elapse(step);seconds-=step
    def record(stage,value):c.results.append(dict(kind='autosave-idle',stage=stage,autosave=value,passed=True))
    assert saved() is None,'Fresh fixture unexpectedly contains autosave'
    # A grid press inside the idle period restarts it.
    idle(59.5);assert saved() is None,'Autosave before 60 s idle';record('59.5s-idle',None)
    c.tap(3,8);idle(59.5);assert saved() is None,'Input did not restart the idle period';record('input-restarts',None)
    idle(1.5);c.wait(lambda _:saved() is not None,timeout=2)
    first=saved();record('saved-after-idle',first)
    # Playing past 60 s, with an edit made while playing (step 4 F -> G), never saves.
    c.tap(1,8);c.tap(5,8);c.tap(5,8);c.tap(4,3);c.tap(3,8)
    idle(65);assert saved()==first,'Autosave while playing';record('no-save-while-playing',first)
    c.tap(1,8);c.wait(lambda s:not s['midi_capture']['outstanding'])
    idle(59.5);assert saved()==first,'Autosave within 60 s of Stop';record('stop-restarts',first)
    idle(1.5);c.wait(lambda _:saved() not in (None,first),timeout=2)
    second=saved();record('saved-after-stop',second)
    c.finish()
    # A fresh process restores the latest autosave, including the edit made while playing.
    out=c.out/'reloaded';out.mkdir()
    loaded=Driver(out,project_seed=c.data_directory,**c.launch_options)
    try:
        loaded.tap(3,8)
        loaded.playback([(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107),(67,97)]])
        loaded.results.append(dict(kind='autosave-restore',phrase=[60,62,64,67],passed=True))
    finally:loaded.finish()
    c.results.append(dict(kind='autosave-idle-session',nested=str(out),passed=True))
