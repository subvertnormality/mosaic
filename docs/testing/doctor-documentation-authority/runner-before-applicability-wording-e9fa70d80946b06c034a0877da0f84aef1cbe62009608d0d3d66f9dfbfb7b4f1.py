"""Explicit Doctor option acceptance runner; never an exhaustive campaign.
Uses canonical public recipes and preserves immutable app/recipe/native identity.
Root coordinates the whole-run native lock. Audio cases are real-time only.
"""
import argparse,fcntl,hashlib,json,shutil,sys,traceback,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests/behaviour'))
from driver import write,digest
from manual_doctor_capture import tracked_driver,close,freeze
from contract import rhythm_doctor_capture_options as audio
from contract import rhythm_doctor_options as ui
CASES={name:getattr(audio,name) for name in ('manual_stereo','manual_left','manual_right','auto_stereo','auto_left','auto_right')}
CASES['setup_options']=ui.setup_options
CASES['ready_options']=lambda c: ui.ready_options(c,c.doctor_ready_fixture)
QUALIFICATION_MANIFEST=ROOT/'tools/doctor-qualification-inventory.json'

def qualification_registration(case,clock_mode,manifest=QUALIFICATION_MANIFEST):
    """Bind specialized identity to exact manifest bytes; no global case claim."""
    raw=manifest.read_bytes();data=json.loads(raw)
    entries=data.get('qualifications',[])
    expected='MA-DOCTOR-MANUAL-START-BEAT-001'
    if (data.get('schema_version')!=1 or data.get('publication_kind')!='doctor-options-qualification'
        or len(entries)!=1 or entries[0].get('id')!=expected):
        raise ValueError('Unknown Doctor qualification registration')
    entry=entries[0]
    if (entry.get('citation')!='manual:rhythm-doctor' or entry.get('feature_id')!='rhythm-doctor'
        or entry.get('global_inventory_member') is not False or entry.get('required_for_manual_build') is not True
        or entry.get('runner')!={'path':'tools/doctor_options_capture.py','role':'manual_right','clock_mode':'real-time'}
        or entry.get('procedure')!={'path':'tests/behaviour/contract/rhythm_doctor_start_beat.py','callable':'next_beat_apply_restore'}
        or entry.get('checkpoint_ids')!=['start-beat-original1','start-beat-next2','start-beat-next-ready','start-beat-restore1','start-beat-restored-ready']
        or entry.get('controlled_time',{}).get('applicable') is not False
        or entry.get('ui_only_witness',{}).get('backend_regression') is not False):
        raise ValueError('Invalid Doctor qualification registration')
    if case=='manual_right' and clock_mode!='real-time':
        raise ValueError('Full Start Beat qualification requires real-time public audio')
    return dict(qualification_manifest=dict(file='qualification-registration.json',
        source_path='tools/doctor-qualification-inventory.json',sha256=hashlib.sha256(raw).hexdigest()),
        specialized_qualifications=[dict(id=expected,citation=entry['citation'])] if case=='manual_right' else [])

