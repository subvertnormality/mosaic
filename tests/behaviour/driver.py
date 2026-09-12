"""User-input driver using only the emulator's public external-suite client."""
import hashlib,json,os,sys,time,uuid,subprocess,shutil
from pathlib import Path
REPO=Path(__file__).resolve().parents[2]
EMULATOR_ROOT=Path(os.environ['MONOME_EMULATOR']).resolve()
sys.path.insert(0,str(EMULATOR_ROOT/'src'))
from automation.client import Session

def startup_lock(timeout=300):
    import contextlib,fcntl
    @contextlib.contextmanager
    def held():
        fd=os.open('/tmp/mosaic-behaviour-%d-startup.lock'%os.getuid(),os.O_RDWR|os.O_CREAT,0o600)
        end=time.monotonic()+timeout
        try:
            while True:
                try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);break
                except BlockingIOError:
                    if time.monotonic()>end:raise TimeoutError('Mosaic startup lock held for over %ss'%timeout)
                    time.sleep(.05)
            yield
        finally:
            os.close(fd)
    return held()

def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

class Driver:
    def __init__(self,out,clock_mode="real-time",experimental_install=None,profile="base-midi",mod_code_root=None,project_seed=None,mod_patches=False):
        self.launch_options=dict(clock_mode=clock_mode,experimental_install=experimental_install,profile=profile,mod_code_root=mod_code_root,mod_patches=mod_patches)
        self.clock_mode=clock_mode;self.logical_ns=0
        self.out=out;self.recipe=[];self.observations=[];self.results=[]
        code=out/'code';code.mkdir();(code/'mosaic').symlink_to(REPO,target_is_directory=True)
        output_profiles=json.loads((REPO/'tests/behaviour/output-profiles.json').read_text())['profiles']
        if profile not in ('base-midi','midi-modulation') and profile not in output_profiles:raise ValueError('Unknown profile')
        if profile in output_profiles and clock_mode!='real-time':raise ValueError('Audio/Crow profiles require real time; DSP and Crow are not controlled-time sources')
        self.profile=profile;self.mod_revisions={};self.applied_mod_patches={}
        if mod_patches and profile!="midi-modulation":raise ValueError("Mod patches require modulation profile")
        patches=json.loads((REPO/"tests/behaviour/mod-patches/manifest.json").read_text()) if mod_patches else {}
        if profile!='base-midi':
            if not mod_code_root:raise ValueError('Mod profile requires an explicit mod code root')
            mods=(output_profiles[profile]['mods'] if profile in output_profiles else json.loads((REPO/'tests/behaviour/mods.lock.json').read_text())['mods'])
            for name,entry in mods.items():
                source=Path(mod_code_root).resolve()/name
                if not source.is_dir():raise ValueError('Missing mod source: '+name)
                if profile in output_profiles:
                    origin=subprocess.check_output(['git','remote','get-url','origin'],cwd=source,text=True).strip()
                    if origin!=entry['url']:raise ValueError('Unexpected mod origin: '+name)
                revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
                if revision!=entry['commit']:raise ValueError('Unexpected mod revision: '+name)
                dirty=subprocess.check_output(['git','status','--porcelain','--untracked-files=all'],cwd=source,text=True)
                if dirty:raise ValueError('Mod source has uncommitted changes: '+name)
                if profile in output_profiles:
                    ignored=subprocess.check_output(['git','ls-files','--others','--ignored','--exclude-standard','--','*.lua','*.sc','*.so','*.scx'],cwd=source,text=True)
                    if ignored:raise ValueError('Ignored runtime source outside mod pin: '+name)
                if name in patches:
                    candidate=patches[name];patch_file=REPO/'tests/behaviour/mod-patches'/candidate['patch']
                    assert digest(patch_file)==candidate['sha256'],'Mod patch changed without manifest update'
                    assert digest(source/candidate['file'])==candidate['before_sha256'],'Mod patch base mismatch'
                    shutil.copytree(source,code/name,ignore=shutil.ignore_patterns('.git','__pycache__'))
                    subprocess.run(['git','apply','--check',str(patch_file)],cwd=code/name,check=True)
                    subprocess.run(['git','apply',str(patch_file)],cwd=code/name,check=True)
                    assert digest(code/name/candidate['file'])==candidate['after_sha256'],'Mod patch output mismatch'
                    self.applied_mod_patches[name]=candidate
                else:(code/name).symlink_to(source,target_is_directory=True)
                self.mod_revisions[name]=revision
        # Concurrent native startups race on JACK's shared registry (emulator R22);
        # serialise session starts across every Mosaic test process on this host.
        with startup_lock():
            self.runtime=Session(script=code/'mosaic/mosaic.lua',code_root=code,
                data=out/'data',data_seeds=([dict(source=str(project_seed),destination='mosaic')] if project_seed else [dict(source=str(REPO/'tests/behaviour/config'),destination='mosaic/config',format='json-files')]),
                midi_config=dict(ports=['Emulator MIDI','Second MIDI','Norns2sinfonion']),random_seed=42,enabled_mods=list(self.mod_revisions),
                clock_mode=clock_mode,experimental_install=experimental_install)
        self.data_directory=Path(self.runtime.info['data'])/'mosaic'
        self.identity=self.runtime.info['application_identity']
        try:
            if profile in output_profiles:
                capability=self.runtime.capabilities()
                supported=' '.join(capability['supported'])
                for required in output_profiles[profile]['capabilities']:
                    if required not in supported:raise ValueError('Missing required output capability: '+required)
                write(self.out/'output-capabilities.json',capability)
            entry=next(f for f in self.identity['files'] if f['path']=='mosaic/mosaic.lua')
            assert entry['sha256']==digest(REPO/'mosaic.lua'),'Wrong application loaded'
            if clock_mode!='real-time':self.elapse(0)  # Drain native deferred init before user input.
        except Exception:
            self.runtime.close(self.out/'native')
            raise
    def action(self,**value):
        self.recipe.append(value);return self.runtime.action(value)
    def elapse(self,seconds):
        if self.clock_mode=="real-time":time.sleep(seconds)
        else:
            ns=round(seconds*1e9)
            self.action(type="advance",nanoseconds=ns);self.logical_ns+=ns
    def snapshot(self):
        value=self.runtime.observe();self.observations.append(value);return value['state']
    def wait(self,predicate,timeout=3):
        start=len(self.observations);end=time.monotonic()+(timeout if self.clock_mode=="real-time" else 180)
        logical_end=self.logical_ns+round(timeout*1e9)
        while time.monotonic()<end:
            state=self.snapshot()
            if len(self.observations)>start+2:del self.observations[start+1:-1]
            if predicate(state):return state
            if self.clock_mode!="real-time" and self.logical_ns>=logical_end:break
            self.elapse(.03 if self.clock_mode=="real-time" else min(.01,(logical_end-self.logical_ns)/1e9))
        raise AssertionError('Required observable output did not arrive')
    def tap(self,x,y):
        self.action(type='grid',x=x,y=y,state=1);self.action(type='grid',x=x,y=y,state=0);self.elapse(.06)
    def key(self,n):
        self.action(type='key',n=n,state=1);self.action(type='key',n=n,state=0);self.elapse(.06)
    def enc(self,n,steps):
        for _ in range(abs(steps)):
            self.elapse(.05);self.action(type='enc',n=n,delta=2 if steps>0 else -2)
        self.elapse(.15)
    def hold_tap(self,first,last):
        self.action(type='grid',x=first[0],y=first[1],state=1)
        try:self.tap(*last)
        finally:self.action(type='grid',x=first[0],y=first[1],state=0)
    def led_values(self,cells,expected):
        indexes=[(y-1)*16+x-1 for x,y in cells]
        state=self.wait(lambda s:[s['grid'][i] for i in indexes]==expected)
        self.results.append(dict(kind='grid',cells=cells,expected=expected,actual=[state['grid'][i] for i in indexes]))
    def screen_header(self,text,selected=None):
        from frame_oracle import header,matches
        expected=header(text,selected=selected);self.wait(lambda s:matches(s,expected))
        self.results.append(dict(kind='screen-header',expected=text,matched=True))
    def configure(self):
        self.tap(3,8);self.enc(1,4);self.enc(3,1);self.key(3);self.tap(5,8)
        for x in range(1,5):self.tap(x,4)
        self.tap(5,8)
        for x,y in ((1,7),(2,6),(3,5),(4,4)):self.tap(x,y)
        self.tap(5,8)
        for x,y in ((1,1),(2,2),(3,3),(4,4)):self.tap(x,y)
        self.tap(3,8);self.tap(1,2);self.hold_tap((1,4),(4,4))
        self.led_values([(1,2)],[15]);self.screen_header('Ch. 1 Device Config')
    def playback(self,expected,cycles=3,timeout=5,settle_seconds=0):
        assert expected and cycles>=2
        assert settle_seconds>=0
        before=self.snapshot()['midi_count'];self.tap(1,8)
        # Capture remains active throughout the wait. Check every captured note,
        # including early/extra notes; this only reduces observation polling.
        if settle_seconds:self.elapse(settle_seconds)
        def notes(s):return [m for m in s['midi'] if m['index']>before and 144<=m['bytes'][0]<=159 and m['bytes'][2]>0]
        # One extra onset closes the preceding complete phrases, including rests.
        state=self.wait(lambda s:len(notes(s))>=len(expected)*cycles+1,timeout)
        actual=[(m['port'],m['bytes']) for m in notes(state)]
        wanted=[expected[i%len(expected)] for i in range(len(actual))]
        assert actual==wanted,dict(expected=wanted,actual=actual)
        self.tap(1,8);self.wait(lambda s:s['midi_capture']['outstanding']==[])
        self.results.append(dict(kind='midi',expected=wanted,actual=actual,complete_cycles=cycles))
        return notes(state)
    def finish(self):
        if getattr(self,"finished",False):return
        try:
            self.runtime.close(self.out/'native')
        finally:
            write(self.out/'recipe.json',self.recipe);write(self.out/'observations.json',self.observations)
            write(self.out/'results.json',self.results)
        if self.observations:
            diagnostics=self.observations[-1]['state']['diagnostics']
            assert diagnostics['enabled_mods']==len(self.mod_revisions) and diagnostics['loaded_mods']==len(self.mod_revisions),'Requested mod profile did not load'
        cleanup=json.loads((self.out/'native/cleanup.json').read_text())
        assert all(c['returncode'] in ((0,-15) if c['service'] in ('sclang','crow') else (0,)) for c in cleanup),cleanup
        log=(self.out/'native/matron.log').read_text(errors='replace')
        errors=[line for line in log.splitlines() if line.startswith('Coroutine error:') or (line.startswith('hook: ') and ' failed, error: ' in line)]
        assert not errors,errors
        for item in self.identity['files']:
            source=Path(self.identity['code_root'])/item['path']
            assert source.is_file() and digest(source)==item['sha256'],'Application/test source changed during execution: '+item['path']
        events=[json.loads(line) for line in (self.out/'native/native-events.jsonl').read_text().splitlines()]
        native=[]
        for event in events:
            if event['kind']!='input' or event['type'] not in (1,2,3,6,7,8,9,10,11,12,13):continue
            t=event['type'];a=event['args']
            if t==6:
                native.append(dict(type='grid_connection',connected=bool(a[0])));continue
            if t==12:
                native.append(dict(type='midi_connection',port=a[0],connected=bool(a[1])));continue
            if t==13:
                native.append(dict(type='runtime_stall',milliseconds=a[0]));continue
            if t in (9,10,11):
                native.append(a[0]);continue
            if t==7:
                native.append(dict(type='midi',port=a[0],bytes=a[1]));continue
            if t==8:
                native.append(dict(type='advance',nanoseconds=a[0]*1000000000+a[1]));continue
            native.append(dict(type='key',n=a[0],state=a[1]) if t==1 else dict(type='enc',n=a[0],delta=a[1]) if t==2 else dict(type='grid',x=a[0]+1,y=a[1]+1,state=a[2]))
        expected=[];held_grid={}
        for action in self.recipe:
            action={k:v for k,v in action.items() if k!='at_monotonic_ns'}
            if action['type']=='grid':
                key=(action['x'],action['y'])
                expected.append(action)
                if action['state']:held_grid[key]=action
                else:held_grid.pop(key,None)
            elif action['type']=='grid_connection':
                # The native grid lifecycle contract releases held cells through
                # the ordinary input callback before it removes the device.
                if not action['connected']:
                    expected.extend(dict(type='grid',x=held['x'],y=held['y'],state=0) for held in held_grid.values())
                    held_grid.clear()
                expected.append(action)
            else:expected.append(action)
        assert native==expected,'Native input trace differs from supplied user recipe'
        from automation.midi_schedule_evidence import verify_midi_schedules
        actions=[json.loads(line) for line in (self.out/'native/actions.jsonl').read_text().splitlines()]
        verify_midi_schedules(events,actions)
        captured=[e for e in events if e['kind'] in (3,11)]
        if captured:assert [e['sequence'] for e in captured]==list(range(1,len(captured)+1)),'Incomplete MIDI capture'

        self.finished=True
