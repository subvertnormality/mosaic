"""User-input driver using only the emulator's public external-suite client."""
import hashlib,json,os,sys,time,uuid
from pathlib import Path
REPO=Path(__file__).resolve().parents[2]
EMULATOR_ROOT=Path(os.environ['MONOME_EMULATOR']).resolve()
sys.path.insert(0,str(EMULATOR_ROOT/'src'))
from automation.client import Session

def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

class Driver:
    def __init__(self,out,clock_mode="real-time",experimental_install=None):
        self.clock_mode=clock_mode;self.logical_ns=0
        self.out=out;self.recipe=[];self.observations=[];self.results=[]
        code=out/'code';code.mkdir();(code/'mosaic').symlink_to(REPO,target_is_directory=True)
        self.runtime=Session(script=code/'mosaic/mosaic.lua',code_root=code,
            data=out/'data',data_seeds=[dict(source=str(REPO/'tests/behaviour/config'),destination='mosaic/config',format='json-files')],
            midi_config=dict(ports=['Emulator MIDI','Second MIDI','Norns2sinfonion']),random_seed=42,
            clock_mode=clock_mode,experimental_install=experimental_install)
        self.identity=self.runtime.info['application_identity']
        try:
            entry=next(f for f in self.identity['files'] if f['path']=='mosaic/mosaic.lua')
            assert entry['sha256']==digest(REPO/'mosaic.lua'),'Wrong application loaded'
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
    def screen_header(self,text):
        from frame_oracle import header,matches
        expected=header(text);self.wait(lambda s:matches(s,expected))
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
    def playback(self,expected,cycles=3,timeout=5):
        assert expected and cycles>=2
        before=self.snapshot()['midi_count'];self.tap(1,8)
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
        try:
            self.runtime.close(self.out/'native')
        finally:
            write(self.out/'recipe.json',self.recipe);write(self.out/'observations.json',self.observations)
            write(self.out/'results.json',self.results)
        cleanup=json.loads((self.out/'native/cleanup.json').read_text())
        assert all(c['returncode']==0 for c in cleanup if c['service']!='sclang'),cleanup
        log=(self.out/'native/matron.log').read_text(errors='replace')
        errors=[line for line in log.splitlines() if line.startswith('Coroutine error:')]
        assert not errors,errors
        for item in self.identity['files']:
            source=Path(self.identity['code_root'])/item['path']
            assert source.is_file() and digest(source)==item['sha256'],'Application/test source changed during execution: '+item['path']
        events=[json.loads(line) for line in (self.out/'native/native-events.jsonl').read_text().splitlines()]
        native=[]
        for event in events:
            if event['kind']!='input' or event['type'] not in (1,2,3,8):continue
            t=event['type'];a=event['args']
            if t==8:
                native.append(dict(type='advance',nanoseconds=a[0]*1000000000+a[1]));continue
            native.append(dict(type='key',n=a[0],state=a[1]) if t==1 else dict(type='enc',n=a[0],delta=a[1]) if t==2 else dict(type='grid',x=a[0]+1,y=a[1]+1,state=a[2]))
        assert native==self.recipe,'Native input trace differs from supplied user recipe'
        captured=[e for e in events if e['kind'] in (3,11)]
        if captured:assert [e['sequence'] for e in captured]==list(range(1,len(captured)+1)),'Incomplete MIDI capture'
