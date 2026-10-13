"""Actual Mosaic Doctor audio-input acceptance; real time only, no emulator changes."""
import argparse, fcntl, hashlib, json, math, os, shutil, struct, sys, time, traceback, uuid, wave
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests/behaviour'))
from driver import write, digest
from manual_capture import tracked_driver, frame, close
CASE='MA-DOCTOR-AUDIO-001'
CITATION='manual/legacy/README-1.4.0.md#rhythm-doctor'

def stimulus(path, seconds=29, rate=48000, fixture=None):
    cfg=fixture or dict(bpm=120,pulse_hz=60,pulse_level=18000,pulse_seconds=.12,pulse_decay=100)
    # Deterministic 120 BPM kick-like pulses. This is input test material, not guide audio.
    frames=bytearray(seconds*rate*4)
    for onset in range(2,seconds*2-1):
        start=onset*rate//2
        for j in range(round(cfg["pulse_seconds"]*rate)):
            value=round(cfg["pulse_level"]*math.sin(2*math.pi*cfg["pulse_hz"]*j/rate)*math.exp(-cfg["pulse_decay"]*j/rate))
            struct.pack_into('<hh',frames,(start+j)*4,value,value)
    with wave.open(str(path),'wb') as wav:
        wav.setnchannels(2);wav.setsampwidth(2);wav.setframerate(rate);wav.writeframes(frames)
    return dict(sha256=digest(path),sample_rate=rate,seconds=seconds,channels=2,
                onsets_seconds=[v/2 for v in range(2,seconds*2-1)])

def freeze(out):
    app=out/'application';app.mkdir()
    shutil.copyfile(ROOT/'mosaic.lua',app/'mosaic.lua')
    shutil.copytree(ROOT/'lib',app/'lib',ignore=shutil.ignore_patterns('tests','.git','__pycache__'))
    shutil.copytree(ROOT/'docs/ui-reimplementation/code',app/'docs/ui-reimplementation/code')
    shutil.copytree(ROOT/'tools/rhythm_doctor',app/'tools/rhythm_doctor',ignore=shutil.ignore_patterns('__pycache__'))
    return app

def checkpoint(c, steps, ident, caption, expect):
    c.results.append(dict(kind='manual-doctor-semantic',citation=CITATION,step=ident,expected=expect,passed=True))
    steps.append(dict(id=ident,caption=caption,expect=expect,citation=CITATION,
                      inputs=c.recipe[checkpoint.cursor:],output=frame(c,CASE,ident)))
    checkpoint.cursor=len(c.recipe)
checkpoint.cursor=0

