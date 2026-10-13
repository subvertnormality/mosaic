"""Independent file/PCM/local-analysis audit for Doctor native audio evidence."""
import hashlib,json,math,sys,tempfile,time,wave
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests/behaviour'))
from pcm_oracle import read_wav

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read_softcut_pcm(path):
    # Stock softcut writes signed little-endian PCM24. Decode its actual format
    # independently; the public ADC input remains exact PCM16 via read_wav.
    with wave.open(str(path),'rb') as wav:
        assert wav.getcomptype()=='NONE' and wav.getsampwidth()==3,'Expected production softcut PCM24'
        rate,count,frames=wav.getframerate(),wav.getnchannels(),wav.getnframes()
        assert count==2 and rate==48000 and frames>0
        raw=wav.readframes(frames)
    assert len(raw)==frames*count*3
    channels=[[],[]]
    for offset in range(0,len(raw),3):
        value=raw[offset]|(raw[offset+1]<<8)|(raw[offset+2]<<16)
        if value & 0x800000:value-=0x1000000
        channels[(offset//3)%count].append(value/8388608)
    return rate,channels

def audit_publication(path):
    path=Path(path);data=json.loads(path.read_text());run=Path(data.get('evidence',{}).get('report',path)).parent
    report=json.loads((run/'report.json').read_text())
    assert not (run/'diagnostic-only.json').exists(),'Diagnostic wrapper is not unchanged-application acceptance'
    assert report['publication_kind']=='doctor-native-audio' and report['passed']
    assert report['clock_mode']=='real-time' and report['controlled_time']['applicable'] is False
    assert report['complete_regression_run'] is False and report['hardware_timing_equivalent'] is False
    assert digest(run/'capture-recipe.py')==report['source']['recipe_sha256']
    assert digest(run/'doctor-scene.yaml')==report['source']['yaml_sha256']
    for relative,expected in report['source']['doctor_files'].items():
        target=run/relative;assert run.resolve() in target.resolve().parents
        assert digest(target)==expected,relative
    job=json.loads((run/'audio-result.json').read_text())
    assert job['status']=='complete' and job['input_sha256']==report['source']['stimulus']['sha256']
    assert all(job['finished'].get(k)==0 for k in ('xruns','nonfinite','server_dead'))
    inputs=list((run/'native/audio-captures').rglob('input.wav'))
    assert len(inputs)==1 and digest(inputs[0])==job['input_sha256']
    rate,channels=read_wav(inputs[0]);assert rate==48000 and len(channels)==2
    assert len(channels[0])==29*rate and channels[0]==channels[1]
    # Verify the injected PCM from the frozen recipe, rather than trusting its metadata.
    import importlib.util
    spec=importlib.util.spec_from_file_location('frozen_doctor_recipe',run/'capture-recipe.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory() as folder:
        import yaml
        fixture=yaml.safe_load((run/'doctor-scene.yaml').read_text())['fixture']
        generated=Path(folder)/'stimulus.wav';module.stimulus(generated,seconds=fixture['input_seconds'],rate=fixture['input_rate'],fixture=fixture)
        assert digest(generated)==job['input_sha256']
    captures=list((run/'rhythm-doctor-captures').glob('*.wav'))
    assert captures,'Missing production softcut capture'
    captured=[]
    for wav in captures:
        rate,ch=read_softcut_pcm(wav);assert rate==48000 and len(ch)==2 and len(ch[0])>=24*rate
        rms=math.sqrt(sum(v*v for v in ch[0])/len(ch[0]));assert rms>.005,'Silent actual capture'
        captured.append(dict(path=str(wav),sha256=digest(wav),frames=len(ch[0]),rms=rms))
    analyses=[]
    for result in (run/'rhythm-doctor-analysis-runtime/results').glob('*.json'):
        envelope=json.loads(result.read_text())
        assert envelope['status']=='COMPLETED' and envelope['command']=='ANALYSE'
        assert envelope['sample_rate']==48000
        bound=[item for item in captured if item['sha256']==envelope['wav_sha256']]
        assert len(bound)==1 and bound[0]['frames']==envelope['frames'],'Analysis must bind exact captured PCM'
        value=envelope['analysis']
        detector=value['detector']
        assert not detector['backend_id'].startswith('remote-'),'Fixture must prove default local analysis'
        for name,relative in [('backend_sha256','tools/rhythm_doctor/rd_analysis_backend.c'),('template_sha256','tools/rhythm_doctor/data/nmf_drum_templates.bin')]:
            assert detector[name]==digest(run/'application'/relative)
        hits=[c for c in value['candidates'] if c['lane']=='BD']
        assert len(hits)>=2,'No kick candidates in local analysis'
        analyses.append(dict(path=str(result),detector=detector,bd_candidates=len(hits)))
    assert analyses,'Missing real local analysis result'
    worker_cleanup=[]
    for pidfile in (run/'rhythm-doctor-analysis-runtime').glob('pid'):
        pid=int(pidfile.read_text().strip());proc=Path('/proc')/str(pid)
        cmd=(proc/'cmdline').read_bytes() if (proc/'cmdline').exists() else b''
        assert b'rd_analysis_worker.py' not in cmd,'Detached Doctor worker remains alive after shutdown'
        worker_cleanup.append(dict(pid=pid,active=False,observed_monotonic_ns=time.monotonic_ns()))
    return dict(passed=True,captures=captured,analyses=analyses,stimulus_sha256=job['input_sha256'],worker_cleanup=worker_cleanup,frames=sum(len(s['steps']) for s in report['scenes']),controlled_time_applicable=False)
