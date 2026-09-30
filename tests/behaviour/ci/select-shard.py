#!/usr/bin/env python3
import argparse,json,os,re,sys
from pathlib import Path
BEHAVIOUR=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BEHAVIOUR))
import suite

TIMINGS=Path(__file__).with_name('shard-durations.json')
UNKNOWN_MS=(60000,60000)

def partition(ids,count,weights,shard_zero_overhead_ms=0,sequential=False):
    """Greedily balance two single-worker lanes, in integer ms: concurrent lanes
    by the slower lane, sequential lanes (run one after the other) by their sum.

    Historical durations predict scheduling cost, never acceptance. New cases
    receive a fixed one-minute estimate in both lanes and are always selected.
    Stale timing entries do not introduce cases into the current registry.
    """
    if type(count) is not int or count<1:raise ValueError('invalid shard count')
    if len(ids)!=len(set(ids)):raise ValueError('duplicate case ID')
    if type(shard_zero_overhead_ms) is not int or shard_zero_overhead_ms<0:
        raise ValueError('invalid shard-zero overhead')
    if not isinstance(weights,dict):raise ValueError('invalid duration map')
    for pair in weights.values():
        if (not isinstance(pair,(list,tuple)) or len(pair)!=2 or
                any(type(n) is not int or n<0 for n in pair) or not any(pair)):
            raise ValueError('durations must be two nonnegative integer milliseconds, not both zero')
    shards=[[] for _ in range(count)]
    loads=[[shard_zero_overhead_ms,shard_zero_overhead_ms]]+[[0,0] for _ in range(count-1)]
    size=(lambda pair:sum(pair)) if sequential else (lambda pair:max(pair))
    for case in sorted(ids,key=lambda c:(-size(weights.get(c,UNKNOWN_MS)),c)):
        pair=weights.get(case,UNKNOWN_MS)
        if sequential:
            index=min(range(count),key=lambda i:(sum(loads[i])+sum(pair),i))
        else:
            index=min(range(count),key=lambda i:(max(loads[i][lane]+pair[lane] for lane in range(2)),
                                                 sum(loads[i]),i))
        shards[index].append(case)
        for lane in range(2):loads[index][lane]+=pair[lane]
    return [sorted(group) for group in shards]

def timings():
    data=json.loads(TIMINGS.read_text())
    if data.get('schema_version')!=1 or data.get('lanes')!=['real-time','controlled-experimental']:
        raise ValueError('unsupported shard duration schema/lanes')
    return data['cases_ms'],data['shard_zero_overhead_ms']

def select(profile,index,count,sequential=False):
    if type(count) is not int or type(index) is not int or count < 1 or index < 0 or index >= count:
        raise ValueError('shard index must be in [0, count)')
    ids=sorted(case for case in suite.case_registry()
               if suite.CASE_PROFILE.get(case,'base-midi') == profile)
    if profile=='base-midi' and count>1:
        weights,overhead=timings()
        return partition(ids,count,weights,overhead,sequential)[index]
    return ids[index::count]

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--profile',required=True)
    p.add_argument('--index',type=int,default=0)
    p.add_argument('--count',type=int,default=1)
    p.add_argument('--json',action='store_true')
    p.add_argument('--sequential',action='store_true',help='balance for lanes run one after the other')
    a=p.parse_args()
    ids=select(a.profile,a.index,a.count,a.sequential)
    if not ids:p.error('empty shard')
    if a.json:print(json.dumps(ids))
    else:print('^(?:'+'|'.join(re.escape(case) for case in ids)+')$')
if __name__=='__main__':main()
