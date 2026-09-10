"""Failed saves and autosave (README line 1054).

README: a rejected load suspends autosaving; "saving a named project ... resumes the
normal idle autosave interval. A failed save leaves autosaving suspended." Part B
checks that sentence: while suspended, a named save into a read-only project
directory fails and autosave stays suspended; a successful named save resumes it.
Part A is characterisation, not manual text: when no suspension is in force, a
failed idle autosave writes nothing and the next input restarts the idle period.
"""
import base64, json, os, shutil, stat, subprocess
from pathlib import Path
from driver import digest


def autosave_failure(c):
    from persisted_ranges import select_project_action, select_project_file
    from frame_oracle import render
    c.configure()
    data = c.data_directory
    ptn, pset = data/'autosave.ptn', data/'autosave.pset'
    def saved(): return (digest(ptn), digest(pset)) if ptn.is_file() and pset.is_file() else None
    def idle(seconds):
        while seconds > 0:
            step = min(30, seconds); c.elapse(step); seconds -= step
    def record(stage, **values): c.results.append(dict(kind='autosave-failure', stage=stage, passed=True, **values))
    mode = stat.S_IMODE(os.stat(data).st_mode)
    def read_only(): os.chmod(data, mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
    # Part A (characterisation): a failed idle autosave, then write access returns.
    assert saved() is None, 'Fresh fixture unexpectedly contains autosave'
    read_only()
    try:
        idle(61.5); assert saved() is None and not ptn.exists(), 'Autosave written to a read-only directory'
    finally: os.chmod(data, mode)
    record('idle-autosave-refused')
    c.tap(3, 8); idle(61.5); assert saved(), 'Input did not restart autosave after an unsuspended failure'
    record('input-restarts-autosave', files=saved())
    # Part B (README): a rejected load suspends autosave.
    broken = data/'broken.ptn'; shutil.copyfile(ptn, broken)
    script = c.out/'bad-range.lua'
    script.write_text("local root,path=table.unpack(arg);local tab=dofile(root..'/lua/lib/tabutil.lua');local saved=assert(tab.load(path));"
                      "local channel=saved[2].song_patterns[1].channels[1];channel.start_trig={4,4};channel.end_trig={2,4};assert(tab.save(saved,path)==nil)")
    source = json.loads(Path(c.launch_options['experimental_install']).read_text())['source']
    subprocess.run(['lua5.3', str(script), source, str(broken)], check=True)
    select_project_file(c, 'broken.ptn'); c.key(3); c.key(1)
    expected = render([(0, 62, 10, 'Slot 1 ch 1 reversed')])
    c.wait(lambda s: all(base64.b64decode(s['frame']['pixels_base64'])[(y*128+x)*4+k] == expected[(y*128+x)*4+k]
                         for y in range(55, 64) for x in range(128) for k in range(3)))
    def stamps(): return {n: (data/n).stat().st_mtime_ns for n in ('autosave.ptn', 'autosave.pset')}
    suspended = stamps()
    c.tap(3, 8); idle(61.5); assert stamps() == suspended, 'Autosave ran while suspended by a rejected load'
    record('suspended-by-rejected-load')
    read_only()
    try:
        select_project_action(c, 0, returning=True); c.key(3); c.key(1)   # named save "new" fails
        assert not (data/'new.ptn').exists(), 'Named save wrote into a read-only directory'
    finally: os.chmod(data, mode)
    record('named-save-failed')
    c.tap(3, 8); idle(61.5); assert stamps() == suspended, 'A failed named save resumed autosave'
    record('failed-save-leaves-suspended')
    select_project_action(c, 0, returning=True); c.key(3); c.key(1)
    assert (data/'new.ptn').is_file() and (data/'new.pset').is_file(), 'Named save failed after write access returned'
    # The same project may autosave to identical bytes: a new write is the evidence.
    written = stamps()
    idle(61.5)
    c.wait(lambda _: all((data/n).stat().st_mtime_ns != written[n] for n in written), timeout=5)
    record('named-save-resumes', files=saved())