def run(out,case,installation,clock_mode,app_root=None,ready_fixture=None,save_ready_fixture=False,ready_fixture_sha256=None):
    audio_case=case not in ('setup_options','ready_options')
    registration=qualification_registration(case,clock_mode)
    shutil.copyfile(QUALIFICATION_MANIFEST,out/registration['qualification_manifest']['file'])
    assert digest(out/registration['qualification_manifest']['file'])==registration['qualification_manifest']['sha256'],'Qualification manifest changed before freeze'
    if ready_fixture:
        assert digest(ready_fixture)==ready_fixture_sha256,'Fixture changed before parsing'
    fixture=json.loads(ready_fixture.read_text()) if ready_fixture else None
    if case=='ready_options':
        assert fixture is not None
        ui._qualify_fixture(fixture)  # Before any native startup or seed import.
        assert digest(ready_fixture)==ready_fixture_sha256,'Fixture changed during qualification'
    if audio_case and clock_mode!='real-time':
        raise ValueError('Public ADC/softcut audio is inapplicable in controlled time')
    recipe=Path(audio.__file__ if audio_case else ui.__file__)
    shutil.copyfile(recipe,out/'acceptance-recipe.py')
    shutil.copyfile(Path(__file__),out/'capture-runner.py')
    # Either source is immutable before launch; never run the changing checkout.
    app=out/'frozen-app'
    if app_root:
        shutil.copytree(app_root,app)
    else:
        app=freeze(out)
    source={str(p.relative_to(app)):digest(p) for p in sorted(app.rglob('*'))
            if p.is_file() and 'test_artefacts' not in p.parts}
    # Pin all imports/config before startup, independent of the minimal app copy.
    paths=set(p for p in (ROOT/'tests/behaviour').rglob('*') if p.is_file() and p.suffix in ('.py','.json'))
    paths.update(ROOT/'tools'/name for name in ('doctor_options_capture.py','doctor_ready_fixture.py',
        'manual_doctor_capture.py','manual_doctor_audit.py','manual_capture.py','manual_model.py',
        'doctor_options_audit.py','doctor-qualification-inventory.json'))
    paths.update(p for p in (ROOT/'manual').glob('*.schema.json'))
    paths.update(ROOT/name for name in ('manual/schema.json','lib/ui_splash_logo.lua',
        'docs/ui-reimplementation/spec.json','docs/ui-reimplementation/tools/model.py'))
    harness={str(p.relative_to(ROOT)):digest(p) for p in sorted(paths) if p.is_file()}
    for name in harness:
        frozen=out/'harness'/name;frozen.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,frozen)
        assert digest(frozen)==harness[name],'Harness changed while being frozen: '+name
    seed=None;seed_hashes={}
    if fixture:
        seed=out/'frozen-project-seed'
        shutil.copytree(fixture['project_seed'],seed)
        assert digest(seed/'autosave.ptn')==fixture['saved_project_sha256']
        seed_hashes={str(p.relative_to(seed)):digest(p) for p in sorted(seed.rglob('*')) if p.is_file()}
        assert seed_hashes==fixture['project_seed_files'],'Seed changed while being frozen'
        write(out/'fixture-prelaunch.json',dict(passed=True,phase='before-native-startup',
            fixture=str(ready_fixture),fixture_sha256=ready_fixture_sha256,
            acquisition_report=fixture['acquisition_report'],acquisition_report_sha256=fixture['acquisition_report_sha256'],
            geometry_receipt=fixture['geometry_receipt'],geometry_receipt_sha256=fixture['geometry_receipt_sha256'],
            project_seed=str(seed),project_seed_files=seed_hashes,saved_project_sha256=fixture['saved_project_sha256']))
    write(out/'source.json',dict(app=str(app),files=source,recipe_sha256=digest(recipe),
        runner_sha256=digest(Path(__file__)),harness_root=str(ROOT),harness_files=harness,
        harness_snapshot=str(out/'harness'),project_seed_files=seed_hashes,qualification_manifest=registration['qualification_manifest']))
    c=None;failure=cleanup_failure=None
    try:
        if ready_fixture:
            assert digest(ready_fixture)==ready_fixture_sha256,'Fixture changed immediately before native startup'
            ui._qualify_fixture(fixture)
            assert all(digest(seed/name)==value for name,value in seed_hashes.items())
        c=tracked_driver(out,clock_mode=clock_mode,experimental_install=str(installation),app_root=app,
            project_seed=seed)
        c.doctor_ready_fixture=fixture
        write(out/'session.json',c.runtime.info)
        write(out/'capabilities.json',c.runtime.capabilities())
        CASES[case](c)
        if case=='manual_right':
            from contract.rhythm_doctor_start_beat import next_beat_apply_restore
            next_beat_apply_restore(c)
        if save_ready_fixture:
            from doctor_ready_fixture import acquire
            acquire(c)
    except Exception:
        failure=traceback.format_exc()
    finally:
        if c:
            try:
                # Preserve evidence on failures before cleanup removes it.
                for name in ('rhythm-doctor-captures','rhythm-doctor-analysis-runtime'):
                    directory=c.data_directory/name
                    if directory.exists():shutil.copytree(directory,out/name)
                input_wav=c.data_directory/'doctor-asymmetric-input.wav'
                if input_wav.exists():shutil.copyfile(input_wav,out/input_wav.name)
                job=getattr(c,'doctor_input_job',None)
                if job:
                    job=c.runtime.capture_status(job['job_id'])
                    write(out/'audio-result.json',job)
                write(out/'results.json',c.results)
            except Exception:
                failure=failure or traceback.format_exc()
            finally:
                try:close(c,{})
                except Exception:cleanup_failure=traceback.format_exc()
                finally:
                    if not (out/'native').exists():
                        try:c.finish()
                        except Exception:cleanup_failure=cleanup_failure or traceback.format_exc()
        changed=[name for name,value in harness.items() if not (ROOT/name).is_file() or digest(ROOT/name)!=value]
        if changed:failure=failure or 'Harness source changed: '+','.join(changed)
        report=dict(schema_version=1,publication_kind='doctor-options-qualification',case=case,
            passed=failure is None and cleanup_failure is None,failure=failure,cleanup_failure=cleanup_failure,
            clock_mode=clock_mode,complete_regression_run=False,hardware_timing_equivalent=False,
            source_identity=c.identity if c else None,source='source.json',results='results.json',
            checkpoints=getattr(c,'doctor_option_frames',[]) if c else [],
            ready_fixture=dict(path=str(ready_fixture),sha256=ready_fixture_sha256) if ready_fixture else None,
            harness_changed=changed,
            controlled_time={'applicable':not audio_case,'reason':
                'Public ADC input and native softcut acquisition require real-time audio; UI-only setup applies in both lanes.'})
        report.update(registration)
        write(out/'report.json',report)
    return report

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--case',choices=sorted(CASES),required=True)
    parser.add_argument('--installation',type=Path,required=True)
    parser.add_argument('--clock-mode',choices=('real-time','controlled-experimental'),default='real-time')
    parser.add_argument('--app-root',type=Path)
    parser.add_argument('--ready-fixture',type=Path)
    parser.add_argument('--ready-fixture-sha256')
    parser.add_argument('--save-ready-fixture',action='store_true')
    parser.add_argument('--output-root',type=Path,required=True)
    args=parser.parse_args()
    if args.case not in ('setup_options','ready_options') and args.clock_mode!='real-time':parser.error('ADC cases require real time')
    if (args.case=='ready_options') != bool(args.ready_fixture):parser.error('READY requires its exact qualified --ready-fixture')
    if bool(args.ready_fixture)!=bool(args.ready_fixture_sha256):parser.error('READY requires --ready-fixture-sha256')
    if args.save_ready_fixture and args.case!='manual_right':parser.error('Fixture export reuses ManualRight acquisition')
    with open('/tmp/mosaic-manual-native.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        out=args.output_root/uuid.uuid4().hex;out.mkdir(parents=True,exist_ok=False)
        report=run(out,args.case,args.installation,args.clock_mode,args.app_root,args.ready_fixture,args.save_ready_fixture,args.ready_fixture_sha256)
        fixture_path=None;fixture_failure=None
        if report['passed'] and args.save_ready_fixture:
            try:
                from doctor_ready_fixture import finalize
                finalize(out,out/'report.json')
                fixture_path=str(out/'ready-fixture/fixture.json')
            except Exception:
                fixture_failure=traceback.format_exc()
                write(out/'fixture-finalize-failure.json',dict(passed=False,failure=fixture_failure))
    passed=report['passed'] and fixture_failure is None
    print(json.dumps(dict(passed=passed,report=str(out/'report.json'),fixture=fixture_path)),flush=True)
    return int(not passed)
if __name__=='__main__':raise SystemExit(main())