def run(out, install, source_path):
    import yaml
    source_path=Path(source_path);data=yaml.safe_load(source_path.read_text())
    assert data['publication_kind']=='doctor-native-audio' and data['fixture']['bpm']==120
    assert data['fixture']['input_rate']==48000 and data['fixture']['input_channels']==2
    shutil.copyfile(source_path,out/'doctor-scene.yaml')
    shutil.copyfile(Path(__file__),out/'capture-recipe.py')
    app=freeze(out);c=None;failure=cleanup_failure=None;steps=[];job=None;preview_hits=None;before=None
    source=dict(recipe_sha256=digest(Path(__file__)),yaml_sha256=digest(source_path),
                yaml_path=str(source_path),source_revision=os.popen('git -C '+str(ROOT)+' rev-parse HEAD').read().strip())
    checkpoint.cursor=0
    try:
        c=tracked_driver(out,experimental_install=str(install),app_root=app)
        write(out/'session.json',c.runtime.info)
        write(out/'capabilities.json',c.runtime.capabilities())
        stimulus_path=c.data_directory/'doctor-stimulus.wav'
        source['stimulus']=stimulus(stimulus_path,seconds=data['fixture']['input_seconds'],rate=data['fixture']['input_rate'],fixture=data['fixture'])
        from frame_oracle import live_header_matches
        for step in data['steps']:
            for action in step['inputs']:
                kind=action['type']
                if kind=='ui':getattr(c.ui,action['method'])(*action.get('args',[]))
                elif kind=='wait':c.elapse(data['fixture'][action['fixture']] if 'fixture' in action else action['seconds'])
                elif kind=='audio-input-start':
                    job=c.runtime.capture_start(data['fixture']['input_seconds'],input='mosaic/doctor-stimulus.wav')
                    write(out/'audio-start.json',job)
                elif kind=='midi-baseline':before=c.snapshot()['midi_count']
                else:raise ValueError('Unsupported Doctor input operation '+kind)
            expected=dict(step['expect'])
            if 'route' in expected:
                route=expected['route'];title,layout=c.ui._rhythm_doctor_screen(route)
                c.wait(lambda state:live_header_matches(state,title,'CH01',layout),timeout=expected.get('timeout',3))
                c.ui.expect_rhythm_doctor_screen(route)
            if 'tooltip' in expected:c.ui.expect_rhythm_doctor_tooltip(expected['tooltip'])
            grid=c.snapshot()['grid'][48:112]
            if expected.get('empty_grid'):assert not any(v in (12,15) for v in grid),'Fresh pattern has active trigs'
            if expected.get('grid')=='preview':
                preview_hits=[i+1 for i,v in enumerate(grid) if v in expected['levels']]
                assert len(preview_hits)>=expected['minimum_trigs'],'Kick input must produce at least two visible preview attacks'
                expected['grid_steps']=preview_hits
            elif expected.get('grid')=='commit':
                painted_hits=[i+1 for i,v in enumerate(grid) if v==expected['level']]
                assert painted_hits==preview_hits,dict(preview=preview_hits,painted=painted_hits)
                expected['grid_steps']=painted_hits
            if 'midi_minimum_attacks' in expected:
                state=c.snapshot();notes=[m for m in state['midi'] if m['index']>before and 144<=m['bytes'][0]<=159 and m['bytes'][2]>0]
                assert len(notes)>=expected['midi_minimum_attacks'],'Painted pattern must emit MIDI attacks'
                assert all(m['port']==expected['port'] for m in notes),'Wrong selected MIDI output'
                c.wait(lambda state:state['midi_capture']['outstanding']==expected['outstanding_notes'])
                expected['midi_start_index']=before
                expected['midi_end_index']=c.snapshot()['midi_count']
                expected['notes']=notes
            checkpoint(c,steps,step['id'],step['caption'],expected)
            steps[-1]['authoring_operations']=step['inputs']
        deadline=time.monotonic()+40
        while job['status']=='capturing' and time.monotonic()<deadline:
            job=c.runtime.capture_status(job['job_id']);time.sleep(.05)
        assert job['status']=='complete',job
        assert job['input_sha256']==source['stimulus']['sha256']
        write(out/'audio-result.json',job)
        for name in ('rhythm-doctor-captures','rhythm-doctor-analysis-runtime'):
            if (c.data_directory/name).exists():shutil.copytree(c.data_directory/name,out/name)
        source['doctor_files']={str(p.relative_to(out)):digest(p) for name in ('rhythm-doctor-captures','rhythm-doctor-analysis-runtime') for p in (out/name).rglob('*') if p.is_file()}
    except Exception:failure=traceback.format_exc()
    finally:
        if c:
            try:close(c,{})
            except Exception:cleanup_failure=traceback.format_exc()
        report=dict(publication_kind=data['publication_kind'],case=data['case'],passed=failure is None and cleanup_failure is None,failure=failure,
                    cleanup_failure=cleanup_failure,source=source,source_identity=c.identity if c else None,
                    clock_mode='real-time',complete_regression_run=False,hardware_timing_equivalent=False,
                    controlled_time=data['controlled_time'],
                    scenes=[dict(id=data['scene_id'],title=data['title'],behaviour_case=data['case'],steps=steps)])
        write(out/'report.json',report)
    return report

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=ROOT/'manual/doctor-scene.yaml');p.add_argument('--audio-install',type=Path,required=True);p.add_argument('--output-root',type=Path,required=True)
    a=p.parse_args();out=a.output_root/uuid.uuid4().hex;out.mkdir(parents=True)
    with open('/tmp/mosaic-manual-native.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX);report=run(out,a.audio_install,a.source)
    print(json.dumps(dict(passed=report['passed'],report=str(out/'report.json'))),flush=True)
    return int(not report['passed'])
if __name__=='__main__':raise SystemExit(main())
