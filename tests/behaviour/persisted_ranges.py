"""Saved-range validation through real autosave, cold boot and native inputs."""
import json,shutil,subprocess
from pathlib import Path
from driver import Driver,digest,EMULATOR_ROOT


def serializer_source(c):
    """Use the qualified norns source in controlled time, the pinned checkout otherwise."""
    install = c.launch_options.get('experimental_install')
    source = (Path(json.loads(Path(install).read_text())['source']) if install else
              EMULATOR_ROOT / '.runtime/deps/norns' if EMULATOR_ROOT else None)
    tabutil = source / 'lua/lib/tabutil.lua' if source else None
    if tabutil is None or not tabutil.is_file():
        raise FileNotFoundError('Pinned norns tabutil source unavailable: ' + str(tabutil))
    return str(source)

def saved_range_compatibility(c,legacy=False):
    from cases import assert_durations
    c.configure();c.ui.song_editor()
    # Author the highest song slot through the actual copy/select gestures.
    c.ui.copy_slot(1,96,control='song_pattern_slot')
    c.ui.tap_control('song_pattern_slot',96)
    c.ui.expect_leds({('song_pattern_slot',1):'alternate',('song_pattern_slot',96):'selected'})
    c.ui.menu('channel_editor')
    c.playback([(1,[144,p,v]) for p,v in [(60,127),(62,117),(64,107),(65,97)]],cycles=2)
    c.elapse(59);c.elapse(2)
    c.wait(lambda _:all((c.data_directory/n).is_file() for n in ['autosave.ptn','autosave.pset']))
    c.finish()
    original={n:digest(c.data_directory/n) for n in ['autosave.ptn','autosave.pset']}
    seed=c.out/'compatible-seed';shutil.copytree(c.data_directory,seed)
    script=c.out/'compatible-range.lua'
    # A one-step range is valid stored data even though no grid gesture authors
    # it. Use the official serializer for this explicit compatibility fixture.
    script.write_text("local root,path,legacy=table.unpack(arg);local tab=dofile(root..'/lua/lib/tabutil.lua');local saved=assert(tab.load(path));local data=saved[2];assert(data.selected_song_pattern==96);local ch=data.song_patterns[96].channels[1];ch.start_trig={3,4};ch.end_trig={3,4};if legacy=='yes' then data.sequencer_patterns=data.song_patterns;data.song_patterns=nil end;assert(tab.save(saved,path)==nil)")
    source=serializer_source(c)
    subprocess.run(['lua5.3',str(script),source,str(seed/'autosave.ptn'),'yes' if legacy else 'no'],check=True)
    seeded={n:digest(seed/n) for n in original}
    next_seed=seed
    for generation in range(2):
        out=c.out/('compatible-load-'+str(generation));out.mkdir()
        loaded=Driver(out,project_seed=next_seed,**c.launch_options)
        try:
            loaded.ui.menu('channel_editor')
            loaded.ui.expect_steps({i:('selected' if i==3 else 'dark') for i in range(1,65)})
            notes=loaded.playback([(1,[144,64,107])],cycles=6)
            assert_durations(loaded,notes,[1]*5)
            field='logical_ns' if loaded.clock_mode=='controlled-experimental' else 'monotonic_ns'
            tolerance=2e-9 if loaded.clock_mode=='controlled-experimental' else .01
            for i,note in enumerate(notes):assert abs((note[field]-notes[0][field])/1e9-i/6)<=tolerance
            loaded.ui.song_editor()
            loaded.ui.expect_leds({('song_pattern_slot',1):'alternate',('song_pattern_slot',96):'selected'})
            loaded.ui.menu('channel_editor')
            before=(loaded.data_directory/'autosave.ptn').stat().st_mtime_ns
            loaded.elapse(59);loaded.elapse(2)
            loaded.wait(lambda _:(loaded.data_directory/'autosave.ptn').stat().st_mtime_ns>before)
            loaded.results.append(dict(kind='compatible-saved-range',slot=96,range=[3,3],legacy_input=legacy and generation==0,generation=generation,autosave_resumed=True,passed=True))
        finally:loaded.finish()
        next_seed=loaded.data_directory
    assert {n:digest(seed/n) for n in seeded}==seeded
    assert {n:digest(c.data_directory/n) for n in original}==original
    c.results.append(dict(kind='upper-slot-one-step-roundtrip',slot=96,legacy=legacy,cold_generations=2,source_preserved=True,passed=True))
