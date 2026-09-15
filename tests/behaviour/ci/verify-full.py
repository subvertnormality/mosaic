#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
BEHAVIOUR=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BEHAVIOUR))
import suite

def load_report(path):
    path=Path(path)
    effective=path.with_name('suite-effective.json')
    if effective.exists():path=effective
    data=json.loads(path.read_text())
    if data.get('status')!='finished' or not data.get('passed'):
        raise ValueError(f'{path}: suite did not pass')
    return path,data

def verify(paths,output):
    loaded=[load_report(p) for p in paths]
    registry=suite.case_registry()
    profiles={'base-midi','midi-modulation','nb-audio','crow-jf'}
    jobs,_=suite.plan_jobs(sorted(registry),suite.LANES,profiles,
        suite.controlled_only_cases(),real_time_only=suite.real_time_only_cases())
    expected=set(jobs);actual={};identities=set();fast=[];startup=[]
    for path,report in loaded:
        ident=report['identity']
        identities.add((ident['mosaic']['revision'],ident['mosaic']['tree_sha256'],
                        ident['emulator']['revision'],ident['norns_source']['lua_tree_sha256']))
        summary=report['summary']
        if not summary.get('sources_stable'):raise ValueError(f'{path}: sources changed')
        if summary.get('required_not_run'):raise ValueError(f'{path}: required cases not run')
        if summary.get('load_sensitive'):raise ValueError(f'{path}: behavior failure recovered only on retry')
        startup.extend(summary.get('startup_retries',[]))
        layers=report.get('layers',{})
        if layers:
            rows=[r for items in layers.values() for r in (items if isinstance(items,list) else [items])]
            failed=[r.get('name') for r in rows if r.get('passed') is not True]
            if failed:raise ValueError(f'{path}: fast-layer failures or omissions: {failed}')
            fast.append(str(path))
        for row in report.get('cases',[]):
            key=(row['case'],row['lane'],row['profile'])
            if key in actual:raise ValueError(f'duplicate case/lane/profile: {key}')
            if row.get('passed') is not True:raise ValueError(f'{path}: failed case {key}')
            actual[key]=str(path)
    if len(identities)!=1:raise ValueError('suite jobs used different source or runtime identities')
    if len(fast)!=1:raise ValueError(f'fast layers must run exactly once, ran in {len(fast)} reports')
    missing=sorted(expected-set(actual));extra=sorted(set(actual)-expected)
    if missing or extra:raise ValueError(f'coverage mismatch: missing={missing[:20]} extra={extra[:20]}')
    result={'complete_behaviour_run':True,'registered_cases':len(registry),
            'applicable_case_lane_runs':len(expected),'reports':len(loaded),
            'startup_retries':startup,'identity':list(identities)[0]}
    Path(output).write_text(json.dumps(result,indent=2)+'\n')
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('reports',nargs='+');a=p.parse_args()
    result=verify(a.reports,a.output);print(json.dumps(result))
if __name__=='__main__':main()
