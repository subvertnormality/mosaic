"""Emulator lane matching the physical-norns PERF-002/003 calibration cases.

    MONOME_EMULATOR=/path/to/monome-emulator python3 tests/behaviour/perf_calibration_emulator.py \
        --case PERF-002-HW-16 --output ../mosaic-behaviour-runs/<new dir> [--windows 4] \
        [--experimental-install <performance-profile installation.json> --performance-profile <profile.json>]

Same user-level builder, functional preflight, window schedule, oracle and
unchanged thresholds as hardware_performance.py. Timestamps come from the
native MIDI export; the physical lane stamps at the Lua send boundary.
"""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
BEHAVIOUR=Path(__file__).resolve().parent;REPO=BEHAVIOUR.parents[1];sys.path.insert(0,str(BEHAVIOUR))
import driver
from dense_workload import build_project
from hardware_performance import CASES,TIMING_THRESHOLDS,dense_oracle,source_identity
from heldout_workloads import recovery_oracle,run_window

class EmulatorLane:
    def __init__(self,d):self.d=d
    def gesture(self,kind,a,b):
        if kind=='grid':
            self.d.action(type='grid',x=a,y=b,state=1);self.d.action(type='grid',x=a,y=b,state=0)
        else:self.d.action(type='enc',n=a,delta=b)
    def lua_load(self,iterations):self.d.action(type='runtime_lua_load',iterations=int(iterations))

def preflight(d,spec):
    marker=d.snapshot()['midi_count'];d.tap(1,8);d.elapse(2.0);d.tap(1,8);d.elapse(.4);state=d.snapshot()
    events=[e for e in state['midi'] if e.get('index',0)>marker] if state['midi'] and 'index' in state['midi'][0] else state['midi']
    channels=sorted({e['bytes'][0]&15 for e in events if len(e['bytes'])==3 and e['bytes'][0]&240==144 and e['bytes'][2]>0 and e['port']==1})
    cc1=sorted({e['bytes'][0]&15 for e in events if len(e['bytes'])==3 and e['bytes'][0]&240==176 and e['bytes'][1]==1 and e['port']==1})
    expected=list(range(spec['channels']));value=dict(note_channels=channels,cc1_channels=cc1,passed=channels==expected and (spec['workload']!='slides' or cc1==expected))
    if not value['passed']:raise AssertionError(('Functional preflight failed',value))
    return value

def main():
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--case',choices=sorted(CASES),required=True);parser.add_argument('--output',required=True);parser.add_argument('--windows',type=int,default=4)
    parser.add_argument('--experimental-install');parser.add_argument('--performance-profile');parser.add_argument('--cost-parameters')
    a=parser.parse_args();spec=CASES[a.case];out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=False)
    emulator=Path(os.environ['MONOME_EMULATOR']).resolve();sys.path.insert(0,str(emulator/'src'))
    from automation.performance_profile import cost_profile_string,load_profile
    cost=load_profile(a.performance_profile)[1] if a.performance_profile else (cost_profile_string(json.loads(a.cost_parameters)) if a.cost_parameters else None)
    if cost and not a.experimental_install:parser.error('a profile requires --experimental-install')
    report=dict(schema_version=1,case=a.case,workload=spec['workload'],channels=spec['channels'],requested_window_seconds=spec['seconds'],lane='emulator-native',
                emulator=str(emulator),emulator_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=emulator,text=True).strip(),
                experimental_install=a.experimental_install,cost_profile=cost,performance_profile=a.performance_profile,source_identity=source_identity(REPO),
                thresholds=TIMING_THRESHOLDS,host_loadavg_before=os.getloadavg(),windows=[],passed=False)
    d=driver.Driver(out,experimental_install=a.experimental_install,cost_profile=cost);bounds=[]
    try:
        tempo=d.snapshot()['diagnostics'].get('tempo');report['tempo_bpm']=tempo
        if tempo!=90:raise AssertionError(('Emulator lane expects the norns default 90 BPM',tempo))
        build_project(d,spec['channels'],spec['workload'])
        if spec.get('fingerprint'):__import__('perf_overload').configure_fingerprint(d)
        d.tap(5,8);d.tap(1,1);d.led_values([(x,4) for x in range(1,17)],[15]*16)
        report['preflight']=preflight(d,spec)
        for window in range(1,a.windows+1):
            start=d.snapshot()['midi_count'];t0=time.monotonic_ns();d.tap(1,8)
            stimulus=run_window(EmulatorLane(d),spec) if (spec.get('render') or spec.get('loads')) else None
            if stimulus is None:d.elapse(spec['seconds'])
            d.tap(1,8);d.elapse(.3 if not spec.get('loads') else 1.5);end=d.snapshot()['midi_count']
            bounds.append((window,start,end,t0,time.monotonic_ns(),stimulus))
            if window<a.windows:d.elapse(2.0)
    except Exception as error:
        report['error']=repr(error)[:2000]
    finally:
        d.finish()
    rows=[json.loads(line) for line in (out/'native/native-events.jsonl').read_text().splitlines()] if (out/'native/native-events.jsonl').exists() else []
    emitted=[r for r in rows if 'index' in r and 'bytes' in r]
    step=15/90
    for window,start,end,t0,t1,stimulus in bounds:
        # Match the physical trace: multi-byte messages only, indexed within the window.
        events=[dict(e,index=i+1,native_index=e['index']) for i,e in enumerate(x for x in emitted if start<x['index']<=end and len(x['bytes'])>1)]
        recovery=None
        try:
            if spec.get('oracle')=='recovery':
                recovery=recovery_oracle(events,spec['channels'],step,spec['loads'][0][0])
                oracle={'timing':{'p99_ns':recovery['recovered_p99_ns'],'maximum_ns':recovery['recovered_max_ns']},'final_phase_error_ns':recovery['final_phase_error_ns'],
                        'service':{'p99_ns':0},'skipped_deadlines':0,'gates':dict(recovery['gates']),'passed':recovery['passed'],'note_ons':recovery['groups']*spec['channels'],
                        'messages':len(events),'steps':recovery['groups'],'slide_cycles_checked':None}
            else:oracle=dense_oracle(events,spec['channels'],spec['seconds'],step,spec['workload'])
            if stimulus is not None:
                oracle['gates']['stimulus_complete']=stimulus['complete'];oracle['passed']=oracle['passed'] and stimulus['complete']
            failure=None
        except AssertionError as error:oracle=None;failure=repr(error)[:2000]
        report['windows'].append(dict(window=window,stimulus=stimulus,recovery=recovery,first_index=start+1,last_index=end,host_window_ns=t1-t0,oracle=oracle,oracle_failure=failure,passed=bool(oracle and oracle['passed']),
                                      resources=dict(matron_cpu_percent=float('nan'))))
    report['host_loadavg_after']=os.getloadavg();report['passed']=bool(report['windows']) and all(w['passed'] for w in report['windows']) and 'error' not in report
    first=next((w for w in report['windows'] if w['oracle']),None);report['oracle']=first and first['oracle']
    (out/'performance.json').write_text(json.dumps(report,indent=2)+'\n');print(out/'performance.json')
    return 0 if 'error' not in report else 1

if __name__=='__main__':sys.exit(main())
