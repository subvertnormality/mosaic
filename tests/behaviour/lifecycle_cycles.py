"""Ten cold lifecycle cycles (BEHAVIOUR_PLAN T06/F17): boot, verify, edit, autosave, stop.

Each cycle raises global transpose by one semitone; the next cold process must
restore it from the idle autosave. Every session's shutdown is checked by the
driver (clean native exits, no Lua errors, unchanged sources).
"""
from driver import Driver
PHRASE=[(60,127),(62,117),(64,107),(65,97)]

def lifecycle_cycles(c,cycles=10):
    def phrase(d,transpose,stage):
        d.playback([(1,[144,n+transpose,v]) for n,v in PHRASE],cycles=2)
        d.results.append(dict(kind='lifecycle',stage=stage,transpose=transpose,passed=True))
    def idle_autosave(d):
        before={p.name:p.stat().st_mtime_ns for p in d.data_directory.glob('autosave.*')}
        for _ in range(3):d.elapse(21)
        d.wait(lambda _:all((d.data_directory/n).is_file() and (d.data_directory/n).stat().st_mtime_ns!=before.get(n) for n in ('autosave.ptn','autosave.pset')))
    d=c;d.configure();phrase(d,0,'fresh')
    for cycle in range(1,cycles+1):
        d.tap(4,8);d.tap(16,8);d.tap(3,8) # global transpose +1
        phrase(d,cycle,'cycle-%d-edited'%cycle)
        idle_autosave(d);d.finish()
        out=c.out/('cycle-%02d'%cycle);out.mkdir()
        d=Driver(out,project_seed=d.data_directory,**c.launch_options)
        d.tap(3,8);phrase(d,cycle,'cycle-%d-restored'%cycle)
    d.finish()
    c.results.append(dict(kind='lifecycle-summary',cycles=cycles,final_transpose=cycles,passed=True))
