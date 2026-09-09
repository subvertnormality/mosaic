"""Characterise historical bytes using pinned norns Lua and extracted C serializer.
This is an integration boundary test, not full native workflow acceptance.
Usage: python3 THIS NORN_SOURCE ARTIFACT_DIRECTORY
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

norns, out = map(Path, sys.argv[1:])
out.mkdir(parents=True, exist_ok=False)
weaver = (norns / 'matron/src/weaver.c').read_text()
start = weaver.rindex('int _midi_send(lua_State *l) {')
end = weaver.index('\n}', start) + 2
serializer = weaver[start:end]
assert 'data[i - 1] = lua_tointeger(l, -1);' in serializer
prefix = r"""
#include <stdint.h>
#include <stdlib.h>
#include <lua.h>
#include <lauxlib.h>
struct dev_midi { int unused; };
static uint8_t captured[3];
static size_t captured_n;
static void dev_midi_send(struct dev_midi *md, uint8_t *data, size_t n) {
  (void)md; captured_n=n;
  for (size_t i=0;i<n && i<3;i++) captured[i]=data[i];
}
#define lua_check_num_args(n) if(lua_gettop(l)!=(n)) return luaL_error(l,"argument count")
"""
suffix = r"""
static int capture(lua_State *l) {
  lua_pushlightuserdata(l, captured);
  lua_insert(l, 1);
  _midi_send(l);
  lua_settop(l, 0);
  lua_createtable(l, captured_n, 0);
  for(size_t i=0;i<captured_n;i++) {
    lua_pushinteger(l, captured[i]); lua_rawseti(l, -2, i+1);
  }
  return 1;
}
int luaopen_nrpn_serializer(lua_State *l) {
  lua_pushcfunction(l, capture); return 1;
}
"""
(out/'serializer.c').write_text(prefix+serializer+suffix)
flags=subprocess.check_output(['pkg-config','--cflags','--libs','lua5.3'],text=True).split()
subprocess.run(['cc','-shared','-fPIC',str(out/'serializer.c'),'-o',str(out/'nrpn_serializer.so'),*flags],check=True)
script=r"""
local root,out=arg[1],arg[2]
package.path=root..'/lua/core/?.lua;'..root..'/lua/lib/?.lua;'..package.path
package.cpath=out..'/?.so;'..package.cpath
_norns={midi={}} -- registration-only host table; serialization below uses real code
local midi=require('midi')
local capture=require('nrpn_serializer')
local boundary={[0]=0,[1]=0,[126]=63,[127]=0,[128]=0,[129]=0,[16383]=0}
for value=0,16383 do
  local old_lsb=(value%128)/2
  local packet=capture(midi.to_data{type='cc',cc=38,val=old_lsb,ch=16})
  -- Independent parity oracle: Lua5.3 cannot convert fractional numbers to integers.
  local expected=value%2==0 and (value%128)/2 or 0
  assert(#packet==3 and packet[1]==191 and packet[2]==38 and packet[3]==expected,
    'legacy conversion changed at '..value)
  if boundary[value]~=nil then assert(packet[3]==boundary[value]) end
  local standard=capture(midi.to_data{type='cc',cc=38,val=value%128,ch=16})
  assert(standard[3]==value%128)
end
print('PASS 16384 historical and 16384 standard low-byte conversions; odd historical values serialize to zero')
"""
(out/'probe.lua').write_text(script)
result=subprocess.run(['lua5.3',str(out/'probe.lua'),str(norns),str(out)],capture_output=True,text=True)
(out/'stdout.log').write_text(result.stdout)
(out/'stderr.log').write_text(result.stderr)
receipt={'exit_code':result.returncode,'cases':32768,'scope':'official Lua plus extracted native serializer; no runtime/device acceptance',
 'sources':{str(norns/p):hashlib.sha256((norns/p).read_bytes()).hexdigest() for p in ['lua/core/midi.lua','matron/src/weaver.c']},
 'serializer_sha256':hashlib.sha256(serializer.encode()).hexdigest(), 'stdout':result.stdout,'stderr':result.stderr}
(out/'results.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
sys.exit(result.returncode)
