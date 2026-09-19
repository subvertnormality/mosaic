#!/usr/bin/env python3
"""Write a new Mosaic project/PSET pair with explicit NRPN encoding metadata."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--norns-source',type=Path,required=True)
parser.add_argument('--project',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--mode',choices=['standard','legacy-half'],required=True)
args=parser.parse_args()
source=args.project.resolve();target=args.output.resolve()
if source.suffix!='.ptn' or target.suffix!='.ptn':parser.error('Project and output must be .ptn files')
if target.exists() or target.with_suffix('.pset').exists():parser.error('Output project/PSET already exists; choose a new output')
if not target.parent.is_dir():parser.error('Output directory must already exist')
codec=Path(__file__).resolve().parents[1]/'lib/devices/nrpn_codec.lua'
script=r"""
local root,source,target,mode,codec_path,operation=table.unpack(arg)
local tab=dofile(root..'/lua/lib/tabutil.lua')
local saved=assert(tab.load(source))
assert(type(saved[1])=='string' and type(saved[2])=='table','Invalid Mosaic project')
if operation=='inspect' then io.write(saved[1]);return end
local codec=dofile(codec_path)
codec.convert(saved[2],mode)
saved[1]=assert(target:match('([^/]+)%.ptn$'))
assert(tab.save(saved,target)==nil,'Could not write converted project')
"""
with tempfile.TemporaryDirectory(prefix='mosaic-nrpn-convert-') as temporary:
    lua=Path(temporary)/'convert.lua';lua.write_text(script)
    command=['lua5.3',str(lua),str(args.norns_source.resolve()),str(source),str(target),args.mode,str(codec)]
    name=subprocess.check_output(command+['inspect'],text=True)
    if not name or Path(name).name!=name or name in ('.','..'):parser.error('Invalid project PSET name')
    pset=source.parent/(name+'.pset')
    pset_data=pset.read_bytes()
    # Reserve both new names exclusively. No existing file may be overwritten.
    with target.open('xb'):
        pass
    try:
        with target.with_suffix('.pset').open('xb') as stream:stream.write(pset_data)
    except BaseException:
        target.unlink();raise
    try:
        subprocess.run(command+['convert'],check=True)
    except BaseException:
        target.unlink();target.with_suffix('.pset').unlink();raise
print(str(target))
