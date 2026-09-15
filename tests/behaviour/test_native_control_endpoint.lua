local root=arg[1]
package.path=root..'/lua/?.lua;'..root..'/lua/core/?.lua;'..root..'/lua/lib/?.lua;'..package.path
util=require('util');controlspec=require('controlspec');norns={pmap={data={}}}
local Control=require('params/control')
for _,reverse in ipairs({false,true}) do
  local c=Control.new('test','Test',controlspec.new(0,28,'lin',1,reverse and 28 or 0,'',1/28))
  local outputs={};c.action=function(value)outputs[#outputs+1]=value end
  for i=1,28 do c:delta(reverse and -1 or 1) end
  assert(#outputs==28)
  local endpoint=reverse and 0 or 28
  assert(c:get()==endpoint)
  c:delta(reverse and -1 or 1)
  assert(#outputs==29 and outputs[29]==endpoint,'Native endpoint callback assumption changed')
end
print('PASS pinned unmodified norns Control: 1/28 normalized increments emit one repeated endpoint callback on first saturated delta')
