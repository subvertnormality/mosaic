"""Named save/load through the parameter menu (README "save and load")."""
from driver import digest

A=[(60,127),(62,117),(64,107),(65,97)]
B=[(60,127),(62,117),(64,107),(67,97)] # step 4 F -> G

def named_save_load(c):
    from persisted_ranges import select_project_action,select_project_file
    c.configure()
    data=c.data_directory
    def files(name):
        ptn,pset=data/(name+'.ptn'),data/(name+'.pset')
        return (digest(ptn),digest(pset)) if ptn.is_file() and pset.is_file() else None
    def idle(seconds):
        while seconds>0:
            step=min(30,seconds);c.elapse(step);seconds-=step
    def record(stage,**values):c.results.append(dict(kind='named-save',stage=stage,passed=True,**values))
    def phrase(stage,notes):
        c.tap(3,8);c.playback([(1,[144,n,v]) for n,v in notes]);record(stage,phrase=[n for n,_ in notes])
    def save(returning=False,typed=None):
        select_project_action(c,0,returning) # opens text entry with the default name "new"
        if typed:
            # Character row, one character after the entry's initial "A", append it,
            # then back to the OK row and confirm.
            c.enc(3,-1)
            c.enc(2,typed)
            c.key(3);c.enc(3,1);c.enc(2,1)
        c.key(3);c.key(1)
    def edit_step_four_to_g():c.tap(5,8);c.tap(5,8);c.tap(4,3);c.tap(3,8)
    phrase('initial-A',A)
    save();first=files('new');assert first,'Default-name save did not write new.ptn/.pset';record('save-default-name',files=first)
    save(returning=True,typed=1)
    typed=[p.stem for p in data.glob('new?.ptn')]
    assert typed==['newB'] and files('newB'),('Typed-name save',sorted(p.name for p in data.iterdir()))
    named=files('newB');record('save-typed-name',name='newB',files=named)
    edit_step_four_to_g();phrase('edited-B',B)
    idle(61.5)
    assert files('autosave'),'Idle autosave missing'
    assert files('new')==first and files('newB')==named,'Autosave overwrote a named save'
    autosaved=files('autosave');record('autosave-preserves-named',autosave=autosaved)
    # Cancel leaves every file unchanged.
    before={p.name:digest(p) for p in data.iterdir() if p.is_file()}
    select_project_action(c,0,returning=True);c.key(2);c.key(1)
    assert {p.name:digest(p) for p in data.iterdir() if p.is_file()}==before,'Cancelled save changed files'
    record('cancel-save')
    # Overwrite the default name with B; the typed-name save keeps A.
    save(returning=True);assert files('new') not in (None,first) and files('newB')==named;record('overwrite-default-name',files=files('new'))
    select_project_file(c,'newB.ptn',returning=True);c.key(3);c.key(1);phrase('load-typed-A',A)
    select_project_file(c,'new.ptn',returning=True);c.key(3);c.key(1);phrase('load-overwritten-B',B)
    assert files('newB')==named,'Loading changed a named save'
