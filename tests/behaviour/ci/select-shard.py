#!/usr/bin/env python3
import argparse,json,os,re,sys
from pathlib import Path
BEHAVIOUR=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BEHAVIOUR))
import suite

def select(profile,index,count):
    if count < 1 or index < 0 or index >= count:
        raise ValueError('shard index must be in [0, count)')
    ids=sorted(case for case in suite.case_registry()
               if suite.CASE_PROFILE.get(case,'base-midi') == profile)
    return ids[index::count]

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--profile',required=True)
    p.add_argument('--index',type=int,default=0)
    p.add_argument('--count',type=int,default=1)
    p.add_argument('--json',action='store_true')
    a=p.parse_args()
    ids=select(a.profile,a.index,a.count)
    if not ids:p.error('empty shard')
    if a.json:print(json.dumps(ids))
    else:print('^(?:'+'|'.join(re.escape(case) for case in ids)+')$')
if __name__=='__main__':main()
